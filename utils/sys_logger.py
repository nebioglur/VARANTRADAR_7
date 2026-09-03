
import os
from datetime import datetime

def log_error(module: str, message: str):
    os.makedirs("data", exist_ok=True)
    with open("data/system_logs.txt", "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{ts}] [{module}] ERROR: {message}\n")
        
def log_info(module: str, message: str):
    os.makedirs("data", exist_ok=True)
    with open("data/system_logs.txt", "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{ts}] [{module}] INFO: {message}\n")
