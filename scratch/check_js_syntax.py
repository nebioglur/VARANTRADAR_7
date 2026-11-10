import sys
sys.stdout.reconfigure(encoding='utf-8')

def check_js_syntax(filename):
    print(f"\n--- Checking {filename} ---")
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    
    lines = code.splitlines()
    print(f"Total lines: {len(lines)}, Total characters: {len(code)}")
    
    stack = []
    in_single_quote = False
    in_double_quote = False
    in_template_literal = False
    in_line_comment = False
    in_block_comment = False
    template_curly_stack = []
    
    escape = False
    
    i = 0
    n = len(code)
    line_num = 1
    col_num = 1
    
    errors = []
    
    while i < n:
        c = code[i]
        nxt = code[i+1] if i + 1 < n else ''
        
        if c == '\n':
            line_num += 1
            col_num = 1
            if in_line_comment:
                in_line_comment = False
            if in_single_quote:
                errors.append(f"Unterminated single quote at line {line_num-1}")
                in_single_quote = False
            if in_double_quote:
                errors.append(f"Unterminated double quote at line {line_num-1}")
                in_double_quote = False
            i += 1
            continue
        else:
            col_num += 1
            
        if in_line_comment:
            i += 1
            continue
            
        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                i += 2
                col_num += 1
                continue
            i += 1
            continue
            
        if escape:
            escape = False
            i += 1
            continue
            
        if c == '\\':
            escape = True
            i += 1
            continue
            
        if in_single_quote:
            if c == "'":
                in_single_quote = False
            i += 1
            continue
            
        if in_double_quote:
            if c == '"':
                in_double_quote = False
            i += 1
            continue
            
        if in_template_literal:
            if c == '`':
                in_template_literal = False
            elif c == '$' and nxt == '{':
                template_curly_stack.append(len(stack))
                stack.append(('${', line_num, col_num))
                i += 2
                col_num += 1
                in_template_literal = False # entering JS expression inside template
                continue
            i += 1
            continue
            
        # Not inside a string or comment
        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            col_num += 1
            continue
            
        if c == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            col_num += 1
            continue
            
        if c == "'":
            in_single_quote = True
            i += 1
            continue
            
        if c == '"':
            in_double_quote = True
            i += 1
            continue
            
        if c == '`':
            in_template_literal = True
            i += 1
            continue
            
        if c in '({[':
            stack.append((c, line_num, col_num))
        elif c in ')}]':
            if not stack:
                errors.append(f"Unexpected closing {c} at line {line_num}, col {col_num}")
            else:
                top, l, col = stack.pop()
                expected = {'(': ')', '{': '}', '[': ']'}.get(top, '')
                if top == '${':
                    expected = '}'
                if c != expected:
                    errors.append(f"Mismatched closing {c} at line {line_num}, col {col_num}; expected {expected} from line {l}, col {col}")
                if top == '${':
                    # returned from expression inside template literal
                    in_template_literal = True
                    if template_curly_stack:
                        template_curly_stack.pop()
        i += 1
        
    for op, l, col in stack:
        errors.append(f"Unclosed {op} from line {l}, col {col}")
        
    print(f"Total syntax issues found: {len(errors)}")
    for e in errors[:20]:
        print(" ", e)

check_js_syntax('ui/app.js')
check_js_syntax('pro8_app.js')
