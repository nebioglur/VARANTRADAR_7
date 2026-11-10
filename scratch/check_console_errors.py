from selenium import webdriver
from selenium.webdriver.edge.options import Options
import time

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
opts.set_capability('ms:loggingPrefs', {'browser': 'ALL'})
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

try:
    driver = webdriver.Edge(options=opts)
except Exception as e:
    print("Could not start Edge webdriver:", e)
    exit(1)

print("Navigating to https://varantradarpro.pythonanywhere.com/#home ...")
driver.get("https://varantradarpro.pythonanywhere.com/#home")
time.sleep(4)

try:
    logs = driver.get_log('browser')
    print(f"Browser logs count: {len(logs)}")
    for log in logs:
        print(f"[{log.get('level')}] {log.get('message')}")
except Exception as e:
    print("Error getting logs:", e)

# Also check clock element text
try:
    clock = driver.find_element("id", "live-clock")
    date = driver.find_element("id", "live-date")
    print("Live clock text:", clock.text)
    print("Live date text:", date.text)
except Exception as e:
    print("Error getting clock text:", e)

driver.quit()
