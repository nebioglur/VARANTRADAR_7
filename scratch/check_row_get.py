import ast, glob, sys

def check_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception:
        return
    try:
        tree = ast.parse(code, filename=path)
    except Exception:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
            val = node.func.value
            if isinstance(val, ast.Name):
                name = val.id
                if any(x in name.lower() for x in ['row', 'trade', 'item', 'res', 'rec', 'ent', 'sig', 'pos', 'cur', 'db', 'sql']):
                    sys.stdout.write(f"{path}:{node.lineno}: {name}.get(...)\n")

with open('scratch/row_get_results.txt', 'w', encoding='utf-8') as out_f:
    sys.stdout = out_f
    for p in glob.glob('*.py') + glob.glob('services/**/*.py', recursive=True) + glob.glob('v8_engine/**/*.py', recursive=True):
        check_file(p)

print("DONE")
