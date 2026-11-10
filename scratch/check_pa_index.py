import urllib.request
url = 'https://varantradarpro.pythonanywhere.com/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = resp.read().decode('utf-8', errors='ignore')
print("Total length:", len(data))
print("First 500 chars:\n", data[:500])
print("\nLast 500 chars:\n", data[-500:])
