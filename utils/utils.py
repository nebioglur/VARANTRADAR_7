import json
import os
from config.constants import PATH_EXPORTS

def load_json(filepath):
    """JSON dosyasını güvenli şekilde okur"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        from utils.logger import logger
        logger.error(f"Error reading JSON {filepath}: {e}")
    return {}

def save_json(data, filepath):
    """JSON verisini güvenli şekilde yazar"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        from utils.logger import logger
        logger.error(f"Error writing JSON {filepath}: {e}")
        return False

def ensure_dirs():
    """Gerekli klasörlerin var olduğundan emin olur"""
    dirs_to_create = ["logs", "database", "exports"]
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    for d in dirs_to_create:
        dir_path = os.path.join(base_dir, d)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
