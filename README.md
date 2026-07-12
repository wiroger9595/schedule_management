# 行程管理系統 (Schedule Management System)

一個功能完整的行程管理應用程式，包含 Flutter 跨平台行動應用程式與 FastAPI Python 後端服務。

## 📋 專案概述

本專案提供一個完整的行程管理解決方案，支援使用者註冊、登入、行程建立與管理、聯絡人管理、地圖整合等功能。

### 核心功能

- 🔐 **使用者認證** - JWT token 認證、Google/Apple OAuth 第三方登入
- 📅 **行程管理** - 建立、編輯、刪除行程，支援會議地點與時間設定
- 👥 **聯絡人管理** - 管理行程參與者與聯絡人清單
- 🗺️ **地圖整合** - Google Maps 整合，支援地點選擇與路線規劃
- 🖼️ **個人檔案** - 使用者檔案上傳至 Cloudinary，支援照片管理
- 📱 **跨平台支援** - iOS、Android、macOS、Web
- 🔔 **本地通知** - 行程提醒通知功能
- 🌐 **國際化** - 多語言支援（Flutter localization）

## 🌐 產品官方介紹網頁

`web/landing.html`（中文）與 `web/landing-en.html`（English）是產品的官方介紹頁（單一 HTML 檔，無外部依賴，字型已內嵌）。兩個頁面互有導覽列語言切換連結。

開啟方式：

```bash
# 方法一：直接用瀏覽器開啟檔案
open web/landing.html          # macOS，中文版
open web/landing-en.html       # macOS，English version
# 或在 Finder 裡雙擊檔案

# 方法二：本機起一個靜態伺服器（適合要測試手機瀏覽器的情況）
cd web
python3 -m http.server 9512
# 瀏覽器開 http://localhost:9512/landing.html    （中文）
# 瀏覽器開 http://localhost:9512/landing-en.html （English）
```

## 🏗️ 系統架構

```
schedule_management/
├── mobile/          # Flutter 前端應用程式
│   ├── lib/
│   │   ├── screens/     # UI 畫面
│   │   ├── services/    # API 與認證服務
│   │   ├── models/      # 資料模型
│   │   └── widgets/     # 可重用元件
│   └── pubspec.yaml
│
└── server/          # Python FastAPI 後端
    ├── app/
    │   ├── api/         # API 路由
    │   ├── models/      # 資料庫模型
    │   ├── services/    # 業務邏輯
    │   ├── core/        # 核心功能（認證、Redis）
    │   └── main.py      # 應用程式入口
    ├── requirements.txt
    └── run.py
```

## 🛠️ 技術棧

### 前端 (Mobile)
- **框架**: Flutter 3.10.4+
- **狀態管理**: StatefulWidget
- **儲存**: flutter_secure_storage（安全存取 token）
- **地圖**: google_maps_flutter
- **定位**: geolocator
- **圖片**: image_picker
- **OAuth**: google_sign_in, sign_in_with_apple
- **通知**: flutter_local_notifications
- **行事曆**: table_calendar

### 後端 (Server)
- **框架**: FastAPI
- **資料庫**: PostgreSQL（SQLModel/asyncpg）
- **快取**: Redis（token 白名單管理）
- **認證**: JWT（python-jose）、OAuth2
- **密碼**: passlib with bcrypt
- **圖片儲存**: Cloudinary
- **AI 整合**: Google Gemini API（google-genai）
- **地圖服務**: OSMnx, NetworkX, GeoPandas

## 📦 資料庫設計

### User 表
```sql
- id (INT, PRIMARY KEY, AUTO INCREMENT)
- user_id (VARCHAR, UNIQUE)
- email (VARCHAR, UNIQUE)
- hashed_password (VARCHAR)
- full_name (VARCHAR)
- phone (VARCHAR)
- line_id (VARCHAR)
- profile_image_path (VARCHAR)
- public_id (VARCHAR) -- Cloudinary public_id
- status (VARCHAR(2), DEFAULT 'Y')
- created_at (TIMESTAMPTZ)
- updated_at (TIMESTAMPTZ)
- google_id (VARCHAR)
- apple_id (VARCHAR)
```

