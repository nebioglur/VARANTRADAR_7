
function toggleSimDetail(dateStr) {
    const detailContainer = document.getElementById('sim-detail-container');
    const detailTbody = document.getElementById('sim-detail-tbody');
    const detailTitle = document.getElementById('sim-detail-title');
    
    if (!detailContainer || !detailTbody || !globalSimData || !globalSimData.days) return;
    
    // Zaten ayni tarih aciksa kapat
    if (detailContainer.style.display === 'block' && detailContainer.dataset.date === dateStr) {
        detailContainer.style.display = 'none';
        detailContainer.dataset.date = '';
        return;
    }
    
    const dayData = globalSimData.days.find(d => d.date === dateStr);
    if (!dayData || !dayData.trades) return;
    
    detailTitle.innerHTML = `<i class=\"fa-solid fa-list\"></i> ${dateStr} - İşlem Detayı`;
    detailTbody.innerHTML = '';
    
    dayData.trades.forEach(t => {
        const isProfit = t.pnl >= 0;
        const color = isProfit ? 'var(--accent-green)' : 'var(--accent-red)';
        const sign = isProfit ? '+' : '';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style=\"font-weight:700; color:var(--text-light);\">${t.symbol}</td>
            <td style=\"font-family:monospace;\">${t.buy_price.toFixed(2)} ₺</td>
            <td style=\"font-family:monospace;\">${t.sell_price.toFixed(2)} ₺</td>
            <td>${t.lot_size.toLocaleString('tr-TR')}</td>
            <td style=\"font-family:monospace;\">${t.invested.toLocaleString('tr-TR')} ₺</td>
            <td style=\"font-family:monospace;\">${t.returned.toLocaleString('tr-TR')} ₺</td>
            <td style=\"color:${color}; font-weight:800; font-family:monospace;\">${sign}${t.pnl.toLocaleString('tr-TR')} ₺</td>
            <td style=\"color:${color}; font-weight:700;\">${sign}%${t.pnl_pct.toFixed(2)}</td>
            <td style=\"font-size:0.75rem;\">${t.reason}</td>
        `;
        detailTbody.appendChild(tr);
    });
    
    detailContainer.style.display = 'block';
    detailContainer.dataset.date = dateStr;
    detailContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
