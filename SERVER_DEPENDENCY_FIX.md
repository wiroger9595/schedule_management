# 伺服器依賴修復總結

## 問題
FastAPI 伺服器啟動失敗，缺少多個必需的 Python 模塊。

## 解決的問題

### 1. 缺少 `python-jose` 模塊
**錯誤訊息**: `ModuleNotFoundError: No module named 'jose'`

**解決方案**:
```bash
pip install 'python-jose[cryptography]'
```

用途：JWT (JSON Web Token) 認證功能

### 2. 缺少 `passlib` 模塊  
**錯誤訊息**: `ModuleNotFoundError: No module named 'passlib'`

**解決方案**:
```bash
pip install passlib bcrypt
```

用途：密碼哈希和驗證功能

### 3. Google Gemini 導入錯誤
**錯誤訊息**: `ImportError: cannot import name 'genai' from 'google'`

**問題原因**: `google-genai` SDK 的導入語法已更新

**解決方案**:
1. 安裝正確的 SDK:
   ```bash
   pip install google-genai
   ```

2. 修正 `/server/app/services/gemini_service.py` 第1行:
   ```python
   # 錯誤寫法
   from google import genai
   
   # 正確寫法
   import google.genai as genai
   ```

### 4. 缺少 `psycopg2` 模塊
**錯誤訊息**: `ModuleNotFoundError: No module named 'psycopg2'`

**解決方案**:
```bash
pip install psycopg2-binary
```

用途：PostgreSQL 數據庫連接驅動

## 安裝的依賴列表

已成功安裝以下 Python 包：
- ✅ `python-jose[cryptography]` - JWT 認證
- ✅ `passlib[bcrypt]` - 密碼加密
- ✅ `google-genai` - Google Gemini AI SDK
- ✅ `psycopg2-binary` - PostgreSQL 驅動

## 修改的文件

### 1. `server/app/services/gemini_service.py`
- **行 1**: 修正 Google Gemini 導入語句
- **變更**: `from google import genai` → `import google.genai as genai`

### 2. `server/requirements.txt` (建議更新)
確保包含以下依賴：
```text
python-jose[cryptography]
passlib[bcrypt]
google-genai
psycopg2-binary
cloudinary
fastapi
uvicorn
sqlmodel
redis
python-dotenv
...其他依賴
```

## 驗證結果

✅ **伺服器狀態**: 正常運行
✅ **運行端口**: http://0.0.0.0:7800
✅ **API 文檔**: http://localhost:7800/docs

服務器啟動日誌：
```
INFO:     Started server process [17400]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 後續注意事項

1. **依賴管理**: 建議定期運行 `pip freeze > requirements.txt` 來更新依賴列表
2. **虛擬環境**: 考慮使用虛擬環境（如 `venv` 或 `conda env`）來隔離項目依賴
3. **Google OAuth 設定**: 參考 `OAUTH_SETUP_GUIDE.md` 完成 OAuth 配置
4. **PostgreSQL 連接**: 確保 `.env` 文件中的 PostgreSQL 連接參數正確

## 相關文檔

- [OAUTH_SETUP_GUIDE.md](./OAUTH_SETUP_GUIDE.md) - Google OAuth 設定指南
- [requirements.txt](./server/requirements.txt) - Python 依賴清單