### Schedule 表
```sql
- id (INT, PRIMARY KEY, AUTO INCREMENT)
- user_id (VARCHAR, FK to users)
- schedule_id (VARCHAR, UNIQUE)
- title (VARCHAR)
- description (TEXT)
- meeting_time (VARCHAR)
- meeting_location (VARCHAR)
- transport_mode (VARCHAR)
- type (VARCHAR) -- meeting/personal
- status (VARCHAR(2), DEFAULT 'P')
- is_reminder (BOOLEAN)
- created_at (TIMESTAMPTZ)
- updated_at (TIMESTAMPTZ)
```

### Contact 表
```sql
- id (INT, PRIMARY KEY, AUTO INCREMENT)
- user_id (VARCHAR)
- name (VARCHAR)
- phone (VARCHAR)
- email (VARCHAR)
- created_at (TIMESTAMPTZ)
```

## 🚀 快速開始

### 前置需求

- **Flutter SDK**: 3.10.4 或更高版本
- **Dart SDK**: 已包含在 Flutter 中
- **Python**: 3.8+
- **PostgreSQL**: 13+
- **Redis**: 6.0+
- **Xcode** (macOS/iOS開發)
- **Android Studio** (Android開發)

### 環境設定

#### 1. 後端設定

```bash
# 進入後端目錄
cd server

# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安裝相依套件
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 檔案，填入必要的設定：
# - DATABASE_URL (PostgreSQL 連線字串)
# - REDIS_URL (Redis 連線字串)
# - SECRET_KEY (JWT 密鑰)
# - CLOUDINARY_CLOUD_NAME
# - CLOUDINARY_API_KEY
# - CLOUDINARY_API_SECRET
# - GOOGLE_GEMINI_API_KEY

# 啟動伺服器
uvicorn app.main:app --reload
# 或
python run.py
```

伺服器將在 `http://localhost:8000` 啟動

**API 文件**: 
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 2. 前端設定

```bash
# 進入前端目錄
cd mobile

# 安裝相依套件
flutter pub get

# 檢查 Flutter 環境
flutter doctor

# 執行應用程式
# macOS
flutter run -d macos

# iOS 模擬器
flutter run -d ios

# Android 模擬器
flutter run -d android

# Chrome（網頁版）
flutter run -d chrome
```

### 資料庫初始化

```bash
cd server

# 執行資料庫遷移
python add_user_fields_migration.py
python add_profile_picture_migration.py
python create_contact_table.py
python create_schedule_attendee_table.py
python add_schedule_fields_migration.py

# 或重置資料庫（警告：會清除所有資料）
python reset_database.py
```

## 🔑 環境變數設定

### 後端 (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/schedule_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Google Gemini
GOOGLE_GEMINI_API_KEY=your-gemini-api-key

# OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
APPLE_CLIENT_ID=your-apple-client-id
```

### 前端設定

前端的 API 端點設定在 `lib/services/api_service.dart`：

```dart
final String baseUrl = 'http://localhost:8000';
```

部署時請修改為實際的後端 API 位址。

## 📱 主要功能說明

### 1. 使用者認證流程

- **註冊**: 使用 email、密碼、全名註冊帳號
- **登入**: 支援一般登入與 Google/Apple OAuth
- **Token 管理**: JWT token 儲存於 flutter_secure_storage
- **自動登出**: 401 回應時自動清除 token 並導向登入頁

### 2. 行程管理

- 建立行程時可指定標題、描述、時間、地點
- 支援交通方式選擇（driving, walking, transit）
- 行程類型：會議或個人行程
- 行程提醒功能
- 整合 Google Maps 顯示地點

### 3. 個人檔案管理

- 上傳個人照片至 Cloudinary
- 支援 PNG、JPG 格式
- 照片儲存路徑：`profile_pictures/{user_id}/`
- 顯示於側邊選單的 DrawerHeader

### 4. 聯絡人管理

- 新增、編輯、刪除聯絡人
- 支援姓名、電話、Email 欄位
- 與行程參與者整合

## 🧪 測試

### 後端測試

```bash
cd server

# 測試 API
python test_api.py

# 測試 Cloudinary
python test_cloudinary.py

# 測試 Gemini API
python test_gemini.py
```

### 前端測試

```bash
cd mobile

# 執行單元測試
flutter test

