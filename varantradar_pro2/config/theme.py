THEME_CONFIG = {
    'dark': {
        'bg_color': '#1E1E1E',
        'text_color': '#FFFFFF',
        'primary_color': '#00ADB5',
        'danger_color': '#FF2E63',
        'success_color': '#00E676'
    },
    'light': {
        'bg_color': '#FFFFFF',
        'text_color': '#121212',
        'primary_color': '#0056b3',
        'danger_color': '#D32F2F',
        'success_color': '#2E7D32'
    }
}

CURRENT_THEME = 'dark'

def get_theme() -> dict:
    return THEME_CONFIG.get(CURRENT_THEME, THEME_CONFIG['dark'])

def set_theme(theme_name: str):
    global CURRENT_THEME
    if theme_name in THEME_CONFIG:
        CURRENT_THEME = theme_name
