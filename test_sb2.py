import os
from supabase import create_client, Client

url = "https://kfslwkmrnjqxirzhfmbn.supabase.co"
key = "sb_publishable_r2tfnmKF3dq_I1YkqGi-Bw_O38IUlEj----sb_publishable_RP_ouZJiDHK_PA_3o1dmfg_G5BgAuzl"
try:
    supabase: Client = create_client(url, key)
    tables_to_test = ['trades', 'v8_signals', 'tavan_audits', 'dashboard_cache', 'signals']
    for tbl in tables_to_test:
        try:
            res = supabase.table(tbl).select("*").limit(1).execute()
            print(f"TABLE {tbl} EXISTS! Data len: {len(res.data)}")
        except Exception as e:
            print(f"TABLE {tbl} ERROR: {e}")
except Exception as e:
    print(f"INIT ERROR: {e}")
