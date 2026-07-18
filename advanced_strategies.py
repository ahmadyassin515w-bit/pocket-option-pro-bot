"""
استراتيجيات التداول المتقدمة - مبنية على منهجيات مثبتة
تجمع بين عدة مؤشرات بطريقة ذكية لتحسين دقة الإشارات
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StrategyEngine:
    """محرك الاستراتيجيات المتقدمة"""

    def __init__(self):
        self.strategies = [
            self.strategy_ema_crossover_confirmed,
            self.strategy_rsi_divergence_reversal,
            self.strategy_bollinger_squeeze_breakout,
            self.strategy_multi_momentum,
            self.strategy_trend_continuation,
            self.strategy_support_resistance_bounce,
        ]

    def evaluate_all_strategies(self, df) -> dict:
        """
        تقييم جميع الاستراتيجيات وإرجاع أفضل نتيجة

        Returns:
            dict مع الاتجاه والثقة والاستراتيجية المستخدمة
        """
        results = []

        for strategy in self.strategies:
            try:
                result = strategy(df)
                if result and result.get("signal"):
                    results.append(result)
            except Exception as e:
                logger.debug(f"خطأ في استراتيجية: {e}")
                continue

        if not results:
            return {"signal": None}

        # ترتيب حسب الثقة
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # حساب الإجماع
        call_count = sum(1 for r in results if r["signal"] == "CALL")
        put_count = sum(1 for r in results if r["signal"] == "PUT")

        best = results[0]

        # تعزيز الثقة إذا كان هناك إجماع
        consensus = max(call_count, put_count) / len(results) if results else 0
        if consensus >= 0.7:
            best["confidence"] = min(100, best["confidence"] + 15)
            best["consensus"] = True
        else:
            best["consensus"] = False

        best["strategies_agree"] = max(call_count, put_count)
        best["strategies_total"] = len(results)

        return best

    def strategy_ema_crossover_confirmed(self, df) -> dict:
        """
        استراتيجية تقاطع EMA المؤكد:
        - تقاطع EMA5 مع EMA13
        - مؤكد بـ MACD في نفس الاتجاه
        - RSI ليس في منطقة تشبع معاكسة
        """
        if len(df) < 5:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ema5 = float(latest.get('EMA_5', 0))
        ema13 = float(latest.get('EMA_13', 0))
        prev_ema5 = float(prev.get('EMA_5', 0))
        prev_ema13 = float(prev.get('EMA_13', 0))
        macd_diff = float(latest.get('MACD_Diff', 0))
        rsi = float(latest.get('RSI', 50))

        # تقاطع صاعد
        if ema5 > ema13 and prev_ema5 <= prev_ema13:
            if macd_diff > 0 and rsi < 70:
                return {
                    "signal": "CALL",
                    "strategy": "EMA Crossover ↑",
                    "confidence": 75,
                    "reason": "تقاطع EMA صاعد + MACD إيجابي"
                }

        # تقاطع هابط
        if ema5 < ema13 and prev_ema5 >= prev_ema13:
            if macd_diff < 0 and rsi > 30:
                return {
                    "signal": "PUT",
                    "strategy": "EMA Crossover ↓",
                    "confidence": 75,
                    "reason": "تقاطع EMA هابط + MACD سلبي"
                }

        return None

    def strategy_rsi_divergence_reversal(self, df) -> dict:
        """
        استراتيجية انعكاس التباعد RSI:
        - RSI في منطقة تشبع
        - تباعد مع السعر
        - تأكيد من Stochastic
        """
        if len(df) < 10:
            return None

        latest = df.iloc[-1]
        rsi = float(latest.get('RSI', 50))
        stoch_k = float(latest.get('Stoch_K', 50))
        close = float(latest['Close'])

        # RSI تشبع بيع + Stochastic تشبع بيع = فرصة شراء
        if rsi < 30 and stoch_k < 25:
            # تأكد أن السعر بدأ يرتد
            if close > float(df.iloc[-2]['Close']):
                return {
                    "signal": "CALL",
                    "strategy": "RSI Reversal ↑",
                    "confidence": 80,
                    "reason": "تشبع بيع مزدوج + بداية ارتداد"
                }

        # RSI تشبع شراء + Stochastic تشبع شراء = فرصة بيع
        if rsi > 70 and stoch_k > 75:
            if close < float(df.iloc[-2]['Close']):
                return {
                    "signal": "PUT",
                    "strategy": "RSI Reversal ↓",
                    "confidence": 80,
                    "reason": "تشبع شراء مزدوج + بداية هبوط"
                }

        return None

    def strategy_bollinger_squeeze_breakout(self, df) -> dict:
        """
        استراتيجية اختراق ضغط البولنجر:
        - BB Width ضيق (squeeze)
        - اختراق واضح لأحد الحدود
        - حجم/زخم مؤكد
        """
        if len(df) < 20:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        bb_width = float(latest.get('BB_Width', 0))
        bb_upper = float(latest.get('BB_Upper', 0))
        bb_lower = float(latest.get('BB_Lower', 0))
        close = float(latest['Close'])
        prev_close = float(prev['Close'])

        # حساب متوسط العرض
        avg_width = df['BB_Width'].rolling(20).mean().iloc[-1] if 'BB_Width' in df.columns else bb_width

        # Squeeze: العرض أقل من المتوسط
        is_squeeze = bb_width < float(avg_width) * 0.8 if avg_width > 0 else False

        if is_squeeze or bb_width < 0.01:
            # اختراق صعودي
            if close > bb_upper and prev_close <= bb_upper:
                macd_diff = float(latest.get('MACD_Diff', 0))
                if macd_diff > 0:
                    return {
                        "signal": "CALL",
                        "strategy": "BB Breakout ↑",
                        "confidence": 70,
                        "reason": "اختراق بولنجر العلوي بعد ضغط"
                    }

            # اختراق هبوطي
            if close < bb_lower and prev_close >= bb_lower:
                macd_diff = float(latest.get('MACD_Diff', 0))
                if macd_diff < 0:
                    return {
                        "signal": "PUT",
                        "strategy": "BB Breakout ↓",
                        "confidence": 70,
                        "reason": "اختراق بولنجر السفلي بعد ضغط"
                    }

        return None

    def strategy_multi_momentum(self, df) -> dict:
        """
        استراتيجية الزخم المتعدد:
        - 3+ مؤشرات زخم في نفس الاتجاه
        - ADX يؤكد وجود اتجاه
        """
        if len(df) < 5:
            return None

        latest = df.iloc[-1]

        rsi = float(latest.get('RSI', 50))
        stoch_k = float(latest.get('Stoch_K', 50))
        cci = float(latest.get('CCI', 0))
        williams = float(latest.get('Williams_R', -50))
        macd_diff = float(latest.get('MACD_Diff', 0))
        adx = float(latest.get('ADX', 0))

        bullish_momentum = 0
        bearish_momentum = 0

        # RSI - فوق 50 = صاعد، تحت 50 = هابط
        if rsi > 55:
            bullish_momentum += 1
        elif rsi < 45:
            bearish_momentum += 1

        # Stochastic - فوق 50 = صاعد، تحت 50 = هابط
        if stoch_k > 55:
            bullish_momentum += 1
        elif stoch_k < 45:
            bearish_momentum += 1

        # CCI - إيجابي = صاعد، سلبي = هابط
        if cci > 50:
            bullish_momentum += 1
        elif cci < -50:
            bearish_momentum += 1

        # Williams %R - فوق -50 = صاعد، تحت -50 = هابط
        if williams > -35:
            bullish_momentum += 1
        elif williams < -65:
            bearish_momentum += 1

        # MACD
        if macd_diff > 0:
            bullish_momentum += 1
        elif macd_diff < 0:
            bearish_momentum += 1

        # يجب أن يكون ADX > 15 (اتجاه موجود)
        if adx < 15:
            return None

        if bullish_momentum >= 4:
            return {
                "signal": "CALL",
                "strategy": "Multi-Momentum ↑",
                "confidence": min(95, 70 + bullish_momentum * 5),
                "reason": f"زخم صاعد قوي ({bullish_momentum}/5 مؤشرات)"
            }
        elif bearish_momentum >= 4:
            return {
                "signal": "PUT",
                "strategy": "Multi-Momentum ↓",
                "confidence": min(95, 70 + bearish_momentum * 5),
                "reason": f"زخم هابط قوي ({bearish_momentum}/5 مؤشرات)"
            }

        return None

    def strategy_trend_continuation(self, df) -> dict:
        """
        استراتيجية استمرار الاتجاه:
        - اتجاه واضح (EMA مرتبة)
        - ارتداد مؤقت (pullback) إلى EMA
        - استئناف الاتجاه
        """
        if len(df) < 10:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        close = float(latest['Close'])
        ema5 = float(latest.get('EMA_5', close))
        ema13 = float(latest.get('EMA_13', close))
        ema21 = float(latest.get('EMA_21', close))

        prev_close = float(prev['Close'])
        prev2_close = float(prev2['Close'])

        # اتجاه صاعد + pullback + استئناف
        if ema5 > ema13 > ema21:
            # السعر لمس EMA13 أو EMA5 ثم ارتد
            if prev_close <= ema5 and close > ema5 and close > prev_close:
                rsi = float(latest.get('RSI', 50))
                if 40 < rsi < 65:  # RSI في منطقة صحية
                    return {
                        "signal": "CALL",
                        "strategy": "Trend Continuation ↑",
                        "confidence": 78,
                        "reason": "ارتداد من EMA في اتجاه صاعد"
                    }

        # اتجاه هابط + pullback + استئناف
        if ema5 < ema13 < ema21:
            if prev_close >= ema5 and close < ema5 and close < prev_close:
                rsi = float(latest.get('RSI', 50))
                if 35 < rsi < 60:
                    return {
                        "signal": "PUT",
                        "strategy": "Trend Continuation ↓",
                        "confidence": 78,
                        "reason": "ارتداد من EMA في اتجاه هابط"
                    }

        return None

    def strategy_support_resistance_bounce(self, df) -> dict:
        """
        استراتيجية الارتداد من الدعم/المقاومة:
        - السعر يصل لمستوى دعم/مقاومة
        - شمعة انعكاسية (Pin Bar أو Engulfing)
        - مؤشر واحد على الأقل يؤكد
        """
        if len(df) < 20:
            return None

        latest = df.iloc[-1]
        close = float(latest['Close'])
        support = float(latest.get('Support', 0))
        resistance = float(latest.get('Resistance', 0))

        if support == 0 or resistance == 0:
            return None

        price_range = resistance - support
        if price_range <= 0:
            return None

        dist_to_support = (close - support) / price_range
        dist_to_resistance = (resistance - close) / price_range

        rsi = float(latest.get('RSI', 50))
        body = float(latest.get('Candle_Body', 0))

        # قرب الدعم + شمعة صاعدة + RSI منخفض
        if dist_to_support < 0.15 and body > 0 and rsi < 45:
            return {
                "signal": "CALL",
                "strategy": "S/R Bounce ↑",
                "confidence": 72,
                "reason": "ارتداد من الدعم + شمعة صاعدة"
            }

        # قرب المقاومة + شمعة هابطة + RSI مرتفع
        if dist_to_resistance < 0.15 and body < 0 and rsi > 55:
            return {
                "signal": "PUT",
                "strategy": "S/R Bounce ↓",
                "confidence": 72,
                "reason": "ارتداد من المقاومة + شمعة هابطة"
            }

        return None


# إنشاء instance عام
strategy_engine = StrategyEngine()
