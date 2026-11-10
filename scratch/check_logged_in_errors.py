from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=375,812') # Mobile viewport like user's phone!
opts.set_capability('ms:loggingPrefs', {'browser': 'ALL'})
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Edge(options=opts)
print("1. Opening /login ...")
driver.get("https://varantradarpro.pythonanywhere.com/login")
time.sleep(2)

# Find username and password inputs
user_inp = driver.find_element(By.ID, "classic-user")
pass_inp = driver.find_element(By.ID, "classic-pass")
user_inp.send_keys("nebioglur")
pass_inp.send_keys("123")

# Click classic login button
login_btn = driver.find_element(By.CSS_SELECTOR, "form[action='/login'] button[type='submit']")
login_btn.click()
time.sleep(3)

print("2. Current URL after login:", driver.current_url)

# Navigate to #home
driver.get("https://varantradarpro.pythonanywhere.com/#home")
time.sleep(5)

print("\n--- BROWSER CONSOLE LOGS ---")
logs = driver.get_log('browser')
for log in logs:
    lvl = log.get('level')
    msg = log.get('message')
    if lvl in ['SEVERE', 'ERROR', 'WARNING']:
        print(f"[{lvl}] {msg}")
    elif 'DASHBOARD' in msg or 'RENDER' in msg or 'CLOCK' in msg:
        print(f"[{lvl}] {msg}")

# Check clock and text
try:
    clock = driver.find_element(By.ID, "live-clock")
    date = driver.find_element(By.ID, "live-date")
    print(f"\nClock: '{clock.text}', Date: '{date.text}'")
except Exception as e:
    print("Clock element error:", e)

# Check all stocks table content
try:
    tbody = driver.find_element(By.ID, "tb-all-stocks-home")
    print(f"All stocks table snippet: {tbody.text[:200]}")
except Exception as e:
    print("All stocks table error:", e)

driver.quit()
