"""Pricing, reservations and actual usage accounting.

The manager holds no provider credentials and never talks to an API. It only
turns an estimated request into a reserved cost and a reported usage into USD.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from aiteam.cost.tokens import estimate_input_tokens
from aiteam.models import UsageRecord

DEFAULT_MAX_OUTPUT_TOKENS = 1200
DEFAULT_SAFETY_MARGIN_PERCENT = 10.0


class CostError(ValueError):
    """Raised when pricing or cost configuration is unusable."""


class UsageUnavailable(CostError):
    """Raised when a provider response has no usable usage data."""


class RequestTooLarge(CostError):
    """Raised when the estimated request cannot fit the configured window."""


@dataclass(frozen=True)
class CostEstimate:
    model: str
    estimated_input_tokens: int
    max_output_tokens: int
    reserved_usd: float


@dataclass
class RoleUsage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0


@dataclass
class CostManager:
    pricing: Mapping[str, Mapping[str, float]]
    budget_usd: float | None = None
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN_PERCENT
    max_context_tokens: int | None = None
    spent_usd: float = 0.0
    reserved_total_usd: float = 0.0
    uncertain_usd: float = 0.0
    usage_unavailable_count: int = 0
    overshoot: bool = False
    records: list[UsageRecord] = field(default_factory=list)
    by_role: dict[str, RoleUsage] = field(default_factory=dict)

    def prices_for(self, model: str) -> tuple[float, float]:
        entry = self.pricing.get(model)
        if not isinstance(entry, Mapping):
            raise CostError(
                f"no pricing entry for model {model!r}; refusing to guess a price"
            )
        try:
            return float(entry["input_per_mtok"]), float(entry["output_per_mtok"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CostError(f"pricing for model {model!r} is incomplete") from exc

    def estimate(
        self, *, model: str, system: str, messages: Sequence[Any], tools: Sequence[Any]
    ) -> CostEstimate:
        estimated_input = estimate_input_tokens(
            model=model, system=system, messages=messages, tools=tools
        )
        if (
            self.max_context_tokens is not None
            and estimated_input + self.max_output_tokens > self.max_context_tokens
        ):
            raise RequestTooLarge(
                "request_too_large: estimated input "
                f"{estimated_input} + max output {self.max_output_tokens} exceeds "
                f"max_context_tokens {self.max_context_tokens}"
            )
        price_in, price_out = self.prices_for(model)
        base = (
            estimated_input * price_in + self.max_output_tokens * price_out
        ) / 1_000_000
        reserved = base * (1 + self.safety_margin_percent / 100)
        return CostEstimate(
            model=model,
            estimated_input_tokens=estimated_input,
            max_output_tokens=self.max_output_tokens,
            reserved_usd=round(reserved, 6),
        )

    def validate_usage(self, usage: Any) -> tuple[int, int]:
        if usage is None:
            raise UsageUnavailable("provider returned no usage data")
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        if isinstance(input_tokens, bool) or not isinstance(input_tokens, int):
            raise UsageUnavailable("provider usage input_tokens is invalid")
        if isinstance(output_tokens, bool) or not isinstance(output_tokens, int):
            raise UsageUnavailable("provider usage output_tokens is invalid")
        if input_tokens <= 0:
            raise UsageUnavailable("provider usage input_tokens is missing or zero")
        if output_tokens < 0:
            raise UsageUnavailable("provider usage output_tokens is negative")
        return input_tokens, output_tokens

    def actual_usd(self, model: str, input_tokens: int, output_tokens: int) -> float:
        price_in, price_out = self.prices_for(model)
        return round(
            (input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6
        )

    def record(self, record: UsageRecord) -> None:
        self.records.append(record)
        self.spent_usd = round(self.spent_usd + record.usd, 6)
        bucket = self.by_role.setdefault(record.role, RoleUsage())
        bucket.calls += 1
        bucket.input_tokens += record.input_tokens
        bucket.output_tokens += record.output_tokens
        bucket.usd = round(bucket.usd + record.usd, 6)
        if self.budget_usd is not None and self.spent_usd > self.budget_usd:
            self.overshoot = True

    def mark_uncertain(self, reserved_usd: float) -> None:
        self.uncertain_usd = round(self.uncertain_usd + reserved_usd, 6)
        self.usage_unavailable_count += 1

    def remaining_usd(self) -> float | None:
        if self.budget_usd is None:
            return None
        if self.uncertain_usd > 0:
            return None
        return round(self.budget_usd - self.spent_usd, 6)

    def uncertainty_note(self) -> str:
        if self.usage_unavailable_count:
            return (
                "Accounting uncertainty: at least one call returned no usable "
                "usage data. Remaining budget is unknown until a human checks "
                "the provider dashboard."
            )
        return (
            "Accounting uncertainty: token counts are local estimates before "
            "each call and provider-reported usage afterwards. Provider billing "
            "may differ because of cached tokens, rounding, service tier or "
            "price changes."
        )
