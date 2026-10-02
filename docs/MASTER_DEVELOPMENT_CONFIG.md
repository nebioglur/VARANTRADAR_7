###############################################################
VARANTRADAR PRO
MASTER DEVELOPMENT CONFIG
CFG-01 → CFG-05
Version 5.0
###############################################################

## GENEL KURAL

Bu projede "Varant" odaklı kod yazılmayacaktır.
Tüm sistem aşağıdaki Asset mimarisine göre geliştirilecektir:

Asset
├── Stock
├── Warrant
├── ETF
├── VIOP
└── Crypto (gelecekte)

Tüm modüller Asset tabanlı olacaktır. Hiçbir modül yalnızca varant için yazılmayacaktır.

###############################################################
## YAZILIM MİMARİSİ
###############################################################

Katmanlı Mimari kullanılacaktır:
Presentation Layer -> Dashboard -> Service Layer -> Engine Layer -> Data Layer -> SQLite/API/Cache

Her Engine yalnızca kendi sorumluluğuna sahip olacaktır.

###############################################################
## TEMEL ENGINE'LAR
###############################################################

- Core Engine
- Scanner Engine
- Radar Engine
- Score Engine
- AI Decision Engine
- Explainable AI Engine
- Trade Planner Engine
- Risk Engine
- Portfolio Engine
- History Engine
- Learning Engine
- Notification Engine
- Dashboard Engine
- Backtest Engine
- Analytics Engine
- Market Data Engine
- Asset Engine
- Warrant Engine
- Stock Engine

###############################################################
## CFG-01 : AI DECISION SYSTEM
###############################################################

Amaç: Yapay zekânın yalnızca puan üretmesi değil, gerçek bir profesyonel analist gibi karar vermesi.

Modüller: AI Confidence, Probability Score, Explainable AI, Counter Opinion, Historical Similarity, Target Estimation, ETA, Risk Estimation, Trade Recommendation, Decision History

Kararlar: 🟢 Güçlü AL, 🟢 AL, 🟡 İzlemeye Değer, 🟠 Düzeltme Beklenebilir, 🔴 İşlemden Kaçın
AI mutlaka nedenini açıklayacaktır.

###############################################################
## CFG-02 : PROFESSIONAL RADAR
###############################################################

Amaç: Tüm hisseleri ve varlıkları sürekli tarayarak en kaliteli fırsatları bulmak. Radar yalnızca aday bulacaktır. Kararı AI verecektir.

Akış: Radar -> Score Engine -> AI Decision -> Trade Planner -> Dashboard

Zaman Dilimleri: 5 dk, 15 dk, 30 dk, 1 Saat, 4 Saat, Günlük, Haftalık (Aynı anda analiz edecektir).

Radar Şunları Hesaplayacaktır: Trend, Momentum, Hacim, Risk, Likidite, Volatilite, AI Score, Confidence, Toplam Score

###############################################################
## CFG-03 : ASSET INTELLIGENCE
###############################################################

Varant yerine Asset mantığı kullanılacaktır.
Her Asset için: Trend, Momentum, Risk, Likidite, Volatilite, Kalite, AI, Confidence hesaplanacaktır.

Varantlarda ek olarak: Delta, Gamma, Theta, Vega, Rho, Elasticity, Time Value, Intrinsic Value, Effective Leverage hesaplanacaktır.
Hisse için: Fair Value, Support, Resistance, ATR, Beta, Sharpe, Sortino, Maximum Drawdown hesaplanacaktır.

Trade Planner Şunları Oluşturacaktır: Entry, Stop, Target-1, Target-2, ETA, Probability, Risk/Reward, Position Size.

###############################################################
## CFG-04 : INSTITUTIONAL WORKSPACE
###############################################################

Dashboard: Widget, Heatmap, Watchlist, AI Center, Radar, Portfolio, Charts, Alerts, Market Overview tek ekranda çalışacaktır.
Dashboard hesaplama yapmayacaktır. Yalnızca Engine'lardan gelen verileri gösterecektir.

