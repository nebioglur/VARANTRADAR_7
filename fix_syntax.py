import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the broken string concatenation
text = text.replace(
    '''D/D</button>';</div>\\';''',
    '''D/D</button></div>';'''
)

text = text.replace(
    '''D/D</button>;</div>\\';''',
    '''D/D</button></div>;'''
)

# And fix any potential similar mistake on the template literal
text = text.replace(
    '''D/D</button></div>;</div>\\';''',
    '''D/D</button></div>;'''
)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched app.js syntax error')
