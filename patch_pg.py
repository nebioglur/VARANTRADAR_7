with open("services/pg_store.py", "r", encoding="utf-8") as f:
    code = f.read()

executemany_code = """
    def executemany(self, sql, params_list):
        sql2 = _translate_sql(sql, self._cur)
        for params in params_list:
            self._cur.execute(sql2, tuple(params) if params else None)
"""

code = code.replace("    def _wrap(self, row):", executemany_code + "\n    def _wrap(self, row):")

with open("services/pg_store.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patched pg_store.py")
