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



// RAG 練習
完整指南已寫入 server/RAG_TRAINING_GUIDE.md，涵蓋 7 個章節：

你以後可以自己做的步驟
🔄 每次優化的標準流程（5 步驟）

# Step 1: 跑測試找出失敗
python run_test_v2.py --provider cerebras --n 90 --rag

# Step 2: 看哪些案例失敗（指南有給查詢腳本）

# Step 3: 建訓練檔案
touch server/app/data/rag_<topic>.py

# Step 4: 灌入資料庫（指南有腳本範本）

# Step 5: 重跑測試驗證提升
python run_test_v2.py --provider cerebras --n 90 --rag
指南最有用的部分
✨ 第 3 章：如何寫「好」範例
最有效的技巧 = 對比組（4 個相似輸入，不同結果）：


# 缺地點 → False
{"user_message": "明天3點打球", "is_complete": False},
# 齊全 → True  
{"user_message": "明天3點在大安公園打球", "is_complete": True},
# 多人齊全 → True
{"user_message": "明天3點跟小明在大安公園打球", "is_complete": True},
# 多人缺地點 → False
{"user_message": "明天3點跟小明打球", "is_complete": False},
✨ 第 5 章：失敗驅動的迭代循環
每輪預期改進：

Round 1：51% → 58%（基礎範例）
Round 2：58% → 62%（自動回灌）
Round 3：62% → 67%（過期行程）
Round 4：67% → 72%（補其他類別）
5+ 輪後 plateau → 考慮 fine-tune
✨ 第 7 章：建議補的訓練檔案
按優先順序：

rag_edge_cases.py — 邊界情況
rag_parsing.py — 時間/地點解析
rag_location.py — 地點歧義
rag_validation.py — 資料驗證
rag_intent.py — 意圖邊界
自助診斷模板
每次新增範例後，照指南第 6 章的檢查清單跑：

 中文 + 英文都有？
 ≥ 10 個範例？
 有正反對比？
 每個都有 rule？
 邊界有覆蓋？
 不和既有範例衝突？
 灌 DB 後測試驗證？
接下來你就可以完全自主建任何主題的 RAG 訓練資料了。🎉