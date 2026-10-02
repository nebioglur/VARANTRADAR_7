# CFG-02: CORE ARCHITECTURE
**Sistemin İskeleti ve Çekirdek Yönetimi**

VarantRadar Pro, bağımsız scriptlerin yan yana çalıştığı basit bir uygulama değildir. Kendine ait bir yaşam döngüsü (Lifecycle), bellek yönetimi ve otonom haberleşme ağı olan bir Kurumsal İşletim Sistemidir (Enterprise Financial Operating System).

Bu belge, sistemin üzerinde yükseleceği teknolojik iskeleti tanımlar.

---

## 1. Core Engine (Sistem Çekirdeği)
Tüm sistemin kalbidir. Sistemin başlatılması (Boot), kapatılması (Shutdown) ve hata anında (Crash) kurtarılması (Recovery) işlemlerinden sorumludur. Hiçbir analiz motoru (Teknik, Temel vs.) doğrudan çalıştırılamaz; hepsi Core Engine tarafından uyandırılarak hafızaya alınır.

## 2. Engine Manager & Service Registry
Sistemde onlarca farklı "Engine" (Motor) bulunacaktır (Sentiment Engine, Quant Engine, Risk Engine vb.).
- **Engine Manager:** Hangi motorun ne zaman çalışacağını, donanım kaynaklarını (CPU/RAM) nasıl kullanacağını koordine eden yöneticidir.
- **Service Registry:** Çalışan tüm motorların kendini kaydettiği bir "Telefon Rehberi"dir. Motorlar birbirleriyle doğrudan (Tightly Coupled) konuşmazlar, Registry üzerinden adres bulurlar. Bu sayede bir motor çökerse, tüm sistem çökmez.

## 3. Event Bus (Olay Yöneticisi)
Piyasalarda veri sürekli akar ve olaylar anlık gelişir. Sistemin hantal bir şekilde sırayla çalışmasını engellemek için **Event-Driven Architecture (Olay Güdümlü Mimari)** kullanılır.
- Bir modül (Örn: Haber Motoru) negatif bir haber yakaladığında doğrudan Portföy yöneticisini çağırmaz. Bunun yerine Event Bus'a `"CRITICAL_NEWS_ALERT"` isimli bir olay (Event) fırlatır (Emit).
- İlgili diğer modüller (Risk Motoru, Otonom Trader) bu olayı dinler (Subscribe) ve eşzamanlı olarak anında kendi aksiyonlarını alırlar.
- Bu yapı, sistemin mikrosaniye seviyesinde asenkron tepki vermesini sağlar.

## 4. Workflow Engine & Scheduler
Zamanlanmış otonom görevlerin beynidir.
- **Scheduler:** Belirli periyotlarda (Örn: Her sabah 09:50'de KAP haberlerini tara, Her saat başı portföy riskini ölç) görevleri kuyruğa alan zamanlayıcıdır.
- **Workflow Engine:** Zincirleme görevleri yönetir. Örneğin bir "Akşam Kapanış Analizi" tetiklendiğinde; sırasıyla *1. Veriyi Çek -> 2. AI Modellerini Çalıştır -> 3. Raporu Oluştur -> 4. Kullanıcıya E-Posta at* zincirinin (Pipeline) hatasız yürümesini sağlar.

## 5. Plugin System (Eklenti Mimarisi)
Kurumsal yazılımlar monolitik (tek parça) olamaz. VarantRadar Pro, **Plug & Play (Tak-Çalıştır)** mantığına sahiptir.
- Sisteme eklenecek olan yeni bir veri kaynağı (Örn: VİOP, Kripto) veya yeni bir yapay zeka dili (Örn: GPT-5 entegrasyonu), çekirdek kodlar değiştirilmeden sisteme dışarıdan bir `Plugin` (Eklenti) olarak dahil edilebilir.
- Bu sayede sistem, gelecekte çıkacak her türlü finansal enstrümana veya teknolojiye dakikalar içinde uyum sağlayabilir.
