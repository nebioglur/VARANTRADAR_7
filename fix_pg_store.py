# -*- coding: utf-8 -*-
with open("services/pg_store.py", "r", encoding="utf-8") as f:
    code = f.read()

bad = """    def executemany(self, sql, params_list):
        sql2 = _translate_sql(sql, self._cur)
        for params in params_list:
            self._cur.execute(sql2, tuple(params) if params else None)"""

good = """    def executemany(self, sql, params_list):
        sql2 = _translate_sql(sql, self._cur)
        import psycopg2.extras
        psycopg2.extras.execute_batch(self._cur, sql2, [tuple(p) if p else None for p in params_list], page_size=1000)"""

if bad in code:
    code = code.replace(bad, good)
    with open("services/pg_store.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Fixed executemany to use execute_batch!")
else:
    print("Could not find the target string.")
