"""
إدارة المخاطر - حساب حجم الصفقة ونظام المارتينجيل المحسّن
"""

import logging
from config import (
    MARTINGALE_STEPS,
    MAX_RISK_PER_TRADE,
    MAX_CONSECUTIVE_LOSSES,
    MAX_DAILY_LOSS_PERCENT,
    DEFAULT_CAPITAL,
)
from database import get_user_settings, get_daily_stats, check_risk_limits

logger = logging.getLogger(__name__)


class RiskManager:
    """مدير المخاطر - يحسب حجم الصفقة ويراقب الحدود"""

    def __init__(self, user_id):
        self.user_id = user_id
        self.settings = get_user_settings(user_id)
        self.daily_stats = get_daily_stats(user_id)

    @property
    def capital(self):
        """رأس المال الحالي"""
        if self.settings:
            return self.settings.capital
        return DEFAULT_CAPITAL

    @property
    def risk_level(self):
        """مستوى المخاطرة"""
        if self.settings:
            return self.settings.risk_level
        return "medium"

    def calculate_trade_amount(self):
        """
        حساب حجم الصفقة المقترح بناءً على:
        - رأس المال
        - مستوى المخاطرة
        - نظام المارتينجيل (وحدة واحدة فقط)
        
        Returns:
            dict مع تفاصيل حجم الصفقة
        """
        # حجم الصفقة الأساسي حسب مستوى المخاطرة
        risk_percentages = {
            "low": 2,       # 2% من رأس المال
            "medium": 5,    # 5% من رأس المال
            "high": 8,      # 8% من رأس المال
        }

        risk_pct = risk_percentages.get(self.risk_level, MAX_RISK_PER_TRADE)
        base_amount = self.capital * (risk_pct / 100)

        # نظام المارتينجيل المحسّن (وحدة واحدة فقط)
        martingale_amount = base_amount
        is_martingale = False

        if self.daily_stats and self.daily_stats.consecutive_losses > 0:
            if self.daily_stats.consecutive_losses <= MARTINGALE_STEPS:
                # مضاعفة وحدة واحدة فقط (x2.2 لتغطية الخسارة + ربح)
                martingale_amount = base_amount * 2.2
                is_martingale = True
            else:
                # بعد تجاوز حد المارتينجيل، نعود للحجم الأساسي
                martingale_amount = base_amount
                is_martingale = False

        # التأكد من عدم تجاوز الحد الأقصى
        max_amount = self.capital * 0.10  # لا تتجاوز 10% أبداً
        final_amount = min(martingale_amount, max_amount)

        return {
            "base_amount": round(base_amount, 2),
            "suggested_amount": round(final_amount, 2),
            "is_martingale": is_martingale,
            "risk_pct": risk_pct,
            "consecutive_losses": self.daily_stats.consecutive_losses if self.daily_stats else 0,
            "capital": self.capital,
        }

    def should_trade(self):
        """
        هل يجب التداول الآن أم التوقف؟
        
        Returns:
            dict مع القرار والسبب
        """
        risk_check = check_risk_limits(self.user_id)

        if risk_check["should_stop"]:
            return {
                "allowed": False,
                "reason": risk_check["reason"],
                "recommendation": "⛔ يُنصح بالتوقف عن التداول اليوم"
            }

        return {
            "allowed": True,
            "reason": "",
            "recommendation": "✅ يمكنك التداول"
        }

    def get_risk_summary(self):
        """
        ملخص حالة المخاطرة
        
        Returns:
            dict مع ملخص شامل
        """
        trade_info = self.calculate_trade_amount()
        trade_check = self.should_trade()

        # حساب نسبة الخسارة اليومية
        daily_loss_pct = 0
        if self.daily_stats and self.capital > 0:
            daily_loss_pct = abs(min(self.daily_stats.profit_loss, 0)) / self.capital * 100

        # حالة المخاطرة
        if daily_loss_pct >= MAX_DAILY_LOSS_PERCENT * 0.8:
            risk_status = "🔴 خطر عالي"
        elif daily_loss_pct >= MAX_DAILY_LOSS_PERCENT * 0.5:
            risk_status = "🟡 تحذير"
        else:
            risk_status = "🟢 آمن"

        return {
            "risk_status": risk_status,
            "capital": self.capital,
            "risk_level": self.risk_level,
            "daily_loss_pct": round(daily_loss_pct, 1),
            "max_daily_loss_pct": MAX_DAILY_LOSS_PERCENT,
            "consecutive_losses": self.daily_stats.consecutive_losses if self.daily_stats else 0,
            "max_consecutive_losses": MAX_CONSECUTIVE_LOSSES,
            "suggested_amount": trade_info["suggested_amount"],
            "is_martingale": trade_info["is_martingale"],
            "can_trade": trade_check["allowed"],
            "stop_reason": trade_check["reason"],
            "today_trades": self.daily_stats.total_signals if self.daily_stats else 0,
            "today_wins": self.daily_stats.wins if self.daily_stats else 0,
            "today_losses": self.daily_stats.losses if self.daily_stats else 0,
            "today_profit": self.daily_stats.profit_loss if self.daily_stats else 0,
        }


def format_risk_message(user_id):
    """
    تنسيق رسالة إدارة المخاطر للمستخدم
    """
    rm = RiskManager(user_id)
    summary = rm.get_risk_summary()

    msg = (
        "⟪❁ إدارة المخاطر ❁⟫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 الحالة: {summary['risk_status']}\n\n"
        f"💰 رأس المال: ${summary['capital']}\n"
        f"📈 مستوى المخاطرة: {summary['risk_level']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 إحصائيات اليوم:\n"
        f"   الصفقات: {summary['today_trades']}\n"
        f"   رابحة: {summary['today_wins']} ✅\n"
        f"   خاسرة: {summary['today_losses']} ❌\n"
        f"   الربح/الخسارة: ${summary['today_profit']:.2f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ حدود المخاطرة:\n"
        f"   الخسارة اليومية: {summary['daily_loss_pct']}% / {summary['max_daily_loss_pct']}%\n"
        f"   خسائر متتالية: {summary['consecutive_losses']} / {summary['max_consecutive_losses']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 الصفقة القادمة:\n"
        f"   المبلغ المقترح: ${summary['suggested_amount']}\n"
    )

    if summary['is_martingale']:
        msg += f"   📌 مارتينجيل (مضاعفة وحدة)\n"

    if not summary['can_trade']:
        msg += f"\n⛔ تم إيقاف التداول:\n   {summary['stop_reason']}\n"

    return msg
