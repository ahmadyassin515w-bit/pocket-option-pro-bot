"""
محرك الإشارات المتقدم - توليد إشارات CALL/PUT مع نظام تقييم الجودة
"""

import pandas as pd
import numpy as np
import logging
from config import (
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    STOCH_OVERBOUGHT, STOCH_OVERSOLD,
    CCI_OVERBOUGHT, CCI_OVERSOLD,
    ADX_STRONG_TREND,
    WILLIAMS_OVERBOUGHT, WILLIAMS_OVERSOLD,
    MIN_CONFIRMATIONS,
    GRADE_A_MIN_CONFIRMATIONS,
    GRADE_B_MIN_CONFIRMATIONS,
    GRADE_C_MIN_CONFIRMATIONS,
)

logger = logging.getLogger(__name__)

TOTAL_INDICATORS = 12


def analyze_signal(df):
    """
    يحلل آخر عدة شموع باستخدام 12 مؤشر ويعيد تأكيدات CALL و PUT.
    
    Returns:
        tuple: (call_conf, put_conf, reasons_call, reasons_put)
    """
    if len(df) < 5:
        return 0, 0, [], []

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]

    call_conf = 0
    put_conf = 0
    reasons_call = []
    reasons_put = []

    close = float(latest['Close'])

    # ═══════════════════════════════════════
    # 1. RSI (مؤشر القوة النسبية)
    # ═══════════════════════════════════════
    try:
        rsi = float(latest['RSI'])
        prev_rsi = float(prev['RSI'])

        if rsi < RSI_OVERSOLD:
            call_conf += 1
            reasons_call.append("RSI تشبع بيع")
        elif rsi > RSI_OVERBOUGHT:
            put_conf += 1
            reasons_put.append("RSI تشبع شراء")

        # RSI Divergence (تباعد)
        if rsi > prev_rsi and close < float(prev['Close']):
            call_conf += 1
            reasons_call.append("تباعد RSI صاعد")
        elif rsi < prev_rsi and close > float(prev['Close']):
            put_conf += 1
            reasons_put.append("تباعد RSI هابط")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 2. MACD
    # ═══════════════════════════════════════
    try:
        macd = float(latest['MACD'])
        macd_signal = float(latest['MACD_Signal'])
        prev_macd = float(prev['MACD'])
        prev_macd_signal = float(prev['MACD_Signal'])

        # تقاطع MACD (إشارة قوية)
        if macd > macd_signal and prev_macd <= prev_macd_signal:
            call_conf += 1
            reasons_call.append("MACD تقاطع صاعد")
        elif macd < macd_signal and prev_macd >= prev_macd_signal:
            put_conf += 1
            reasons_put.append("MACD تقاطع هابط")
        # اتجاه MACD
        elif macd > macd_signal:
            call_conf += 1
            reasons_call.append("MACD إيجابي")
        elif macd < macd_signal:
            put_conf += 1
            reasons_put.append("MACD سلبي")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 3. EMA Crossover (تقاطع المتوسطات)
    # ═══════════════════════════════════════
    try:
        ema5 = float(latest['EMA_5'])
        ema13 = float(latest['EMA_13'])
        ema21 = float(latest['EMA_21'])

        if ema5 > ema13 > ema21:
            call_conf += 1
            reasons_call.append("EMA ترتيب صاعد")
        elif ema5 < ema13 < ema21:
            put_conf += 1
            reasons_put.append("EMA ترتيب هابط")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 4. Bollinger Bands (البولنجر باند)
    # ═══════════════════════════════════════
    try:
        bb_lower = float(latest['BB_Lower'])
        bb_upper = float(latest['BB_Upper'])
        bb_middle = float(latest['BB_Middle'])

        if close <= bb_lower:
            call_conf += 1
            reasons_call.append("BB ارتداد من القاع")
        elif close >= bb_upper:
            put_conf += 1
            reasons_put.append("BB ارتداد من القمة")
        elif close > bb_middle and float(prev['Close']) <= bb_middle:
            call_conf += 1
            reasons_call.append("BB اختراق الوسط ↑")
        elif close < bb_middle and float(prev['Close']) >= bb_middle:
            put_conf += 1
            reasons_put.append("BB اختراق الوسط ↓")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 5. Stochastic (الاستوكاستيك)
    # ═══════════════════════════════════════
    try:
        stoch_k = float(latest['Stoch_K'])
        stoch_d = float(latest['Stoch_D'])
        prev_stoch_k = float(prev['Stoch_K'])
        prev_stoch_d = float(prev['Stoch_D'])

        # تشبع + تقاطع (إشارة قوية)
        if stoch_k < STOCH_OVERSOLD and stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
            call_conf += 1
            reasons_call.append("Stoch تقاطع صاعد")
        elif stoch_k > STOCH_OVERBOUGHT and stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
            put_conf += 1
            reasons_put.append("Stoch تقاطع هابط")
        # تشبع فقط
        elif stoch_k < STOCH_OVERSOLD:
            call_conf += 1
            reasons_call.append("Stoch تشبع بيع")
        elif stoch_k > STOCH_OVERBOUGHT:
            put_conf += 1
            reasons_put.append("Stoch تشبع شراء")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 6. CCI (مؤشر قناة السلع)
    # ═══════════════════════════════════════
    try:
        cci = float(latest['CCI'])
        if cci < CCI_OVERSOLD:
            call_conf += 1
            reasons_call.append("CCI تشبع بيع")
        elif cci > CCI_OVERBOUGHT:
            put_conf += 1
            reasons_put.append("CCI تشبع شراء")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 7. Williams %R
    # ═══════════════════════════════════════
    try:
        williams = float(latest['Williams_R'])
        if williams < WILLIAMS_OVERSOLD:
            call_conf += 1
            reasons_call.append("W%R تشبع بيع")
        elif williams > WILLIAMS_OVERBOUGHT:
            put_conf += 1
            reasons_put.append("W%R تشبع شراء")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 8. ADX + DI (قوة الاتجاه)
    # ═══════════════════════════════════════
    try:
        adx = float(latest['ADX'])
        adx_pos = float(latest['ADX_Pos'])
        adx_neg = float(latest['ADX_Neg'])

        if adx > ADX_STRONG_TREND:
            if adx_pos > adx_neg:
                call_conf += 1
                reasons_call.append("ADX اتجاه صاعد قوي")
            elif adx_neg > adx_pos:
                put_conf += 1
                reasons_put.append("ADX اتجاه هابط قوي")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 9. Parabolic SAR
    # ═══════════════════════════════════════
    try:
        psar = float(latest['PSAR'])
        prev_psar = float(prev['PSAR'])

        if close > psar and float(prev['Close']) <= prev_psar:
            # انعكاس SAR - إشارة قوية
            call_conf += 1
            reasons_call.append("SAR انعكاس صاعد")
        elif close < psar and float(prev['Close']) >= prev_psar:
            put_conf += 1
            reasons_put.append("SAR انعكاس هابط")
        elif close > psar:
            call_conf += 1
            reasons_call.append("SAR صاعد")
        elif close < psar:
            put_conf += 1
            reasons_put.append("SAR هابط")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 10. Ichimoku (إيشيموكو)
    # ═══════════════════════════════════════
    try:
        ich_a = float(latest['Ichimoku_A'])
        ich_b = float(latest['Ichimoku_B'])
        ich_conv = float(latest['Ichimoku_Conv'])
        ich_base = float(latest['Ichimoku_Base'])

        if close > ich_a and close > ich_b and ich_conv > ich_base:
            call_conf += 1
            reasons_call.append("Ichimoku صاعد")
        elif close < ich_a and close < ich_b and ich_conv < ich_base:
            put_conf += 1
            reasons_put.append("Ichimoku هابط")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 11. Price Action (حركة السعر)
    # ═══════════════════════════════════════
    try:
        closes = [float(df.iloc[-i]['Close']) for i in range(1, 5)]
        # 3 شموع هابطة متتالية = احتمال ارتداد صعودي
        if closes[0] < closes[1] < closes[2] < closes[3]:
            call_conf += 1
            reasons_call.append("3 شموع هابطة (ارتداد)")
        # 3 شموع صاعدة متتالية = احتمال ارتداد هبوطي
        elif closes[0] > closes[1] > closes[2] > closes[3]:
            put_conf += 1
            reasons_put.append("3 شموع صاعدة (ارتداد)")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 12. Candle Pattern (نمط الشمعة)
    # ═══════════════════════════════════════
    try:
        body = float(latest['Candle_Body'])
        lower_shadow = float(latest['Candle_Lower_Shadow'])
        upper_shadow = float(latest['Candle_Upper_Shadow'])
        body_abs = abs(body)

        # Pin Bar صاعد (ذيل سفلي طويل)
        if lower_shadow > body_abs * 2 and upper_shadow < body_abs * 0.5:
            call_conf += 1
            reasons_call.append("Pin Bar صاعد")
        # Pin Bar هابط (ذيل علوي طويل)
        elif upper_shadow > body_abs * 2 and lower_shadow < body_abs * 0.5:
            put_conf += 1
            reasons_put.append("Pin Bar هابط")
        # Engulfing (ابتلاع)
        elif body > 0 and float(prev['Candle_Body']) < 0 and body_abs > abs(float(prev['Candle_Body'])):
            call_conf += 1
            reasons_call.append("ابتلاع صاعد")
        elif body < 0 and float(prev['Candle_Body']) > 0 and body_abs > abs(float(prev['Candle_Body'])):
            put_conf += 1
            reasons_put.append("ابتلاع هابط")
    except Exception:
        pass

    return call_conf, put_conf, reasons_call, reasons_put


