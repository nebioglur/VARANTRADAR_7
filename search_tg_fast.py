import os

def search_files(directory, keyword):
    target_dirs = ["api", "config", "core", "utils", "scanner", "analysis", "services"]
    target_files = ["server.py", "main.py", "app.py"]
    
    for item in os.listdir(directory):
        path = os.path.join(directory, item)
        if os.path.isdir(path) and item in target_dirs:
            for root, dirs, files in os.walk(path):
                if '__pycache__' in root:
                    continue
                for file in files:
                    if file.endswith('.py'):
                        try:
                            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                for i, line in enumerate(f.readlines()):
                                    if keyword.lower() in line.lower():
                                        print(f"{os.path.join(root, file)}:{i+1}: {line.strip()}")
                        except:
                            pass
        elif os.path.isfile(path) and item in target_files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f.readlines()):
                        if keyword.lower() in line.lower():
                            print(f"{path}:{i+1}: {line.strip()}")
            except:
                pass

search_files(r"C:\Users\nebio\Desktop\VarantRadarPro", "send_radar_alert")
