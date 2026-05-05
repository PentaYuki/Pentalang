#!/bin/bash
set -e

# Đảm bảo PATH có đầy đủ các thư mục chứa lệnh Docker và Credential Helper
export PATH=$PATH:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Applications/Docker.app/Contents/Resources/bin

# Configuration
REPO="gooleseswsq11/pentalang"
TAG="latest"
ARCH=$(uname -m)

echo "📦 Đang đóng gói Kotoba Designer cho Docker Hub..."

# 1. Đăng nhập (nếu chưa)
if ! docker info > /dev/null 2>&1; then
    echo "❌ Lỗi: Docker chưa chạy hoặc không có quyền truy cập."
    echo "Gợi ý: Hãy mở ứng dụng Docker Desktop trên Mac của bạn."
    exit 1
fi

# 2. Build và Push Image Đa nền tảng (Intel & Apple Silicon)
echo "🛠  Đang build image đa nền tảng (linux/amd64, linux/arm64)..."
echo "⚠️  Lưu ý: Quá trình này có thể tốn 5-10 phút."
docker buildx build --platform linux/amd64,linux/arm64 -t $REPO:$TAG --push .

echo "✅ Hoàn tất! Người dùng khác hiện có thể chạy bằng file docker-compose.user.yml"
