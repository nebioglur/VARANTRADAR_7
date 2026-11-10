with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace interval="1d" with interval="5m" in fast_data fetch
text = text.replace('interval=\"1d\"', 'interval=\"5m\"')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched server.py fast_data interval')
