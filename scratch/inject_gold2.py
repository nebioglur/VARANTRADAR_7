import sys

for filename in ['ui/app.js', 'live_app.js']:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if "if (globalDashboardData['signals_5m']" in line and "tavan_adaylari" in line:
            # Find the closing brace of this block
            # Just count down 10 lines and verify
            if "}" in lines[i+9]:
                # Inject at i+10
                injection = """
                    // MTF Radar ile Kesisim Kontrolu (Altin Firsat)
                    let mtfMatch = false;
                    if (globalDashboardData['mtf_results'] && Array.isArray(globalDashboardData['mtf_results'])) {
                        mtfMatch = globalDashboardData['mtf_results'].some(m => m.Symbol === res.Symbol);
                    }
                    if (mtfMatch && (cat === 'tavan_adaylari' || cat === 'opportunities_1h')) {
                        symStr += ` <span style="background: linear-gradient(90deg, #fbbf24, #d97706); color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: bold; margin-left: 5px; box-shadow: 0 0 10px rgba(251,191,36,0.6); animation: pulse 2s infinite;" title="Altın Fırsat: Hem Tavan/1S Radarı hem de MTF İvme (1S/15D) Radarı eşleşti!"><i class="fa-solid fa-crown"></i> ALTIN</span>`;
                        tr.style.borderLeft = "3px solid #fbbf24";
                        tr.style.backgroundColor = "rgba(251,191,36,0.05)";
                    }
"""
                lines.insert(i+10, injection)
                break
                
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Injected properly in {filename}")
