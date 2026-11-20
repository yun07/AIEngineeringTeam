"""Budget reservation around every provider call.

Budget authority lives here, not in an agent. A call is allowed only when

    actual_spend + reserved_in_flight + reserved_next <= budget

A provider error or missing usage data keeps the reservation unresolved, so
the exposure stays visible instead of turning into a silent zero.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from aiteam.cost.manager import (
    CostEstimate,
    CostManager,
    RequestTooLarge,
    UsageUnavailable,
)
from aiteam.models import UsageRecord, utc_now_iso


class BudgetError(RuntimeError):
    """Raised when a call must not proceed or accounting became uncertain."""

    def __init__(
        self,
        reason: str,
        message: str,
        *,
        estimated_usd: float | None = None,
        remaining_usd: float | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.estimated_usd = estimated_usd
        self.remaining_usd = remaining_usd


@dataclass
class Reservation:
    id: str
    model: str
    role: str
    task_id: str
    reserved_usd: float
    state: str = "in_flight"  # in_flight | settled | uncertain


@dataclass
class BudgetGuard:
    manager: CostManager
    budget_usd: float | None
    store: Any
    run_id: str
    event_sink: Callable[[str, dict[str, Any]], None]
    reservations: dict[str, Reservation] = field(default_factory=dict)
    accounting_blocked: bool = False

    def in_flight_usd(self) -> float:
        return round(
            sum(
                reservation.reserved_usd
                for reservation in self.reservations.values()
                if reservation.state in ("in_flight", "uncertain")
            ),
            6,
        )

    def scope(self, *, task_id: str, role: str, model: str) -> ScopedCostGuard:
        return ScopedCostGuard(
            guard=self, task_id=task_id, role=role, model=model
        )


@dataclass
class ScopedCostGuard:
    guard: BudgetGuard
    task_id: str
    role: str
    model: str

    def before_call(
        self,
        *,
        system: str,
        messages: Sequence[Any],
        tools: Sequence[Any] = (),
    ) -> str:
        if self.guard.accounting_blocked:
            raise BudgetError(
                "accounting_blocked",
                (
                    "accounting_blocked: a previous call left unresolved cost "
                    "exposure; further calls are refused until a human reviews "
                    "the provider usage"
                ),
                estimated_usd=None,
                remaining_usd=None,
            )

        manager = self.guard.manager
        try:
            estimate: CostEstimate = manager.estimate(
                model=self.model, system=system, messages=messages, tools=tools
            )
        except RequestTooLarge as exc:
            self.guard.event_sink(
                "request_rejected",
                {
                    "task": self.task_id,
                    "role": self.role,
                    "model": self.model,
                    "reason": str(exc),
                },
            )
            raise BudgetError("request_too_large", str(exc)) from None
        in_flight = self.guard.in_flight_usd()
        budget = self.guard.budget_usd
        if (
            budget is not None
            and manager.spent_usd + in_flight + estimate.reserved_usd
            > budget + 1e-9
        ):
            remaining = max(0.0, budget - manager.spent_usd - in_flight)
            self.guard.event_sink(
                "budget_stopped",
                {
                    "task": self.task_id,
                    "role": self.role,
                    "model": self.model,
                    "estimated_input_tokens": estimate.estimated_input_tokens,
                    "max_output_tokens": estimate.max_output_tokens,
                    "reserved_usd": estimate.reserved_usd,
                    "spent_usd": manager.spent_usd,
                    "in_flight_usd": in_flight,
                    "budget_usd": budget,
                    "remaining_usd": round(remaining, 6),
                },
            )
            raise BudgetError(
                "budget_exceeded",
                (
                    f"budget_exceeded: spent {manager.spent_usd:.6f} + "
                    f"in-flight {in_flight:.6f} + reserved "
                    f"{estimate.reserved_usd:.6f} exceeds budget "
                    f"{budget:.6f}"
                ),
                estimated_usd=estimate.reserved_usd,
                remaining_usd=round(remaining, 6),
            )

        reservation = Reservation(
            id=uuid.uuid4().hex[:12],
            model=self.model,
            role=self.role,
            task_id=self.task_id,
            reserved_usd=estimate.reserved_usd,
        )
        self.guard.reservations[reservation.id] = reservation
        manager.reserved_total_usd = round(
            manager.reserved_total_usd + estimate.reserved_usd, 6
        )
        self.guard.event_sink(
            "budget_reserved",
            {
                "reservation_id": reservation.id,
                "task": self.task_id,
                "role": self.role,
                "model": self.model,
                "estimated_input_tokens": estimate.estimated_input_tokens,
                "max_output_tokens": estimate.max_output_tokens,
                "reserved_usd": estimate.reserved_usd,
            },
        )
        return reservation.id

    def settle_success(self, reservation_id: str, usage: Any) -> UsageRecord | None:
        manager = self.guard.manager
        reservation = self._reservation(reservation_id)
        try:
            input_tokens, output_tokens = manager.validate_usage(usage)
        except UsageUnavailable as exc:
            self._mark_uncertain(reservation, str(exc))
            raise BudgetError(
                "usage_unavailable",
                f"usage_unavailable: {exc}",
                estimated_usd=reservation.reserved_usd,
            ) from None

        usd = manager.actual_usd(reservation.model, input_tokens, output_tokens)
        record = UsageRecord(
            ts=utc_now_iso(),
            run_id=self.guard.run_id,
            task_id=reservation.task_id,
            role=reservation.role,
            model=reservation.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            usd=usd,
        )
        self.guard.store.append_usage(record)
        manager.record(record)
        reservation.state = "settled"
        self.guard.event_sink(
            "usage_recorded",
            {
                "reservation_id": reservation.id,
                "task": reservation.task_id,
                "role": reservation.role,
                "model": reservation.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "usd": usd,
                "spent_usd": manager.spent_usd,
                "budget_usd": self.guard.budget_usd,
            },
        )

        if (
            self.guard.budget_usd is not None
            and manager.spent_usd > self.guard.budget_usd + 1e-9
        ):
            self.guard.accounting_blocked = True
            self.guard.event_sink(
                "budget_overshoot",
                {
                    "task": reservation.task_id,
                    "role": reservation.role,
                    "spent_usd": manager.spent_usd,
                    "budget_usd": self.guard.budget_usd,
                },
            )
            raise BudgetError(
                "budget_overshoot",
                (
                    f"budget_overshoot: actual spend {manager.spent_usd:.6f} "
                    f"exceeds budget {self.guard.budget_usd:.6f}"
                ),
                estimated_usd=reservation.reserved_usd,
                remaining_usd=0.0,
            )
        return record

    def settle_failure(self, reservation_id: str, reason: str = "provider_error") -> None:
        """Keep the reservation unresolved: the exposure is unknown, not zero."""
        reservation = self._reservation(reservation_id)
        self._mark_uncertain(reservation, reason)

    def _mark_uncertain(self, reservation: Reservation, reason: str) -> None:
        if reservation.state == "uncertain":
            return
        reservation.state = "uncertain"
        self.guard.accounting_blocked = True
        self.guard.manager.mark_uncertain(reservation.reserved_usd)
        self.guard.event_sink(
            "usage_unavailable",
            {
                "reservation_id": reservation.id,
                "task": reservation.task_id,
                "role": reservation.role,
                "model": reservation.model,
                "reserved_usd": reservation.reserved_usd,
                "reason": reason,
                "uncertain_usd": self.guard.manager.uncertain_usd,
            },
        )

    def _reservation(self, reservation_id: str) -> Reservation:
        try:
            reservation = self.guard.reservations[reservation_id]
        except KeyError as exc:
            raise RuntimeError(
                f"unknown reservation {reservation_id!r}"
            ) from exc
        if reservation.state != "in_flight":
            raise RuntimeError(
                f"reservation {reservation_id!r} is already {reservation.state}"
            )
        return reservation
