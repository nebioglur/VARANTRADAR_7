# -*- coding: utf-8 -*-
import re

with open("ui/app.js", "r", encoding="utf-8") as f:
    text = f.read()

def alert_replacer(match):
    content = match.group(1)
    return f"Swal.fire({{title: 'Sistem Mesaji', text: {content}, icon: 'info', background: '#1a1f2e', color: '#fff', confirmButtonColor: '#38bdf8'}})"

def confirm_replacer(match):
    content = match.group(1)
    return f"!(await Swal.fire({{title: 'Onay', text: {content}, icon: 'warning', showCancelButton: true, background: '#1a1f2e', color: '#fff', confirmButtonText: 'Evet', cancelButtonText: 'Iptal', confirmButtonColor: '#10b981', cancelButtonColor: '#ef4444'}})).isConfirmed"

# Replace alert(...)
text = re.sub(r'alert\((.*?)\)', alert_replacer, text)

# Replace !confirm(...)
text = re.sub(r'!confirm\((.*?)\)', confirm_replacer, text)

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(text)

print("SWAL PATCH DONE")
