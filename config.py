import os

# ═══════════════════════════════════════════════════════════════
# إعدادات البوت الرئيسية
# ═══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# مفاتيح API المجانية (اختياري - يعمل بدونها)
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "demo")
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY", "")

# ═══════════════════════════════════════════════════════════════
# أزواج العملات OTC المتاحة على Pocket Option
# ═══════════════════════════════════════════════════════════════
ASSETS_TO_MONITOR = [
    {"symbol": "AUDCAD=X", "name": "AUD/CAD-OTC", "category": "Cross"},
    {"symbol": "AUDCHF=X", "name": "AUD/CHF-OTC", "category": "Cross"},
    {"symbol": "AUDNZD=X", "name": "AUD/NZD-OTC", "category": "Cross"},
    {"symbol": "EURCHF=X", "name": "EUR/CHF-OTC", "category": "Cross"},
    {"symbol": "EURUSD=X", "name": "EUR/USD-OTC", "category": "Major"},
    {"symbol": "EURNZD=X", "name": "EUR/NZD-OTC", "category": "Cross"},
    {"symbol": "EURGBP=X", "name": "EUR/GBP-OTC", "category": "Cross"},
    {"symbol": "EURJPY=X", "name": "EUR/JPY-OTC", "category": "JPY"},
    {"symbol": "CADCHF=X", "name": "CAD/CHF-OTC", "category": "Cross"},
    {"symbol": "CADJPY=X", "name": "CAD/JPY-OTC", "category": "JPY"},
    {"symbol": "CHFJPY=X", "name": "CHF/JPY-OTC", "category": "JPY"},
]

# ═══════════════════════════════════════════════════════════════
# إعدادات التحليل الفني
# ═══════════════════════════════════════════════════════════════

# RSI
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

# EMA
EMA_SHORT_PERIOD = 5
EMA_MEDIUM_PERIOD = 13
EMA_LONG_PERIOD = 21

# البولنجر باند
BB_PERIOD = 20
BB_STD = 2

# الاستوكاستيك
STOCH_PERIOD = 14
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20

# CCI
CCI_OVERBOUGHT = 100
CCI_OVERSOLD = -100

# ADX
ADX_PERIOD = 14
ADX_STRONG_TREND = 25

# Williams %R
WILLIAMS_OVERBOUGHT = -20
WILLIAMS_OVERSOLD = -80

# ═══════════════════════════════════════════════════════════════
# إعدادات الإشارات
# ═══════════════════════════════════════════════════════════════

# مدة الصفقة
TRADE_DURATION = "1 دقيقة"

# الحد الأدنى لنسبة الربح المطلوبة
MIN_PAYOUT_PERCENTAGE = 80

# الحد الأقصى للصفقات اليومية
MAX_DAILY_TRADES = 30

# عدد التأكيدات المطلوبة للدخول (من 12 مؤشر)
MIN_CONFIRMATIONS = 6

# إعدادات الإشارات التلقائية (بالدقائق)
AUTO_SIGNAL_INTERVAL = 5

# الحد الأقصى للإشارات لكل طلب
MAX_SIGNALS_PER_REQUEST = 5

# ═══════════════════════════════════════════════════════════════
# إعدادات إدارة المخاطر
# ═══════════════════════════════════════════════════════════════

# مارتينجيل
MARTINGALE_STEPS = 1  # وحدة واحدة فقط

# نسبة المخاطرة من رأس المال
MAX_RISK_PER_TRADE = 5  # %

# الحد الأقصى للخسائر اليومية المتتالية قبل التوقف
MAX_CONSECUTIVE_LOSSES = 3

# الحد الأقصى لنسبة الخسارة اليومية
MAX_DAILY_LOSS_PERCENT = 15  # %

# رأس المال الافتراضي
DEFAULT_CAPITAL = 100  # $

# ═══════════════════════════════════════════════════════════════
# تصنيف جودة الإشارات
# ═══════════════════════════════════════════════════════════════

# Grade A: إشارة ممتازة
GRADE_A_MIN_CONFIRMATIONS = 9

# Grade B: إشارة جيدة
GRADE_B_MIN_CONFIRMATIONS = 7

# Grade C: إشارة مقبولة
GRADE_C_MIN_CONFIRMATIONS = 6

# ═══════════════════════════════════════════════════════════════
# إعدادات Multi-Timeframe
# ═══════════════════════════════════════════════════════════════

TIMEFRAMES = {
    "1m": {"period": "1d", "interval": "1m"},
    "5m": {"period": "5d", "interval": "5m"},
    "15m": {"period": "1mo", "interval": "15m"},
}

# ═══════════════════════════════════════════════════════════════
# إعدادات التقرير اليومي
# ═══════════════════════════════════════════════════════════════

DAILY_REPORT_HOUR = 23  # ساعة إرسال التقرير اليومي (GMT+3)
DAILY_REPORT_MINUTE = 55
