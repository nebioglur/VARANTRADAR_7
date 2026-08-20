# Borsa İstanbul (BIST) Güncel Hisse Listesi (Otomatik Çekildi)
# Toplam: 613 Hisse

BIST_SYMBOLS = [
    "A1CAP.IS", "A1YEN.IS", "AAGYO.IS", "ACSEL.IS", "ADEL.IS", "ADESE.IS", "ADGYO.IS", "AEFES.IS", "AFYON.IS", "AGESA.IS",
    "AGHOL.IS", "AGROT.IS", "AGYO.IS", "AHGAZ.IS", "AHSGY.IS", "AKBET.IS", "AKBNK.IS", "AKCNS.IS", "AKENR.IS", "AKFGY.IS",
    "AKFIS.IS", "AKFYE.IS", "AKGRT.IS", "AKHAN.IS", "AKMGY.IS", "AKSA.IS", "AKSEN.IS", "AKSGY.IS", "AKSUE.IS", "AKYHO.IS",
    "ALARK.IS", "ALBRK.IS", "ALCAR.IS", "ALCTL.IS", "ALFAS.IS", "ALGYO.IS", "ALKA.IS", "ALKIM.IS", "ALKLC.IS", "ALTINS1.IS",
    "ALTNY.IS", "ALVES.IS", "AMSY.IS", "ANELE.IS", "ANGEN.IS", "ANHYT.IS", "ANSGR.IS", "ARASE.IS", "ARCLK.IS", "ARDYZ.IS",
    "ARENA.IS", "ARFYE.IS", "ARMGD.IS", "ARSAN.IS", "ARTMS.IS", "ARZUM.IS", "ASELS.IS", "ASGYO.IS", "ASTOR.IS", "ASUZU.IS",
    "ATAGY.IS", "ATAKP.IS", "ATATP.IS", "ATATR.IS", "ATEKS.IS", "ATLAS.IS", "ATSYH.IS", "AVGYO.IS", "AVHOL.IS", "AVOD.IS",
    "AVPGY.IS", "AYCES.IS", "AYDEM.IS", "AYEN.IS", "AYES.IS", "AYGAZ.IS", "AZTEK.IS", "BAGFS.IS", "BAHKM.IS", "BAKAB.IS",
    "BALAT.IS", "BALSU.IS", "BANVT.IS", "BARMA.IS", "BASCM.IS", "BASGZ.IS", "BAYRK.IS", "BEGYO.IS", "BELEN.IS", "BERA.IS",
    "BESLR.IS", "BESTE.IS", "BETAE.IS", "BEYAZ.IS", "BFREN.IS", "BIENY.IS", "BIGCH.IS", "BIGEN.IS", "BIGTK.IS", "BIMAS.IS",
    "BINBN.IS", "BINHO.IS", "BIOEN.IS", "BIZIM.IS", "BJKAS.IS", "BLCYT.IS", "BLKGN.IS", "BLUME.IS", "BMSCH.IS", "BMSTL.IS",
    "BNATR.IS", "BNTAS.IS", "BOBET.IS", "BORLS.IS", "BORSK.IS", "BOSSA.IS", "BRISA.IS", "BRKO.IS", "BRKSN.IS", "BRKVY.IS",
    "BRLSM.IS", "BRMEN.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "BUCIM.IS", "BULGS.IS", "BURCE.IS", "BURVA.IS",
    "BVSAN.IS", "BYDNR.IS", "CANTE.IS", "CASA.IS", "CATES.IS", "CCOLA.IS", "CELHA.IS", "CEMAS.IS", "CEMTS.IS", "CEMZY.IS",
    "CEOEM.IS", "CEYLN.IS", "CGCAM.IS", "CIMSA.IS", "CLEBI.IS", "CMBTN.IS", "CMENT.IS", "COKLU.IS", "CONSE.IS", "COSMO.IS",
    "CRDFA.IS", "CRFSA.IS", "CUSAN.IS", "CVKMD.IS", "CWENE.IS", "DAFNE.IS", "DAGI.IS", "DAPGM.IS", "DARDL.IS", "DCTTR.IS",
    "DEFNE.IS", "DENGE.IS", "DERHL.IS", "DERIM.IS", "DESA.IS", "DESPC.IS", "DEVA.IS", "DGATE.IS", "DGGYO.IS", "DGNMO.IS",
    "DIRIT.IS", "DITAS.IS", "DMRGD.IS", "DMSAS.IS", "DNISI.IS", "DOAS.IS", "DOCO.IS", "DOFER.IS", "DOFRB.IS", "DOGUB.IS",
    "DOHOL.IS", "DOKTA.IS", "DSTKF.IS", "DUNYH.IS", "DUPNT.IS", "DURDO.IS", "DURKN.IS", "DYOBY.IS", "DZGYO.IS", "EBEBK.IS",
    "ECILC.IS", "ECOGR.IS", "ECZYT.IS", "EDATA.IS", "EDIP.IS", "EFOR.IS", "EGEEN.IS", "EGEGY.IS", "EGEPO.IS", "EGGUB.IS",
    "EGPRO.IS", "EGSER.IS", "EKDMR.IS", "EKGYO.IS", "EKIM.IS", "EKIZ.IS", "EKOS.IS", "EKSUN.IS", "ELITE.IS", "ELTEK.IS",
    "EMKEL.IS", "EMNIS.IS", "EMPAE.IS", "ENDAE.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "ENPRA.IS", "ENRVT.IS", "ENSRI.IS",
    "ENTRA.IS", "EPLAS.IS", "ERBOS.IS", "ERCB.IS", "EREGL.IS", "ERSU.IS", "ESCAR.IS", "ESCOM.IS", "ESEN.IS", "ETILR.IS",
    "ETYAT.IS", "EUHOL.IS", "EUKYO.IS", "EUPWR.IS", "EUREN.IS", "EUYO.IS", "EYGYO.IS", "FADE.IS", "FENER.IS", "FHEAL.IS",
    "FLAP.IS", "FMIZP.IS", "FMPLAST.IS", "FONET.IS", "FORMT.IS", "FORTE.IS", "FRIGO.IS", "FRMPL.IS", "FROTO.IS", "FZLGY.IS",
    "GADIS.IS", "GARAN.IS", "GARFA.IS", "GATEG.IS", "GEDIK.IS", "GEDZA.IS", "GENIL.IS", "GENKM.IS", "GENTS.IS", "GEREL.IS",
    "GESAN.IS", "GIPTA.IS", "GLBMD.IS", "GLCVY.IS", "GLRMK.IS", "GLRYH.IS", "GLYHO.IS", "GMTAS.IS", "GOKNR.IS", "GOLDA.IS",
    "GOLTS.IS", "GOODY.IS", "GORBN.IS", "GOZDE.IS", "GRNYO.IS", "GRSEL.IS", "GRTHO.IS", "GSDDE.IS", "GSDHO.IS", "GSRAY.IS",
    "GUBRF.IS", "GUNDG.IS", "GWIND.IS", "GZNMI.IS", "HAFSA.IS", "HALKB.IS", "HATEK.IS", "HATSN.IS", "HDFGS.IS", "HEDEF.IS",
    "HEKTS.IS", "HKTM.IS", "HLGYO.IS", "HOROZ.IS", "HRKET.IS", "HTTBT.IS", "HUBVC.IS", "HUNER.IS", "HURGZ.IS", "HZNDR.IS",
    "ICBCT.IS", "ICUGS.IS", "IDGYO.IS", "IEYHO.IS", "IHAAS.IS", "IHEVA.IS", "IHGZT.IS", "IHLAS.IS", "IHLGM.IS", "IHYAY.IS",
    "IMASM.IS", "INDES.IS", "INFO.IS", "INGRM.IS", "INTEK.IS", "INTEM.IS", "INVEO.IS", "INVES.IS", "ISBIR.IS", "ISBTR.IS",
    "ISCTR.IS", "ISDMR.IS", "ISFIN.IS", "ISGYO.IS", "ISKPL.IS", "ISKUR.IS", "ISMEN.IS", "ISSEN.IS", "ISVEA.IS", "IZENR.IS",
    "IZFAS.IS", "IZINV.IS", "IZMDC.IS", "JANTS.IS", "KAPLM.IS", "KAREL.IS", "KARSN.IS", "KARTN.IS", "KATMR.IS", "KAYSE.IS",
    "KBORU.IS", "KCAER.IS", "KCHOL.IS", "KENT.IS", "KERVN.IS", "KFEIN.IS", "KGYO.IS", "KIMMR.IS", "KLGYO.IS", "KLKIM.IS",
    "KLMSN.IS", "KLNMA.IS", "KLRHO.IS", "KLSER.IS", "KLSYN.IS", "KLYPV.IS", "KMPUR.IS", "KNFRT.IS", "KOCMT.IS", "KONKA.IS",
    "KONTR.IS", "KONYA.IS", "KOPOL.IS", "KORDS.IS", "KOTON.IS", "KRDMA.IS", "KRDMB.IS", "KRDMD.IS",
    "KRGYO.IS", "KRONT.IS", "KRPLS.IS", "KRSTL.IS", "KRTEK.IS", "KRVAK.IS", "KRVGD.IS", "KSTUR.IS", "KTLEV.IS", "KTSKR.IS",
    "KUTPO.IS", "KUVVA.IS", "KUYAS.IS", "KZBGY.IS", "KZGYO.IS", "LIDER.IS", "LIDFA.IS", "LILAK.IS", "LINK.IS", "LKMNH.IS",
    "LMKDC.IS", "LOGO.IS", "LRSHO.IS", "LUKSK.IS", "LXGYO.IS", "LYDHO.IS", "LYDYE.IS", "MAALT.IS", "MACKO.IS", "MAGEN.IS",
    "MAKIM.IS", "MAKTK.IS", "MANAS.IS", "MARBL.IS", "MARKA.IS", "MARMR.IS", "MARTI.IS", "MAVI.IS", "MCARD.IS", "MEDTR.IS",
    "MEGAP.IS", "MEGMT.IS", "MEKAG.IS", "MEPET.IS", "MERCN.IS", "MERIT.IS", "MERKO.IS", "METRO.IS", "MEYSU.IS", "MGROS.IS",
    "MHRGY.IS", "MIATK.IS", "MMCAS.IS", "MNDRS.IS", "MNDTR.IS", "MOBTL.IS", "MOGAN.IS", "MOPAS.IS", "MPARK.IS", "MRGYO.IS",
    "MRSHL.IS", "MSGYO.IS", "MTRKS.IS", "MTRYO.IS", "MZHLD.IS", "NATEN.IS", "NETAS.IS", "NETCD.IS", "NIBAS.IS", "NINSA.IS",
    "NTGAZ.IS", "NTHOL.IS", "NUGYO.IS", "NUHCM.IS", "OBAMS.IS", "OBASE.IS", "ODAS.IS", "ODINE.IS", "OFSYM.IS", "ONCSM.IS",
    "ONRYT.IS", "ORCAY.IS", "ORGE.IS", "ORMA.IS", "ORZAX.IS", "OSMEN.IS", "OSTIM.IS", "OTKAR.IS", "OTTO.IS", "OYAKC.IS",
    "OYAYO.IS", "OYLMP.IS", "OYLUM.IS", "OYYAT.IS", "OZATD.IS", "OZGYO.IS", "OZKGY.IS", "OZRDN.IS", "OZSUB.IS", "OZYSR.IS",
    "PAGYO.IS", "PAHOL.IS", "PAMEL.IS", "PAPIL.IS", "PARSN.IS", "PASEU.IS", "PATEK.IS", "PCILT.IS", "PEKGY.IS", "PENGD.IS",
    "PENTA.IS", "PETKM.IS", "PETUN.IS", "PGOLD.IS", "PGSUS.IS", "PINSU.IS", "PKART.IS", "PKENT.IS", "PLTFM.IS", "PLTUR.IS",
    "PNLSN.IS", "PNSUT.IS", "POLHO.IS", "POLTK.IS", "PRDGS.IS", "PRKAB.IS", "PRKME.IS", "PRZMA.IS", "PSDTC.IS", "PSGYO.IS",
    "QNBFK.IS", "QNBTR.IS", "QUAGR.IS", "RALYH.IS", "RAYSG.IS", "REEDR.IS", "RGYAS.IS", "RNPOL.IS", "RODRG.IS", "RTALB.IS",
    "RUBNS.IS", "RUZYE.IS", "RYGYO.IS", "RYSAS.IS", "SAFKR.IS", "SAHOL.IS", "SAMAT.IS", "SANEL.IS", "SANFM.IS", "SANKO.IS",
    "SARKY.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SEGMN.IS", "SEGYO.IS", "SEKFK.IS", "SEKUR.IS", "SELEC.IS", "SELVA.IS",
    "SERNT.IS", "SEYHO.IS", "SEYKM.IS", "SILVR.IS", "SISE.IS", "SKBNK.IS", "SKTAS.IS", "SKYLP.IS", "SKYMD.IS", "SMART.IS",
    "SMRTG.IS", "SMRVA.IS", "SNGYO.IS", "SNICA.IS", "SNPAM.IS", "SODSN.IS", "SOHOE.IS", "SOKE.IS", "SOKM.IS", "SONME.IS",
    "SRVGY.IS", "SUMAS.IS", "SUNPL.IS", "SUNTK.IS", "SURGY.IS", "SUWEN.IS", "SVGYO.IS", "TABAK.IS", "TABGD.IS", "TARKM.IS",
    "TATEN.IS", "TATGD.IS", "TAVHL.IS", "TBORG.IS", "TCELL.IS", "TCKRC.IS", "TDGYO.IS", "TEHOL.IS", "TEKTU.IS", "TERA.IS",
    "TEZOL.IS", "TGSAS.IS", "THYAO.IS", "TKFEN.IS", "TKNSA.IS", "TKURU.IS", "TLMAN.IS", "TMPOL.IS", "TMSN.IS", "TNZTP.IS",
    "TOASO.IS", "TRALT.IS", "TRCAS.IS", "TRENJ.IS", "TRGYO.IS", "TRHOL.IS", "TRILC.IS", "TRMET.IS", "TRNSK.IS", "TSGYO.IS",
    "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUKAS.IS", "TUPRS.IS", "TUREX.IS", "TURGG.IS", "TURNT.IS",
    "TURSG.IS", "UCAYM.IS", "UFUK.IS", "ULAS.IS", "ULKER.IS", "ULUFA.IS", "ULUSE.IS", "ULUUN.IS", "UNLU.IS", "USAK.IS",
    "VAKBN.IS", "VAKFA.IS", "VAKFN.IS", "VAKKO.IS", "VANGD.IS", "VBTYZ.IS", "VERUS.IS", "VESBE.IS", "VESTL.IS", "VKFYO.IS",
    "VKGYO.IS", "VKING.IS", "VRGYO.IS", "VSNMD.IS", "YAPRK.IS", "YATAS.IS", "YAYLA.IS", "YBTAS.IS", "YEOTK.IS", "YESIL.IS",
    "YGGYO.IS", "YIGIT.IS", "YKBNK.IS", "YKSLN.IS", "YONGA.IS", "YUNSA.IS", "YYAPI.IS", "YYLGD.IS", "ZEDUR.IS", "ZERGY.IS",
    "ZGYO.IS", "ZOREN.IS", "ZRGYO.IS", "ZTCNR.IS"
]

