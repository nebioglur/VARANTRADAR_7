import os

def search_files(directory, keyword):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or '__pycache__' in root or 'varantradar_pro2' in root:
            continue
        for file in files:
            if file.endswith('.py') or file.endswith('.json'):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if keyword.lower() in line.lower():
                                print(f"{os.path.join(root, file)}:{i+1}: {line.strip()}")
                except Exception as e:
                    pass

search_files(r"C:\Users\nebio\Desktop\VarantRadarPro", "telegram")
