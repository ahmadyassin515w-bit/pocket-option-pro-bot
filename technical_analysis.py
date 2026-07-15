"""
التحليل الفني المتقدم - 12+ مؤشر فني مع تحليل مستويات الدعم والمقاومة
"""

import pandas as pd
import numpy as np
import ta
import logging

logger = logging.getLogger(__name__)


def calculate_all_indicators(df):
    """
    يحسب جميع المؤشرات الفنية (12+ مؤشر) لتحليل شامل.
    """
    if df is None or df.empty or len(df) < 20:
        return df

    try:
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        open_price = df['Open'].squeeze()
        volume = df['Volume'].squeeze() if 'Volume' in df.columns else pd.Series([0] * len(df), index=df.index)
    except Exception as e:
        logger.error(f"خطأ في تحضير البيانات: {e}")
        return df

    # ═══════════════════════════════════════
    # 1. RSI (مؤشر القوة النسبية)
    # ═══════════════════════════════════════
    try:
        rsi_indicator = ta.momentum.RSIIndicator(close=close, window=14)
        df['RSI'] = rsi_indicator.rsi()
    except Exception:
        df['RSI'] = pd.Series([50.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 2. MACD
    # ═══════════════════════════════════════
    try:
        macd_indicator = ta.trend.MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        df['MACD'] = macd_indicator.macd()
        df['MACD_Signal'] = macd_indicator.macd_signal()
        df['MACD_Diff'] = macd_indicator.macd_diff()
    except Exception:
        df['MACD'] = pd.Series([0.0] * len(df), index=df.index)
        df['MACD_Signal'] = pd.Series([0.0] * len(df), index=df.index)
        df['MACD_Diff'] = pd.Series([0.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 3. EMA (المتوسطات الأسية)
    # ═══════════════════════════════════════
    try:
        df['EMA_5'] = ta.trend.EMAIndicator(close=close, window=5).ema_indicator()
        df['EMA_13'] = ta.trend.EMAIndicator(close=close, window=13).ema_indicator()
        df['EMA_21'] = ta.trend.EMAIndicator(close=close, window=21).ema_indicator()
        df['EMA_50'] = ta.trend.EMAIndicator(close=close, window=min(50, len(df) - 1)).ema_indicator()
    except Exception:
        df['EMA_5'] = close
        df['EMA_13'] = close
        df['EMA_21'] = close
        df['EMA_50'] = close

    # ═══════════════════════════════════════
    # 4. Bollinger Bands (البولنجر باند)
    # ═══════════════════════════════════════
    try:
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Lower'] = bb.bollinger_lband()
        df['BB_Middle'] = bb.bollinger_mavg()
        df['BB_Width'] = bb.bollinger_wband()
        df['BB_Percent'] = bb.bollinger_pband()
    except Exception:
        df['BB_Upper'] = close
        df['BB_Lower'] = close
        df['BB_Middle'] = close
        df['BB_Width'] = pd.Series([0.0] * len(df), index=df.index)
        df['BB_Percent'] = pd.Series([0.5] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 5. Stochastic Oscillator (الاستوكاستيك)
    # ═══════════════════════════════════════
    try:
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        df['Stoch_K'] = stoch.stoch()
        df['Stoch_D'] = stoch.stoch_signal()
    except Exception:
        df['Stoch_K'] = pd.Series([50.0] * len(df), index=df.index)
        df['Stoch_D'] = pd.Series([50.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 6. CCI (مؤشر قناة السلع)
    # ═══════════════════════════════════════
    try:
        cci = ta.trend.CCIIndicator(high=high, low=low, close=close, window=20)
        df['CCI'] = cci.cci()
    except Exception:
        df['CCI'] = pd.Series([0.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 7. Williams %R
    # ═══════════════════════════════════════
    try:
        williams = ta.momentum.WilliamsRIndicator(high=high, low=low, close=close, lbp=14)
        df['Williams_R'] = williams.williams_r()
    except Exception:
        df['Williams_R'] = pd.Series([-50.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 8. ADX (مؤشر الاتجاه المتوسط)
    # ═══════════════════════════════════════
    try:
        adx = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        df['ADX'] = adx.adx()
        df['ADX_Pos'] = adx.adx_pos()
        df['ADX_Neg'] = adx.adx_neg()
    except Exception:
        df['ADX'] = pd.Series([0.0] * len(df), index=df.index)
        df['ADX_Pos'] = pd.Series([0.0] * len(df), index=df.index)
        df['ADX_Neg'] = pd.Series([0.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 9. ATR (متوسط المدى الحقيقي)
    # ═══════════════════════════════════════
    try:
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14)
        df['ATR'] = atr.average_true_range()
    except Exception:
        df['ATR'] = pd.Series([0.0] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 10. Ichimoku (إيشيموكو)
    # ═══════════════════════════════════════
    try:
        window1 = min(9, len(df) - 1)
        window2 = min(26, len(df) - 1)
        window3 = min(52, len(df) - 1)
        ichimoku = ta.trend.IchimokuIndicator(high=high, low=low, window1=window1, window2=window2, window3=window3)
        df['Ichimoku_A'] = ichimoku.ichimoku_a()
        df['Ichimoku_B'] = ichimoku.ichimoku_b()
        df['Ichimoku_Base'] = ichimoku.ichimoku_base_line()
        df['Ichimoku_Conv'] = ichimoku.ichimoku_conversion_line()
    except Exception:
        df['Ichimoku_A'] = close
        df['Ichimoku_B'] = close
        df['Ichimoku_Base'] = close
        df['Ichimoku_Conv'] = close

    # ═══════════════════════════════════════
    # 11. Parabolic SAR
    # ═══════════════════════════════════════
    try:
        psar = ta.trend.PSARIndicator(high=high, low=low, close=close)
        df['PSAR'] = psar.psar()
        df['PSAR_Up'] = psar.psar_up()
        df['PSAR_Down'] = psar.psar_down()
    except Exception:
        df['PSAR'] = close
        df['PSAR_Up'] = pd.Series([float('nan')] * len(df), index=df.index)
        df['PSAR_Down'] = pd.Series([float('nan')] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 12. أنماط الشموع (Candlestick Patterns)
    # ═══════════════════════════════════════
    try:
        df['Candle_Body'] = close - open_price
        df['Candle_Body_Abs'] = abs(close - open_price)
        df['Candle_Upper_Shadow'] = high - pd.concat([close, open_price], axis=1).max(axis=1)
        df['Candle_Lower_Shadow'] = pd.concat([close, open_price], axis=1).min(axis=1) - low
        df['Candle_Range'] = high - low
        # نسبة الجسم للمدى
        df['Body_Ratio'] = df['Candle_Body_Abs'] / df['Candle_Range'].replace(0, np.nan)
    except Exception:
        df['Candle_Body'] = pd.Series([0.0] * len(df), index=df.index)
        df['Candle_Body_Abs'] = pd.Series([0.0] * len(df), index=df.index)
        df['Candle_Upper_Shadow'] = pd.Series([0.0] * len(df), index=df.index)
        df['Candle_Lower_Shadow'] = pd.Series([0.0] * len(df), index=df.index)
        df['Candle_Range'] = pd.Series([0.0] * len(df), index=df.index)
        df['Body_Ratio'] = pd.Series([0.5] * len(df), index=df.index)

    # ═══════════════════════════════════════
    # 13. مستويات الدعم والمقاومة
    # ═══════════════════════════════════════
    try:
        df['Support'], df['Resistance'] = calculate_support_resistance(df)
    except Exception:
        df['Support'] = low.rolling(20).min()
        df['Resistance'] = high.rolling(20).max()

    # ═══════════════════════════════════════
    # 14. قوة الاتجاه (Trend Strength)
    # ═══════════════════════════════════════
    try:
        df['Trend_Strength'] = calculate_trend_strength(df)
    except Exception:
        df['Trend_Strength'] = pd.Series([0.0] * len(df), index=df.index)

    return df


def calculate_support_resistance(df, window=20):
    """
    حساب مستويات الدعم والمقاومة الديناميكية
    """
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    close = df['Close'].squeeze()

    # الدعم: أدنى قاع في آخر N شمعة
    support = low.rolling(window=window, min_periods=5).min()

    # المقاومة: أعلى قمة في آخر N شمعة
    resistance = high.rolling(window=window, min_periods=5).max()

    return support, resistance


def calculate_trend_strength(df):
    """
    حساب قوة الاتجاه من 0 إلى 100
    يعتمد على عدة عوامل: ADX, EMA alignment, price momentum
    """
    strength = pd.Series([50.0] * len(df), index=df.index)

    try:
        adx = df['ADX'].fillna(0)
        ema5 = df['EMA_5']
        ema13 = df['EMA_13']
        ema21 = df['EMA_21']
        close = df['Close'].squeeze()

        # مساهمة ADX (0-40 نقطة)
        adx_score = (adx / 100) * 40

        # مساهمة ترتيب EMA (0-30 نقطة)
        ema_aligned_up = ((ema5 > ema13) & (ema13 > ema21)).astype(float) * 30
        ema_aligned_down = ((ema5 < ema13) & (ema13 < ema21)).astype(float) * 30
        ema_score = ema_aligned_up + ema_aligned_down

        # مساهمة الزخم (0-30 نقطة)
        momentum = close.pct_change(5).fillna(0).abs() * 1000
        momentum_score = momentum.clip(0, 30)

        strength = (adx_score + ema_score + momentum_score).clip(0, 100)
    except Exception:
        pass

    return strength


def analyze_multi_timeframe(data_dict):
    """
    تحليل Multi-Timeframe - يحلل عدة فريمات ويعطي نتيجة مجمعة
    
    Args:
        data_dict: dict مع البيانات لكل فريم {timeframe: DataFrame}
    
    Returns:
        dict مع نتائج التحليل لكل فريم
    """
    results = {}

    for tf_name, df in data_dict.items():
        if df is None or df.empty or len(df) < 20:
            continue

        try:
            df_analyzed = calculate_all_indicators(df.copy())
            latest = df_analyzed.iloc[-1]

            # تحديد الاتجاه في هذا الفريم
            trend = "NEUTRAL"
            ema5 = float(latest.get('EMA_5', 0))
            ema13 = float(latest.get('EMA_13', 0))
            ema21 = float(latest.get('EMA_21', 0))
            close = float(latest['Close'])

            if ema5 > ema13 > ema21 and close > ema5:
                trend = "BULLISH"
            elif ema5 < ema13 < ema21 and close < ema5:
                trend = "BEARISH"

            results[tf_name] = {
                "trend": trend,
                "rsi": float(latest.get('RSI', 50)),
                "adx": float(latest.get('ADX', 0)),
                "trend_strength": float(latest.get('Trend_Strength', 50)),
                "close": close,
            }
        except Exception as e:
            logger.debug(f"خطأ في تحليل {tf_name}: {e}")
            continue

    return results


def get_market_overview(df):
    """
    يعطي نظرة عامة سريعة على حالة السوق
    """
    if df is None or df.empty or len(df) < 20:
        return None

    try:
        latest = df.iloc[-1]
        close = float(latest['Close'])

        overview = {
            "price": close,
            "rsi": float(latest.get('RSI', 50)),
            "macd_trend": "صاعد" if float(latest.get('MACD_Diff', 0)) > 0 else "هابط",
            "bb_position": float(latest.get('BB_Percent', 0.5)),
            "adx": float(latest.get('ADX', 0)),
            "trend_strength": float(latest.get('Trend_Strength', 50)),
            "volatility": float(latest.get('ATR', 0)),
            "support": float(latest.get('Support', close)),
            "resistance": float(latest.get('Resistance', close)),
        }
        return overview
    except Exception:
        return None