# Macro and Index symbols
MACRO_SYMBOLS = {
    "BIST100": "XU100.IS",
    "USD/TRY": "TRY=X",
    "EUR/TRY": "EURTRY=X",
    "GOLD": "GC=F",
    "SILVER": "SI=F"
}

# V11 - Global Market Symbols (Örnek)
GLOBAL_SYMBOLS = [
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOGL",
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
    "EURUSD=X", "GBPUSD=X", "JPY=X"
]

# Yeni Pazar Tanımlamaları
FX_SYMBOLS = [
    "USDTRY=X", "EURTRY=X", "GBPTRY=X", "CHFTRY=X", "JPYTRY=X",
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"
]

COMMODITY_SYMBOLS = [
    "GC=F", # Altın (Gold)
    "SI=F", # Gümüş (Silver)
    "CL=F", # Ham Petrol (Crude Oil)
    "BZ=F", # Brent Petrol
    "HG=F", # Bakır (Copper)
    "PA=F"  # Paladyum
]

CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOGE-USD", "DOT-USD", "LINK-USD"
]

ALL_GLOBAL_SYMBOLS = BIST_SYMBOLS + list(MACRO_SYMBOLS.values()) + GLOBAL_SYMBOLS + FX_SYMBOLS + COMMODITY_SYMBOLS + CRYPTO_SYMBOLS

