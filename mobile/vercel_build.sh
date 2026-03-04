#!/bin/bash

# Ensure script stops on first error
set -e

echo "========================================="
echo "Building Flutter Web for Vercel Deployment"
echo "========================================="

# 1. 設置 Flutter 環境 (Vercel 本身沒有內建 Flutter，我們需要動態下載)
FLUTTER_VERSION="3.29.0" # 你可以根據你的專案修改對應版本
FLUTTER_SDK_URL="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"

if [ ! -d "flutter" ]; then
    echo ">> 下載 Flutter SDK (${FLUTTER_VERSION})..."
    curl -O $FLUTTER_SDK_URL
    tar xf flutter_linux_${FLUTTER_VERSION}-stable.tar.xz
    rm flutter_linux_${FLUTTER_VERSION}-stable.tar.xz
fi

# 將 Flutter 加入環境變數
export PATH="$PATH:`pwd`/flutter/bin"
export FLUTTER_ROOT="`pwd`/flutter"
export FORCE_FLUTTER_RUN_AS_ROOT=true
git config --global --add safe.directory $(pwd)/flutter
git config --global --add safe.directory /vercel/path0/mobile/flutter

# Disable telemetry completely to bypass interactive prompts
export FLUTTER_WEB=true
export PUB_HOSTED_URL="https://pub.dartlang.org"
flutter config --no-analytics > /dev/null 2>&1
dart --disable-analytics > /dev/null 2>&1

# 4. 安裝依賴與編譯
echo ">> 清理並安裝 packages..."
flutter clean
flutter pub get

# 5. 編譯 Flutter Web (使用 stage 環境配置)
# Vercel 預設是在根目錄 `/` 運行，所以 `--base-href "/"`
echo ">> 正在編譯 Flutter Web 版本 (設定 base-href 為 '/', 環境變數 ENV=stage)..."
echo ">> Injecting environment variables into index.html..."
if [ -f ".env-stage" ]; then
  export $(grep -v '^#' .env-stage | xargs)
  sed -i "s|YOUR_WEB_CLIENT_ID.apps.googleusercontent.com|$WEB_CLIENT_ID|g" web/index.html
  sed -i "s|<!-- <script src=\"https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY\"></script> -->|<script src=\"https://maps.googleapis.com/maps/api/js?key=$GOOGLE_MAPS_API_KEY\"></script>|g" web/index.html
fi

flutter config --enable-web
flutter build web --release --dart-define=ENV=stage --dart-define-from-file=.env-stage --base-href "/"

echo "========================================="
echo "✅ Vercel 編譯完成！"
echo "========================================="
