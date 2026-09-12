import sys

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = '<span style="color:var(--text-muted);">Kapanış:</span>'

if target in c:
    idx = c.find('card.innerHTML = `')
    if idx != -1:
        logic = '''
            // Get today's date in YYYY-MM-DD
            const todayObj = new Date();
            const yyyy = todayObj.getFullYear();
            const mm = String(todayObj.getMonth() + 1).padStart(2, '0');
            const dd = String(todayObj.getDate()).padStart(2, '0');
            const todayStr = `${yyyy}-${mm}-${dd}`;
            
            const closeLabel = (item.date === todayStr) ? 'Anlık:' : 'Kapanış:';
            
            '''
        c = c[:idx] + logic + c[idx:]
        c = c.replace(target, '<span style="color:var(--text-muted);">${closeLabel}</span>')
        
        with open('ui/app.js', 'w', encoding='utf-8') as f:
            f.write(c)
        print('Injected and replaced successfully')
    else:
        print('card.innerHTML not found')
else:
    print('Target not found')
