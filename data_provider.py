"""
مزود البيانات - جلب بيانات الفوركس من مصادر مجانية متعددة
يستخدم نظام fallback ذكي مع تخزين مؤقت لتقليل الطلبات
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import logging
import time
import os

from config import ALPHA_VANTAGE_KEY, TWELVE_DATA_KEY, TIMEFRAMES

logger = logging.getLogger(__name__)

LOCAL_TZ = timezone(timedelta(hours=3))

# ═══════════════════════════════════════════════════════════════
# التخزين المؤقت لتقليل الطلبات
# ═══════════════════════════════════════════════════════════════
_cache = {}
CACHE_DURATION = 60  # ثانية


def _get_from_cache(key):
    """جلب من الكاش إذا لم تنتهِ صلاحيته"""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
    return None


def _set_cache(key, data):
    """حفظ في الكاش"""
    _cache[key] = (data, time.time())


# ═══════════════════════════════════════════════════════════════
# الدالة الرئيسية لجلب البيانات
# ═══════════════════════════════════════════════════════════════

def fetch_forex_data(symbol, name, timeframe="1m"):
    """
    جلب بيانات الفوركس من مصادر متعددة مع fallback ذكي.
    لا يستخدم بيانات وهمية - يعيد None إذا فشلت جميع المصادر.
    
    Returns:
        DataFrame أو None إذا فشل الجلب
    """
    cache_key = f"{symbol}_{timeframe}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    # المحاولة 1: Yahoo Finance (الأكثر موثوقية للبيانات المجانية)
    df = fetch_from_yfinance(symbol, timeframe)
    if df is not None and len(df) >= 30:
        _set_cache(cache_key, df)
        logger.info(f"✅ {name}: بيانات من Yahoo Finance ({len(df)} شمعة)")
        return df

    # المحاولة 2: Alpha Vantage
    if ALPHA_VANTAGE_KEY:
        df = fetch_from_alphavantage(symbol, timeframe)
        if df is not None and len(df) >= 30:
            _set_cache(cache_key, df)
            logger.info(f"✅ {name}: بيانات من Alpha Vantage ({len(df)} شمعة)")
            return df

    # المحاولة 3: Twelve Data
    if TWELVE_DATA_KEY:
        df = fetch_from_twelvedata(symbol, timeframe)
        if df is not None and len(df) >= 30:
            _set_cache(cache_key, df)
            logger.info(f"✅ {name}: بيانات من Twelve Data ({len(df)} شمعة)")
            return df

    # لا توجد بيانات متاحة
    logger.warning(f"⚠️ {name}: فشل جلب البيانات من جميع المصادر")
    return None


def fetch_multi_timeframe_data(symbol, name):
    """
    جلب بيانات من عدة فريمات زمنية للتحليل المتعدد.
    
    Returns:
        dict مع البيانات لكل فريم زمني
    """
    results = {}
    for tf_name, tf_config in TIMEFRAMES.items():
        df = fetch_forex_data(symbol, name, tf_name)
        if df is not None and len(df) >= 30:
            results[tf_name] = df
    return results


# ═══════════════════════════════════════════════════════════════
# Yahoo Finance
# ═══════════════════════════════════════════════════════════════

def fetch_from_yfinance(symbol, timeframe="1m"):
    """جلب من yfinance مع محاولات متعددة"""
    try:
        import yfinance as yf

        # تحديد الفترة والفاصل بناءً على الفريم
        tf_mapping = {
            "1m": [("1d", "1m"), ("2d", "2m")],
            "5m": [("5d", "5m"), ("1mo", "5m")],
            "15m": [("1mo", "15m"), ("3mo", "15m")],
        }

        attempts = tf_mapping.get(timeframe, [("1d", "1m")])

        for period, interval in attempts:
            try:
                data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    timeout=15
                )
                if data is not None and not data.empty and len(data) >= 30:
                    # تسطيح الأعمدة إذا كانت MultiIndex
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    # التأكد من وجود الأعمدة المطلوبة
                    required_cols = ['Open', 'High', 'Low', 'Close']
                    if all(col in data.columns for col in required_cols):
                        return data
            except Exception as e:
                logger.debug(f"yfinance attempt failed ({period}/{interval}): {e}")
                continue
    except ImportError:
        logger.error("yfinance غير مثبت")
    except Exception as e:
        logger.error(f"خطأ في yfinance: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Alpha Vantage
# ═══════════════════════════════════════════════════════════════

def fetch_from_alphavantage(symbol, timeframe="1m"):
    """جلب من Alpha Vantage API"""
    try:
        pair = symbol.replace("=X", "").replace("/", "")
        from_currency = pair[:3]
        to_currency = pair[3:]

        # تحديد الفاصل الزمني
        interval_map = {"1m": "1min", "5m": "5min", "15m": "15min"}
        av_interval = interval_map.get(timeframe, "1min")

        url = (
            f"https://www.alphavantage.co/query?"
            f"function=FX_INTRADAY"
            f"&from_symbol={from_currency}"
            f"&to_symbol={to_currency}"
            f"&interval={av_interval}"
            f"&apikey={ALPHA_VANTAGE_KEY}"
            f"&outputsize=compact"
        )

        response = requests.get(url, timeout=12)
        if response.status_code != 200:
            return None

        data = response.json()

        # التحقق من وجود رسالة خطأ
        if "Error Message" in data or "Note" in data:
            return None

        # البحث عن مفتاح البيانات
        ts_key = None
        for key in data.keys():
            if "Time Series" in key:
                ts_key = key
                break

        if not ts_key:
            return None

        ts = data[ts_key]
        rows = []
        for timestamp, values in ts.items():
            rows.append({
                'Date': pd.Timestamp(timestamp),
                'Open': float(values['1. open']),
                'High': float(values['2. high']),
                'Low': float(values['3. low']),
                'Close': float(values['4. close']),
                'Volume': 0
            })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)

        if len(df) >= 30:
            return df

    except requests.exceptions.Timeout:
        logger.debug("Alpha Vantage timeout")
    except Exception as e:
        logger.debug(f"Alpha Vantage error: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# Twelve Data
# ═══════════════════════════════════════════════════════════════

def fetch_from_twelvedata(symbol, timeframe="1m"):
    """جلب من Twelve Data API"""
    try:
        pair = symbol.replace("=X", "")
        td_symbol = f"{pair[:3]}/{pair[3:]}"

        interval_map = {"1m": "1min", "5m": "5min", "15m": "15min"}
        td_interval = interval_map.get(timeframe, "1min")

        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={td_symbol}"
            f"&interval={td_interval}"
            f"&outputsize=100"
            f"&apikey={TWELVE_DATA_KEY}"
        )

        response = requests.get(url, timeout=12)
        if response.status_code != 200:
            return None

        data = response.json()
        if "values" not in data:
            return None

        rows = []
        for item in data["values"]:
            rows.append({
                'Date': pd.Timestamp(item['datetime']),
                'Open': float(item['open']),
                'High': float(item['high']),
                'Low': float(item['low']),
                'Close': float(item['close']),
                'Volume': int(item.get('volume', 0))
            })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)

        if len(df) >= 30:
            return df

    except requests.exceptions.Timeout:
        logger.debug("Twelve Data timeout")
    except Exception as e:
        logger.debug(f"Twelve Data error: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# أدوات مساعدة
# ═══════════════════════════════════════════════════════════════

def get_data_source_status():
    """فحص حالة مصادر البيانات المتاحة"""
    status = {
        "yfinance": False,
        "alphavantage": False,
        "twelvedata": False,
    }

    # فحص yfinance
    try:
        import yfinance as yf
        data = yf.download("EURUSD=X", period="1d", interval="1m", progress=False, timeout=10)
        if data is not None and not data.empty:
            status["yfinance"] = True
    except:
        pass

    # فحص Alpha Vantage
    if ALPHA_VANTAGE_KEY and ALPHA_VANTAGE_KEY != "demo":
        status["alphavantage"] = True
    elif ALPHA_VANTAGE_KEY == "demo":
        status["alphavantage"] = True  # محدود لكن يعمل

    # فحص Twelve Data
    if TWELVE_DATA_KEY:
        status["twelvedata"] = True

    return status


def clear_cache():
    """مسح التخزين المؤقت"""
    global _cache
    _cache = {}
    logger.info("تم مسح الكاش")