def get_signal_grade(confirmations):
    """
    تحديد درجة جودة الإشارة
    
    Returns:
        tuple: (grade, emoji, description)
    """
    if confirmations >= GRADE_A_MIN_CONFIRMATIONS:
        return "A", "🅰️", "ممتازة"
    elif confirmations >= GRADE_B_MIN_CONFIRMATIONS:
        return "B", "🅱️", "جيدة"
    elif confirmations >= GRADE_C_MIN_CONFIRMATIONS:
        return "C", "©️", "مقبولة"
    else:
        return "D", "❌", "ضعيفة"


def check_support_resistance_filter(df):
    """
    فلتر إضافي: هل السعر قريب من دعم/مقاومة؟
    يعطي نقاط إضافية للإشارات القريبة من مستويات مهمة.
    
    Returns:
        dict مع معلومات الدعم والمقاومة
    """
    try:
        latest = df.iloc[-1]
        close = float(latest['Close'])
        support = float(latest.get('Support', close))
        resistance = float(latest.get('Resistance', close))

        price_range = resistance - support if resistance > support else 1

        # المسافة من الدعم والمقاومة كنسبة
        dist_to_support = (close - support) / price_range if price_range > 0 else 0.5
        dist_to_resistance = (resistance - close) / price_range if price_range > 0 else 0.5

        return {
            "support": support,
            "resistance": resistance,
            "near_support": dist_to_support < 0.15,  # قريب من الدعم (15%)
            "near_resistance": dist_to_resistance < 0.15,  # قريب من المقاومة (15%)
            "dist_to_support_pct": dist_to_support * 100,
            "dist_to_resistance_pct": dist_to_resistance * 100,
        }
    except Exception:
        return {
            "support": 0, "resistance": 0,
            "near_support": False, "near_resistance": False,
            "dist_to_support_pct": 50, "dist_to_resistance_pct": 50,
        }


