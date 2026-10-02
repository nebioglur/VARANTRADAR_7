import ast
with open(r"C:\Users\nebio\Desktop\VarantRadarPro\analysis\technical.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if "tavan" in node.name.lower():
            print(f"Function: {node.name} at line {node.lineno}")
