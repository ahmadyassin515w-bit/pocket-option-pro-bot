"""
محرك الإشارات المتقدم - توليد إشارات CALL/PUT مع نظام تقييم الجودة
الإصدار المحسّن: شروط واقعية تعمل في ظروف السوق العادية
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
    شروط محسّنة تعمل في ظروف السوق العادية (ليست فقط المتطرفة).
    
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
    prev_close = float(prev['Close'])

    # ═══════════════════════════════════════
    # 1. RSI (مؤشر القوة النسبية) - شروط موسّعة
    # ═══════════════════════════════════════
    try:
        rsi = float(latest['RSI'])
        prev_rsi = float(prev['RSI'])

        # تشبع كلاسيكي
        if rsi < 35:
            call_conf += 1
            reasons_call.append("RSI تشبع بيع")
        elif rsi > 65:
            put_conf += 1
            reasons_put.append("RSI تشبع شراء")
        # اتجاه RSI
        elif rsi < 45 and prev_rsi < rsi:
            call_conf += 1
            reasons_call.append("RSI صاعد من القاع")
        elif rsi > 55 and prev_rsi > rsi:
            put_conf += 1
            reasons_put.append("RSI هابط من القمة")
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
        macd_diff = float(latest.get('MACD_Diff', macd - macd_signal))
        prev_macd_diff = float(prev.get('MACD_Diff', prev_macd - prev_macd_signal))

        # تقاطع MACD (إشارة قوية)
        if macd > macd_signal and prev_macd <= prev_macd_signal:
            call_conf += 1
            reasons_call.append("MACD تقاطع صاعد")
        elif macd < macd_signal and prev_macd >= prev_macd_signal:
            put_conf += 1
            reasons_put.append("MACD تقاطع هابط")
        # اتجاه MACD (الهيستوجرام يتزايد/يتناقص)
        elif macd > macd_signal and macd_diff > prev_macd_diff:
            call_conf += 1
            reasons_call.append("MACD+ متزايد")
        elif macd < macd_signal and macd_diff < prev_macd_diff:
            put_conf += 1
            reasons_put.append("MACD- متزايد")
        # MACD فوق/تحت الصفر
        elif macd > 0 and macd > macd_signal:
            call_conf += 1
            reasons_call.append("MACD إيجابي")
        elif macd < 0 and macd < macd_signal:
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

        # ترتيب كامل
        if ema5 > ema13 > ema21:
            call_conf += 1
            reasons_call.append("EMA ترتيب صاعد")
        elif ema5 < ema13 < ema21:
            put_conf += 1
            reasons_put.append("EMA ترتيب هابط")
        # السعر فوق/تحت EMA
        elif close > ema5 and close > ema13:
            call_conf += 1
            reasons_call.append("السعر فوق EMA")
        elif close < ema5 and close < ema13:
            put_conf += 1
            reasons_put.append("السعر تحت EMA")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 4. Bollinger Bands (البولنجر باند)
    # ═══════════════════════════════════════
    try:
        bb_lower = float(latest['BB_Lower'])
        bb_upper = float(latest['BB_Upper'])
        bb_middle = float(latest['BB_Middle'])

        # حساب موقع السعر في البولنجر (0-100%)
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            bb_position = (close - bb_lower) / bb_range * 100

            if bb_position <= 15:
                call_conf += 1
                reasons_call.append("BB قرب القاع")
            elif bb_position >= 85:
                put_conf += 1
                reasons_put.append("BB قرب القمة")
            elif close > bb_middle and prev_close <= bb_middle:
                call_conf += 1
                reasons_call.append("BB اختراق الوسط ↑")
            elif close < bb_middle and prev_close >= bb_middle:
                put_conf += 1
                reasons_put.append("BB اختراق الوسط ↓")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 5. Stochastic (الاستوكاستيك) - شروط موسّعة
    # ═══════════════════════════════════════
    try:
        stoch_k = float(latest['Stoch_K'])
        stoch_d = float(latest['Stoch_D'])
        prev_stoch_k = float(prev['Stoch_K'])
        prev_stoch_d = float(prev['Stoch_D'])

        # تشبع + تقاطع
        if stoch_k < 30 and stoch_k > stoch_d:
            call_conf += 1
            reasons_call.append("Stoch صاعد من التشبع")
        elif stoch_k > 70 and stoch_k < stoch_d:
            put_conf += 1
            reasons_put.append("Stoch هابط من التشبع")
        # تقاطع K و D
        elif stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
            call_conf += 1
            reasons_call.append("Stoch تقاطع ↑")
        elif stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
            put_conf += 1
            reasons_put.append("Stoch تقاطع ↓")
        # اتجاه عام
        elif stoch_k < 35:
            call_conf += 1
            reasons_call.append("Stoch منطقة بيع")
        elif stoch_k > 65:
            put_conf += 1
            reasons_put.append("Stoch منطقة شراء")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 6. CCI (مؤشر قناة السلع) - شروط موسّعة
    # ═══════════════════════════════════════
    try:
        cci = float(latest['CCI'])
        prev_cci = float(prev['CCI'])

        if cci < -50:
            call_conf += 1
            reasons_call.append("CCI سلبي")
        elif cci > 50:
            put_conf += 1
            reasons_put.append("CCI إيجابي")
        # CCI يتحول
        elif cci > prev_cci and cci > -20 and prev_cci < -20:
            call_conf += 1
            reasons_call.append("CCI يتحول ↑")
        elif cci < prev_cci and cci < 20 and prev_cci > 20:
            put_conf += 1
            reasons_put.append("CCI يتحول ↓")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 7. Williams %R - شروط موسّعة
    # ═══════════════════════════════════════
    try:
        williams = float(latest['Williams_R'])
        prev_williams = float(prev['Williams_R'])

        if williams < -70:
            call_conf += 1
            reasons_call.append("W%R تشبع بيع")
        elif williams > -30:
            put_conf += 1
            reasons_put.append("W%R تشبع شراء")
        # Williams يتحول
        elif williams > prev_williams and williams < -50:
            call_conf += 1
            reasons_call.append("W%R صاعد")
        elif williams < prev_williams and williams > -50:
            put_conf += 1
            reasons_put.append("W%R هابط")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 8. ADX + DI (قوة الاتجاه) - شروط موسّعة
    # ═══════════════════════════════════════
    try:
        adx = float(latest['ADX'])
        adx_pos = float(latest['ADX_Pos'])
        adx_neg = float(latest['ADX_Neg'])

        # اتجاه قوي
        if adx > 20:
            if adx_pos > adx_neg:
                call_conf += 1
                reasons_call.append("ADX صاعد")
            elif adx_neg > adx_pos:
                put_conf += 1
                reasons_put.append("ADX هابط")
        # حتى بدون ADX قوي، DI يعطي إشارة
        elif adx_pos > adx_neg * 1.3:
            call_conf += 1
            reasons_call.append("DI+ مسيطر")
        elif adx_neg > adx_pos * 1.3:
            put_conf += 1
            reasons_put.append("DI- مسيطر")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 9. Parabolic SAR
    # ═══════════════════════════════════════
    try:
        psar = float(latest['PSAR'])
        prev_psar = float(prev['PSAR'])

        if close > psar:
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

        # السعر فوق/تحت السحابة
        cloud_top = max(ich_a, ich_b)
        cloud_bottom = min(ich_a, ich_b)

        if close > cloud_top:
            call_conf += 1
            reasons_call.append("فوق سحابة Ichimoku")
        elif close < cloud_bottom:
            put_conf += 1
            reasons_put.append("تحت سحابة Ichimoku")
        # Conversion vs Base
        elif ich_conv > ich_base:
            call_conf += 1
            reasons_call.append("Ichimoku Conv>Base")
        elif ich_conv < ich_base:
            put_conf += 1
            reasons_put.append("Ichimoku Conv<Base")
    except Exception:
        pass

    # ═══════════════════════════════════════
    # 11. Price Action (حركة السعر)
    # ═══════════════════════════════════════
    try:
        closes = [float(df.iloc[-i]['Close']) for i in range(1, 5)]
        
        # 2+ شموع في نفس الاتجاه
        if closes[0] > closes[1] and closes[1] > closes[2]:
            call_conf += 1
            reasons_call.append("زخم صاعد")
        elif closes[0] < closes[1] and closes[1] < closes[2]:
            put_conf += 1
            reasons_put.append("زخم هابط")
        # ارتداد بعد هبوط
        elif closes[0] > closes[1] and closes[1] < closes[2] and closes[2] < closes[3]:
            call_conf += 1
            reasons_call.append("ارتداد صاعد")
        # ارتداد بعد صعود
        elif closes[0] < closes[1] and closes[1] > closes[2] and closes[2] > closes[3]:
            put_conf += 1
            reasons_put.append("ارتداد هابط")
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

        if body_abs > 0:
            # Pin Bar صاعد (ذيل سفلي طويل)
            if lower_shadow > body_abs * 1.5 and upper_shadow < body_abs:
                call_conf += 1
                reasons_call.append("Pin Bar صاعد")
            # Pin Bar هابط (ذيل علوي طويل)
            elif upper_shadow > body_abs * 1.5 and lower_shadow < body_abs:
                put_conf += 1
                reasons_put.append("Pin Bar هابط")
            # شمعة صاعدة قوية
            elif body > 0 and body_abs > lower_shadow and body_abs > upper_shadow:
                call_conf += 1
                reasons_call.append("شمعة صاعدة قوية")
            # شمعة هابطة قوية
            elif body < 0 and body_abs > lower_shadow and body_abs > upper_shadow:
                put_conf += 1
                reasons_put.append("شمعة هابطة قوية")
        else:
            # Doji - نستخدم الاتجاه السابق
            if prev_close > float(df.iloc[-3]['Close']):
                put_conf += 1
                reasons_put.append("Doji بعد صعود")
            elif prev_close < float(df.iloc[-3]['Close']):
                call_conf += 1
                reasons_call.append("Doji بعد هبوط")
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
    """
    try:
        latest = df.iloc[-1]
        close = float(latest['Close'])
        support = float(latest.get('Support', close))
        resistance = float(latest.get('Resistance', close))

        price_range = resistance - support if resistance > support else 1

        dist_to_support = (close - support) / price_range if price_range > 0 else 0.5
        dist_to_resistance = (resistance - close) / price_range if price_range > 0 else 0.5

        return {
            "support": support,
            "resistance": resistance,
            "near_support": dist_to_support < 0.20,
            "near_resistance": dist_to_resistance < 0.20,
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
    # فلترة لتقليل الإشارات الخاطئة
    # ═══════════════════════════════════════

    # فلتر: يجب أن يكون الفرق بين CALL و PUT واضح (2+ نقاط)
    if abs(call_conf - put_conf) < 2:
        return None

    # فلتر الشموع: لا تدخل عكس آخر 3 شموع
    try:
        last_3_closes = [float(df_clean.iloc[-i]['Close']) for i in range(1, 4)]
        candles_up = last_3_closes[0] > last_3_closes[1] > last_3_closes[2]  # 3 شموع صاعدة
        candles_down = last_3_closes[0] < last_3_closes[1] < last_3_closes[2]  # 3 شموع هابطة
        
        # لا تدخل PUT إذا آخر 3 شموع صاعدة بقوة
        if candles_up and put_conf > call_conf:
            return None
        # لا تدخل CALL إذا آخر 3 شموع هابطة بقوة
        if candles_down and call_conf > put_conf:
            return None
    except Exception:
        pass

    # تعزيز الإشارة إذا كانت قريبة من دعم/مقاومة
    sr_bonus = ""
    if sr_info["near_support"] and call_conf > put_conf:
        call_conf += 1
        sr_bonus = "قرب الدعم 🎯"
    elif sr_info["near_resistance"] and put_conf > call_conf:
        put_conf += 1
        sr_bonus = "قرب المقاومة 🎯"

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
