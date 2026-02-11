# Google OAuth 設定指南

## 問題說明

錯誤訊息：`Access blocked: Authorization Error - Storagerelay URI is not allowed for 'NATIVE_IOS' client type`

**原因**：您使用的 OAuth Client ID 類型為 **iOS (Native)**，但應用在瀏覽器環境中運行時會使用不同的 OAuth 流程，導致不相容。

## 解決方案

### 步驟 1：確認現有的 OAuth Client IDs

前往 [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)

您應該會看到至少一個 OAuth 2.0 Client ID：
- **iOS Client ID**: `644901002244-soa2s80jbm0l9ne9jgdf7ifrq5rl7rac.apps.googleusercontent.com`

### 步驟 2：為不同平台創建對應的 Client ID

#### A. iOS 原生應用 (已設定)
- ✅ Client Type: **iOS**
- ✅ Client ID: `644901002244-soa2s80jbm0l9ne9jgdf7ifrq5rl7rac.apps.googleusercontent.com`
- Bundle ID: 您的應用 Bundle ID (檢查 `ios/Runner/Info.plist`)

#### B. Android 原生應用 (如需支援)
1. 點擊 **+ CREATE CREDENTIALS** → **OAuth 2.0 Client ID**
2. Application type: **Android**
3. Package name: 從 `android/app/build.gradle` 中的 `applicationId` 取得
4. SHA-1 fingerprint: 執行以下命令取得
   ```bash
   cd android
   ./gradlew signingReport
   ```

#### C. Web 應用 (測試或 Web 版本)
1. 點擊 **+ CREATE CREDENTIALS** → **OAuth 2.0 Client ID**
2. Application type: **Web application**
3. Name: `Schedule Management Web Client`
4. Authorized redirect URIs:
   ```
   http://localhost:3000
   http://localhost:8080
   https://your-web-domain.com (如果有部署)
   ```

### 步驟 3：更新 Flutter 應用配置

#### iOS 設定 (`ios/Runner/Info.plist`)
確認已經設定 URL Scheme：
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <!-- 反轉的 iOS Client ID -->
      <string>com.googleusercontent.apps.644901002244-soa2s80jbm0l9ne9jgdf7ifrq5rl7rac</string>
    </array>
  </dict>
</array>
```

#### Android 設定 (`android/app/src/main/AndroidManifest.xml`)
```xml
<activity
    android:name="com.google.android.gms.auth.api.signin.internal.SignInHubActivity"
    android:excludeFromRecents="true"
    android:exported="false"
    android:theme="@android:style/Theme.Translucent.NoTitleBar" />
```

### 步驟 4：環境變數設定 (可選)

如果您想要更靈活的配置，可以在 `.env` 中設定：

```bash
# iOS OAuth Client ID
GOOGLE_IOS_CLIENT_ID=644901002244-soa2s80jbm0l9ne9jgdf7ifrq5rl7rac.apps.googleusercontent.com

# Android OAuth Client ID (從 Google Cloud Console 取得)
GOOGLE_ANDROID_CLIENT_ID=YOUR_ANDROID_CLIENT_ID.apps.googleusercontent.com

# Web OAuth Client ID (從 Google Cloud Console 取得)
GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID.apps.googleusercontent.com
```

### 步驟 5：測試不同平台

#### iOS 測試
```bash
cd mobile
flutter run -d iPhone
```

#### Android 測試
```bash
cd mobile
flutter run -d <android-device-id>
```

#### Web 測試
```bash
cd mobile
flutter run -d chrome
```

## 常見問題

### Q1: 為什麼需要不同的 Client ID？
**A**: 不同平台使用不同的 OAuth 流程：
- **iOS/Android**: 使用原生 OAuth 流程，需要 Bundle ID 或 Package Name
- **Web**: 使用瀏覽器重定向流程，需要 Redirect URIs

### Q2: 錯誤 "invalid_client" 怎麼辦？
**A**: 
1. 確認 Client ID 正確
2. 確認平台類型匹配（iOS 應用不要用 Web Client ID）
3. 確認 Bundle ID 或 Package Name 一致

### Q3: 如何確認使用了正確的 Client ID？
**A**: 在 `auth_service.dart` 中，代碼會根據平台自動選擇：
- iOS → 使用 iOS Client ID
- Android → 從 `google-services.json` 讀取
- Web → 需要設定 `serverClientId`

## 後端設定

您的後端 (`server/app/main.py`) 目前是簡單的 Mock 驗證。如果要正式驗證 Google ID Token，需要安裝：

```bash
pip install google-auth
```

然後更新 `/api/auth/google` 端點：

```python
from google.oauth2 import id_token
from google.auth.transport import requests

@app.post("/api/auth/google")
def google_auth(data: dict, session: Session = Depends(get_session)):
    try:
        # 驗證 ID Token
        idinfo = id_token.verify_oauth2_token(
            data['id_token'], 
            requests.Request(), 
            'YOUR_WEB_CLIENT_ID.apps.googleusercontent.com'
        )
        
        # 確保 token 是來自正確的 client
        if idinfo['aud'] not in [IOS_CLIENT_ID, ANDROID_CLIENT_ID, WEB_CLIENT_ID]:
            raise ValueError('Invalid client ID')
            
        google_id = idinfo['sub']
        email = idinfo['email']
        
        # ... 其餘邏輯保持不變
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## 下一步

1. ✅ 已更新 `auth_service.dart` 支援多平台
2. ⏳ 在 Google Cloud Console 創建對應平台的 Client ID
3. ⏳ 測試不同平台的 OAuth 登入流程
4. ⏳ (可選) 實作後端 ID Token 驗證
