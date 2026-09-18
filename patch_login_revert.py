# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_login = '''        if True: # Her zaman klasik login goster (Supabase Auth Bypass)
            flag = '<script>window.VR_CLASSIC_ONLY=1;</script>'
            if '<head>' in html:'''

new_login = '''        if os.environ.get('CLASSIC_ONLY') == '1':
            flag = '<script>window.VR_CLASSIC_ONLY=1;</script>'
            if '<head>' in html:'''

content = content.replace(old_login, new_login)
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_LOGIN_REVERT_OK")