###############################################################
## ORTAK KURALLAR
###############################################################

- Kod SOLID prensiplerine uygun olacaktır.
- Dependency Injection kullanılacaktır.
- Magic Number kullanılmayacaktır.
- Her Engine bağımsız olacaktır.
- Kod tekrarına izin verilmeyecektir.
- Type Hint kullanılacaktır.
- Docstring zorunludur.
- Unit Test yazılacaktır.
- Logging zorunludur.
- Cache kullanılacaktır.
- Config merkezi olacaktır.
- API katmanı ayrılacaktır.
- SQLite Repository Pattern kullanılacaktır.
- Asenkron işlemler mümkün olduğunca kullanılacaktır.

###############################################################
## AI KURALLARI
###############################################################

AI hiçbir zaman yalnızca AL/SAT demeyecektir. Mutlaka açıklayacaktır.

Örnek:
Neden AL?
- EMA20 > EMA50
- MACD pozitif
- ADX güçlü
- RSI uygun
- Hacim arttı
- Endeks güçlü

Karşıt Görüş:
- Dirence yakın
- ATR yüksek

AI Confidence: 92% | Probability: 87%

###############################################################
## TRADE PLANNER
###############################################################

Her sinyal için şunlar hesaplanacaktır:
Entry, Stop, Target-1, Target-2, ETA, Risk, Reward, Probability, Confidence, Position Size, Maximum Loss, Expected Return.

###############################################################
## PERFORMANS
###############################################################

Paralel tarama, Cache, Lazy Loading, Asenkron API, Optimize SQLite, Memory Management, Background Scheduler zorunludur.

###############################################################
## HEDEF
###############################################################

Program yalnızca veri gösteren bir uygulama olmayacaktır.
Program;
• Piyasayı tarayacak
• En iyi hisseleri bulacak
• En iyi varantları bulacak
• Risk analizi yapacak
• İşlem planı oluşturacak
• Yapay zekâ ile karar verecek
• Kararını açıklayacak
• Portföyü yönetecek
• Geçmiş performansını ölçecek
• Zamanla kendi başarısını analiz ederek gelişecektir.

Bu hedef doğrultusunda tüm geliştirmeler Asset-first mimarisi ile gerçekleştirilecektir.
###############################################################

###############################################################
## CFG-05 : QUANT RESEARCH & STRATEGY LABORATORY
###############################################################

Amaç: Radar, AI ve işlem stratejilerinin geçmiş veriler üzerinde test edilmesi, optimize edilmesi ve istatistiksel olarak doğrulanması.

Modüller: 
- Backtest Engine (Tek, Çoklu, Portföy testleri, Çoklu Timeframe)
- Strategy Lab (EMA, RSI, MACD, Ichimoku, AI, Hybrid stratejiler)
- Optimization Center (Grid, Random, Bayesian, Genetic, AI Kalibrasyon)
- Walk-Forward Analysis (In-Sample, Out-of-Sample, Stability Score)
- Monte Carlo Simulation (10.000 Senaryo, Sermaye/Risk simülasyonları)
- Performance Analytics (CAGR, Win Rate, Profit Factor, Expectancy, Sharpe, Sortino, Calmar, Recovery Factor)
- Risk Analytics (VaR, CVaR, Drawdown, ATR, Beta)
- AI Learning Center (Radar/AI İsabet Oranı, Karar Geçmişi, Öğrenme Eğrisi)
- Strategy Comparison (AI vs Klasik, Radar vs Manuel, Benchmark karşılaştırmaları)
- Research Dashboard (Gelişmiş analitik paneller ve raporlamalar)

CFG-05 TAMAMLANDIĞINDA:
✓ Tüm stratejiler test edilir
✓ Sinyal başarı oranları ölçülür
✓ Overfitting Walk-Forward ile engellenir
✓ Monte Carlo ile binlerce senaryo çalıştırılır
✓ Profesyonel metrikler hesaplanır
✓ Kurumsal seviyede Quant Research laboratuvarı oluşturulur!
###############################################################

