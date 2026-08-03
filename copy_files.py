import os
import shutil

src_dir = r"C:\Users\nebio\Desktop\VarantRadarPro"
dest_dir = os.path.join(src_dir, "varantradar_pro2")

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

items_to_copy = [
    "analysis", "config", "core", "data", "scanner", "ui", "utils", "decision", "services", "database",
    "execution", "engines", "portfolio", "ai_core", "api", "plugins", "learning", "validation", "varantradar_sdk",
    "server.py", "main.py", "run_bot.py", "app.py", "ai_engine.py", "requirements.txt", "render.yaml", "runtime.txt", "Dockerfile", ".gitignore",
    "check_intervals.py", "fetch_symbols.py", "update_symbols.py"
]

for item in items_to_copy:
    src_path = os.path.join(src_dir, item)
    dest_path = os.path.join(dest_dir, item)
    
    if os.path.exists(src_path):
        if os.path.isdir(src_path):
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            print(f"Copied directory: {item}")
        else:
            shutil.copy2(src_path, dest_path)
            print(f"Copied file: {item}")
    else:
        print(f"Warning: {item} does not exist in source directory.")

print("Copy completed successfully.")
