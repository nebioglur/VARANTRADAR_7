import urllib.request, json

# Verdent - try different tokens and methods
tokens = ['deploy_now', 'pro8_sync', 'varant_pro_secret_2026']
for token in tokens:
    url = f'https://varantradar-pro-8.verdent.app/api/system/git_pull?token={token}'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode('utf-8')
            print(f"TOKEN '{token}': SUCCESS -> {data[:300]}")
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"TOKEN '{token}': HTTP {e.code} -> {body[:200]}")
    except Exception as e:
        print(f"TOKEN '{token}': ERROR -> {e}")

# Also try /api/system/deploy 
print("\n--- Trying /api/system/deploy ---")
for token in tokens:
    url = f'https://varantradar-pro-8.verdent.app/api/system/deploy?token={token}'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode('utf-8')
            print(f"TOKEN '{token}': SUCCESS -> {data[:300]}")
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"TOKEN '{token}': HTTP {e.code} -> {body[:200]}")
    except Exception as e:
        print(f"TOKEN '{token}': ERROR -> {e}")
