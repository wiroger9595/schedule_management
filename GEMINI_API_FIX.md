# Gemini API 修復總結

## 問題描述

AI 行程提取功能報錯：
```
404 NOT_FOUND: models/gemini-1.5-flash is not found for API version v1beta
```

## 根本原因

Google Gemini API 的模型命名規則和版本已更新：
1. **舊版 SDK** (`google-generativeai`): 使用模型名稱如 `gemini-1.5-flash`
2. **新版 SDK** (`google-genai`): 需要完整路徑如 `models/gemini-2.5-flash`

## 解決方案

### 1. 列出可用模型

創建測試腳本來查看所有可用的 Gemini 模型：

```python
import google.genai as genai
client = genai.Client(api_key=api_key)

for model in client.models.list():
    print(f"Model: {model.name}")
```

**發現**: 總共有 45 個可用模型，最新的穩定模型是 `models/gemini-2.5-flash`

### 2. 更新服務配置

**檔案**: `/server/app/services/gemini_service.py`

**變更前**（第 16-18 行）:
```python
self.client = genai.Client(api_key=self.api_key)
# Using a stable model alias or specific version as per new SDK recommendations
self.model_name = 'gemini-1.5-flash'
```

**變更後**:
```python
self.client = genai.Client(api_key=self.api_key)
# Use the latest stable Gemini 2.5 Flash model
# Model name must include 'models/' prefix as per google-genai SDK
self.model_name = 'models/gemini-2.5-flash'
```

### 3. 驗證修復

**測試 1: 簡單提示**
```python
response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="用繁體中文說 hello"
)
# ✓ 輸出: 你好。
```

**測試 2: 完整行程提取**
```python
result = gemini_service.extract_schedule_info("明天下午3點跟Robert在信義區吃飯")
# ✓ 成功提取:
# {
#   "title": "跟Robert吃飯",
#   "start_time": "2026-02-12T15:00:00",
#   "location": "信義區",
#   "type": "meeting",
#   "attendees": "Robert"
# }
```

## 可用的 Gemini 模型（部分列表）

| 模型名稱 | 用途 | 推薦場景 |
|---------|------|---------|
| `models/gemini-2.5-flash` | 最新穩定版，快速響應 | ✅ **當前使用** - 行程提取 |
| `models/gemini-2.5-pro` | 更強大的推理能力 | 複雜任務、長文本分析 |
| `models/gemini-flash-latest` | 自動指向最新 Flash | 想要自動更新的場景 |
| `models/gemini-pro-latest` | 自動指向最新 Pro | 需要最強性能 |

完整列表包含 45 個模型，包括：
- Gemini 文字生成模型（2.5 / 2.0 / 3.0 系列）
- Gemma 開源模型（3-1b 到 3-27b）
- Imagen 圖片生成模型
- Veo 影片生成模型
- 嵌入和 AQA 模型

## API 使用範例

### 基本文字生成
```python
import google.genai as genai

client = genai.Client(api_key="YOUR_API_KEY")
response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="你的提示詞"
)
print(response.text)
```

### 結構化輸出 (JSON)
```python
response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="提取這段文字的關鍵資訊並以 JSON 返回：明天下午3點開會",
    config={
        "response_mime_type": "application/json",
        "temperature": 0.2  # 較低溫度提高一致性
    }
)
```

## 重要提醒

### ✅ 正確做法
1. **使用完整模型名稱**: `models/gemini-2.5-flash` ✓
2. **檢查 API 文檔**: Google Gemini SDK 經常更新
3. **列出可用模型**: 使用 `client.models.list()` 確認

### ❌ 常見錯誤
1. ~~使用舊格式~~: `gemini-1.5-flash` ✗
2. ~~忽略 `models/` 前綴~~: `gemini-2.5-flash` ✗
3. ~~假設模型永久可用~~: 某些模型會被淘汰

## 相關檔案

### 修改的檔案
- ✏️ `/server/app/services/gemini_service.py` - 已更新模型名稱

### 測試腳本
- 📝 `/server/list_gemini_models.py` - 列出所有可用模型
- 📝 `/server/test_gemini_quick.py` - 快速測試 API
- 📝 `/server/test_schedule_extraction.py` - 測試完整工作流程

## 下一步

✅ Gemini API 已修復並正常工作
✅ AI 行程提取功能可正常使用
✅ 伺服器完全運行正常

可以開始測試完整的行程管理功能了！
