import subprocess
import time
import re
import sys
import os
import webbrowser

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def start_live_system():
    print("=" * 65)
    print("🚀 VARANTRADAR PRO - CANLI SUNUCU & DIŞ DÜNYA TÜNELİ BAŞLATILIYOR")
    print("=" * 65)
    
    workspace = r"C:\Users\nebioglur\Desktop\TUM MASAUSTU_Kurtarilan\TUM MASAUSTU\VarantRadarPro"
    os.chdir(workspace)
    
    # 1. Python Server başlat (arka planda)
    print("\n[1/2] Yerel Python sunucusu (Port 8080) başlatılıyor...")
    server_proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    # Server'ın portu dinlemesi için 3 saniye bekle
    time.sleep(3)
    
    # 2. Cloudflare Tunnel başlat ve URL'yi yakala
    print("[2/2] Güvenli Cloudflare HTTPS tüneli açılıyor...")
    cloudflared_path = os.path.join(workspace, "cloudflared.exe")
    
    tunnel_proc = subprocess.Popen(
        [cloudflared_path, "tunnel", "--url", "http://localhost:8080"],
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    tunnel_url = None
    start_time = time.time()
    
    # Output'tan .trycloudflare.com URL'sini yakala
    while time.time() - start_time < 20:
        line = tunnel_proc.stdout.readline()
        if not line:
            continue
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break
            
    print("\n" + "=" * 65)
    if tunnel_url:
        print("🎉 TEBRİKLER! UYGULAMANIZ CANLI YAYINDA!")
        print("=" * 65)
        print(f"\n📱 CEP TELEFONUNUZDAN VEYA İNTERNETTEN AÇILACAK LİNK:")
        print(f"\n👉 {tunnel_url}/#v8\n")
        print("=" * 65)
        print("ℹ️  Bu pencere açık kaldığı sürece telefonunuzdan ve her yerden")
        print("   VarantRadar Pro'ya ücretsiz, kesintisiz ve canlı bağlanabilirsiniz.")
        print("   (Kapatmak istediğinizde bu pencereyi kapatmanız yeterlidir.)")
        print("=" * 65)
        
        # Kullanıcının tarayıcısında da aç
        try:
            webbrowser.open(tunnel_url + "/#v8")
        except Exception:
            pass
    else:
        print("⚠️ Tünel URL'si beklenenden uzun sürdü, ancak sunucu çalışıyor.")
        print("Yerel Adres: http://localhost:8080")
    
    # Pencerenin açık kalmasını sağla
    try:
        while True:
            time.sleep(1)
            if server_proc.poll() is not None:
                print("Sunucu kapandı.")
                break
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
        server_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    start_live_system()
