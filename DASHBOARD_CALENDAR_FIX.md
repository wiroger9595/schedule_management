# Dashboard 和日曆顯示修復

## 問題描述

1. **Dashboard 顯示空白**: AI 創建行程成功但未顯示。
2. **Flutter 類型錯誤**: `type 'int' is not a subtype of type 'String'`。

## 根本原因

### 1. 後端 Schedule 模型字段名稱不匹配
前端期望 `start_time` 和 `location`，但後端只有 `meeting_time` 和 `meeting_location`。

### 2. FastAPI 自動驗證過濾字段 (類型錯誤主因)
即使我們在 `Schedule` 模型中添加了自定義 `dict()` 方法來生成正確的字段，FastAPI 的 `response_model=List[Schedule]` 會：
1. **重新驗證數據**: 將返回的字典重新映射回 `Schedule` 模型。
2. **強制類型轉換**: 將 ID 從字符串（如 `"sch_123"`）強制轉回整數（如果是整數 ID），或者因為類型不匹配而報錯。
3. **過濾未定義字段**: 因為 `start_time` 和 `location` 是 `@property` 而不是字段，被自動過濾掉。
4. **輸出結果**: 返回了整數 ID (1, 2...) 而不是字符串 ID，且缺少關鍵字段。

前端接收到整數 ID，但在 Dart 模型中定義為 String，導致 `int is not subtype of String` 錯誤。

## 解決方案

### 1. 覆寫 Schedule 模型的 `dict()` 方法 (已完成)
在 `/server/app/models/schedule.py` 中添加邏輯，確保序列化時包含 `id` (字符串), `start_time`, `location`。

### 2. 更新 API 路由以繞過嚴格驗證 (本次修復)
修改 `/server/app/main.py` 中的 `read_schedules` 和 `create_schedule`：

**修改前**:
```python
@app.get("/api/schedules", response_model=List[Schedule])  # ❌ 強制驗證和過濾
def read_schedules(...):
    return session.exec(...).all()
```

**修改後**:
```python
@app.get("/api/schedules")  # ✅ 移除 response_model
def read_schedules(...):
    schedules = session.exec(...).all()
    # 手動調用 dict() 以保留所有自定義字段和字符串 ID
    return [s.dict() for s in schedules]
```

## 驗證結果

### API 響應變化
**修復前 (模擬)**:
```json
[
  { "id": 1, "meeting_time": "...", "status": "P" }  // ❌ ID是數字，缺 start_time
]
```

**修復後**:
```json
[
  {
    "id": "sch_u123...",           // ✅ ID是字符串
    "start_time": "2026-02-12...", // ✅ 包含計算屬性
    "location": "信義區",            // ✅ 包含計算屬性
    "title": "...",
    ...
  }
]
```

### Flutter 前端
- ✅ `id` 類型匹配 (String) -> 錯誤解決
- ✅ `start_time` 存在 -> 列表顯示正常
- ✅ `location` 存在 -> 地點顯示正常

## 相關文件
- ✏️ `/server/app/main.py` - 更新 API 路由
- ✏️ `/server/app/models/schedule.py` - 自定義序列化邏輯

## 下一步
請刷新 App 或重啟，Dashboard 和 Calendar 應該能正常顯示之前創建的行程，且不再報錯。
