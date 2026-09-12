import os
import ast

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        routes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and getattr(dec.func, 'attr', '') == 'route':
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            routes.append(dec.args[0].value)
        return classes, functions, routes
    except Exception as e:
        return [], [], []

print('--- CODEBASE SCAN ---')
for root, dirs, files in os.walk('.'):
    if '.git' in root or 'venv' in root or '__pycache__' in root or 'scratch' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            cls, funcs, routes = analyze_file(path)
            print(f'File: {path}')
            if cls: print(f'  Classes: {cls}')
            if routes: print(f'  Routes: {routes}')
            if funcs: print(f'  Functions: {funcs[:15]} {"..." if len(funcs)>15 else ""}')