# 執行整合測試
flutter drive --target=test_driver/app.dart
```

## 📝 API 端點

### 認證相關
- `POST /auth/register` - 註冊新使用者
- `POST /auth/token` - 登入取得 JWT token
- `POST /auth/logout` - 登出（清除 Redis token）
- `POST /auth/google` - Google OAuth 登入
- `POST /auth/apple` - Apple OAuth 登入

### 使用者相關
- `GET /users/me` - 取得當前使用者資訊
- `PUT /users/me` - 更新使用者資訊
- `POST /users/me/upload-profile-picture` - 上傳個人照片
- `DELETE /users/me/profile-picture` - 刪除個人照片

### 行程相關
- `GET /schedules` - 取得使用者所有行程
- `POST /schedules` - 建立新行程
- `GET /schedules/{schedule_id}` - 取得特定行程
- `PUT /schedules/{schedule_id}` - 更新行程
- `DELETE /schedules/{schedule_id}` - 刪除行程

### 聯絡人相關
- `GET /contacts` - 取得所有聯絡人
- `POST /contacts` - 建立新聯絡人
- `PUT /contacts/{contact_id}` - 更新聯絡人
- `DELETE /contacts/{contact_id}` - 刪除聯絡人

## 🐛 常見問題

### 1. Flutter 構建錯誤

**問題**: `CocoaPods not installed`

**解決方案**:
```bash
sudo gem install cocoapods
cd mobile/ios
pod install
```

### 2. 後端資料庫連線失敗

**問題**: `connection refused`

**解決方案**:
- 確認 PostgreSQL 正在運行：`brew services list` (mac)
- 檢查 `.env` 中的 `DATABASE_URL` 是否正確
- 測試連線：`psql -U postgres`

### 3. Redis 連線錯誤

**問題**: `Error connecting to Redis`

**解決方案**:
```bash
# 啟動 Redis
brew services start redis  # macOS
# 或
redis-server  # 直接啟動

# 測試連線
redis-cli ping  # 應回傳 PONG
```

### 4. Cloudinary 上傳失敗

**檢查項目**:
- 確認 `.env` 中 Cloudinary 憑證正確
- 測試上傳：`python test_cloudinary.py`
- 檢查網路連線

### 5. Google Maps 無法顯示

**解決方案**:
- 確認 Google Maps API Key 已設定
- 在 Google Cloud Console 啟用 Maps SDK for iOS/Android
- iOS: 編輯 `ios/Runner/AppDelegate.swift` 加入 API Key
- Android: 編輯 `android/app/src/main/AndroidManifest.xml`

## 🔐 安全性考量

- ✅ 密碼使用 bcrypt 雜湊儲存
- ✅ JWT token 有時效性（30分鐘）
- ✅ Token 白名單機制（Redis）
- ✅ HTTPS 連線（生產環境）
- ✅ SQL Injection 防護（SQLModel ORM）
- ✅ CORS 限制
- ✅ 環境變數管理敏感資訊
- ✅ Token 儲存於安全儲存空間（flutter_secure_storage）

## 📈 未來開發計劃

- [ ] 推播通知（Firebase Cloud Messaging）
- [ ] 行程分享功能
- [ ] 群組行程管理
- [ ] 行程匯入/匯出（iCal 格式）
- [ ] 離線模式支援
- [ ] 多語言完整支援
- [ ] Dark Mode 深色模式
- [ ] 行程分析與統計
- [ ] Google Calendar 整合s
- [ ] Line Bot 整合

## 🤝 參與開發

歡迎提交 Issue 或 Pull Request！

### 開發流程

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權條款。

## 📧 聯絡方式

如有任何問題或建議，請透過以下方式聯絡：

- 建立 Issue
- Email: [您的Email]

---

**Made with ❤️ using Flutter & FastAPI**



明天跟副理去摩鐵


更
刪除打球的行程


我不要去露營


更改打球的地點
change place for play baskball
河濱公園

成淵高中籃球場

更新談生意的地點和時間


談生意
改成9點


改到春春花牛肉麵店星期三五點

建國高架旁籃球場




 我下禮拜五跟小小哈找吃飯
請問幾點開始？
請問要將哪個行程改成晚上10點？
是新增行程
'請問新增的行程是在哪個日期，還有地點在哪裡？

我已經說 下禮拜五？？
大同區承德路一段1號4樓
sumire 菫樂

更改找吃飯的參與的人


更改小小哈吃飯的聯絡人

三小時要去東吳考試
忠孝復興站

買衣服活動地點改到東區


打球改成星期天並且自己去