BIST30_SYMBOLS = ["AKBNK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "EKGYO.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KRDMD.IS", "ODAS.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", "TTKOM.IS", "TUPRS.IS", "YKBNK.IS", "ALFAS.IS"]

BIST50_SYMBOLS = BIST30_SYMBOLS + ["AEFES.IS", "AGHOL.IS", "AKCNS.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "BERA.IS", "BRISA.IS", "CANTE.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "ENJSA.IS", "EUPWR.IS", "GESAN.IS", "ISMEN.IS", "KLSER.IS"]

# Yaklaşık olarak Yıldız Pazar hisseleri (Piyasa Değeri Yüksek) - Temsili Olarak BIST_SYMBOLS'un ilk 200'ü alınmıştır. Gerçek hayatta KAP'tan beslenir.
YILDIZ_SYMBOLS = BIST_SYMBOLS[:200]

# ==========================================
# ♟️ BIST Sektörel Domino & Kardeş Hisse Kümeleri
# ==========================================
DOMINO_CLUSTERS = {
    "SAVUNMA": ["ASELS.IS", "SDTTR.IS", "PAPIL.IS", "PATEK.IS", "ALTNY.IS"],
    "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "CLEBI.IS", "RYSAS.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "TSKB.IS", "ALBRK.IS"],
    "HOLDING": ["KCHOL.IS", "SAHOL.IS", "DOHOL.IS", "AGHOL.IS", "ALARK.IS", "BERA.IS", "TKFEN.IS", "ENKAI.IS"],
    "OTOMOTIV": ["FROTO.IS", "TOASO.IS", "TTRAK.IS", "DOAS.IS", "ASUZU.IS", "OTKAR.IS", "KORDS.IS", "BRISA.IS"],
    "ENERJI": ["ASTOR.IS", "EUPWR.IS", "GESAN.IS", "CWENE.IS", "ALFAS.IS", "SMRTG.IS", "KONTR.IS", "YEOTK.IS", "ZOREN.IS", "AKSEN.IS", "ENERY.IS"],
    "DEMIR_CELIK": ["EREGL.IS", "KRDMD.IS", "ISDMR.IS", "KCAER.IS", "CEMTS.IS", "CVKMD.IS"],
    "YAZILIM_TEKNO": ["MIATK.IS", "FONET.IS", "VBTYZ.IS", "ARDYZ.IS", "FORTE.IS", "LINK.IS", "LOGO.IS", "REEDR.IS", "OBAMS.IS"],
    "PERAKENDE_GIDA": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "CCOLA.IS", "AEFES.IS", "ULKER.IS", "TATGD.IS"],
    "KIMYA_PETROL": ["TUPRS.IS", "PETKM.IS", "SASA.IS", "HEKTS.IS", "GUBRF.IS", "BAGFS.IS", "AKSA.IS"],
    "CIMENTO_GYO": ["EKGYO.IS", "ISGYO.IS", "OYAKC.IS", "CIMSA.IS", "AKCNS.IS", "NUHCM.IS", "BOBET.IS"],
    "CAM_SERAMIK": ["SISE.IS", "KLSER.IS", "EGSER.IS", "QUAGR.IS", "KUTPO.IS"],
    "ILETISIM": ["TCELL.IS", "TTKOM.IS"]
}

