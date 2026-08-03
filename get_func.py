import ast

def get_function_source(filename, function_name):
    with open(filename, 'r', encoding='utf-8') as file:
        source_code = file.read()

    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            lines = source_code.split('\n')[start_line:end_line]
            return '\n'.join(lines)
    return None

source = get_function_source('main.py', 'run_simulation_api')
if source:
    print(source)
