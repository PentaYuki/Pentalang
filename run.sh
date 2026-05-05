#!/bin/bash

# 🌸 Kotoba Designer Runner

echo "=========================================="
echo "   🌸 KOTOBA DESIGNER (言葉デザイナー) 🌸   "
echo "=========================================="

# 1. Check for Virtual Environment
if [ -d ".venv" ]; then
    echo "📦 Đang kích hoạt môi trường ảo (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Đang kích hoạt môi trường ảo (venv)..."
    source venv/bin/activate
else
    echo "⚠️  Không tìm thấy thư mục môi trường ảo (.venv). Đang dùng Python hệ thống..."
fi

# 2. Check for VoiceVox (Port 8081 check)
# we use lsof or nc to check if something is listening
if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 8081 > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "📢 [Cảnh báo] Không tìm thấy VoiceVox trên port 8081."
        echo "   -> Hãy chắc chắn bạn đã khởi động VoiceVox Engine để Yuki có thể nói chuyện nhé!"
    else
        echo "🔊 [OK] Đã tìm thấy VoiceVox Engine."
    fi
fi

# 3. Launch the Application
echo "🚀 Đang khởi động ứng dụng..."
python3 kotoba_designer.py

echo "=========================================="
echo "   👋 Hẹn gặp lại Onii-san sau nhé!       "
echo "=========================================="
