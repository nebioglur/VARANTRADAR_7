import logging
import os
from logging.handlers import RotatingFileHandler
from config.constants import PATH_LOGS

def setup_logger():
    # Klasör yoksa oluştur
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), PATH_LOGS)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger("VarantRadar")
    
    # Eğer daha önce handler eklendiyse tekrar ekleme (Streamlit re-run sorunu)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Konsol çıktısı
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        
        # Dosya çıktısı (Rotating: 5MB üzeri dosyayı böler, 5 yedek tutar)
        log_file = os.path.join(log_dir, 'app.log')
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
    return logger

logger = setup_logger()
