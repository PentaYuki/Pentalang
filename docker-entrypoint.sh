#!/bin/bash
set -e

echo "🚀 Khởi động Kotoba Designer trong Docker..."

# Chạy setup để tải model nếu chưa có
./setup_models.sh

# Kiểm tra DISPLAY
if [ -z "$DISPLAY" ]; then
    echo "⚠️  CẢNH BÁO: Biến DISPLAY chưa được thiết lập. GUI sẽ không hiển thị được!"
fi

# Chạy ứng dụng chính
exec python kotoba_designer.py
