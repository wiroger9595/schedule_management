# Context 管理策略

## 降低 Context 消耗的方法

### 1. 精準指定檔案（避免大範圍探索）
```
❌ 耗 token: "找出所有跟 location 有關的程式碼"
✅ 省 token: "修改 server/app/services/here_service.py 的 validate_location 函數"
```

### 2. 用 /clear 分段工作
- 完成一個獨立功能後 → `/clear` 開新 session
- 下一個 session 開頭直接說: "我在做 XXX，請先讀 CLAUDE.md"

### 3. 引用 CLAUDE.md 代替重複解釋
```
❌ 耗 token: 每次重新解釋 "後端用 FastAPI，前端用 Flutter..."
✅ 省 token: CLAUDE.md 會自動載入，不需重述架構
```

### 4. Subagent 隔離大型搜尋
```
❌ 耗 token: 在主對話裡大量 grep/glob
✅ 省 token: 用 Explore subagent 搜尋，只把結果帶回主對話
```

### 5. 小任務 → 直接給檔案路徑
```
"修改 mobile/lib/widgets/chat_widget.dart 第 380 行的 onConfirm callback"
→ Claude 直接 Read 該檔，不需搜尋
```

## Session 開場白模板

### 修 Bug
```
請讀 CLAUDE.md。問題：[描述 bug]，在 [檔案路徑]，[錯誤訊息]。
```

### 新功能
```
請讀 CLAUDE.md。新需求：[功能描述]。
相關檔案：[列出 2-3 個檔案]。
```

### 架構問題
```
請讀 CLAUDE.md，然後用 Plan subagent 設計 [功能] 的實作方案。
```

## Context 壓縮觸發點
當對話接近 context 上限時（Claude 會提示），系統自動壓縮歷史。
此時最重要的決策/規則已存在：
- `CLAUDE.md` → 架構/規則
- `server/CLAUDE.md` → 後端細節
- `mobile/CLAUDE.md` → 前端細節
- `memory/` → 個人偏好/決策記錄

所以壓縮後仍可繼續工作，不會遺失關鍵資訊。
