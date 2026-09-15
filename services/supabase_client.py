import os
import json
from supabase import create_client, Client

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://supabase-api-prod.verdent.ai/p/pf565ccea3c6a9b19d28e')
SUPABASE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoyMTA1MTI2MzA2LCJpYXQiOjE3ODk1MDcxMDYsImlzcyI6InN1cGFiYXNlIiwicHJvamVjdF9yZWYiOiJwZjU2NWNjZWEzYzZhOWIxOWQyOGUiLCJyb2xlIjoiYW5vbiJ9.cG_7QJGV7r0n7JIrvsSb2G1lnGwHg14TAJM0koDOq28')

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"[SUPABASE INIT ERROR] {e}")
    supabase = None

def get_supabase():
    return supabase

def get_kv(table_name: str, key: str, default_val=None):
    if not supabase: return default_val
    try:
        res = supabase.table(table_name).select("*").eq("id", key).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("value", default_val)
    except Exception as e:
        print(f"[SUPABASE GET KV ERROR] {table_name}/{key}: {e}")
    return default_val

def set_kv(table_name: str, key: str, value: dict):
    if not supabase: return False
    try:
        # Upsert
        data = {"id": key, "value": value}
        supabase.table(table_name).upsert(data).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE SET KV ERROR] {table_name}/{key}: {e}")
        return False
