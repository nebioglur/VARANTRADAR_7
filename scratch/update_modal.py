import sys

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

idx_start = c.find("let allItems = global_stats_data.summary?.all_time_symbols || [];")
if idx_start == -1:
    print("Could not find start index!")
    sys.exit(1)

idx_end = c.find("title.innerHTML = titleText;", idx_start)
if idx_end == -1:
    print("Could not find end index!")
    sys.exit(1)

new_logic = """let allItems = [];
    let isDaily = (typeof current_stats_mode !== 'undefined' && current_stats_mode === 'daily');
    let prefix = isDaily ? 'Günün' : 'Tüm Zamanların';

    if (isDaily) {
        const history = global_stats_data.daily_breakdown || global_stats_data.history || [];
        if (history.length > 0) {
            allItems = history[0].all_symbols || [];
        }
    } else {
        allItems = global_stats_data.summary?.all_time_symbols || [];
    }
    
    if (type === 'tavan') {
        items = allItems.filter(it => it.hit_ceiling);
        titleText = `<i class="fa-solid fa-rocket"></i> ${prefix} Tavan Hisseleri`;
    } else if (type === 'plus5') {
        items = allItems.filter(it => it.hit_plus5);
        titleText = `<i class="fa-solid fa-chart-line"></i> ${prefix} +%5 Yapan Hisseleri`;
    } else if (type === 'positive_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) > 0);
        titleText = `<i class="fa-solid fa-arrow-trend-up"></i> ${isDaily ? 'Günü' : 'Tüm Zamanlarda'} Kârda Kapatanlar`;
    } else if (type === 'negative_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) < 0);
        titleText = `<i class="fa-solid fa-arrow-trend-down"></i> ${isDaily ? 'Günü' : 'Tüm Zamanlarda'} Zararda Kapatanlar`;
    } else if (type === 'elite_positive_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) > 0 && (it.morning_score >= 99.9));
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Elit Kârda Kapatanları (100 Puan)`;
    } else if (type === 'elite_negative_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) < 0 && (it.morning_score >= 99.9));
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Elit Zararda Kapatanları (100 Puan)`;
    } else if (type === 'elite_all') {
        items = allItems.filter(it => it.morning_score >= 99.9);
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Tüm Elit Önerileri (100 Puan)`;
    } else if (type === 'all') {
        items = allItems;
        titleText = `<i class="fa-solid fa-list-ul"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Tüm Önerileri`;
    } else if (type === 'daily_all' && date) {
        const dayData = (global_stats_data.daily_breakdown || []).find(d => d.date === date);
        items = dayData?.all_symbols || [];
        titleText = `<i class="fa-regular fa-calendar"></i> ${date} Tarihli Tüm Öneriler`;
    }
    
    """

new_content = c[:idx_start] + new_logic + c[idx_end:]

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated ui/app.js successfully!")
