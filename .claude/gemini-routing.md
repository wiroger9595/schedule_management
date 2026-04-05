# Gemini CLI 分流指引

## 何時用 Gemini CLI（省 Claude Code token）

### 適合 Gemini 的任務
```bash
# 分析 log / 錯誤排查
gemini "分析這段 server log，找出根本原因：$(cat server/server.log | tail -200)"

# 解釋第三方套件行為
gemini "LangGraph StateGraph 的 invoke() 和 stream() 差異是什麼？"

# 產生樣板程式碼
gemini "幫我寫一個 FastAPI endpoint，接收 JSON body {title, start_time}，存入 PostgreSQL"

# 大檔案分析（不需要編輯）
gemini "讀這個檔案，告訴我哪些函數可以合併優化：$(cat server/app/api/endpoints/schedules.py)"

# 翻譯 / 文字處理
gemini "把這些 UI 文字翻成英文 JSON key-value：..."

# 研究 API 文件
gemini "HERE Geocoding API 的 in=circle 參數格式是什麼？"
```

### 適合 Claude Code 的任務
- 直接編輯多個相關檔案
- 需要理解整個對話 context 的 bug fix
- 涉及多檔案架構的新功能
- 需要記憶之前錯誤/決策的任務

## Gemini CLI 安裝
```bash
npm install -g @google/generative-ai-cli
# 或
pip install google-generativeai
gemini auth login
```

## 分流決策樹
```
任務需要編輯檔案？
  ├─ 是 → 用 Claude Code
  └─ 否 → 任務需要理解對話歷史？
            ├─ 是 → 用 Claude Code  
            └─ 否 → 用 Gemini CLI（省錢）
```
