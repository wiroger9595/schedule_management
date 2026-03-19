#!/bin/bash

# Ensure script stops on first error
set -e

echo "========================================="
echo "Building Flutter Web for Vercel Deployment"
echo "========================================="

# 1. 設置 Flutter 環境 (Vercel 本身沒有內建 Flutter，我們需要動態下載)
FLUTTER_VERSION="3.38.5" # 你可以根據你的專案修改對應版本
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

echo ">> Injecting environment variables into index.html..."
if [ ! -f ".env-stage" ]; then
  echo ">> .env-stage not found! Creating from Vercel system environment variables..."
  echo "WEB_CLIENT_ID=${WEB_CLIENT_ID:-644901002244-biqc0uracgbtr33cvkm50l3tpb6aap29.apps.googleusercontent.com}" > .env-stage
  echo "IOS_CLIENT_ID=${IOS_CLIENT_ID:-644901002244-soa2s80jbm0l9ne9jgdf7ifrq5rl7rac.apps.googleusercontent.com}" >> .env-stage
  echo "GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY:-AIzaSyCeppdyrBY73xJ-sZzqChzlzOc0u1nqgmc}" >> .env-stage
fi

# Apply to web/index.html (so placeholders get swapped before build)
if [ -f ".env-stage" ]; then
  export $(grep -v '^#' .env-stage | xargs)
  sed -i "s|<!-- <script src=\"https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY\"></script> -->|<script src=\"https://maps.googleapis.com/maps/api/js?key=$GOOGLE_MAPS_API_KEY\&loading=async\" async defer></script>|g" web/index.html
fi

flutter config --enable-web
flutter build web --release --dart-define=ENV=stage --dart-define-from-file=.env-stage --base-href "/"

echo "========================================="
echo "✅ Vercel 編譯完成！"
echo "========================================="
