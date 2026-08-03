TRANSLATIONS = {
    'tr': {
        'app_title': 'VarantRadar Pro',
        'score': 'Güven Puanı',
        'buy': 'AL',
        'sell': 'SAT',
        'wait': 'BEKLE',
        'reason': 'Neden?',
        'error': 'Hata',
        'success': 'Başarılı'
    },
    'en': {
        'app_title': 'VarantRadar Pro',
        'score': 'Confidence Score',
        'buy': 'BUY',
        'sell': 'SELL',
        'wait': 'WAIT',
        'reason': 'Reason',
        'error': 'Error',
        'success': 'Success'
    }
}

CURRENT_LANG = 'tr'

def t(key: str) -> str:
    return TRANSLATIONS.get(CURRENT_LANG, {}).get(key, key)

def set_language(lang: str):
    global CURRENT_LANG
    if lang in TRANSLATIONS:
        CURRENT_LANG = lang
