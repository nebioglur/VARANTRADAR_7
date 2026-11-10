import ast

class RowGetVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.findings = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            # check the value
            val = ast.unparse(node.func.value)
            self.findings.append((node.lineno, val, ast.unparse(node)))
        self.generic_visit(node)

with open("server.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())

visitor = RowGetVisitor("server.py")
visitor.visit(tree)

print(f"Total .get() calls in server.py: {len(visitor.findings)}")
for lineno, val, call_str in visitor.findings:
    if any(k in val.lower() for k in ["row", "cursor", "fetch", "cur", "trade", "equity", "pos"]):
        print(f"Line {lineno}: {val} -> {call_str[:80]}")