def generate_signal_for_asset(df, min_conf_override=None):
    """
    يولد إشارة CALL أو PUT بناءً على تأكيدات متعددة مع فلترة متقدمة.
    
    Args:
        df: DataFrame مع المؤشرات المحسوبة
        min_conf_override: تجاوز الحد الأدنى للتأكيدات (اختياري)
    
    Returns:
        dict مع تفاصيل الإشارة أو None
    """
    if df is None or df.empty or len(df) < 30:
        return None

    # إزالة NaN من الأعمدة الأساسية
    required_cols = ['RSI', 'MACD', 'EMA_5']
    existing_cols = [col for col in required_cols if col in df.columns]
    if existing_cols:
        df_clean = df.dropna(subset=existing_cols)
    else:
        df_clean = df.dropna()

    if len(df_clean) < 5:
        return None

    # تحليل الإشارات
    call_conf, put_conf, reasons_call, reasons_put = analyze_signal(df_clean)

    # الحد الأدنى المطلوب
    min_conf = min_conf_override if min_conf_override else MIN_CONFIRMATIONS

    # فلتر الدعم والمقاومة
    sr_info = check_support_resistance_filter(df_clean)

    # ═══════════════════════════════════════
    # فلترة متقدمة لتقليل الإشارات الخاطئة
    # ═══════════════════════════════════════

    # فلتر 1: يجب أن يكون الفرق بين CALL و PUT واضح (3+ نقاط)
    if abs(call_conf - put_conf) < 2:
        return None

    # فلتر 2: فحص ADX - إذا لا يوجد اتجاه واضح، لا نعطي إشارة
    try:
        adx_val = float(df_clean.iloc[-1].get('ADX', 0))
        # إذا ADX ضعيف جداً والإشارة ليست قوية جداً
        if adx_val < 15 and max(call_conf, put_conf) < GRADE_A_MIN_CONFIRMATIONS:
            return None
    except Exception:
        pass

    # فلتر 3: تعزيز الإشارة إذا كانت قريبة من دعم/مقاومة
    sr_bonus = ""
    if sr_info["near_support"] and call_conf > put_conf:
        call_conf += 1  # نقطة إضافية
        sr_bonus = "قرب الدعم"
    elif sr_info["near_resistance"] and put_conf > call_conf:
        put_conf += 1  # نقطة إضافية
        sr_bonus = "قرب المقاومة"

    # توليد الإشارة النهائية
    if call_conf >= min_conf and call_conf > put_conf:
        grade, grade_emoji, grade_desc = get_signal_grade(call_conf)
        strength = min(int((call_conf / TOTAL_INDICATORS) * 100), 100)

        signal = {
            "direction": "CALL",
            "confirmations": call_conf,
            "total_indicators": TOTAL_INDICATORS,
            "strength": strength,
            "reasons": reasons_call,
            "close": float(df_clean.iloc[-1]['Close']),
            "grade": grade,
            "grade_emoji": grade_emoji,
            "grade_desc": grade_desc,
            "support": sr_info["support"],
            "resistance": sr_info["resistance"],
            "sr_bonus": sr_bonus,
        }
        return signal

    elif put_conf >= min_conf and put_conf > call_conf:
        grade, grade_emoji, grade_desc = get_signal_grade(put_conf)
        strength = min(int((put_conf / TOTAL_INDICATORS) * 100), 100)

        signal = {
            "direction": "PUT",
            "confirmations": put_conf,
            "total_indicators": TOTAL_INDICATORS,
            "strength": strength,
            "reasons": reasons_put,
            "close": float(df_clean.iloc[-1]['Close']),
            "grade": grade,
            "grade_emoji": grade_emoji,
            "grade_desc": grade_desc,
            "support": sr_info["support"],
            "resistance": sr_info["resistance"],
            "sr_bonus": sr_bonus,
        }
        return signal

    return None
