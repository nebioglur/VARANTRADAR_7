from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
driver = webdriver.Edge(options=opts)

driver.get('https://varantradarpro.pythonanywhere.com/login')
time.sleep(2)
driver.find_element(By.ID, 'classic-user').send_keys('nebioglur')
driver.find_element(By.ID, 'classic-pass').send_keys('123')
driver.find_element(By.CSS_SELECTOR, "form[action='/login'] button[type='submit']").click()
time.sleep(3)

driver.get('https://varantradarpro.pythonanywhere.com/#home')
time.sleep(4)

# 1. Check if market closed warning is displayed
try:
    warning = driver.find_element(By.ID, 'market-closed-warning')
    print('Market closed warning displayed?:', warning.is_displayed())
except Exception as e:
    print('Warning element check error:', e)

# 2. Check shield status text
try:
    shield = driver.find_element(By.ID, 'shield-status')
    print('Shield status text:', shield.text.encode('ascii', errors='replace').decode('ascii'))
except Exception as e:
    print('Shield element error:', e)

# 3. Check first row of all stocks table
try:
    tbody = driver.find_element(By.ID, 'tb-all-stocks-home')
    first_row = tbody.find_elements(By.TAG_NAME, 'tr')[0]
    tds = [td.text.encode('ascii', errors='replace').decode('ascii') for td in first_row.find_elements(By.TAG_NAME, 'td')]
    print('First row columns count:', len(tds))
    print('Row values:')
    headers = ['Hisse', 'Fiyat', 'Önc.Kapanış', 'Değişim', 'GünİçiGüç%', 'SaatlikAkış', 'Hacim(TL)', 'HacimGücü%', '⭐ PUAN', '🛡️ GÜVEN', 'İşlem']
    for h, val in zip(headers, tds):
        print(f"  {h:15}: {val}")
except Exception as e:
    print('Table check error:', e)

driver.quit()
