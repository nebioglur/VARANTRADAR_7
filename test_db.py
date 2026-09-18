
from services.trade_database import get_connection
conn = get_connection()
cur = conn.cursor()
cur.execute('INSERT INTO live_settings (key, value) VALUES (''test'', ''123'') ON CONFLICT DO NOTHING')
conn.commit()
cur.execute('SELECT * FROM live_settings WHERE key=''test''')
print(cur.fetchone())

