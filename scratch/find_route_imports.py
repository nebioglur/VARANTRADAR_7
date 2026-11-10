import ast

with open("server.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        # check decorators
        is_route = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "route"
            for d in node.decorator_list
        )
        if is_route:
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Import):
                    for alias in subnode.names:
                        print(f"Route {node.name} imports {alias.name}")
                elif isinstance(subnode, ast.ImportFrom):
                    print(f"Route {node.name} imports from {subnode.module}: {[a.name for a in subnode.names]}")
