# Hướng dẫn chạy Kotoba Designer trên Windows

Chào bạn! Vì Windows không hỗ trợ hiển thị giao diện Linux trực tiếp từ Docker như Mac, bạn cần cài đặt một "Cửa sổ hiển thị" (X Server).

## Lưu ý quan trọng
Bản image trên Docker Hub hiện đã hỗ trợ **Multi-Arch**, nghĩa là máy Windows (chip Intel/AMD) của bạn sẽ tự động chạy được sau khi cài đặt các bước dưới đây.

### 1. Cài đặt VcXsrv (Miễn phí)
1. Tải về và cài đặt **VcXsrv Windows X Server** từ [SourceForge](https://sourceforge.net/projects/vcxsrv/).
2. Sau khi cài xong, mở ứng dụng **XLaunch** từ menu Start.
3. Cấu hình các bước như sau:
   - **Display settings**: Chọn "Multiple windows".
   - **Select how to start client**: Chọn "Start no client".
   - **Extra settings**: **BẮT BUỘC** tích chọn **"Disable access control"**.
   - Nhấn "Finish" để bắt đầu server.

### 2. Cho phép kết nối qua Firewall
Khi chạy XLaunch lần đầu, Windows Firewall sẽ hiện thông báo. Bạn hãy tích chọn **cho phép (Allow)** cả "Private" và "Public" networks.

### 3. Cấu hình Docker Compose
Trên máy Windows, bạn sẽ dùng file `docker-compose.user.yml` nhưng cần thay đổi dòng `DISPLAY` một chút:

1. Mở file `docker-compose.user.yml`.
2. Sửa dòng `DISPLAY=host.docker.internal:0` thành:
   ```yaml
   environment:
     - DISPLAY=YOUR_IP_ADDRESS:0.0
   ```
   *(Thay `YOUR_IP_ADDRESS` bằng địa chỉ IP nội bộ của máy Windows của bạn, ví dụ: `192.168.1.5`)*.

### 4. Chạy ứng dụng
Mở Windows Terminal hoặc PowerShell tại thư mục chứa file:
```powershell
docker-compose -f docker-compose.user.yml up
```

Chúc bạn có trải nghiệm tuyệt vời với Kotoba Designer!
