import os
from pathlib import Path

# 📂 Cấu hình các file muốn lấy
INCLUDE_EXTS = ['.py', '.json', '.sh', '.md', '.txt', '.yml']
EXCLUDE_DIRS = ['.venv', 'venv', '__pycache__', 'voice', 'models', '.git', '.gemini', 'voicevox']
EXCLUDE_FILES = ['.DS_Store', 'package-lock.json']

def export_source_code(output_file="project_full_source.txt"):
    root_dir = Path(__file__).parent
    count = 0
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"================================================\n")
        out.write(f"   KOTOBA DESIGNER - FULL SOURCE EXPORT\n")
        out.write(f"================================================\n\n")
        
        for root, dirs, files in os.walk(root_dir):
            # Loại bỏ các thư mục không muốn lấy
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(root_dir)
                
                # Kiểm tra định dạng file
                if file_path.suffix in INCLUDE_EXTS or file in ['Dockerfile', '.gitignore']:
                    if file not in EXCLUDE_FILES:
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            
                            out.write(f"\n\n{'#'*80}\n")
                            out.write(f"FILE: {rel_path}\n")
                            out.write(f"{'#'*80}\n\n")
                            out.write(content)
                            out.write("\n")
                            
                            print(f"✅ Đã thêm: {rel_path}")
                            count += 1
                        except Exception as e:
                            print(f"❌ Lỗi đọc file {rel_path}: {e}")
                            
    print(f"\n✨ XONG! Đã gom {count} file vào: {output_file}")

if __name__ == "__main__":
    export_source_code()
