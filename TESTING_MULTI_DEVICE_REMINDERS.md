# 多設備提醒功能測試指南

## 模擬器限制 ⚠️

| 功能 | iOS 模擬器 | Android 模擬器 | 真實設備 |
|------|----------|-------------|--------|
| FCM 推播接收 | ❌ 不支援 | ⚠️ 部分支援* | ✅ 完全支援 |
| Firebase 初始化 | ✅ 支援 | ✅ 支援 | ✅ 支援 |
| 本地通知 | ✅ 支援 | ✅ 支援 | ✅ 支援 |
| DeviceService | ✅ 支援 | ✅ 支援 | ✅ 支援 |

*Android 模擬器需要 Google Play Services；部分雲端模擬器（Firebase Test Lab）支援完全 FCM

---

## 方案 A：後端測試（推薦先做）

不需要真實設備或模擬器，直接在後端測試推播邏輯。

### 1. 啟動後端

```bash
cd server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 測試多設備註冊

使用 curl 模擬多設備註冊：

```bash
# 1. 登入取得 token（先設定正確的 email/password）
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}' \
  | jq -r '.access_token')

# 2. 註冊「iPhone」設備
curl -X POST http://localhost:8000/api/users/me/devices/fcm-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "iPhone-12-A1B2C3D4",
    "platform": "ios",
    "fcm_token": "iphone_token_12345"
  }'

# 3. 註冊「MacBook」設備
curl -X POST http://localhost:8000/api/users/me/devices/fcm-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "MacBook-Pro-X5Y6Z7W8",
    "platform": "macos",
    "fcm_token": "macos_token_67890"
  }'

# 4. 驗證設備已註冊
curl -X GET http://localhost:8000/api/users/me/devices \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 3. 建立排程並驗證提醒被排隊

```bash
# 創建一個 5 分鐘後的排程
FUTURE_TIME=$(python3 -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(minutes=5)).isoformat())")

curl -X POST http://localhost:8000/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "咖啡會",
    "start_time": "'$FUTURE_TIME'",
    "end_time": "'$(python3 -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(minutes=35)).isoformat())")'"，
    "location": "星巴克",
    "latitude": 25.033,
    "longitude": 121.5654,
    "transport_mode": "car"
  }' | jq
```

### 4. 查看後端日誌

在後端日誌中查看：

```
[Startup] Reminder scheduler initialized
Schedule {schedule_id}: car → 25 min from default location
Updated reminder_leave_by_time for schedule {schedule_id}: 2026-07-04 14:50:00
Scheduled reminder for schedule {schedule_id} at 2026-07-04 14:50:00 UTC
```

等到提醒時間到達，應該看到：

```
Sent reminder to device iPhone-12-A1B2C3D4 (platform: ios)
Sent reminder to device MacBook-Pro-X5Y6Z7W8 (platform: macos)
```

---

## 方案 B：真實設備測試（完整測試）

如果有 iPhone 和 Mac，這是最完整的測試方式。

### 1. 設定 Firebase

確保已完成 `MACOS_PUSH_SETUP.md` 中的所有步驟。

### 2. 在真實設備上執行

```bash
# iPhone
flutter run -d <iPhone device name>

# Mac
flutter run -d macos
```

### 3. 測試流程

1. **iPhone 登入**
   - 開啟應用 → 登入帳號
   - 查看後端日誌，應看到 FCM token 被註冊
   - 檢查："已為設備註冊 FCM token"

2. **Mac 登入（同帳號）**
   - 開啟應用 → 登入同帳號
   - 查看後端日誌，應看到另一個設備被註冊
   - 驗證：`/api/users/me/devices` 應返回 2 個設備

3. **建立排程**
   - 在 iPhone 或 Mac 上建立排程
   - 設定時間為 5 分鐘後
   - 選擇交通工具（例：開車）
   
4. **等待提醒**
   - 時間到達時，iPhone 和 Mac 都應收到推播通知
   - 通知內容：「是時候出發了 🚗 | 會議名稱 (預計 X 分鐘車程)」

5. **登出測試**
   - 在 iPhone 登出
   - 驗證：設備應從 `user_devices` 表中刪除
   - 後續排程只會推播到 Mac

---

## 方案 C：本地模擬測試（不需真實設備）

透過本地通知和日誌測試邏輯。

### 1. 使用 iOS 模擬器

```bash
# 建立模擬器
xcrun simctl create "iPhone 15 Pro" com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro

# 運行應用
flutter run -d <simulator-id>
```

