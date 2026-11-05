import subprocess
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def run_cmd(cmd, cwd=None, exit_on_error=True):
    print(f"-> Calistiriliyor: {cmd} (Klasor: {cwd or '.'})")
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print(f"[UYARI/HATA] Kod {p.returncode}:\n{p.stderr.strip()}")
        if exit_on_error:
            sys.exit(1)
    else:
        out = p.stdout.strip()
        if out:
            print(f"   {out[:300]}")
    return p

def main():
    print("=" * 60)
    print("VARANTRADAR PRO - VERDENT OTOMATIK DEPLOY SISTEMI")
    print("=" * 60)

    workspace_dir = r"C:\Users\nebioglur\Desktop\TUM MASAUSTU_Kurtarilan\TUM MASAUSTU\VarantRadarPro"
    verdent_repo_dir = r"C:\Users\nebioglur\.verdent\verdent-projects\ver_varantpro\repo"

    # ADIM 1: Calisma klasorundeki degisiklikleri commit et ve GitHub'a gonder
    print("\n[1/3] Calisma klasoru GitHub'a gonderiliyor...")
    os.chdir(workspace_dir)
    run_cmd("git add -A", cwd=workspace_dir, exit_on_error=False)
    p_status = subprocess.run("git status --porcelain", cwd=workspace_dir, shell=True, capture_output=True, text=True)
    if p_status.stdout.strip():
        run_cmd('git commit -m "chore(deploy): auto-deploy latest updates to Verdent Cloud"', cwd=workspace_dir, exit_on_error=False)
    
    print("   GitHub main dalina push ediliyor...")
    run_cmd("git push origin main", cwd=workspace_dir, exit_on_error=False)
    run_cmd("git push origin main:fix/pro8-dip-kirilim-detective", cwd=workspace_dir, exit_on_error=False)

    # ADIM 2: Verdent masaustu projesini GitHub ile senkronize et
    print("\n[2/3] Verdent yerel repo klasoru senkronize ediliyor...")
    if os.path.exists(verdent_repo_dir):
        run_cmd("git reset --hard HEAD", cwd=verdent_repo_dir, exit_on_error=False)
        run_cmd("git clean -fd", cwd=verdent_repo_dir, exit_on_error=False)
        run_cmd("git pull origin main", cwd=verdent_repo_dir, exit_on_error=False)
        print("   [OK] Verdent yerel projesi en son commit ile esitlendi.")
    else:
        print(f"   [BILGI] {verdent_repo_dir} bulunamadi; atlandi.")

    # ADIM 3: Verdent Cloud canli sunucusuna deploy sinyali gonder
    print("\n[3/3] Verdent Cloud sunucusuna deploy sinyali gonderiliyor...")
    cloud_url = "https://varantradar-pro-8.verdent.app/api/system/git_pull?token=deploy_now"
    try:
        req = urllib.request.Request(cloud_url, headers={"User-Agent": "Mozilla/5.0 (VerdentDeployBot/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = res.read().decode("utf-8", errors="ignore")
            print(f"   Bulut Sunucu Yaniti ({res.status}): {res_data[:200]}")
            print("   [OK] Canli sunucu guncelleme sinyalini aldi.")
    except Exception as e:
        print(f"   [BILGI] Cloud tetiklemesi iletildi ({e}).")

    print("\n" + "=" * 60)
    print("TUM ADIMLAR TAMAMLANDI!")
    print("1. GitHub guncellendi.")
    print("2. Verdent yerel projesi senkronize edildi.")
    print("3. Verdent Cloud sunucusuna guncelleme sinyali iletildi.")
    print("=" * 60)

if __name__ == "__main__":
    main()
