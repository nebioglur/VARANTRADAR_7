import re

with open('ui/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

new_css = '''
.fullscreen-card {
    position: fixed !important;
    top: 5vh !important;
    left: 5vw !important;
    width: 90vw !important;
    height: 90vh !important;
    z-index: 999999 !important;
    background: var(--bg-card, #0f172a) !important;
    margin: 0 !important;
    padding: 2rem !important;
    border-radius: 16px !important;
    box-sizing: border-box !important;
    box-shadow: 0 0 0 9999px rgba(0,0,0,0.85), 0 20px 40px rgba(0,0,0,0.5) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    display: flex !important;
    flex-direction: column !important;
}
.fullscreen-card .table-scroll-wrapper {
    flex: 1 !important;
    max-height: none !important;
    height: 100% !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
}
'''

# Find the existing .fullscreen-card block and replace it
text = re.sub(r'\.fullscreen-card \{.*?\n\}', '', text, flags=re.DOTALL)
text = re.sub(r'\.fullscreen-card \.table-scroll-wrapper \{.*?\n\}', '', text, flags=re.DOTALL)
text = re.sub(r'\.fullscreen-card \.card-title \{.*?\n\}', '', text, flags=re.DOTALL)

text += new_css

with open('ui/style.css', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched style.css for centered fullscreen cards')
