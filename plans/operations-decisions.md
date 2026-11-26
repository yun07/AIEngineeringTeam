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

---

## OD-002 — Workflow Optimization and Minimum Round Trips

- **Date:** 2026-11-24
- **Classification:** Collaboration Workflow / Orchestration
- **Status:** Human approved — 常設規則已寫入 [`AGENTS.md`](../AGENTS.md) §9。
- **Authority:** 只屬 operation 同 documentation 規則；不改變 Workflow Engine、Agent 架構、QA 獨立性、evidence validation、retry 規則或 Cost Guard。

### Decision

1. 角色分工：
   - **Human**：Project Owner，唯一 decision-maker 及 Merge Approver。
   - **ChatGPT**：Workflow Improvement Owner / Documentation Steward，主動識別工作流低效、同 Human 討論 evidence 與取捨，並在取得同意及授權後負責文件更新。
   - **Zoo Code**：執行已批准的工作包，提供可驗證 evidence，不擴大 scope。
2. 工作流採用四項原則：**One-pass Execution**、**One-pass Output**、**Minimum Task Fragmentation**、**Minimum Round Trips**。
3. 以完整 task package 取代不必要的串行小任務；只有真實 approval gate、足以改變設計的未知、或 review 邊界才分拆。
4. 追加讀檔或測試，只可在現有 evidence 不足，或有真實風險／approval gate 要求時進行。
5. 若 ChatGPT 具備 repository 寫入權限，由 ChatGPT 直接更新文件；Zoo Code 為 fallback。
6. 詳細常設規則以 [`AGENTS.md`](../AGENTS.md) §9 為準。本檔只記錄決定、理據同範圍，不重複條文。

### Rationale

- Token Efficiency Review（2026-11-24，read-only audit）顯示大部分可避免開銷來自 orchestration：重複 full-suite 執行、raw JUnit 輸出、無效的輸出讀取、重疊讀檔、重複報告，以及每個 turn 的固定開銷。此判斷屬基於可見 session 與 tool-call 記錄的定性評估，並非實測 token telemetry。屬工具層問題，同 engine 無關。
- 以「一次做完整、一次講清楚」方式協作，可減少 round trip，同時保留 independent review、evidence 同 Human 決定權。

### Audit evidence（保留為 evidence，不是硬性規則）

以下係該次 Token Efficiency Review 的 findings，只作日後參考與再評估依據；除 [`AGENTS.md`](../AGENTS.md) §9 已寫明的原則外，不構成逐條必須遵守的規則。

| ID | 觀察 |
|---|---|
| F1 | 完整 JUnit XML（41.3KB）被寫入 context，只因輸出過濾不足 |
| F2 | 同一 commit 重跑 full suite，只為取得 exit code |
| F3 | Full suite 次數同 change-set 的比例需要受控 |
| F4 | `git commit -m` 引號錯誤，導致一次失敗重試 |
| F5 | 連續 4 次無效的測試輸出讀取（findstr 大小寫、summary 行、管道 exit code） |
| F6 | 尋找 Python 環境用了 4 次呼叫 |
| F7 | `findstr` 不支援 regex anchor，導致一次失敗 |
| F8 | `workflow.py` 以 7 段重疊 slice 讀取 |
| F9 | 每個 turn 重複注入 `environment_details` 會產生額外 context 開銷；能否由 client 設定關閉或減少，仍屬 `UNVERIFIED` |
| F10 | 兩份報告重複同一批 evidence |
| F11 | Preflight 在無內容差異時重複執行 |

### Scope note

本決定不授權任何 code、engine、client settings 或 automation 改動，亦不改變 preflight、review 同 merge approval 要求。

---

## OD-003 — Collaboration Workflow v2

- **Date:** 2026-11-26
- **Classification:** Collaboration Workflow / Orchestration
- **Status:** Human approved — 詳細常設規則寫入 [`AGENTS.md`](../AGENTS.md) §9；本條只記錄決定、理據同範圍。
- **Authority:** 只屬 operation / documentation 規則。不改變 Python Workflow Engine、runtime code、tests、client settings、automation、dependency 或產品架構，亦不放寬 Human approval、independent review 或 independent QA。

### Decision

1. 三方角色沿用並收緊：Human 保留 commit / push / merge 批准權；ChatGPT 負責優化流程、準備 coherent work package、獨立審閱實際改動同 evidence、維持文件一致；Zoo Code 負責執行已批准 work package、做一次 self-review 同 refinement、提供精簡 evidence-based 報告。
2. 原則維持 One-pass Execution、One-pass Output、Minimum Round Trips，並明確以一個 coherent work package（單一 review 邊界）取代連串小任務。
3. 只向 Human 提出 material decision、真正 ambiguity、風險或必要授權；已議定細節由 executor 在授權範圍內處理。
4. 減少重複讀檔、報告、dispatch 同無必要 rerun，但不得因此降低 independent QA、independent review 或 evidence 品質。
5. 複雜工作（多步驟、多檔案、跨模組）執行一次 `Execute → Self-review → Refine → Final report` 循環；small / low-risk 工作按比例檢查，不設儀式。Self-review 唔可以取代 independent QA 或 reviewer 的獨立檢視。

### Rationale

- OD-002 只覆蓋 one-pass 同 round-trip 紀律；實際協作仍出現 work package 切得過碎、executor 無正式自檢步驟、報告重複等問題。
- 將「完整 work package + 一次自檢 + 精簡報告」寫成常設規則，可減少來回，同時保留全部驗證關卡。

### Scope note

本決定不授權任何 code、engine、runtime、test、client settings 或 automation 改動，亦不改變 preflight、independent review、independent QA 同 merge approval 要求。詳細條文只保留在 [`AGENTS.md`](../AGENTS.md) §9，避免重複。
