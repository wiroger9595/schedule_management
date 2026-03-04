#!/bin/bash

# Ensure script stops on first error
set -e

echo "========================================="
echo "Starting Flutter Web build and deployment to GitHub Pages"
echo "========================================="

# 1. 確保你目前在 mobile 目錄下
if [ ! -f "pubspec.yaml" ]; then
    echo "❌ 錯誤：找不到 pubspec.yaml。請確定你是在 mobile 或專案根目錄下執行。"
    echo "如果是，請在 mobile 目錄底下執行此腳本。"
    exit 1
fi

# 2. 清理之前建立的檔案並安裝依賴
echo ">> 清理專案與讀取 packages..."
flutter clean
flutter pub get

# 3. 建立 Flutter Web 應用程式
# 注意：這裡的 --base-href 需要改成你的 GitHub Repository 名稱！
# 例如，如果你的 GitHub repo URL 是 https://github.com/myusername/my-flutter-app
# 則下面的 --base-href 就要寫成 '/my-flutter-app/'
# 💡 若你是部署在 User/Organization Page (例如: myusername.github.io)，請將 --base-href 設為 '/'
REPO_NAME="schedule_management"
echo ">> 正在編譯 Flutter Web 版本 (設定 base-href 為 '/${REPO_NAME}/', 環境變數 ENV=stage)..."
flutter build web --release --dart-define=ENV=stage --base-href "/${REPO_NAME}/"

# 4. 進入編譯後的目錄
cd build/web

# 5. 初始化一個新的 Git 儲存庫
echo ">> 初始化暫時的 git 儲存庫並推送到 gh-pages 分支..."
git init
git checkout -B gh-pages
git add -A
git commit -m "Deploy Flutter Web to GitHub Pages"

# 6. 推送至 GitHub 的 gh-pages 分支
# 請確保你在此腳本的上一層 (專案根目錄) 已經綁定過 GitHub Remote (通常是 origin)
# 這裡會強制覆蓋 (-f) 遠端的 gh-pages 分支
git push -f git@github.com:wiroger9595/schedule_management.git gh-pages

echo "========================================="
echo "✅ 成功部署至 GitHub Pages！"
echo "請到你 GitHub 儲存庫的 [Settings > Pages] 確認："
echo "  1. Source 是否已經選取為 'gh-pages' 分支"
echo "  2. 按下 Save 之後，大約等幾分鐘，GitHub 就會產生你的專屬連結！"
echo "========================================="