###############################################################
## CFG-06 : PORTFOLIO INTELLIGENCE CENTER ULTIMATE
###############################################################

Ama: Hisse, varant ve dier varlk snflarn tek bir akll portfy altnda ynetmek. Riski analiz etmek, denge nerileri sunmak, AI destekli karar vermek.

Modller:
- Portfolio Manager (oklu Portfy, Sanal/Gerek)
- Position Manager (Kademeli Alm/Satm, PnL, Komisyon)
- Risk Engine (Beta, ATR, Volatilite, VaR, CVaR)
- AI Portfolio Advisor (Risk Yorumu, eitlendirme, Salk Skoru)
- Performance Center (CAGR, Alpha, Beta, Sharpe, Sortino)
- Rebalance Engine (Risk bazl, Yzde bazl, AI dengeleme)
- Position Sizing (Kelly Criterion, ATR/Volatilite bazl)
- Scenario Simulator (Boa/Ay, Kur oku, Endeks k)
- Portfolio Health (eitlendirme, Likidite, Risk Skorlar)
- Report Center (PDF/Excel Raporlama)
- Enterprise Portfolio Analytics (Efficient Frontier, Mean-Variance Optimization, Black-Litterman Model)
- Explainable AI (Feature Importance, Karar Gemii)
- Learning Center (Portfy Baar Oran, AI Evrimi)

CFG-06 TAMAMLANDIINDA:
? oklu varlk portfy ynetimi
? AI destekli portfy danman
? Otomatik dengeleme ve pozisyon bykl optimizasyonu
? Efficient Frontier analizi ve Black-Litterman optimizasyonu
? Kurumsal performans ve risk raporlar
###############################################################

###############################################################
## CFG-07 : ENTERPRISE PORTFOLIO ANALYTICS & AI COACH
###############################################################

Amaç: Bireysel portföy yönetimini, tam teşekküllü bir kurumsal yatırım bankası veya hedge fon altyapısına yükseltmek. Faktör yatırımları, Black-Litterman, tam teşekküllü korelasyon analizi ve AI destekli yatırım danışmanı içerir.

Modüller:
- Modern Portfolio Theory & Advanced Optimization (MPT, Black-Litterman, Risk Parity, Min Variance)
- Factor Investing Center (Value, Growth, Momentum, Quality, Low Vol, vb.)
- Dynamic Asset Allocation (Tactical, Strategic, Smart Beta)
- Correlation & Diversification Matrix (Rolling, Cross-asset, Heatmap)
- Portfolio Attribution Analysis (Return, Risk, Timing, Selection)
- Goal & Liquidity Management (Target Risk/Return, Spread/Slippage, Exit Time)
- Cost & Virtual Portfolio Center (Tax, Fees, Shadow/Twin Portfolio, Paper Trading)
- Enterprise Reporting (Executive, PDF, Excel, PowerPoint)
- Advanced Explainable AI & Investment Coach (Confidence Score, Health/Quality Score, Prediction Intervals)

CFG-07 TAMAMLANDIĞINDA:
✓ Hedge fon seviyesinde Faktör ve Korelasyon analizi
✓ Portföy getirilerinin tam (Attribution) analizi
✓ Sanal Portföy (Paper Trading) ve Dijital İkiz (AI Twin)
✓ Kurumsal (Executive) Raporlama (PDF, Excel, PPT)
✓ AI Yatırım Koçu (Explainable AI & Health Scores)
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-07
#
# SMART MONEY & INSTITUTIONAL FLOW CENTER ULTIMATE
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: Kurumsal yatırımcı davranışlarını, akıllı para hareketlerini, hacim akışını ve piyasa mikro yapısını analiz ederek hisse ve varantlarda erken fırsatları tespit etmek.

