import os
import shutil
from pathlib import Path

# 📂 Cấu hình các file và thư mục
INCLUDE_EXTS = ['.py', '.json', '.sh', '.md', '.txt', '.yml', '.yaml', '.dockerfile']
INCLUDE_FILES = ['Dockerfile', '.gitignore', 'requirements.txt']
EXCLUDE_DIRS = ['.venv', 'venv', '__pycache__', 'voice', 'models', '.git', '.gemini', 'voicevox', 'backup_source']

def backup_project_source(dest_folder="backup_source"):
    root_dir = Path(__file__).parent
    dest_path = root_dir / dest_folder
    
    # Xóa thư mục cũ nếu có để làm mới
    if dest_path.exists():
        shutil.rmtree(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    count = 0
    print(f"🚀 Bắt đầu sao lưu vào thư mục: {dest_folder}...")

    for root, dirs, files in os.walk(root_dir):
        # Loại bỏ các thư mục không muốn lấy
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(root_dir)
            
            # Kiểm tra định dạng file hoặc tên file cụ thể
            should_copy = (file_path.suffix.lower() in INCLUDE_EXTS) or (file in INCLUDE_FILES)
            
            if should_copy:
                target_path = dest_path / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(file_path, target_path)
                print(f"  + Copy: {rel_path}")
                count += 1

    print(f"\n✨ XONG! Đã sao lưu {count} file vào thư mục: {dest_folder}/")

if __name__ == "__main__":
    backup_project_source()
