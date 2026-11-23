# AGENTS.md

本檔案係每次工作嘅簡短指引，唔係技術規格，亦唔應該包含完整架構或決策內容。
目標：減少不必要嘅 Input Tokens，同時保留足夠資訊，確保實作品質同架構一致性。

## Communication Language

1. ChatGPT 同 Zoo Code 對 Human 嘅所有對話回覆、狀態更新、提問、解釋、handoff 同報告，一律使用繁體中文（粵語）。
2. 英文技術詞彙、程式碼、識別碼、檔名、指令同 API 名稱可以保留英文。
3. 本規則不要求將 source code、technical specifications 或 project documentation 翻譯成粵語。

## Mandatory Session Bootstrap（新 Session）

1. 當 Human 只提供 `AGENTS.md` 嘅公開 GitHub 連結，必須將該連結視為本 Project 嘅入口點，並自動啟動 Session Bootstrap 同 Alignment 流程。
2. 必須由同一個 repository 同 branch context 自動定位並讀取 `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md`。
3. 必須依 Protocol 嘅強制 bootstrap 閱讀次序：
   - `AGENTS.md`
   - `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` 嘅 configuration 及 bootstrap 指示
   - `README.md`
   - `AI_Engineering_Team.md`
   - 按當前 task 選讀相關 Layer 2 文件
4. ChatGPT 必須直接讀取公開可存取嘅 repository 文件。文件已可存取時，不得要求 Human 貼上或上載。
5. 如果無法讀取所需文件，必須指出實際缺失嘅文件名稱及存取限制，不得靜默跳過或假設內容。
6. Bootstrap 完成後，必須報告精簡 alignment status，涵蓋：
   - 作為證據嘅 repository、branch 同 commit
   - 已成功讀取嘅文件，以及任何缺失文件
   - 當前 project / milestone / task 狀態
   - 已確認決策及未解決、需要 Human 決定嘅事項
   - Work authorization 狀態
7. Bootstrap 同 Alignment 屬只讀程序，不代表授權 implementation、code execution、file modification、commit、merge 或 M4。
8. 與 Human 溝通一律使用繁體中文（粵語）；英文技術詞彙、code、identifiers、filenames、commands、API names 可以保留英文。

## Token-efficient Context Management

1. 新 Session 先完成 Protocol §0.3 bootstrap。同一 session 內開始新 Task 時，不要重新閱讀所有 Project Documents；先睇當前 Task 相關嘅程式碼、測試同設定。
2. 本檔案只放工作指引；完整技術規格、架構細節同決策紀錄唔應該搬入嚟。
3. `README.md` 只用嚟了解 Project 概況；一般 Coding Task 不需要重讀整份 README。
4. `plans/phase1-architecture-plan.md` 只讀與當前 Task 有關嘅章節，不要每次讀完整文件。
5. `AI_Engineering_Team.md` 只在涉及核心架構、設計原則或重大決策時，才查閱相關部分。
6. 以下文件屬歷史研究及決策紀錄，預設不讀取：
   - `plans/oss-architecture-research.md`
   - `plans/architecture-decision-review.md`

   只有用戶明確要求研究、比較或追查歷史決策時，才讀取。
7. 優先讀取當前 Task 直接相關嘅程式碼、測試及設定檔。
8. 如果某份文件已經在當前 Task 嘅 Context 中，而且冇證據顯示內容已改變，不要無故重新讀取。
9. 不要為咗熟悉整個 Project 而讀取無關檔案。
10. 如果發現真正影響實作嘅文件衝突，只指出相關文件及章節，不要自動重新閱讀所有文件。
11. 不要每次工作都重新輸出完整 Project Summary。
12. 完成 Task 後，只用繁體中文簡潔報告：
    - 修改了甚麼
    - 執行了甚麼測試
    - 測試結果
    - 尚未解決的問題

## Development Workflow（Human + ChatGPT + Zoo Code）

權威來源：文件修改治理以 [`AI_Engineering_Team.md`](AI_Engineering_Team.md) §4.8 為準；alignment 流程以 [`UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md`](UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md) 為準。本節只定義日常操作，唔重複完整規則。流程總覽、改善前後對照同限制見 [`README.md`](README.md) §6.2–6.4。

### 1. 改動分類與授權

| 類別 | 例子 | Review branch | Commit / Push | Merge |
|---|---|---|---|---|
| Documentation | AGENTS、README、Protocol、Charter、plan | 必須 | 完成檢查後可直接 commit/push，不需逐次批准 | 只可由 Human 批准 |
| Code / Milestone | Python engine、tests、config | 必須 | 每步須 Human 明確批准 | 只可由 Human 批准 |

