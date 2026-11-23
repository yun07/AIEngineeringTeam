# Operations Decisions

本檔案記錄與 AI Engineering Team 架構無關的操作層面決定，避免日後誤將工具層問題當作引擎缺陷處理。

---

## OD-001 — Zoo Code Orchestration Issue

- **Date:** 2026-11-23
- **Classification:** External Tooling / Zoo Code Orchestration
- **Status:** Recorded — No AI Engineering Team architecture change required.

### Decision

1. 重複生成完整報告、retry，以及重複傳送 context，屬於 **Zoo Code 自身的 operation / orchestration / tool-calling 問題**。
2. 這不是 AI Engineering Team 的 Python Workflow Engine defect。
3. **不得**為修理 Zoo Code 的問題而修改 AI Engineering Team 的核心架構、Workflow Engine 或 Agent 設計。
4. Zoo Code 應在自己的操作流程處理：
   - 正確使用 `attempt_completion`。
   - 確保 `result` 參數完整。
   - 避免無必要地重新生成完整報告。
   - Tool call 失敗時，只作有限次數的精簡 retry。
5. 除非日後有獨立證據證明 Python Workflow Engine 本身存在 defect，否則不要將這個問題列入 AI Engineering Team 的修復工作。

### Scope note

此決定只約束工具操作流程，不改變任何 runtime 行為、預算規則、Evidence Validator 或 Agent 權限。