# ==========================================
# 🎯 Varant Dayanak Eşleştirme Sözlüğü
# ==========================================
WARRANT_UNDERLYING_MAP = {
    "THYAO": {"prefix": "TH", "leverage": 6.8, "name": "THYAO Alım Varantı"},
    "AKBNK": {"prefix": "AK", "leverage": 6.2, "name": "AKBNK Alım Varantı"},
    "GARAN": {"prefix": "GA", "leverage": 5.9, "name": "GARAN Alım Varantı"},
    "ISCTR": {"prefix": "IS", "leverage": 6.5, "name": "ISCTR Alım Varantı"},
    "YKBNK": {"prefix": "YK", "leverage": 6.4, "name": "YKBNK Alım Varantı"},
    "EREGL": {"prefix": "ER", "leverage": 5.5, "name": "EREGL Alım Varantı"},
    "TUPRS": {"prefix": "TP", "leverage": 7.0, "name": "TUPRS Alım Varantı"},
    "KCHOL": {"prefix": "KC", "leverage": 6.0, "name": "KCHOL Alım Varantı"},
    "SAHOL": {"prefix": "SA", "leverage": 5.8, "name": "SAHOL Alım Varantı"},
    "SISE": {"prefix": "SI", "leverage": 5.4, "name": "SISE Alım Varantı"},
    "PETKM": {"prefix": "PE", "leverage": 6.1, "name": "PETKM Alım Varantı"},
    "BIMAS": {"prefix": "BI", "leverage": 5.7, "name": "BIMAS Alım Varantı"},
    "ASELS": {"prefix": "AS", "leverage": 6.3, "name": "ASELS Alım Varantı"},
    "EKGYO": {"prefix": "EK", "leverage": 6.9, "name": "EKGYO Alım Varantı"},
    "FROTO": {"prefix": "FR", "leverage": 5.8, "name": "FROTO Alım Varantı"},
    "TOASO": {"prefix": "TO", "leverage": 5.6, "name": "TOASO Alım Varantı"},
    "TCELL": {"prefix": "TC", "leverage": 6.0, "name": "TCELL Alım Varantı"},
    "PGSUS": {"prefix": "PG", "leverage": 7.2, "name": "PGSUS Alım Varantı"}
}