Modüller:
- Smart Money Engine (MFI, CMF, OBV, VWAP, Volume Delta)
- Institutional Flow (Büyük Emir Analizi, Alıcı/Satıcı Baskısı, Emir Dengesizliği)
- Liquidity Engine (Derinlik, Likidite Havuzları)
- Volume Analytics (Göreceli Hacim, Hacim Patlaması/Kuruması)
- Order Flow Engine (Bid/Ask Analizi, Order Imbalance, Liquidity Sweep)
- Sector Rotation (Sektör Para Girişi, Lider Sektörler)
- Capital Flow (Endeks/Sektör/Hisse Para Akışı)
- AI Smart Money (Kurumsal Güven Skoru, Manipülasyon Riski)
- Flow Alert Center (Büyük Para Girişi/Çıkışı)
- Smart Money Reports
- Enterprise Analytics (Volume Profile, Footprint)

CFG-07 TAMAMLANDIĞINDA:
✓ Akıllı para hareketlerini analiz eder.
✓ Emir akışını ve likiditeyi değerlendirir.
✓ Sektör rotasyonunu takip eder.
✓ Manipülasyon riskini ve Kurumsal izleri (Footprint) tespit eder.
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-08
#
# AI INTELLIGENCE CENTER ULTIMATE (Version 8.0)
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: Yapay zekâyı yalnızca sinyal üreten bir sistem olmaktan çıkarıp; piyasayı yorumlayan, kararlarını açıklayan, geçmişten öğrenen, güven seviyesini hesaplayan ve kullanıcıyla etkileşim kurabilen profesyonel bir AI karar destek merkezi oluşturmak.

Modüller:
- AI Decision Engine (AL/SAT, Güçlü Kararlar)
- AI Confidence Engine (Güven Skoru, Olasılık Dağılımı)
- Explainable AI (Neden bu karar? Karar Ağacı)
- Counter Opinion Engine (Karşıt Görüş, Risk Analizi)
- Historical Similarity Engine (Tarihsel Benzerlik, Pattern Matching)
- Natural Language AI & Chat Center (Doğal Dil ile Sorgulama, AI Asistan)
- Forecast Engine (Hedef Fiyat Tahmini)
- Enterprise AI (Multi-Agent, Consensus)

CFG-08 TAMAMLANDIĞINDA:
✓ Kararlarını açıklayan ve güven seviyesini ölçen bir AI altyapısı kurulur.
✓ Doğal dille konuşabilen bir asistan sisteme dahil olur.
✓ Geçmiş benzer formasyonları bularak olasılık hesaplar.
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-08.2
#
# AI AGENT MARKETPLACE & AUTONOMOUS INTELLIGENCE PLATFORM
# Version 8.2 Enterprise Ultimate
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: Uzmanlaşmış AI ajanlarının birlikte çalıştığı, kendi görevlerini üstlendiği, birbirleriyle iletişim kurduğu ve ortak karar aldığı otonom bir AI ekosistemi oluşturmak.

Modüller (31-46 Arası):
- AI Agent Marketplace (Trend, Volume, Smart Money, Risk Ajanları)
- Multi Agent Coordinator (Consensus, Debate)
- Autonomous Research & Radar
- AI Strategy Factory & Indicator Factory
- Autonomous Portfolio & Risk
- AI Collaboration Center (Agent Messaging, Voting)
- Enterprise Orchestration & Analytics

CFG-08.2 TAMAMLANDIĞINDA:
✓ Çoklu AI ajan mimarisi kurulur.
✓ Ajanlar kendi aralarında tartışıp konsensüs sağlar.
✓ Otonom tarama ve portföy yönetimi devreye girer.
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-08.3
#
# FINANCIAL OPERATING SYSTEM (FinOS)
# Version 8.3 Enterprise Ultimate
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: VarantRadar Pro'yu dağınık modüllerden oluşan bir araç olmaktan çıkarıp, kendi Kernel (Çekirdek), Event Bus, Unified Data Layer, Scheduler ve Plugin altyapısına sahip tam teşekküllü bir Finansal İşletim Sistemi (FinOS) seviyesine taşımak.

