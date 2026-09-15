import os

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'switchMainTab(\'backtest\', this)"'
idx = text.find(target)
if idx != -1:
    # Find the end of the line
    end_idx = text.find('</button>', idx)
    if end_idx != -1:
        end_idx += 9 # Include </button>
        
        insert = '\n            <button class="nav-btn" onclick="window.location.href=\'/v8\'" style="color:#0ea5e9; border:1px solid rgba(14,165,233,0.4);"><i class="fa-solid fa-brain"></i> V8 ENGINE (YENİ)</button>'
        
        if 'window.location.href=\'/v8\'' not in text:
            text = text[:end_idx] + insert + text[end_idx:]
            with open('ui/index.html', 'w', encoding='utf-8') as f:
                f.write(text)
            print('V8 button added to ui/index.html')
        else:
            print('Already exists')
else:
    print('Target not found')
