import ast, glob

class RowGetVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.findings = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            val = ast.unparse(node.func.value)
            self.findings.append((node.lineno, val, ast.unparse(node)))
        self.generic_visit(node)

for py_file in glob.glob("services/*.py") + glob.glob("v8_engine/*.py"):
    with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
        try:
            tree = ast.parse(f.read())
            v = RowGetVisitor(py_file)
            v.visit(tree)
            for lineno, val, call_str in v.findings:
                if any(k in val.lower() for k in ["row", "cursor", "fetch", "cur", "trade", "equity", "pos"]):
                    print(f"{py_file}:{lineno}: {val} -> {call_str[:70]}")
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")
