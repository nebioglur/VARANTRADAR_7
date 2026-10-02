import ast

def get_function_source(filename, function_names):
    with open(filename, 'r', encoding='utf-8') as file:
        source_code = file.read()

    tree = ast.parse(source_code)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            lines = source_code.split('\n')[start_line:end_line]
            results.append('\n'.join(lines))
    return '\n\n'.join(results)

source = get_function_source(r'C:\Users\nebio\Desktop\VarantRadarPro\scanner\universal_scanner.py', ['scan_pool_bulk_1h', 'scan_pool_bulk_5m'])
if source:
    print(source)