Modüller:
- FinOS Kernel & Module Manager
- Unified Data Layer (BIST, VIOP, Kripto tek çatı)
- Digital Twin & Scenario Replay (Sanal Simülasyon)
- Event Queue & Message Broker
- Final Decision Dashboard
- Executive KPI & Reporting Center
- Scheduled Automation & Workflow Engine
- System Health & Performance Monitor
- Enterprise Security & Plugin SDK
- Cloud Sync & Enterprise Orchestration

CFG-08.3 TAMAMLANDIĞINDA:
✓ Sistem bir 'Uygulama' olmaktan çıkar, 'İşletim Sistemi' mantığıyla çalışır.
✓ Tüm modüller Event Bus üzerinden haberleşir.
✓ Geçmiş piyasa koşulları 'Digital Twin' ile simüle edilebilir.
✓ C-Level (Executive) KPI Dashboard'lar ile tüm zeka tek ekrandan izlenir.
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-09
#
# INSTITUTIONAL MARKET INTELLIGENCE PLATFORM
# Version 9.0 Enterprise Ultimate
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: Piyasa verilerini, haberleri, makroekonomik gelişmeleri, sektör hareketlerini, Temel Analizi (Fundamental) ve Quant modellerini tek merkezde birleştirerek kurumsal seviyede Market Intelligence Hub oluşturmak.

Modüller (61-76 Arası):
- Market Overview & Breadth Engine (Advance/Decline)
- Sector & Macro Economic Intelligence
- News & Sentiment Engine
- Market Regime Engine (Boğa/Ayı/Yatay)
- Alert Center (Anlık Uyarılar)
- Enterprise Quant & Fundamental Intelligence (Modül 76)
  - Finansal Oranlar, DCF, Piotroski F Score, Altman Z Score
  - Multi-Factor Models (Value, Growth, Momentum)

CFG-09 TAMAMLANDIĞINDA:
✓ Hisse sadece teknik olarak değil; Temel (Bilanço), Makro, Kantitatif ve Sentiment olarak da analiz edilecek.
✓ Tüm bu veriler yapay zekanın Karar Alma mekanizmasına (AI Decision) entegre edilecek.
✓ VarantRadar Pro, Bloomberg Terminali seviyesinde bir Kurumsal Zeka Merkezi haline gelecek.
###############################################################

###############################################################
# VARANTRADAR PRO
#
# CFG-10
#
# ENTERPRISE FINANCIAL INTELLIGENCE ECOSYSTEM
# Version 10.0 Ultimate
###############################################################

Durum: Planlandı
Öncelik: ★★★★★

Amaç: VarantRadar'ı sadece analiz yapan bir uygulama olmaktan çıkarıp; Hisse, Varant, VİOP, ETF, Fon, Endeks, Döviz, Emtia, Tahvil, Kripto için çalışan, modüler, yapay zekâ destekli, kurumsal yatırım ekosistemine dönüştürmek.

Modüller (91-100 Arası):
- Enterprise Investment Hub
- Global Market Intelligence
- Institutional Research Center
- Executive Decision Engine (Tüm skorların birleşimi)
- Autonomous Investment Assistant
- Advanced Quant Lab
- Fundamental Intelligence Center
- Enterprise Risk Platform
- Digital Investment Office (AI CIO, AI CRO, AI Quant Director)
- Enterprise Platform Services

CFG-10 TAMAMLANDIĞINDA:
✓ Tüm varlık sınıfları tek platformda analiz edilir.
✓ Teknik, temel, kantitatif, makro ve haber analizleri ortak AI karar motorunda (Executive Decision Engine) birleşir.
✓ Kullanıcıya 'Sanal Yönetim Kurulu' (Digital Investment Office) eşlik eder.
###############################################################
