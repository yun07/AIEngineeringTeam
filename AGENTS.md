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
