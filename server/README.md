Walkthrough - PostgreSQL & Redis Integration
I have successfully integrated PostgreSQL and Redis into the Python backend and optimized the Flutter application to handle authentication securely.

Changes
Server (Python/FastAPI)
Database: Configured SQLModel with asyncpg to connect to PostgreSQL.
Cache: Configured redis.asyncio to connect to Redis for token management.
Authentication: Implemented full JWT-based authentication (/auth/register, /auth/token).
Tokens are whitelisted in Redis for the duration of their validity (30 minutes).
Models: Defined 
User
 and 
Schedule
 models mapping to database tables.
API: Refactored 
main.py
 to use the database for schedule operations.
Mobile (Flutter)
Auth Service: Updated to match the backend's OAuth2 form-data requirement for login.
API Service: Added automatic logout on 401 Unauthorized responses.
Security: Ensured tokens are stored using flutter_secure_storage.
Verification Results
Server Code Integrity
Ran a python script to import all new modules (app.models, app.auth, app.database).

python3 -c "from app.models import User; from app.auth import router; print('Imports successful')"
# Output: Imports successful
Next Steps
Ensure you have PostgreSQL and Redis running locally.
Run the server:
cd server
source venv/bin/activate
uvicorn main:app --reload
Run the mobile app:
cd mobile
flutter run



// 跑之前記得
pip install -r requirements.txt

// 下個月跟小明去淡水碼頭

// 明年五月要跟阿糖，阿文，po-a 去爬大屯山

5月7號，先幫我預計先記錄6點

// 下下週跟小美去台北車站打遊戲

我要更改與文哥見面的時間

// 今年9月要去泰國普吉島旅遊

下禮拜天 
早上11點

下下週三

// 2026 2 24
詳細地址
改用精準地圖 api 服務商

// @ 新增 修改
// 新增 提示用戶 後到聯絡人 新增手機

我要更改打球時間
我要更改見面時間
建國高速公路下的籃球場
我的打球的時間還要改地點

// 通知橫幅 

// ai 要加通行方式
   ai 確認時間時要回覆確切時間
   為主畫面


// ai 




// 啟動方式
# iOS
flutter clean && flutter run --dart-define-from-file=.env
# Web
flutter clean && flutter run -d chrome --web-port=7800 --dart-define-from-file=.env


// 上版語法
./deploy.sh



