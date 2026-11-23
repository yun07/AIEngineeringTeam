# AGENTS.md

本檔案係每次工作嘅簡短指引，唔係技術規格，亦唔應該包含完整架構或決策內容。
目標：減少不必要嘅 Input Tokens，同時保留足夠資訊，確保實作品質同架構一致性。

## Token-efficient Context Management

1. 每次新 Task 開始時，不要重新閱讀所有 Project Documents。先睇當前 Task 相關嘅程式碼、測試同設定。
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

## Git Workflow Rules

所有 Git 操作由 Zoo Code 負責執行，不需要用戶手動複製 Git 指令。

本節有兩套規則，適用範圍唔同，先睇清楚再執行：

- **一般程式碼、功能及 Milestone 工作**：遵守下面「逐次 Commit / Push 批准」規則。
- **文件修改（Document Change & Review Governance）**：屬明確例外。Zoo Code 可在獨立 review branch 完成必要檢查後直接 Commit 及 Push，無須逐次取得批准。
- **禁止未經批准 Commit / Push 的規則**：只適用於一般程式碼及 Milestone 工作，不適用於上述文件修改流程。任何情況下，未經 User 明確批准仍不得 Merge 到 `main` 或其他保護分支。

文件修改的完整流程見 [`AI_Engineering_Team.md`](AI_Engineering_Team.md) §4.8 及本檔案 Document Change & Review Governance 一節。

### 一般程式碼、功能及 Milestone 工作：逐次批准

每次完成一個 Milestone 或一組完整功能後：

1. 檢查 `git status`。
2. 執行相關測試。
3. 檢查 `git diff` 及 `git diff --check`。
4. 用繁體中文向用戶摘要修改內容。
5. 建議清晰的 Conventional Commit message。
6. 等待用戶批准後才執行 `git add` 及 `git commit`。
7. Commit 成功後，再向用戶確認是否執行 `git push`。
8. Push 必須獲得用戶明確批准。

禁止（只適用於一般程式碼、功能及 Milestone 工作；不適用於 Document Change & Review Governance 的文件修改流程）：

- 未經批准自動 Commit。
- 未經批准自動 Push。
- 將 `.env`、API keys、passwords 或其他 secrets 加入 Git。
- 使用 `git reset --hard`、`git clean -fd` 或強制 Push，除非用戶明確批准。
- 未經用戶明確批准 Merge 到 `main` 或其他保護分支。

如果 Git 指令失敗，先分析錯誤原因，不要自行修改 Git 設定或憑證。

## Document Change & Review Governance

規則來源：[`AI_Engineering_Team.md`](AI_Engineering_Team.md) §4.8 為唯一權威；本節只係執行提示。

角色：Zoo Code = Worker / Merge Executor（改文件、跑檢查、Git 操作，並在 User 明確批准後執行 Merge）；ChatGPT = Reviewer（直接檢查 GitHub 實際文件及 diff，不執行 Merge）；User = Approver / 唯一 Merge Approver（批准接受、Merge 及下一階段工作）。

1. 每次文件修改都在獨立 review branch 進行，不得直接改 `main`。
2. 完成後先跑必要檢查（最少 `git diff --check`），再直接 commit 及 push review branch。此步驟屬文件修改既定流程，不需額外逐次批准；Merge 仍須 User 明確批准。
3. 交 ChatGPT 獨立審查；不得要求對方只信 Zoo Code 摘要。有問題由 Zoo Code 修正，再交審查。
4. User 係唯一 Merge Approver；只有 User 明確批准後，Zoo Code（Merge Executor）才可執行 Merge 到 `main`。Merge 批准不代表批准下一階段工作。
5. 不得把未批准的修改或既有未提交改動帶入 review branch 或 Merge。Commit 只包含本次 scope 內的文件。
6. 如果有與本次 scope 無關的未提交改動，必須保持原狀，並在報告中明確確認未被觸碰。
7. 完成後只回報：review branch 名、commit hash、修改文件名稱、`git diff --check` 結果、`git status --short`、未觸碰範圍確認。

## 文件角色速查

| 文件 | 幾時用 |
|---|---|
| `AGENTS.md` | 每次工作先睇，作為讀取紀律 |
| `README.md` | 需要了解項目概況時 |
| `plans/phase1-architecture-plan.md` | 實作前只查與當前 Task 有關嘅章節 |
| `AI_Engineering_Team.md` | 涉及原則或重大決策時 |
| `plans/oss-architecture-research.md`、`plans/architecture-decision-review.md` | 已封存，預設不讀 |

## 建議讀取次序

1. 當前 Task 相關嘅程式碼、測試、設定檔
2. `AGENTS.md`
3. `plans/phase1-architecture-plan.md` 相關章節
4. 有需要才查 `AI_Engineering_Team.md`

不要為了「熟習成個 Project」而一次過讀完所有文件。