- 批准文件修改不等於批准 code、測試、commit、push、merge 或下一個 milestone。
- 任何情況下不得直接改 `main`、force push、`reset --hard`，或 clean 未批准改動。
- 不得將 `.env`、API keys、passwords 或其他 secrets 加入 Git。

### 2. Branch 與 scope

1. 以最新 `origin/main` 建立獨立 review branch（可用獨立 worktree）。
2. 一個 branch 只做一個 scope；commit 只包含該 scope 檔案。
3. 保留 working tree 內其他未提交改動，不得 stage、覆蓋、reset 或帶入 merge。
4. Review branch 一經提交審查，不得重寫歷史；有修正就加新 commit。

### 3. Preflight validation（提交前）

Preflight 係 Zoo 喺 commit 前執行嘅檢查，唔係 Git hook。今次未安裝 hook，亦未設定 CI；如需自動觸發，要另行授權。

交付前只跑一個 command：

```text
python scripts/preflight.py
```

在 `ai-team` conda 環境執行（先 `conda activate ai-team`）。

它會檢查：

- 目前 branch、HEAD、`origin/main` 同 merge/rebase 狀態；
- `git diff --check`；
- 相對 `origin/main` 嘅修改檔案清單；
- 5 份 active docs 嘅過時 Status header、舊 paste 指令、Protocol Part 1 placeholder；
- Protocol／AGENTS bootstrap 入口次序。

PASS 只輸出簡短摘要；FAIL 會逐項列出原因，唔需要另外貼多條 git 命令。Commit 後用 `git diff --stat origin/main...HEAD` 核對 commit 範圍。

Code 改動另加 `python -m pytest`，報告實際指令、exit code、通過/失敗數；UI 改動附 screenshot 或 recording。

### 4. 證據包（Evidence package）

Review 只接受可驗證證據：

- `git diff`（Reviewer 直接讀 GitHub branch/diff）
- 檢查指令同實際輸出
- 測試結果（code）或 screenshot/log（UI）
- 未解決問題清單

Worker 回報只需：branch、commit hash、files、checks、open issues。唔需要重貼完整 diff 或長篇報告。

### 5. 獨立審查（Independent Review）

- ChatGPT 直接讀 GitHub review branch 嘅實際文件同 diff；Zoo 嘅摘要唔係證據。
- Reviewer 要核對：scope 有冇超出授權、文件有冇矛盾、未批准建議有冇被寫成已批准規則、測試/證據是否對應。
- 有問題由 Zoo 修正並加 commit；Reviewer 唔執行 merge。
- 同一 scope 只做必要 review rounds；每次修正要有新證據，唔好重複全文審查。

### 6. Human Approval

- Human 係唯一 Merge Approver；只有明確批准後才可 merge。
- Merge 批准只覆蓋該次 merge，不代表批准下一個 milestone、M4 或 implementation。
- Human approval 永不因自動化、CI 或 review 通過而省略。

### 7. 效率規則

- 同一 session 內不要重讀未改動文件；不要重複貼上同一 diff 或報告。
- 不要為同一 scope 建立多個重複 branch 或重複 commit。
- 冇新證據時不要重試或重新生成同一報告；失敗就報告原因同下一步。
- Zoo Code orchestration 嘅重複報告/context 浪費按 OD-001 處理，唔係 Workflow Engine 問題。

## 文件角色速查

| 文件 | 幾時用 |
|---|---|
| `AGENTS.md` | 每次工作先睇，作為讀取紀律 |
| `README.md` | 需要了解項目概況時 |
| `plans/phase1-architecture-plan.md` | 實作前只查與當前 Task 有關嘅章節 |
| `AI_Engineering_Team.md` | 涉及原則或重大決策時 |
| `plans/oss-architecture-research.md`、`plans/architecture-decision-review.md` | 已封存，預設不讀 |

## 建議讀取次序

- 新 Session：依 Protocol §0.3 bootstrap（`AGENTS.md` → Protocol → `README.md` → `AI_Engineering_Team.md` → Layer 2）。
- 同一 session 內的新 Task：先讀當前 Task 相關嘅程式碼、測試、設定；需要時才查 plan 相關章節或 Charter。
- 不要為了「熟習成個 Project」而一次過讀完所有文件，亦不要重讀未改動文件。
