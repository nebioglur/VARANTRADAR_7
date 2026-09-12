import sys

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

bad_logic = '''
            // Get today's date in YYYY-MM-DD
            const todayObj = new Date();
            const yyyy = todayObj.getFullYear();
            const mm = String(todayObj.getMonth() + 1).padStart(2, '0');
            const dd = String(todayObj.getDate()).padStart(2, '0');
            const todayStr = `${yyyy}-${mm}-${dd}`;
            
            const closeLabel = (item.date === todayStr) ? 'Anlık:' : 'Kapanış:';
            
            '''

c = c.replace(bad_logic, '')

correct_idx = c.find("const card = document.createElement('div');\\n            card.className = 'history-card';")
if correct_idx == -1:
    correct_idx = c.find("const card = document.createElement('div');\n            card.className = 'history-card';")

if correct_idx != -1:
    c = c[:correct_idx] + bad_logic + c[correct_idx:]
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Fixed successfully')
else:
    print('Correct idx not found')
