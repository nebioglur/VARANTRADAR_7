from services.trade_database import get_connection
owner = "sb:498f6314-9087-472a-88ea-b1b59e237f16"
conn = get_connection()
c = conn.cursor()
c.execute("UPDATE app_users SET cash_balance = 107770 WHERE owner_key = %s", (owner,))
conn.commit()
print("Updated cash!")
