"""
محرك التعلم الآلي والتكيف - يتعلم من نتائج الصفقات السابقة
ويحسّن استراتيجيات التداول تلقائياً
"""

import numpy as np
import pandas as pd
import logging
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# ملف حفظ النموذج
MODEL_FILE = "ml_model_data.json"


class AdaptiveMLEngine:
    """
    محرك تعلم آلي تكيّفي يعتمد على:
    1. تحليل أنماط النجاح/الفشل السابقة
    2. تعديل أوزان المؤشرات بناءً على الأداء
    3. تحديد أفضل ظروف السوق للتداول
    4. تصنيف الأصول حسب الأداء التاريخي
    """

    def __init__(self):
        self.indicator_weights = self._default_weights()
        self.asset_scores = defaultdict(lambda: {"wins": 0, "losses": 0, "score": 50})
        self.time_performance = defaultdict(lambda: {"wins": 0, "losses": 0})
        self.pattern_memory = []
        self.volatility_thresholds = {}
        self.load_model()

    def _default_weights(self):
        """أوزان افتراضية متساوية لجميع المؤشرات"""
        return {
            "RSI": 1.0,
            "MACD": 1.0,
            "EMA": 1.0,
            "BB": 1.0,
            "Stoch": 1.0,
            "CCI": 1.0,
            "Williams": 1.0,
            "ADX": 1.0,
            "SAR": 1.0,
            "Ichimoku": 1.0,
            "PriceAction": 1.0,
            "CandlePattern": 1.0,
        }

    def load_model(self):
        """تحميل بيانات النموذج المحفوظة"""
        try:
            if os.path.exists(MODEL_FILE):
                with open(MODEL_FILE, 'r') as f:
                    data = json.load(f)
                    self.indicator_weights = data.get("weights", self._default_weights())
                    self.asset_scores = defaultdict(
                        lambda: {"wins": 0, "losses": 0, "score": 50},
                        data.get("asset_scores", {})
                    )
                    self.time_performance = defaultdict(
                        lambda: {"wins": 0, "losses": 0},
                        data.get("time_performance", {})
                    )
                    self.volatility_thresholds = data.get("volatility_thresholds", {})
                    logger.info("✅ تم تحميل نموذج ML بنجاح")
        except Exception as e:
            logger.error(f"خطأ في تحميل النموذج: {e}")

    def save_model(self):
        """حفظ بيانات النموذج"""
        try:
            data = {
                "weights": self.indicator_weights,
                "asset_scores": dict(self.asset_scores),
                "time_performance": dict(self.time_performance),
                "volatility_thresholds": self.volatility_thresholds,
                "last_updated": datetime.now().isoformat(),
            }
            with open(MODEL_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ النموذج: {e}")

    def record_trade_result(self, asset: str, direction: str, reasons: list,
                            result: str, hour: int, indicators_state: dict = None):
        """
        تسجيل نتيجة صفقة لتحديث النموذج

        Args:
            asset: اسم الأصل
            direction: CALL أو PUT
            reasons: قائمة أسباب الإشارة (أسماء المؤشرات)
            result: "win" أو "loss"
            hour: ساعة الصفقة
            indicators_state: حالة المؤشرات وقت الصفقة
        """
        is_win = result == "win"

        # 1. تحديث أوزان المؤشرات
        self._update_indicator_weights(reasons, is_win)

        # 2. تحديث أداء الأصل
        self._update_asset_score(asset, is_win)

        # 3. تحديث أداء الوقت
        self._update_time_performance(hour, is_win)

        # 4. حفظ النمط
        if indicators_state:
            self.pattern_memory.append({
                "asset": asset,
                "direction": direction,
                "indicators": indicators_state,
                "result": result,
                "hour": hour,
                "timestamp": datetime.now().isoformat(),
            })
            # نحتفظ بآخر 500 نمط فقط
            if len(self.pattern_memory) > 500:
                self.pattern_memory = self.pattern_memory[-500:]

        # حفظ التحديثات
        self.save_model()

    def _update_indicator_weights(self, reasons: list, is_win: bool):
        """تحديث أوزان المؤشرات بناءً على النتيجة"""
        # معدل التعلم
        learning_rate = 0.05

        for reason in reasons:
            # تحديد المؤشر من السبب
            indicator = self._extract_indicator_name(reason)
            if indicator and indicator in self.indicator_weights:
                if is_win:
                    # زيادة وزن المؤشر الناجح
                    self.indicator_weights[indicator] = min(
                        2.0, self.indicator_weights[indicator] + learning_rate
                    )
                else:
                    # تقليل وزن المؤشر الفاشل
                    self.indicator_weights[indicator] = max(
                        0.3, self.indicator_weights[indicator] - learning_rate
                    )

    def _extract_indicator_name(self, reason: str) -> str:
        """استخراج اسم المؤشر من سبب الإشارة"""
        mapping = {
            "RSI": "RSI",
            "MACD": "MACD",
            "EMA": "EMA",
            "BB": "BB",
            "Bollinger": "BB",
            "Stoch": "Stoch",
            "CCI": "CCI",
            "Williams": "Williams",
            "W%R": "Williams",
            "ADX": "ADX",
            "DI": "ADX",
            "SAR": "SAR",
            "Ichimoku": "Ichimoku",
            "سحابة": "Ichimoku",
            "زخم": "PriceAction",
            "ارتداد": "PriceAction",
            "Pin Bar": "CandlePattern",
            "شمعة": "CandlePattern",
            "Doji": "CandlePattern",
        }
        for key, value in mapping.items():
            if key in reason:
                return value
        return None

    def _update_asset_score(self, asset: str, is_win: bool):
        """تحديث درجة الأصل"""
        if asset not in self.asset_scores:
            self.asset_scores[asset] = {"wins": 0, "losses": 0, "score": 50}

        if is_win:
            self.asset_scores[asset]["wins"] += 1
        else:
            self.asset_scores[asset]["losses"] += 1

        # حساب الدرجة (0-100)
        total = self.asset_scores[asset]["wins"] + self.asset_scores[asset]["losses"]
        if total > 0:
            win_rate = self.asset_scores[asset]["wins"] / total
            self.asset_scores[asset]["score"] = round(win_rate * 100, 1)

    def _update_time_performance(self, hour: int, is_win: bool):
        """تحديث أداء الوقت"""
        hour_key = str(hour)
        if hour_key not in self.time_performance:
            self.time_performance[hour_key] = {"wins": 0, "losses": 0}

        if is_win:
            self.time_performance[hour_key]["wins"] += 1
        else:
            self.time_performance[hour_key]["losses"] += 1

    def get_weighted_score(self, confirmations_by_indicator: dict) -> float:
        """
        حساب درجة مرجّحة بناءً على أوزان المؤشرات المتعلمة

        Args:
            confirmations_by_indicator: dict {indicator_name: 1 or 0}

        Returns:
            float: الدرجة المرجّحة (0-100)
        """
        total_weight = 0
        weighted_score = 0

        for indicator, confirmed in confirmations_by_indicator.items():
            weight = self.indicator_weights.get(indicator, 1.0)
            total_weight += weight
            if confirmed:
                weighted_score += weight

        if total_weight == 0:
            return 0

        return (weighted_score / total_weight) * 100

    def get_asset_recommendation(self, asset: str) -> dict:
        """
        توصية بشأن الأصل بناءً على الأداء التاريخي

        Returns:
            dict مع التوصية والدرجة
        """
        if asset in self.asset_scores:
            score = self.asset_scores[asset]["score"]
            total = self.asset_scores[asset]["wins"] + self.asset_scores[asset]["losses"]

            if total < 5:
                return {"recommendation": "neutral", "score": 50, "confidence": "low"}
            elif score >= 65:
                return {"recommendation": "strong", "score": score, "confidence": "high"}
            elif score >= 50:
                return {"recommendation": "moderate", "score": score, "confidence": "medium"}
            else:
                return {"recommendation": "weak", "score": score, "confidence": "high"}

        return {"recommendation": "neutral", "score": 50, "confidence": "low"}

    def get_best_trading_hours(self) -> list:
        """أفضل ساعات التداول بناءً على البيانات التاريخية"""
        hour_scores = []

        for hour_str, data in self.time_performance.items():
            total = data["wins"] + data["losses"]
            if total >= 3:
                win_rate = data["wins"] / total * 100
                hour_scores.append({
                    "hour": int(hour_str),
                    "win_rate": round(win_rate, 1),
                    "total_trades": total,
                })

        hour_scores.sort(key=lambda x: x["win_rate"], reverse=True)
        return hour_scores[:5]

    def should_enhance_signal(self, asset: str, hour: int) -> dict:
        """
        هل يجب تعزيز أو تخفيض الإشارة بناءً على ML؟

        Returns:
            dict مع المعامل والسبب
        """
        multiplier = 1.0
        reasons = []

        # فحص أداء الأصل
        asset_rec = self.get_asset_recommendation(asset)
        if asset_rec["recommendation"] == "strong" and asset_rec["confidence"] == "high":
            multiplier += 0.2
            reasons.append(f"أداء تاريخي ممتاز ({asset_rec['score']}%)")
        elif asset_rec["recommendation"] == "weak" and asset_rec["confidence"] == "high":
            multiplier -= 0.3
            reasons.append(f"أداء تاريخي ضعيف ({asset_rec['score']}%)")

        # فحص أداء الوقت
        hour_key = str(hour)
        if hour_key in self.time_performance:
            data = self.time_performance[hour_key]
            total = data["wins"] + data["losses"]
            if total >= 5:
                win_rate = data["wins"] / total
                if win_rate >= 0.7:
                    multiplier += 0.15
                    reasons.append(f"ساعة ذهبية ({win_rate*100:.0f}% نجاح)")
                elif win_rate <= 0.35:
                    multiplier -= 0.2
                    reasons.append(f"ساعة ضعيفة ({win_rate*100:.0f}% نجاح)")

        return {
            "multiplier": round(multiplier, 2),
            "reasons": reasons,
            "enhanced": multiplier > 1.0,
            "weakened": multiplier < 1.0,
        }

    def get_ml_summary(self) -> str:
        """ملخص حالة نموذج التعلم الآلي"""
        # أفضل المؤشرات
        sorted_weights = sorted(
            self.indicator_weights.items(),
            key=lambda x: x[1], reverse=True
        )
        top_indicators = sorted_weights[:3]
        weak_indicators = sorted_weights[-3:]

        # أفضل الأصول
        sorted_assets = sorted(
            [(k, v) for k, v in self.asset_scores.items() if v["wins"] + v["losses"] >= 3],
            key=lambda x: x[1]["score"], reverse=True
        )
        top_assets = sorted_assets[:3]

        # أفضل الأوقات
        best_hours = self.get_best_trading_hours()

        total_patterns = len(self.pattern_memory)

        msg = (
            "⟪🧠 محرك التعلم الآلي ⟫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 أنماط محفوظة: {total_patterns}\n\n"
        )

        if top_indicators:
            msg += "💪 أقوى المؤشرات:\n"
            for name, weight in top_indicators:
                bar = "█" * int(weight * 5) + "░" * (10 - int(weight * 5))
                msg += f"   {name}: [{bar}] {weight:.2f}\n"
            msg += "\n"

        if weak_indicators:
            msg += "⚠️ أضعف المؤشرات:\n"
            for name, weight in weak_indicators:
                bar = "█" * int(weight * 5) + "░" * (10 - int(weight * 5))
                msg += f"   {name}: [{bar}] {weight:.2f}\n"
            msg += "\n"

        if top_assets:
            msg += "🏆 أفضل الأصول:\n"
            for asset, data in top_assets:
                msg += f"   {asset}: {data['score']}% ({data['wins']}W/{data['losses']}L)\n"
            msg += "\n"

        if best_hours:
            msg += "⏰ أفضل أوقات التداول:\n"
            for h in best_hours[:3]:
                msg += f"   الساعة {h['hour']}:00 - نسبة نجاح {h['win_rate']}%\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 النموذج يتحسن مع كل صفقة مسجّلة"

        return msg


class VolatilityAnalyzer:
    """محلل التقلبات - يحدد أفضل ظروف السوق للتداول"""

    @staticmethod
    def analyze_volatility(df) -> dict:
        """
        تحليل تقلبات السوق الحالية

        Returns:
            dict مع مستوى التقلب وتوصية التداول
        """
        try:
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0
            bb_width = df['BB_Width'].iloc[-1] if 'BB_Width' in df.columns else 0
            close = float(df['Close'].iloc[-1])

            # نسبة ATR للسعر
            atr_pct = (atr / close * 100) if close > 0 else 0

            # تحديد مستوى التقلب
            if atr_pct > 0.5 or bb_width > 0.03:
                volatility_level = "high"
                trade_recommendation = "حذر - تقلبات عالية"
                confidence_modifier = -0.15
            elif atr_pct < 0.1 or bb_width < 0.005:
                volatility_level = "low"
                trade_recommendation = "انتظار - سوق هادئ جداً"
                confidence_modifier = -0.1
            else:
                volatility_level = "optimal"
                trade_recommendation = "مناسب للتداول"
                confidence_modifier = 0.1

            return {
                "level": volatility_level,
                "atr_pct": round(atr_pct, 4),
                "bb_width": round(float(bb_width), 5),
                "recommendation": trade_recommendation,
                "confidence_modifier": confidence_modifier,
            }
        except Exception as e:
            logger.error(f"خطأ في تحليل التقلبات: {e}")
            return {
                "level": "unknown",
                "atr_pct": 0,
                "bb_width": 0,
                "recommendation": "غير متاح",
                "confidence_modifier": 0,
            }


class TrendConfirmation:
    """تأكيد الاتجاه متعدد المستويات"""

    @staticmethod
    def confirm_trend(df) -> dict:
        """
        تأكيد الاتجاه باستخدام عدة طبقات

        Returns:
            dict مع اتجاه مؤكد ودرجة الثقة
        """
        try:
            latest = df.iloc[-1]
            close = float(latest['Close'])

            bullish_points = 0
            bearish_points = 0
            total_checks = 0

            # 1. EMA Alignment
            ema5 = float(latest.get('EMA_5', close))
            ema13 = float(latest.get('EMA_13', close))
            ema21 = float(latest.get('EMA_21', close))
            ema50 = float(latest.get('EMA_50', close))

            total_checks += 2
            if ema5 > ema13 > ema21:
                bullish_points += 2
            elif ema5 < ema13 < ema21:
                bearish_points += 2

            # 2. Price vs EMAs
            total_checks += 1
            if close > ema5 and close > ema13 and close > ema21:
                bullish_points += 1
            elif close < ema5 and close < ema13 and close < ema21:
                bearish_points += 1

            # 3. MACD Direction
            macd_diff = float(latest.get('MACD_Diff', 0))
            total_checks += 1
            if macd_diff > 0:
                bullish_points += 1
            elif macd_diff < 0:
                bearish_points += 1

            # 4. ADX Direction
            adx_pos = float(latest.get('ADX_Pos', 0))
            adx_neg = float(latest.get('ADX_Neg', 0))
            total_checks += 1
            if adx_pos > adx_neg:
                bullish_points += 1
            elif adx_neg > adx_pos:
                bearish_points += 1

            # 5. Ichimoku Cloud
            ich_a = float(latest.get('Ichimoku_A', close))
            ich_b = float(latest.get('Ichimoku_B', close))
            cloud_top = max(ich_a, ich_b)
            cloud_bottom = min(ich_a, ich_b)
            total_checks += 1
            if close > cloud_top:
                bullish_points += 1
            elif close < cloud_bottom:
                bearish_points += 1

            # 6. SAR
            psar = float(latest.get('PSAR', close))
            total_checks += 1
            if close > psar:
                bullish_points += 1
            elif close < psar:
                bearish_points += 1

            # تحديد الاتجاه المؤكد
            if bullish_points >= total_checks * 0.7:
                trend = "BULLISH"
                confidence = bullish_points / total_checks
            elif bearish_points >= total_checks * 0.7:
                trend = "BEARISH"
                confidence = bearish_points / total_checks
            else:
                trend = "NEUTRAL"
                confidence = max(bullish_points, bearish_points) / total_checks

            return {
                "trend": trend,
                "confidence": round(confidence * 100, 1),
                "bullish_score": bullish_points,
                "bearish_score": bearish_points,
                "total_checks": total_checks,
            }
        except Exception as e:
            logger.error(f"خطأ في تأكيد الاتجاه: {e}")
            return {
                "trend": "NEUTRAL",
                "confidence": 0,
                "bullish_score": 0,
                "bearish_score": 0,
                "total_checks": 0,
            }


class DivergenceDetector:
    """كاشف التباعد (Divergence) - إشارات انعكاس قوية"""

    @staticmethod
    def detect_divergence(df, lookback=10) -> dict:
        """
        كشف التباعد بين السعر والمؤشرات

        Returns:
            dict مع نوع التباعد والمؤشرات المتباعدة
        """
        try:
            if len(df) < lookback + 5:
                return {"found": False}

            close = df['Close'].squeeze()
            rsi = df['RSI'] if 'RSI' in df.columns else None
            macd = df['MACD_Diff'] if 'MACD_Diff' in df.columns else None

            divergences = []

            # RSI Divergence
            if rsi is not None:
                price_higher = close.iloc[-1] > close.iloc[-lookback]
                rsi_lower = float(rsi.iloc[-1]) < float(rsi.iloc[-lookback])

                price_lower = close.iloc[-1] < close.iloc[-lookback]
                rsi_higher = float(rsi.iloc[-1]) > float(rsi.iloc[-lookback])

                if price_higher and rsi_lower:
                    divergences.append({
                        "type": "bearish",
                        "indicator": "RSI",
                        "description": "تباعد سلبي RSI (انعكاس هبوطي محتمل)"
                    })
                elif price_lower and rsi_higher:
                    divergences.append({
                        "type": "bullish",
                        "indicator": "RSI",
                        "description": "تباعد إيجابي RSI (انعكاس صعودي محتمل)"
                    })

            # MACD Divergence
            if macd is not None:
                price_higher = close.iloc[-1] > close.iloc[-lookback]
                macd_lower = float(macd.iloc[-1]) < float(macd.iloc[-lookback])

                price_lower = close.iloc[-1] < close.iloc[-lookback]
                macd_higher = float(macd.iloc[-1]) > float(macd.iloc[-lookback])

                if price_higher and macd_lower:
                    divergences.append({
                        "type": "bearish",
                        "indicator": "MACD",
                        "description": "تباعد سلبي MACD"
                    })
                elif price_lower and macd_higher:
                    divergences.append({
                        "type": "bullish",
                        "indicator": "MACD",
                        "description": "تباعد إيجابي MACD"
                    })

            if divergences:
                return {
                    "found": True,
                    "divergences": divergences,
                    "count": len(divergences),
                }

            return {"found": False}

        except Exception as e:
            logger.error(f"خطأ في كشف التباعد: {e}")
            return {"found": False}


# إنشاء instance عام
ml_engine = AdaptiveMLEngine()
volatility_analyzer = VolatilityAnalyzer()
trend_confirmation = TrendConfirmation()
divergence_detector = DivergenceDetector()
