# Google Maps API Key 設置指南 (自動化與環境變數版)

我們已經為 Android 和 iOS 配置了標準的環境變數讀取機制。您不再需要修改任何代碼文件，只需在配置文件中填入 API Key。

## 1. 獲取 API Key
前往 [Google Cloud Console](https://console.cloud.google.com/) 申請 API Key，確保啟用 Maps SDK for Android 和 Maps SDK for iOS。

## 2. 配置 Android
編輯文件：`mobile/.env`
```properties
GOOGLE_MAPS_API_KEY=AIzaSy... (填入您的Key)
```
*系統會自動通過 Gradle 腳本讀取並注入。*

## 3. 配置 iOS
編輯文件：`mobile/ios/Flutter/Config.xcconfig`
```xcconfig
GOOGLE_MAPS_API_KEY=AIzaSy... (填入您的Key)
```
*系統會自動通過 Xcode Configuration 讀取並注入。*

## 4. 運行
修改配置後，請**停止並重新運行 (Stop -> Run)** App。
(不要使用 Hot Restart，因為這涉及原生層的變更)

---
### 為什麼這樣做是正規的？
1. **安全性**: API Key 不再硬編碼在 `AppDelegate.swift` 或 `AndroidManifest.xml` 中。
2. **版本控制**: 您可以將 `.env` 和 `Config.xcconfig` 加入 `.gitignore` (如果需要)，防止 Key 洩漏到公開倉庫。
3. **可維護性**: 切換環境（開發/生產）只需更換配置文件，無需改代碼。
