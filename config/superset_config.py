import os
from urllib.parse import quote_plus

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

_metadata_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")

if _metadata_uri:
    SQLALCHEMY_DATABASE_URI = _metadata_uri
else:
    _db_user = os.environ.get("DATABASE_USER") or os.environ["POSTGRES_USER"]
    _db_password = quote_plus(os.environ.get("DATABASE_PASSWORD") or os.environ["POSTGRES_PASSWORD"])
    _db_host = os.environ.get("DATABASE_HOST", "postgres")
    _db_port = os.environ.get("DATABASE_PORT", "5432")
    _db_name = os.environ.get("DATABASE_DB", "superset")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{_db_user}:{_db_password}@"
        f"{_db_host}:{_db_port}/{_db_name}"
    )

# --- RBAC ---
FEATURE_FLAGS = {
    "DASHBOARD_RBAC": True,
}

FAB_ADD_SECURITY_API = True

# --- Performance (Redis) ---
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_CACHE_DB = int(os.environ.get("REDIS_CACHE_DB", "1"))


def _redis_cache_config(key_prefix: str, timeout: int) -> dict:
    return {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": timeout,
        "CACHE_KEY_PREFIX": key_prefix,
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": REDIS_CACHE_DB,
    }


CACHE_CONFIG = _redis_cache_config("superset_cache_", 300)
DATA_CACHE_CONFIG = _redis_cache_config("superset_data_", 86400)

ROW_LIMIT = int(os.environ.get("SUPERSET_ROW_LIMIT", "50000"))
SQL_MAX_ROW = int(os.environ.get("SUPERSET_SQL_MAX_ROW", "100000"))

# --- Branding (ATP Corporate Design: atp-corporate-design skill) ---
APP_NAME = os.environ.get("SUPERSET_APP_NAME", "ATP architekten ingenieure")
LOGO_TARGET_PATH = os.environ.get("SUPERSET_LOGO_TARGET_PATH", "/superset/welcome/")
_brand_logo_height = os.environ.get("SUPERSET_LOGO_HEIGHT", "64px")
_brand_logo_max_width = int(os.environ.get("SUPERSET_LOGO_MAX_WIDTH", "360"))
_brand_font_ui = os.environ.get(
    "SUPERSET_BRAND_FONT_UI",
    "Univers, 'Linotype Univers', 'Helvetica Neue', Helvetica, Arial, sans-serif",
)
_brand_font_code = os.environ.get(
    "SUPERSET_BRAND_FONT_CODE",
    "Univers, 'Linotype Univers', 'Courier New', monospace",
)

# Official ATP palette: red #CC0033, black #000000, gray 40% / 10% surfaces
_brand_primary = os.environ.get("SUPERSET_BRAND_COLOR", "#CC0033")
_brand_link = os.environ.get("SUPERSET_BRAND_COLOR_LINK", _brand_primary)
_brand_text = os.environ.get("SUPERSET_BRAND_COLOR_TEXT", "#000000")
_brand_neutral = os.environ.get("SUPERSET_BRAND_COLOR_NEUTRAL", "#666666")
_brand_bg = os.environ.get("SUPERSET_BRAND_COLOR_BG", "#E6E6E6")
_brand_surface = os.environ.get("SUPERSET_BRAND_COLOR_SURFACE", "#FFFFFF")
_brand_success = os.environ.get("SUPERSET_BRAND_COLOR_SUCCESS", "#666666")
_brand_warning = os.environ.get("SUPERSET_BRAND_COLOR_WARNING", "#666666")
_brand_error = os.environ.get("SUPERSET_BRAND_COLOR_ERROR", "#CC0033")
_brand_info = os.environ.get("SUPERSET_BRAND_COLOR_INFO", "#666666")

_branding_base = "/static/assets/images/branding"
_app_icon = os.environ.get("SUPERSET_APP_ICON")
if _app_icon:
    APP_ICON = _app_icon
    APP_ICON_DARK = os.environ.get("SUPERSET_APP_ICON_DARK", _app_icon)
elif os.environ.get("SUPERSET_LOGO_S3_KEY"):
    APP_ICON = f"{_branding_base}/logo.png"
    APP_ICON_DARK = f"{_branding_base}/logo-dark.png"
else:
    APP_ICON = "/static/assets/images/superset-logo-horiz.png"
    APP_ICON_DARK = APP_ICON

FAVICONS = [{"href": f"{_branding_base}/favicon.png"}]

_shared_theme_tokens = {
    "brandAppName": APP_NAME,
    "brandLogoAlt": APP_NAME,
    "brandLogoMargin": "16px 32px 16px 0",
    "brandLogoHref": LOGO_TARGET_PATH,
    "brandLogoHeight": _brand_logo_height,
    "brandIconMaxWidth": _brand_logo_max_width,
    "brandSpinnerUrl": None,
    "brandSpinnerSvg": None,
    "colorPrimary": _brand_primary,
    "colorLink": _brand_link,
    "colorError": _brand_error,
    "colorWarning": _brand_warning,
    "colorSuccess": _brand_success,
    "colorInfo": _brand_info,
    "fontUrls": [],
    "fontFamily": _brand_font_ui,
    "fontFamilyCode": _brand_font_code,
    "transitionTiming": 0.3,
    "fontSizeXS": "8",
    "fontSizeXXL": "24",
    "fontWeightNormal": "300",
    "fontWeightLight": "300",
    "fontWeightStrong": "500",
    "fontWeightBold": "500",
}

THEME_DEFAULT = {
    "algorithm": "default",
    "token": {
        **_shared_theme_tokens,
        "brandLogoUrl": APP_ICON,
        "colorText": _brand_text,
        "colorTextSecondary": _brand_neutral,
        "colorBgLayout": _brand_bg,
        "colorBgContainer": _brand_surface,
        "colorBorder": _brand_bg,
        "colorEditorSelection": "#F5F5F5",
    },
}

THEME_DARK = {
    "algorithm": "dark",
    "token": {
        **_shared_theme_tokens,
        "brandLogoUrl": APP_ICON_DARK,
        "colorText": "#E6E6E6",
        "colorTextSecondary": "#999999",
        "colorBgLayout": "#1A1A1A",
        "colorBgContainer": "#141414",
        "colorBorder": "#333333",
        "colorEditorSelection": "#333333",
    },
}
