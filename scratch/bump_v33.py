with open('ui/sw.js', 'r', encoding='utf-8') as f:
    sw = f.read()

sw = sw.replace("'vr-static-v32'", "'vr-static-v33'")
with open('ui/sw.js', 'w', encoding='utf-8') as f:
    f.write(sw)

with open('ui/index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

idx = idx.replace('app.js?v=20261106_v32', 'app.js?v=20261106_v33')
idx = idx.replace('sw.js?v=20261106_v32', 'sw.js?v=20261106_v33')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

print('Bumped cache version to v33')
