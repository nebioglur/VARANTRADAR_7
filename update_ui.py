import re

with open(r'C:\Users\nebio\Desktop\VarantRadarPro\ui\app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# For Tavan Adayları
js = js.replace(
    '<h5>${item.Symbol}</h5>',
    '<h5>${item.Symbol} ${item.Time_Label ? `<span style="font-size:0.7rem; padding:2px 6px; border-radius:12px; background:rgba(255,255,255,0.1); color:#ff9800; margin-left:5px;"><i class="fa-regular fa-clock"></i> ${item.Time_Label}</span>` : ""}</h5>'
)

# For 1 Saatlik Fırsatlar
js = js.replace(
    '<h5>${item.Sembol}</h5>',
    '<h5>${item.Sembol} ${item.Time_Label ? `<span style="font-size:0.7rem; padding:2px 6px; border-radius:12px; background:rgba(255,255,255,0.1); color:#ff9800; margin-left:5px;"><i class="fa-regular fa-clock"></i> ${item.Time_Label}</span>` : ""}</h5>'
)

# For 5m signals
js = js.replace(
    '<h6>${item.Symbol}</h6>',
    '<h6>${item.Symbol} ${item.Time_Label ? `<span style="font-size:0.7rem; padding:2px 6px; border-radius:12px; background:rgba(255,255,255,0.1); color:#ff9800; margin-left:5px;"><i class="fa-regular fa-clock"></i> ${item.Time_Label}</span>` : ""}</h6>'
)

with open(r'C:\Users\nebio\Desktop\VarantRadarPro\ui\app.js', 'w', encoding='utf-8') as f:
    f.write(js)