**限制**：無法測試 FCM 推播（模擬器不支援），但可以測試：
- ✅ Firebase 初始化
- ✅ DeviceService（生成設備 ID）
- ✅ API 調用（token 註冊）
- ✅ 本地通知（用 NotificationService.showLocalNotification）

### 2. 模擬本地推播（補償方案）

編輯 `mobile/lib/services/notification_service.dart`，在 `_handleForegroundMessage()` 之後添加測試模式：

```dart
void _setupTestReminders() {
  // 測試用：每 30 秒檢查一次是否該顯示本地提醒
  Timer.periodic(Duration(seconds: 30), (_) {
    // 這會在模擬器上模擬 FCM 推播
    final message = RemoteMessage(
      notification: RemoteNotification(
        title: '是時候出發了 🚗',
        body: '咖啡會 @ 15:00 (預計 25 分鐘車程)',
      ),
      data: {'type': 'departure_reminder'},
    );
    _handleForegroundMessage(message);
  });
}
```

呼叫時機（在 `_setupFirebaseMessaging()` 中）：

```dart
void _setupFirebaseMessaging() {
  // ... 其他代碼 ...
  
  // 測試模式（開發時啟用）
  if (kDebugMode) {
    _setupTestReminders();
  }
}
```

---

## 推薦測試順序

### 第一階段：後端驗證（無需任何硬體）
1. ✅ 建立測試帳號
2. ✅ 模擬多設備註冊（curl）
3. ✅ 建立排程，驗證提醒被排隊
4. ✅ 檢查後端日誌確認推播嘗試

**耗時**：15 分鐘

### 第二階段：前端基礎測試（用模擬器）
1. ✅ 運行 iOS/Android 模擬器
2. ✅ 驗證 Firebase 初始化成功
3. ✅ 驗證 API 呼叫能成功註冊 token
4. ✅ 驗證本地通知能正常顯示

**耗時**：30 分鐘

### 第三階段：完整測試（真實設備）
1. ✅ iPhone 登入 → 註冊 FCM token
2. ✅ Mac 登入（同帳號）→ 註冊另一個 token
3. ✅ 建立排程 → 驗證推播發送到兩個設備
4. ✅ 驗證登出時設備被清理

**耗時**：30 分鐘

---

## 除錯技巧

### 後端日誌太多？過濾提醒相關日誌

```bash
# 只看提醒相關的日誌
journalctl -u schedule-management -f | grep -i reminder
```

或在 Python 代碼中添加：

```python
# 在 reminder_service.py 和 background_reminder_scheduler.py 中
logger.info(f"[REMINDER] {message}")  # 便於 grep
```

### 驗證 APScheduler 是否真的排隊了任務

添加臨時調試代碼：

```python
# 在 background_reminder_scheduler.py 的 schedule_reminder() 方法中
def schedule_reminder(self, schedule_id: str, leave_by_time: datetime, user_id: str):
    # ...
    print(f"[DEBUG] Scheduled jobs: {self.scheduler.get_jobs()}")
    print(f"[DEBUG] New job: {job_id} at {leave_by_time}")
```

### 本地測試時模擬推播延遲

如果想測試離線情況（收到推播時應用在背景）：

1. 在 iOS 模擬器上終止應用
2. 等待幾秒鐘
3. 在 Mac 上手動建立排程
4. 重新開啟 iOS 應用 → 應觸發 `onMessageOpenedApp`

---

## 常見問題

**Q: 模擬器上為什麼收不到推播？**  
A: iOS 模擬器不支援 FCM。用真實 iPhone 或先用後端 curl 測試。

**Q: 後端沒看到「Sent reminder to device」訊息**  
A: 
1. 檢查排程的 `reminder_leave_by_time` 是否設置
2. 檢查設備的 fcm_token 是否正確
3. 檢查 Firebase 認證 (`FIREBASE_SERVICE_ACCOUNT_JSON` 環境變數)

**Q: 能否在不登入 Firebase 的情況下測試？**  
A: 可以。後端若無 Firebase 憑證，會輸出 `[Push SKIP] Firebase not configured...` 但仍會排隊任務。

---

## 生產環境前的清單

- [ ] 真實 iPhone 和 Mac 都能收到推播
- [ ] 登出時設備被正確移除
- [ ] 交通工具選擇能正確影響提醒時間
- [ ] 多人帳號間的推播互不影響
- [ ] 排程更新時提醒被重新排隊
- [ ] Firebase 配置正確（iOS 和 macOS 都有對應的 App）
