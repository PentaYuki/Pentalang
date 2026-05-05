# 🌸 Kotoba Designer (言葉デザイナー) — AI-Powered Japanese Learning
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/qt-for-python)
[![MLX](https://img.shields.io/badge/Optimized-Apple_Silicon_MLX-000000?logo=apple&logoColor=white)](https://github.com/ml-explore/mlx)
[![VoiceVox](https://img.shields.io/badge/Voice-VoiceVox-FF69B4)](https://voicevox.hiroshiba.jp/)

**Kotoba Designer** là một hệ thống thiết kế bài học tiếng Nhật trực quan (Node-Based) kết hợp sức mạnh của **AI Local** và **Voice Synthesis**. Bạn có thể xây dựng cấu trúc bài học bằng cách kéo thả các khối từ vựng, ngữ pháp và để trợ lý ảo **Yuki** giúp bạn ôn luyện thông qua các trò chơi tương tác thông minh.

---

## ✨ Tính năng Nổi bật (Core Features)

### 1. 🏗️ Visual Lesson Editor (Node-Based)
- **Thiết kế bài học bằng tư duy sơ đồ**: Thay vì danh sách từ vựng khô khan, bạn tạo các khối (Node) và kết nối chúng bằng dây dẫn (Wires).
- **Phân loại thông minh**: Hỗ trợ các khối Từ vựng (`Kotoba`), Ngữ pháp (`Grammar`) và các Nhóm (`Group`) để tổ chức bài học khoa học.
- **Tự động hóa**: Hệ thống tự động dán nhãn các liên kết và sinh dữ liệu JSON để AI có thể hiểu được ý tưởng thiết kế của bạn.

### 2. 🤖 Trợ lý AI Yuki (The Kawaii Assistant)
- **Cá tính sống động**: Yuki không chỉ là một bot chat; cô ấy có cá tính "Kawaii", hay gọi bạn là "Onii-san" và sử dụng rất nhiều emoji Nhật Bản.
- **Hệ thống cảm xúc & âm đệm**: Yuki biết sử dụng các từ đệm tự nhiên như *"Eh?", "Waa!", "Yatta!"* nhờ tích hợp sâu với VoiceVox.
- **Phản hồi theo năng lực (Tiered Rewards)**: Yuki sẽ khen ngợi nồng nhiệt nếu bạn đạt điểm cao (Rank S/A) và an ủi, động viên chân thành nếu bạn làm bài chưa tốt (Rank C).

### 3. 🎮 Hệ thống Trò chơi & Gamification
- **Game 1 — Nazonazo (なぞなぞ)**: Giải đố tiếng Nhật kết hợp kiến thức Văn hóa ⛩, Du lịch 🌸, Anime 🎌 và Yōkai 👺.
- **Game 2 — Design Quiz**: AI tự động phân tích sơ đồ bài học bạn vừa vẽ để tạo ra các câu hỏi tình huống thực tế.
- **Hệ thống Điểm & Streak**: Theo dõi tiến độ học tập hàng ngày, tích lũy điểm thưởng và duy trì chuỗi ngày học tập (Streak) để nhận phần thưởng đặc biệt từ Yuki.
- **Năng lượng & Thể lực**: Cơ chế giới hạn năng lượng học tập hàng ngày giúp bạn phân bổ thời gian học hợp lý, tránh quá tải.

### 4. 🚀 Tối ưu hóa Apple Silicon (MLX Support)
- **Siêu tốc độ trên Mac**: Hỗ trợ native framework **MLX** của Apple, cho phép chạy các mô hình ngôn ngữ lớn (LLM) như **Qwen2** hay **Gemma 2** với tốc độ cực nhanh và tiết kiệm RAM tối đa trên chip M1/M2/M3/M4.
- **Chế độ dự phòng**: Tự động chuyển đổi giữa MLX (cho Mac) và llama.cpp (cho GGUF) để đảm bảo tính ổn định trên mọi nền tảng.

---

## 🛠️ Công nghệ Sử dụng (Tech Stack)

| Thành phần | Công nghệ |
| :--- | :--- |
| **Giao diện (UI)** | Python + PySide6 (Qt) |
| **Đồ họa Node** | Custom QGraphicsScene/View với Bezier curves |
| **AI Backend (Local)** | llama.cpp (GGUF) & MLX-LM (Apple Silicon) |
| **Mô hình ngôn ngữ** | Qwen2, Gemma 2, Llama 3 (Bonsai-8B) |
| **Giọng nói (TTS)** | VoiceVox HTTP Client |
| **Lưu trữ** | JSON-based data structure |

---

## 📂 Cấu trúc Thư mục

```text
PentaLang/
├── kotoba_designer.py    # GUI chính, quản lý editor và các khối node
├── Ai.py                 # "Bộ não" của hệ thống (LLM Client, Quiz Engine, Voice Enhancer)
├── data/
│   └── lesson/           # Nơi lưu trữ file bài học (.json)
├── voice/                # Cache âm thanh đã được sinh ra
├── models/               # Thư mục chứa các file mô hình LLM (.gguf hoặc MLX dir)
└── .venv/                # Môi trường ảo Python
```

---

## 🚀 Cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- **OS**: Windows, macOS (Khuyến khích Apple Silicon), hoặc Linux.
- **Python**: 3.10 trở lên.
- **VoiceVox Engine**: Cần khởi chạy VoiceVox Server trên port `8081`.

### 2. Cài đặt thư viện
```bash
python3 -m pip install PySide6 requests urllib3 mlx-lm google-generativeai
```

### 3. Chuẩn bị mô hình (LLM)
Hệ thống sẽ tự động tìm kiếm mô hình trong thư mục `models/` theo thứ tự ưu tiên:
1. `mlx-qwen2-7b` (Thư mục MLX)
2. `swallow-gemma-2-9b-it.gguf`
3. `qwen2-7b-instruct.gguf`
4. `Bonsai-8B.gguf`

### 4. Khởi chạy
```bash
python3 kotoba_designer.py
```

---

## 🎨 Tùy chỉnh (Configuration)

- **AI Persona**: Bạn có thể chỉnh sửa tính cách của Yuki trong class `BonsaiLLM` tại file `Ai.py`.
- **API Keys**: Hỗ trợ tích hợp **Gemini 1.5 Flash** nếu bạn có API Key (giúp Yuki thông minh hơn cả bản Local).
- **Themes**: Giao diện được thiết kế theo phong cách Dark-mode hiện đại, có thể tùy chỉnh màu sắc trong `kotoba_designer.py`.

---

*Học tiếng Nhật không chỉ là học từ vựng, mà là thiết kế trải nghiệm văn hóa của chính bạn.* 🌸
