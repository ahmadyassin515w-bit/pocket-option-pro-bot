"""
بوت إشارات Pocket Option - الإصدار المتقدم V2
بوت تليجرام احترافي لتحليل الأسواق وتوليد إشارات التداول
مع تعلم آلي واستراتيجيات متقدمة
"""

import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler
)
import asyncio
import os

from config import (
    TELEGRAM_BOT_TOKEN, ASSETS_TO_MONITOR,
    MAX_DAILY_TRADES, TRADE_DURATION, MIN_PAYOUT_PERCENTAGE,
    MIN_CONFIRMATIONS, AUTO_SIGNAL_INTERVAL, MAX_SIGNALS_PER_REQUEST,
    DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE,
    GRADE_A_MIN_CONFIRMATIONS,
)
from technical_analysis import calculate_all_indicators, get_market_overview, analyze_multi_timeframe
from signals import generate_signal_for_asset, get_signal_grade
from data_provider import fetch_forex_data, fetch_multi_timeframe_data, get_data_source_status
from database import (
    initialize_db, Trade, UserSettings, DailyStats, AssetPerformance,
    get_user_settings, update_user_setting, update_daily_stats,
    get_daily_stats, check_risk_limits, update_asset_performance,
    get_best_performing_assets, get_worst_performing_assets, db
)
from risk_manager import RiskManager, format_risk_message
from ml_engine import (
    ml_engine, volatility_analyzer, trend_confirmation, divergence_detector
)
from advanced_strategies import strategy_engine
from chart_generator import generate_chart, generate_quick_chart

# ═══════════════════════════════════════════════════════════════
# إعداد التسجيل
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
initialize_db()

# التوقيت المحلي GMT+3
LOCAL_TZ = timezone(timedelta(hours=3))


def get_local_time():
    return datetime.now(LOCAL_TZ)


# ═══════════════════════════════════════════════════════════════
# أمر /start
# ═══════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user_settings(user_id)

    welcome_msg = (
        "╔══════════════════════════════╗\n"
        "║  ⟪❁ PocketOption Pro V2 ❁⟫  ║\n"
        "╚══════════════════════════════╝\n\n"
        "مرحباً بك في بوت إشارات التداول المتقدم 🎯\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 المواصفات:\n"
        "• 12+ مؤشر فني + 6 استراتيجيات ذكية\n"
        "• 🧠 تعلم آلي تكيّفي (يتحسن مع كل صفقة)\n"
        "• تحليل التقلبات والتباعد (Divergence)\n"
        "• تأكيد اتجاه متعدد المستويات\n"
        "• إدارة مخاطر ديناميكية\n"
        "• نظام تقييم A/B/C مع تعزيز ML\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 الأوامر:\n\n"
        "📊 الإشارات:\n"
        "/signals - إشارات ذكية (ML + استراتيجيات)\n"
        "/forex - إشارات الفوركس\n"
        "/crypto - إشارات الكريبتو\n"
        "/stocks - إشارات الأسهم\n"
        "/best - أفضل الفرص حالياً\n"
        "/market - حالة السوق\n\n"
        "🧠 التعلم الآلي:\n"
        "/ml - حالة محرك التعلم الآلي\n"
        "/strategy - تحليل الاستراتيجيات\n\n"
        "🔔 تلقائي:\n"
        "/auto_on - إشارات تلقائية\n"
        "/auto_off - إيقاف\n\n"
        "📈 السجل:\n"
        "/history - سجل الصفقات\n"
        "/stats - الإحصائيات\n"
        "/performance - أداء الأزواج\n"
        "/report - تقرير شامل\n\n"
        "💰 المخاطر:\n"
        "/risk - إدارة المخاطر\n"
        "/win - تسجيل ربح ✅\n"
        "/loss - تسجيل خسارة ❌\n\n"
        "⚙️ الإعدادات:\n"
        "/settings - تعديل الإعدادات\n"
        "/help - المساعدة\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ تداول بمسؤولية - لا يوجد ضمان للأرباح"
    )
    await update.message.reply_text(welcome_msg)


# ═══════════════════════════════════════════════════════════════
# أمر /help
# ═══════════════════════════════════════════════════════════════

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = (
        "⟪❁ المساعدة - V2 ❁⟫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 أوامر الإشارات:\n"
        "/signals - إشارات ذكية (ML + 6 استراتيجيات)\n"
        "/forex - فوركس فقط\n"
        "/crypto - كريبتو فقط\n"
        "/stocks - أسهم فقط\n"
        "/best - أفضل الفرص\n"
        "/market - نظرة عامة\n\n"
        "🧠 التعلم الآلي:\n"
        "/ml - حالة النموذج وأوزان المؤشرات\n"
        "/strategy - تحليل استراتيجي متقدم\n\n"
        "🔔 تلقائي:\n"
        "/auto_on - تفعيل\n"
        "/auto_off - إيقاف\n\n"
        "📈 السجل والتقارير:\n"
        "/history - آخر 10 صفقات\n"
        "/stats - إحصائيات شاملة\n"
        "/performance - أداء كل زوج\n"
        "/report - تقرير يومي مفصّل\n"
        "/win - تسجيل ربح\n"
        "/loss - تسجيل خسارة\n\n"
        "💰 إدارة المخاطر:\n"
        "/risk - حالة المخاطرة\n\n"
        "⚙️ الإعدادات:\n"
        "/settings - عرض وتعديل\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🧠 كيف يعمل التعلم الآلي؟\n"
        "• يسجّل نتائج كل صفقة (/win أو /loss)\n"
        "• يحلل أي المؤشرات تنجح أكثر\n"
        "• يعدّل أوزان المؤشرات تلقائياً\n"
        "• يحدد أفضل الأصول وأوقات التداول\n"
        "• كلما سجّلت نتائج أكثر، زادت الدقة\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 نظام التقييم المحسّن:\n"
        "🅰️ Grade A: ممتازة (9+/12) + تأكيد ML\n"
        "🅱️ Grade B: جيدة (7-8/12)\n"
        "©️ Grade C: مقبولة (6/12)\n\n"
        "⚠️ تداول بمسؤولية!"
    )
    await update.message.reply_text(help_msg)


# ═══════════════════════════════════════════════════════════════
# أمر /signals - توليد الإشارات المتقدمة
# ═══════════════════════════════════════════════════════════════

async def get_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    risk_check = check_risk_limits(user_id)
    if risk_check["should_stop"]:
        await update.message.reply_text(
            f"⛔ تم إيقاف التداول اليوم\n\n"
            f"السبب: {risk_check['reason']}\n\n"
            f"💡 يُنصح بالراحة والعودة غداً"
        )
        return

    await update.message.reply_text("⏳ جاري التحليل المتقدم (ML + 6 استراتيجيات)...")

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals = await analyze_all_assets_v2(user_id, min_conf)

    if signals:
        for sig_msg in signals:
            await update.message.reply_text(sig_msg)
            await asyncio.sleep(0.5)

        rm = RiskManager(user_id)
        trade_info = rm.calculate_trade_amount()

        summary_msg = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ تم توليد {len(signals)} إشارة ذكية\n\n"
            f"💰 المبلغ المقترح: ${trade_info['suggested_amount']}\n"
        )
        if trade_info['is_martingale']:
            summary_msg += f"📌 مارتينجيل (مضاعفة وحدة)\n"

        summary_msg += (
            f"\n🧠 معزّزة بالتعلم الآلي\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"سجّل النتيجة: /win أو /loss"
        )
        await update.message.reply_text(summary_msg)
    else:
        await update.message.reply_text(
            "⏸ لا توجد إشارات قوية حالياً\n\n"
            "💡 الأسباب المحتملة:\n"
            "• السوق في حالة تذبذب\n"
            "• لا يوجد اتجاه واضح\n"
            "• التقلبات غير مناسبة\n\n"
            "جرّب بعد دقائق أو فعّل /auto_on"
        )


# ═══════════════════════════════════════════════════════════════
# تحليل متقدم V2 مع ML والاستراتيجيات
# ═══════════════════════════════════════════════════════════════

async def analyze_all_assets_v2(user_id=0, min_conf=None):
    """تحليل متقدم يدمج ML + استراتيجيات + مؤشرات"""
    signals_list = []
    now = get_local_time()
    current_hour = now.hour

    if min_conf is None:
        min_conf = MIN_CONFIRMATIONS

    for asset_info in ASSETS_TO_MONITOR:
        if len(signals_list) >= MAX_SIGNALS_PER_REQUEST:
            break

        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            data = fetch_forex_data(symbol, name)

            if data is None or data.empty or len(data) < 30:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            df_ta = calculate_all_indicators(data.copy())

            if df_ta is None or df_ta.empty:
                continue

            # ═══ التحليل الأساسي ═══
            signal = generate_signal_for_asset(df_ta, min_conf_override=min_conf)

            # ═══ تحليل الاستراتيجيات المتقدمة ═══
            strategy_result = strategy_engine.evaluate_all_strategies(df_ta)

            # ═══ تحليل التقلبات ═══
            vol_analysis = volatility_analyzer.analyze_volatility(df_ta)

            # ═══ تأكيد الاتجاه ═══
            trend_info = trend_confirmation.confirm_trend(df_ta)

            # ═══ كشف التباعد ═══
            div_info = divergence_detector.detect_divergence(df_ta)

            # ═══ تعزيز ML ═══
            ml_enhancement = ml_engine.should_enhance_signal(name, current_hour)

            # ═══ القرار النهائي ═══
            final_signal = None
            extra_info = []

            if signal:
                # إشارة أساسية موجودة - نعززها
                final_signal = signal

                # ═══ فلتر الاتجاه: لا تدخل عكس الاتجاه المؤكد 80%+ ═══
                trend_against = (
                    (trend_info["trend"] == "BULLISH" and trend_info["confidence"] >= 80 and signal["direction"] == "PUT") or
                    (trend_info["trend"] == "BEARISH" and trend_info["confidence"] >= 80 and signal["direction"] == "CALL")
                )
                if trend_against:
                    final_signal = None
                    continue

                # تعزيز بالاستراتيجيات
                if strategy_result.get("signal") == signal["direction"]:
                    signal["confirmations"] = min(12, signal["confirmations"] + 1)
                    extra_info.append(f"🎯 {strategy_result.get('strategy', 'Strategy')}")

                # تعزيز بتأكيد الاتجاه
                if trend_info["trend"] == "BULLISH" and signal["direction"] == "CALL":
                    extra_info.append(f"📈 اتجاه مؤكد ({trend_info['confidence']}%)")
                elif trend_info["trend"] == "BEARISH" and signal["direction"] == "PUT":
                    extra_info.append(f"📉 اتجاه مؤكد ({trend_info['confidence']}%)")
                else:
                    # الاتجاه لا يدعم - تخفيض التأكيدات
                    if trend_info["trend"] != "NEUTRAL" and trend_info["confidence"] >= 60:
                        signal["confirmations"] = max(min_conf, signal["confirmations"] - 1)

                # تعزيز بالتباعد
                if div_info.get("found"):
                    for div in div_info["divergences"]:
                        if (div["type"] == "bullish" and signal["direction"] == "CALL") or \
                           (div["type"] == "bearish" and signal["direction"] == "PUT"):
                            extra_info.append(f"🔀 {div['description']}")
                            signal["confirmations"] = min(12, signal["confirmations"] + 1)

                # تعزيز ML
                if ml_enhancement["enhanced"]:
                    extra_info.extend([f"🧠 {r}" for r in ml_enhancement["reasons"]])

            elif strategy_result.get("signal") and strategy_result.get("confidence", 0) >= 75:
                # لا إشارة أساسية لكن استراتيجية قوية
                direction = strategy_result["signal"]
                confidence = strategy_result["confidence"]

                # تأكد أن الاتجاه يدعم
                trend_supports = (
                    (trend_info["trend"] == "BULLISH" and direction == "CALL") or
                    (trend_info["trend"] == "BEARISH" and direction == "PUT") or
                    trend_info["trend"] == "NEUTRAL"
                )

                if trend_supports and vol_analysis["level"] != "low":
                    conf_count = int(confidence / 100 * 12)
                    conf_count = max(min_conf, min(12, conf_count))

                    final_signal = {
                        "direction": direction,
                        "confirmations": conf_count,
                        "total_indicators": 12,
                        "strength": confidence,
                        "reasons": [strategy_result.get("reason", "استراتيجية متقدمة")],
                        "close": float(df_ta.iloc[-1]['Close']),
                        "grade": "B" if conf_count >= 7 else "C",
                        "grade_emoji": "🅱️" if conf_count >= 7 else "©️",
                        "grade_desc": "جيدة" if conf_count >= 7 else "مقبولة",
                        "sr_bonus": "",
                    }
                    extra_info.append(f"🎯 {strategy_result.get('strategy', 'Strategy')}")
                    if strategy_result.get("consensus"):
                        extra_info.append("✅ إجماع الاستراتيجيات")

            # ═══ فلتر التقلبات ═══
            if final_signal and vol_analysis["level"] == "low":
                # سوق هادئ جداً - تخفيض
                if final_signal["confirmations"] < 8:
                    continue  # تجاهل الإشارات الضعيفة في سوق هادئ

            # ═══ تنسيق الإشارة النهائية ═══
            if final_signal:
                # إعادة حساب الدرجة بعد التعزيز
                conf = final_signal["confirmations"]
                if conf >= 9:
                    final_signal["grade"] = "A"
                    final_signal["grade_emoji"] = "🅰️"
                    final_signal["grade_desc"] = "ممتازة"
                elif conf >= 7:
                    final_signal["grade"] = "B"
                    final_signal["grade_emoji"] = "🅱️"
                    final_signal["grade_desc"] = "جيدة"

                signal_time = now + timedelta(minutes=len(signals_list) * 2 + 1)
                time_str = signal_time.strftime("%H:%M")

                direction_emoji = "🟢 CALL ↑" if final_signal["direction"] == "CALL" else "🔴 PUT ↓"
                total = final_signal["total_indicators"]
                strength_bar = "█" * conf + "░" * (total - conf)
                reasons_str = " | ".join(final_signal["reasons"][:4])

                sig_msg = (
                    f"╔═══════════════════════╗\n"
                    f"║   SIGNAL 1M {final_signal['grade_emoji']}        ║\n"
                    f"╚═══════════════════════╝\n\n"
                    f"📊 الزوج: {name}\n"
                    f"🕓 الوقت: {time_str}\n"
                    f"⏳ المدة: M1\n"
                    f"🎯 الاتجاه: {direction_emoji}\n\n"
                    f"💪 القوة: [{strength_bar}] {conf}/{total}\n"
                    f"📈 التقييم: {final_signal['grade_emoji']} {final_signal['grade_desc']}\n"
                    f"📋 الأسباب: {reasons_str}\n"
                )

                # إضافة معلومات التعزيز
                if extra_info:
                    sig_msg += f"\n🔬 تعزيزات:\n"
                    for info in extra_info[:3]:
                        sig_msg += f"   {info}\n"

                # حالة التقلبات
                if vol_analysis["level"] == "optimal":
                    sig_msg += f"\n✅ تقلبات مثالية للتداول"
                elif vol_analysis["level"] == "high":
                    sig_msg += f"\n⚠️ تقلبات عالية - حذر"

                if final_signal.get("sr_bonus"):
                    sig_msg += f"\n🎯 {final_signal['sr_bonus']}"

                signals_list.append(sig_msg)

                # حفظ في قاعدة البيانات
                try:
                    Trade.create(
                        user_id=user_id,
                        asset=name,
                        signal_type=final_signal["direction"],
                        entry_price=final_signal["close"],
                        confirmations=conf,
                        grade=final_signal["grade"],
                        reasons=", ".join(final_signal["reasons"]),
                    )
                except Exception as e:
                    logger.error(f"خطأ في حفظ الصفقة: {e}")

        except Exception as e:
            logger.error(f"خطأ في تحليل {name}: {e}")
            continue

    return signals_list


# ═══════════════════════════════════════════════════════════════
# أوامر الفئات المنفصلة: /forex /crypto /stocks
# ═══════════════════════════════════════════════════════════════

async def analyze_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, category_name: str):
    """تحليل أصول فئة محددة"""
    user_id = update.effective_user.id

    risk_check = check_risk_limits(user_id)
    if risk_check["should_stop"]:
        await update.message.reply_text(
            f"⛔ تم إيقاف التداول اليوم\n\nالسبب: {risk_check['reason']}\n\n💡 يُنصح بالراحة والعودة غداً"
        )
        return

    await update.message.reply_text(f"⏳ جاري تحليل {category_name} (ML + استراتيجيات)...")

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals_list = []
    now = get_local_time()
    current_hour = now.hour

    category_assets = [a for a in ASSETS_TO_MONITOR if a["category"] == category]

    for asset_info in category_assets:
        if len(signals_list) >= MAX_SIGNALS_PER_REQUEST:
            break

        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            data = fetch_forex_data(symbol, name)
            if data is None or data.empty or len(data) < 30:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            df_ta = calculate_all_indicators(data.copy())
            if df_ta is None or df_ta.empty:
                continue

            # التحليل الأساسي
            signal = generate_signal_for_asset(df_ta, min_conf_override=min_conf)

            # الاستراتيجيات
            strategy_result = strategy_engine.evaluate_all_strategies(df_ta)

            # تعزيز ML
            ml_enhancement = ml_engine.should_enhance_signal(name, current_hour)

            # التقلبات
            vol_analysis = volatility_analyzer.analyze_volatility(df_ta)

            final_signal = None
            extra_info = []

            if signal:
                final_signal = signal
                if strategy_result.get("signal") == signal["direction"]:
                    signal["confirmations"] = min(12, signal["confirmations"] + 1)
                    extra_info.append(f"🎯 {strategy_result.get('strategy', '')}")
                if ml_enhancement["enhanced"]:
                    extra_info.extend([f"🧠 {r}" for r in ml_enhancement["reasons"]])

            elif strategy_result.get("signal") and strategy_result.get("confidence", 0) >= 75:
                direction = strategy_result["signal"]
                conf_count = max(min_conf, min(12, int(strategy_result["confidence"] / 100 * 12)))
                final_signal = {
                    "direction": direction,
                    "confirmations": conf_count,
                    "total_indicators": 12,
                    "reasons": [strategy_result.get("reason", "استراتيجية")],
                    "close": float(df_ta.iloc[-1]['Close']),
                    "grade": "B" if conf_count >= 7 else "C",
                    "grade_emoji": "🅱️" if conf_count >= 7 else "©️",
                    "grade_desc": "جيدة" if conf_count >= 7 else "مقبولة",
                    "sr_bonus": "",
                }
                extra_info.append(f"🎯 {strategy_result.get('strategy', '')}")

            if final_signal:
                conf = final_signal["confirmations"]
                if conf >= 9:
                    final_signal["grade"], final_signal["grade_emoji"], final_signal["grade_desc"] = "A", "🅰️", "ممتازة"
                elif conf >= 7:
                    final_signal["grade"], final_signal["grade_emoji"], final_signal["grade_desc"] = "B", "🅱️", "جيدة"

                signal_time = now + timedelta(minutes=len(signals_list) * 2 + 1)
                time_str = signal_time.strftime("%H:%M")
                direction_emoji = "🟢 CALL ↑" if final_signal["direction"] == "CALL" else "🔴 PUT ↓"
                total = final_signal["total_indicators"]
                strength_bar = "█" * conf + "░" * (total - conf)
                reasons_str = " | ".join(final_signal["reasons"][:4])

                sig_msg = (
                    f"╔═══════════════════════╗\n"
                    f"║   SIGNAL 1M {final_signal['grade_emoji']}        ║\n"
                    f"╚═══════════════════════╝\n\n"
                    f"📊 الأصل: {name}\n"
                    f"🕓 الوقت: {time_str}\n"
                    f"⏳ المدة: M1\n"
                    f"🎯 الاتجاه: {direction_emoji}\n\n"
                    f"💪 القوة: [{strength_bar}] {conf}/{total}\n"
                    f"📈 التقييم: {final_signal['grade_emoji']} {final_signal['grade_desc']}\n"
                    f"📋 الأسباب: {reasons_str}\n"
                )
                if extra_info:
                    sig_msg += f"\n🔬 تعزيزات:\n"
                    for info in extra_info[:3]:
                        sig_msg += f"   {info}\n"

                if vol_analysis["level"] == "optimal":
                    sig_msg += f"\n✅ تقلبات مثالية"

                if final_signal.get("sr_bonus"):
                    sig_msg += f"\n🎯 {final_signal['sr_bonus']}"

                signals_list.append(sig_msg)

                try:
                    Trade.create(
                        user_id=user_id, asset=name,
                        signal_type=final_signal["direction"],
                        entry_price=final_signal["close"],
                        confirmations=conf, grade=final_signal["grade"],
                        reasons=", ".join(final_signal["reasons"]),
                    )
                except Exception as e:
                    logger.error(f"خطأ في حفظ الصفقة: {e}")
        except Exception as e:
            logger.error(f"خطأ في تحليل {name}: {e}")
            continue

    if signals_list:
        for sig_msg in signals_list:
            await update.message.reply_text(sig_msg)
            await asyncio.sleep(0.5)
        await update.message.reply_text(
            f"✅ تم توليد {len(signals_list)} إشارة من {category_name}\n"
            f"🧠 معزّزة بالتعلم الآلي والاستراتيجيات"
        )
    else:
        await update.message.reply_text(
            f"⏸ لا توجد إشارات قوية في {category_name} حالياً\n\n"
            "💡 جرّب بعد دقائق أو فعّل /auto_on"
        )


async def forex_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await analyze_by_category(update, context, "Forex", "أزواج الفوركس 💱")


async def crypto_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await analyze_by_category(update, context, "Crypto", "العملات المشفرة ₿")


async def stocks_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await analyze_by_category(update, context, "Stocks", "الأسهم الأمريكية 📈")


# ═══════════════════════════════════════════════════════════════
# أمر /ml - حالة التعلم الآلي
# ═══════════════════════════════════════════════════════════════

async def ml_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة محرك التعلم الآلي"""
    msg = ml_engine.get_ml_summary()
    await update.message.reply_text(msg)


# ═══════════════════════════════════════════════════════════════
# أمر /strategy - تحليل استراتيجي
# ═══════════════════════════════════════════════════════════════

async def strategy_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحليل استراتيجي متقدم لأفضل 5 أصول"""
    await update.message.reply_text("⏳ جاري التحليل الاستراتيجي المتقدم...")

    results = []
    for asset_info in ASSETS_TO_MONITOR[:15]:
        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            data = fetch_forex_data(symbol, name)
            if data is None or data.empty or len(data) < 30:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            df_ta = calculate_all_indicators(data.copy())
            if df_ta is None:
                continue

            strat = strategy_engine.evaluate_all_strategies(df_ta)
            vol = volatility_analyzer.analyze_volatility(df_ta)
            trend = trend_confirmation.confirm_trend(df_ta)
            div = divergence_detector.detect_divergence(df_ta)

            if strat.get("signal"):
                results.append({
                    "name": name,
                    "strategy": strat,
                    "volatility": vol,
                    "trend": trend,
                    "divergence": div,
                })
        except Exception:
            continue

    if results:
        # فلتر: الإشارة يجب أن تتوافق مع الاتجاه
        filtered_results = []
        for r in results:
            strat = r["strategy"]
            trend = r["trend"]["trend"]
            signal = strat["signal"]
            # قبول فقط إذا الاتجاه يدعم الإشارة أو محايد
            if (signal == "CALL" and trend in ["BULLISH", "NEUTRAL"]) or \
               (signal == "PUT" and trend in ["BEARISH", "NEUTRAL"]):
                filtered_results.append(r)
            # أو إذا كان تباعد (انعكاس) مع ثقة عالية
            elif r["divergence"].get("found") and strat.get("confidence", 0) >= 80:
                filtered_results.append(r)

        if not filtered_results:
            filtered_results = results  # إذا لم يبقَ شيء، أعرض الكل

        filtered_results.sort(key=lambda x: x["strategy"].get("confidence", 0), reverse=True)

        now = get_local_time()
        msg = (
            "⟪🎯 التحليل الاستراتيجي المتقدم ⟫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, r in enumerate(filtered_results[:5], 1):
            strat = r["strategy"]
            direction = "🟢 CALL" if strat["signal"] == "CALL" else "🔴 PUT"
            confidence = strat.get("confidence", 0)
            entry_time = now + timedelta(minutes=i * 2)
            time_str = entry_time.strftime("%H:%M")

            msg += (
                f"{i}. {r['name']}\n"
                f"   {direction} | ثقة: {confidence}%\n"
                f"   🕓 وقت الدخول: {time_str}\n"
                f"   📊 {strat.get('strategy', 'N/A')}\n"
                f"   📈 اتجاه: {r['trend']['trend']} ({r['trend']['confidence']}%)\n"
                f"   📉 تقلبات: {r['volatility']['level']}\n"
            )

            if r["divergence"].get("found"):
                msg += f"   🔀 تباعد مكتشف!\n"

            if strat.get("consensus"):
                msg += f"   ✅ إجماع ({strat['strategies_agree']}/{strat['strategies_total']})\n"

            msg += "\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 ركّز على الإشارات بثقة 75%+ مع إجماع\n"
            "⏰ ادخل الصفقة في الوقت المحدد"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(
            "⏸ لا توجد فرص استراتيجية واضحة حالياً\n"
            "جرّب بعد دقائق..."
        )


# ═══════════════════════════════════════════════════════════════
# أمر /report - تقرير شامل
# ═══════════════════════════════════════════════════════════════

async def full_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تقرير شامل عن الأداء"""
    user_id = update.effective_user.id

    try:
        total_trades = Trade.select().count()
        wins = Trade.select().where(Trade.result == "win").count()
        losses = Trade.select().where(Trade.result == "loss").count()
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        # أفضل الأصول
        best_assets = get_best_performing_assets(3)
        worst_assets = get_worst_performing_assets(3)

        # ML insights
        best_hours = ml_engine.get_best_trading_hours()

        msg = (
            "╔══════════════════════════════╗\n"
            "║     📊 التقرير الشامل 🧠     ║\n"
            "╚══════════════════════════════╝\n\n"
            f"📈 الأداء العام:\n"
            f"   الصفقات: {total_trades}\n"
            f"   ✅ رابحة: {wins}\n"
            f"   ❌ خاسرة: {losses}\n"
            f"   📊 نسبة النجاح: {win_rate:.1f}%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
        )

        if best_assets:
            msg += "🏆 أفضل الأصول:\n"
            for asset in best_assets:
                msg += f"   • {asset.asset}: {asset.win_rate:.0f}% ({asset.wins}W/{asset.losses}L)\n"
            msg += "\n"

        if worst_assets:
            msg += "⚠️ أضعف الأصول:\n"
            for asset in worst_assets:
                msg += f"   • {asset.asset}: {asset.win_rate:.0f}% ({asset.wins}W/{asset.losses}L)\n"
            msg += "\n"

        msg += "━━━━━━━━━━━━━━━━━━━━━\n"

        if best_hours:
            msg += "⏰ أفضل أوقات التداول (ML):\n"
            for h in best_hours[:3]:
                msg += f"   • الساعة {h['hour']}:00 - نجاح {h['win_rate']}%\n"
            msg += "\n"

        # توصيات
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 توصيات ML:\n"
        if win_rate >= 65:
            msg += "   ✅ أداء ممتاز! حافظ على استراتيجيتك\n"
        elif win_rate >= 50:
            msg += "   👍 أداء جيد. ركّز على Grade A فقط\n"
        elif win_rate > 0:
            msg += "   ⚠️ أداء ضعيف. قلل الصفقات وانتظر الإشارات القوية\n"
        else:
            msg += "   📌 سجّل نتائج صفقاتك لتفعيل التحليل\n"

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"خطأ في التقرير: {e}")
        await update.message.reply_text("❌ حدث خطأ في إنشاء التقرير.")


# ═══════════════════════════════════════════════════════════════
# أمر /best - أفضل الأزواج حالياً
# ═══════════════════════════════════════════════════════════════

async def best_pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري البحث عن أفضل الفرص...")

    best_signals = []
    now = get_local_time()

    for asset_info in ASSETS_TO_MONITOR:
        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            data = fetch_forex_data(symbol, name)
            if data is None or data.empty or len(data) < 30:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            df_ta = calculate_all_indicators(data.copy())
            if df_ta is None:
                continue

            signal = generate_signal_for_asset(df_ta, min_conf_override=6)
            strategy_result = strategy_engine.evaluate_all_strategies(df_ta)

            if signal:
                # تعزيز بالاستراتيجية
                bonus = 0
                if strategy_result.get("signal") == signal["direction"]:
                    bonus = 1

                best_signals.append({
                    "name": name,
                    "signal": signal,
                    "bonus": bonus,
                    "strategy": strategy_result.get("strategy", ""),
                })
        except Exception as e:
            logger.error(f"خطأ في مسح {name}: {e}")
            continue

    best_signals.sort(key=lambda x: x["signal"]["confirmations"] + x["bonus"], reverse=True)

    if best_signals:
        msg = (
            "⟪❁ أفضل الفرص المتاحة ❁⟫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, item in enumerate(best_signals[:5], 1):
            sig = item["signal"]
            direction = "🟢 CALL" if sig["direction"] == "CALL" else "🔴 PUT"
            total_score = sig['confirmations'] + item['bonus']
            msg += (
                f"{i}. {item['name']}\n"
                f"   {direction} | {sig['grade_emoji']} | "
                f"القوة: {total_score}/{sig['total_indicators']}\n"
            )
            if item["strategy"]:
                msg += f"   🎯 {item['strategy']}\n"
            msg += "\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 استخدم /signals للإشارات المفصّلة"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(
            "⏸ لا توجد فرص قوية حالياً\n"
            "جرّب بعد دقائق..."
        )


# ═══════════════════════════════════════════════════════════════
# أمر /market - حالة السوق
# ═══════════════════════════════════════════════════════════════

async def market_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري تحليل حالة السوق...")

    msg = (
        "⟪❁ حالة السوق ❁⟫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    analyzed = 0

    for asset_info in ASSETS_TO_MONITOR[:8]:
        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            data = fetch_forex_data(symbol, name)
            if data is None or data.empty or len(data) < 30:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            df_ta = calculate_all_indicators(data.copy())
            if df_ta is None:
                continue

            overview = get_market_overview(df_ta)
            if overview is None:
                continue

            analyzed += 1

            rsi = overview["rsi"]
            trend_str = overview["trend_strength"]

            if rsi > 55 and trend_str > 55:
                trend_emoji = "🟢"
                bullish_count += 1
            elif rsi < 45 and trend_str > 55:
                trend_emoji = "🔴"
                bearish_count += 1
            else:
                trend_emoji = "⚪"
                neutral_count += 1

            msg += (
                f"{trend_emoji} {name}\n"
                f"   RSI: {rsi:.0f} | ADX: {overview['adx']:.0f} | "
                f"MACD: {overview['macd_trend']}\n\n"
            )

        except Exception as e:
            logger.error(f"خطأ في {name}: {e}")
            continue

    if analyzed > 0:
        msg += (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 الملخص ({analyzed} زوج):\n"
            f"   🟢 صاعد: {bullish_count}\n"
            f"   🔴 هابط: {bearish_count}\n"
            f"   ⚪ محايد: {neutral_count}\n\n"
        )

        if bullish_count > bearish_count:
            msg += "💡 السوق يميل للصعود - ابحث عن CALL"
        elif bearish_count > bullish_count:
            msg += "💡 السوق يميل للهبوط - ابحث عن PUT"
        else:
            msg += "💡 السوق متذبذب - انتظر إشارة واضحة"
    else:
        msg += "⚠️ لم يتم تحليل أي زوج - تحقق من اتصال الإنترنت"

    await update.message.reply_text(msg)


# ═══════════════════════════════════════════════════════════════
# أمر /risk - إدارة المخاطر
# ═══════════════════════════════════════════════════════════════

async def risk_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = format_risk_message(user_id)
    await update.message.reply_text(msg)


# ═══════════════════════════════════════════════════════════════
# الإشارات التلقائية
# ═══════════════════════════════════════════════════════════════

async def auto_signals_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة الإشارات التلقائية المحسّنة"""
    chat_id = context.job.chat_id
    user_id = context.job.data.get("user_id", 0) if context.job.data else 0

    risk_check = check_risk_limits(user_id)
    if risk_check["should_stop"]:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⛔ تم إيقاف الإشارات التلقائية\n{risk_check['reason']}"
        )
        context.job.schedule_removal()
        return

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals = await analyze_all_assets_v2(user_id, min_conf)

    if signals:
        now = get_local_time()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔔 إشارات تلقائية ذكية - {now.strftime('%H:%M')}\n━━━━━━━━━━━━━━━━━━━━━"
        )
        for sig_msg in signals:
            await context.bot.send_message(chat_id=chat_id, text=sig_msg)
            await asyncio.sleep(0.3)


async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل الإشارات التلقائية"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    settings = get_user_settings(user_id)
    interval = settings.signal_interval if settings else AUTO_SIGNAL_INTERVAL

    current_jobs = context.job_queue.get_jobs_by_name(f"auto_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()

    context.job_queue.run_repeating(
        auto_signals_job,
        interval=interval * 60,
        first=10,
        chat_id=chat_id,
        name=f"auto_{chat_id}",
        data={"user_id": user_id}
    )

    update_user_setting(user_id, "auto_signals", True)

    await update.message.reply_text(
        f"✅ تم تفعيل الإشارات التلقائية الذكية\n\n"
        f"📡 ستصلك إشارات كل {interval} دقائق\n"
        f"🧠 معزّزة بالتعلم الآلي\n"
        f"⚠️ سيتم الإيقاف تلقائياً عند تجاوز حدود المخاطرة\n\n"
        f"لإيقافها: /auto_off"
    )


async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف الإشارات التلقائية"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    current_jobs = context.job_queue.get_jobs_by_name(f"auto_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()

    update_user_setting(user_id, "auto_signals", False)

    await update.message.reply_text("⏹ تم إيقاف الإشارات التلقائية.")


# ═══════════════════════════════════════════════════════════════
# تسجيل النتائج مع تحديث ML
# ═══════════════════════════════════════════════════════════════

async def record_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل صفقة رابحة مع تحديث ML"""
    user_id = update.effective_user.id
    try:
        last_trade = (Trade.select()
                      .where(Trade.user_id == user_id, Trade.result == "pending")
                      .order_by(Trade.timestamp.desc())
                      .first())

        if not last_trade:
            last_trade = (Trade.select()
                          .where(Trade.result == "pending")
                          .order_by(Trade.timestamp.desc())
                          .first())

        if last_trade:
            last_trade.result = "win"
            last_trade.save()

            rm = RiskManager(user_id)
            amount = rm.calculate_trade_amount()["suggested_amount"]
            update_daily_stats(user_id, "win", amount)
            update_asset_performance(last_trade.asset, "win")

            # تحديث ML
            reasons = last_trade.reasons.split(", ") if last_trade.reasons else []
            now = get_local_time()
            ml_engine.record_trade_result(
                asset=last_trade.asset,
                direction=last_trade.signal_type,
                reasons=reasons,
                result="win",
                hour=now.hour,
            )

            await update.message.reply_text(
                f"✅ تم تسجيل ربح!\n\n"
                f"📊 {last_trade.asset} | {last_trade.signal_type}\n"
                f"💪 {last_trade.confirmations}/12 | Grade {last_trade.grade}\n"
                f"💰 +${amount:.2f}\n\n"
                f"🧠 تم تحديث نموذج التعلم الآلي\n"
                f"🎉 أحسنت! استمر"
            )
        else:
            await update.message.reply_text("⚠️ لا توجد صفقة معلقة لتسجيلها.")
    except Exception as e:
        logger.error(f"خطأ win: {e}")
        await update.message.reply_text("❌ حدث خطأ في التسجيل.")


async def record_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل صفقة خاسرة مع تحديث ML"""
    user_id = update.effective_user.id
    try:
        last_trade = (Trade.select()
                      .where(Trade.user_id == user_id, Trade.result == "pending")
                      .order_by(Trade.timestamp.desc())
                      .first())

        if not last_trade:
            last_trade = (Trade.select()
                          .where(Trade.result == "pending")
                          .order_by(Trade.timestamp.desc())
                          .first())

        if last_trade:
            last_trade.result = "loss"
            last_trade.save()

            rm = RiskManager(user_id)
            amount = rm.calculate_trade_amount()["suggested_amount"]
            stats = update_daily_stats(user_id, "loss", amount)
            update_asset_performance(last_trade.asset, "loss")

            # تحديث ML
            reasons = last_trade.reasons.split(", ") if last_trade.reasons else []
            now = get_local_time()
            ml_engine.record_trade_result(
                asset=last_trade.asset,
                direction=last_trade.signal_type,
                reasons=reasons,
                result="loss",
                hour=now.hour,
            )

            msg = (
                f"❌ تم تسجيل خسارة\n\n"
                f"📊 {last_trade.asset} | {last_trade.signal_type}\n"
                f"💪 {last_trade.confirmations}/12 | Grade {last_trade.grade}\n"
                f"💸 -${amount:.2f}\n"
                f"\n🧠 تم تحديث نموذج التعلم الآلي"
            )

            if stats and stats.consecutive_losses == 1:
                next_amount = amount * 2.2
                msg += f"\n\n📌 الصفقة القادمة: مارتينجيل ${next_amount:.2f}"

            risk_check = check_risk_limits(user_id)
            if risk_check["should_stop"]:
                msg += f"\n\n⛔ تحذير: {risk_check['reason']}\n💡 يُنصح بالتوقف"

            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("⚠️ لا توجد صفقة معلقة لتسجيلها.")
    except Exception as e:
        logger.error(f"خطأ loss: {e}")
        await update.message.reply_text("❌ حدث خطأ في التسجيل.")


# ═══════════════════════════════════════════════════════════════
# أمر /history - سجل الصفقات
# ═══════════════════════════════════════════════════════════════

async def get_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        trades = (Trade.select()
                  .order_by(Trade.timestamp.desc())
                  .limit(10))
        trade_list = list(trades)

        if not trade_list:
            await update.message.reply_text("📋 لا يوجد سجل صفقات حتى الآن.")
            return

        history_msg = "⟪❁ سجل الصفقات ❁⟫\n━━━━━━━━━━━━━━━━━━━━━\n\n"

        for trade in trade_list:
            direction_emoji = "🟢" if trade.signal_type == "CALL" else "🔴"
            result_emoji = "✅" if trade.result == "win" else "❌" if trade.result == "loss" else "⏳"
            grade = trade.grade if trade.grade else "?"

            history_msg += (
                f"{direction_emoji} {trade.asset} | {trade.signal_type} {result_emoji}\n"
                f"   💪 {trade.confirmations}/12 | Grade {grade}\n"
                f"   📅 {trade.timestamp.strftime('%H:%M %d/%m')}\n\n"
            )

        await update.message.reply_text(history_msg)

    except Exception as e:
        logger.error(f"خطأ في السجل: {e}")
        await update.message.reply_text("❌ حدث خطأ في جلب السجل.")


# ═══════════════════════════════════════════════════════════════
# أمر /stats - الإحصائيات
# ═══════════════════════════════════════════════════════════════

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        total_trades = Trade.select().count()
        wins = Trade.select().where(Trade.result == "win").count()
        losses = Trade.select().where(Trade.result == "loss").count()
        pending = Trade.select().where(Trade.result == "pending").count()

        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_trades = Trade.select().where(Trade.timestamp >= today_start).count()
        today_wins = Trade.select().where(
            Trade.timestamp >= today_start, Trade.result == "win"
        ).count()
        today_losses = Trade.select().where(
            Trade.timestamp >= today_start, Trade.result == "loss"
        ).count()
        today_rate = (today_wins / (today_wins + today_losses) * 100) if (today_wins + today_losses) > 0 else 0

        grade_a_wins = Trade.select().where(Trade.grade == "A", Trade.result == "win").count()
        grade_a_total = Trade.select().where(Trade.grade == "A", Trade.result != "pending").count()
        grade_a_rate = (grade_a_wins / grade_a_total * 100) if grade_a_total > 0 else 0

        grade_b_wins = Trade.select().where(Trade.grade == "B", Trade.result == "win").count()
        grade_b_total = Trade.select().where(Trade.grade == "B", Trade.result != "pending").count()
        grade_b_rate = (grade_b_wins / grade_b_total * 100) if grade_b_total > 0 else 0

        stats_msg = (
            "⟪❁ إحصائيات الأداء ❁⟫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 الإجمالي:\n"
            f"   الصفقات: {total_trades}\n"
            f"   ✅ رابحة: {wins}\n"
            f"   ❌ خاسرة: {losses}\n"
            f"   ⏳ معلقة: {pending}\n"
            f"   📈 نسبة النجاح: {win_rate:.1f}%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 اليوم:\n"
            f"   الصفقات: {today_trades}\n"
            f"   ✅ رابحة: {today_wins}\n"
            f"   ❌ خاسرة: {today_losses}\n"
            f"   📈 نسبة النجاح: {today_rate:.1f}%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 أداء حسب الدرجة:\n"
            f"   🅰️ Grade A: {grade_a_rate:.0f}% ({grade_a_wins}/{grade_a_total})\n"
            f"   🅱️ Grade B: {grade_b_rate:.0f}% ({grade_b_wins}/{grade_b_total})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 نصيحة: ركّز على Grade A و B فقط"
        )
        await update.message.reply_text(stats_msg)

    except Exception as e:
        logger.error(f"خطأ في الإحصائيات: {e}")
        await update.message.reply_text("❌ حدث خطأ في الإحصائيات.")


# ═══════════════════════════════════════════════════════════════
# أمر /performance - أداء الأزواج
# ═══════════════════════════════════════════════════════════════

async def asset_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        best = get_best_performing_assets(5)
        worst = get_worst_performing_assets(3)

        msg = "⟪❁ أداء الأزواج ❁⟫\n━━━━━━━━━━━━━━━━━━━━━\n\n"

        if best:
            msg += "🏆 الأفضل أداءً:\n"
            for i, asset in enumerate(best, 1):
                total = asset.wins + asset.losses
                msg += (
                    f"   {i}. {asset.asset}\n"
                    f"      نسبة النجاح: {asset.win_rate:.0f}%\n"
                    f"      ({asset.wins}✅ / {asset.losses}❌ من {total})\n\n"
                )

        if worst:
            msg += "⚠️ الأضعف أداءً:\n"
            for asset in worst:
                total = asset.wins + asset.losses
                msg += (
                    f"   • {asset.asset}: {asset.win_rate:.0f}%\n"
                    f"     ({asset.wins}✅ / {asset.losses}❌)\n"
                )
            msg += "\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 تجنب الأزواج ذات الأداء الضعيف"
        )
        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"خطأ في الأداء: {e}")
        await update.message.reply_text("❌ لا توجد بيانات أداء كافية بعد.\nسجّل نتائج صفقاتك بـ /win أو /loss")


# ═══════════════════════════════════════════════════════════════
# أمر /settings - الإعدادات
# ═══════════════════════════════════════════════════════════════

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings = get_user_settings(user_id)

    keyboard = [
        [
            InlineKeyboardButton(f"🎯 التأكيدات: {user_settings.min_confirmations}/12", callback_data="conf_header"),
        ],
        [
            InlineKeyboardButton("6", callback_data="conf_6"),
            InlineKeyboardButton("7", callback_data="conf_7"),
            InlineKeyboardButton("8", callback_data="conf_8"),
            InlineKeyboardButton("9", callback_data="conf_9"),
        ],
        [
            InlineKeyboardButton(f"⏱ الفترة: {user_settings.signal_interval} دقائق", callback_data="interval_header"),
        ],
        [
            InlineKeyboardButton("3 دق", callback_data="interval_3"),
            InlineKeyboardButton("5 دق", callback_data="interval_5"),
            InlineKeyboardButton("10 دق", callback_data="interval_10"),
            InlineKeyboardButton("15 دق", callback_data="interval_15"),
        ],
        [
            InlineKeyboardButton(f"⚡ المخاطرة: {user_settings.risk_level}", callback_data="risk_header"),
        ],
        [
            InlineKeyboardButton("منخفض", callback_data="risk_low"),
            InlineKeyboardButton("متوسط", callback_data="risk_medium"),
            InlineKeyboardButton("عالي", callback_data="risk_high"),
        ],
        [
            InlineKeyboardButton(f"💵 رأس المال: ${user_settings.capital}", callback_data="cap_header"),
        ],
        [
            InlineKeyboardButton("$50", callback_data="capital_50"),
            InlineKeyboardButton("$100", callback_data="capital_100"),
            InlineKeyboardButton("$200", callback_data="capital_200"),
            InlineKeyboardButton("$500", callback_data="capital_500"),
            InlineKeyboardButton("$1000", callback_data="capital_1000"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⟪❁ الإعدادات ❁⟫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "اختر الإعداد الذي تريد تغييره:\n",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.endswith("_header"):
        return

    response = ""

    if data.startswith("conf_"):
        conf = int(data.split("_")[1])
        update_user_setting(user_id, "min_confirmations", conf)
        response = f"✅ تم تغيير التأكيدات المطلوبة إلى: {conf}/12"

    elif data.startswith("interval_"):
        interval = int(data.split("_")[1])
        update_user_setting(user_id, "signal_interval", interval)
        response = f"✅ تم تغيير فترة الإشارات إلى: {interval} دقائق\nأعد تفعيل /auto_on لتطبيق التغيير"

    elif data.startswith("risk_"):
        level = data.split("_")[1]
        update_user_setting(user_id, "risk_level", level)
        level_ar = {"low": "منخفض", "medium": "متوسط", "high": "عالي"}
        response = f"✅ تم تغيير مستوى المخاطرة إلى: {level_ar.get(level, level)}"

    elif data.startswith("capital_"):
        capital = float(data.split("_")[1])
        update_user_setting(user_id, "capital", capital)
        response = f"✅ تم تحديث رأس المال إلى: ${capital}"

    elif data.startswith("chart_"):
        symbol = data.replace("chart_", "")
        target_asset = None
        for asset in ASSETS_TO_MONITOR:
            if asset["symbol"] == symbol:
                target_asset = asset
                break
        if target_asset:
            await send_chart_for_asset(update, target_asset)
        else:
            response = "❌ لم أجد الزوج"

    if response:
        await query.edit_message_text(response)


# ═══════════════════════════════════════════════════════════════
# التقرير اليومي
# ═══════════════════════════════════════════════════════════════

async def daily_report_job(context: ContextTypes.DEFAULT_TYPE):
    """إرسال التقرير اليومي"""
    chat_id = context.job.chat_id
    user_id = context.job.data.get("user_id", 0) if context.job.data else 0

    try:
        total_trades = Trade.select().where(
            Trade.timestamp >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()

        if total_trades == 0:
            return

        stats = get_daily_stats(user_id)
        if not stats:
            return

        win_rate = stats.win_rate
        emoji = "🎉" if win_rate >= 70 else "👍" if win_rate >= 50 else "💪"

        report = (
            f"╔══════════════════════════════╗\n"
            f"║     📊 التقرير اليومي {emoji}     ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 النتائج:\n"
            f"   الصفقات: {stats.total_signals}\n"
            f"   ✅ رابحة: {stats.wins}\n"
            f"   ❌ خاسرة: {stats.losses}\n"
            f"   📊 نسبة النجاح: {win_rate:.1f}%\n"
            f"   💰 الربح/الخسارة: ${stats.profit_loss:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 تحليل ML:\n"
        )

        best_hours = ml_engine.get_best_trading_hours()
        if best_hours:
            report += f"   أفضل ساعة: {best_hours[0]['hour']}:00 ({best_hours[0]['win_rate']}%)\n"

        report += f"\n💡 نصيحة الغد: "
        if win_rate >= 70:
            report += "أداء ممتاز! حافظ على نفس الاستراتيجية"
        elif win_rate >= 50:
            report += "أداء جيد. ركّز على إشارات Grade A"
        else:
            report += "راجع استراتيجيتك. قلل عدد الصفقات وركّز على الجودة"

        await context.bot.send_message(chat_id=chat_id, text=report)

    except Exception as e:
        logger.error(f"خطأ في التقرير اليومي: {e}")


# ═══════════════════════════════════════════════════════════════
# أمر /chart - الرسم البياني
# ═══════════════════════════════════════════════════════════════

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الرسم البياني لزوج محدد"""
    # إذا المستخدم حدد زوج
    if context.args:
        asset_query = " ".join(context.args).upper()
        # البحث عن الزوج
        target_asset = None
        for asset in ASSETS_TO_MONITOR:
            if asset_query in asset["name"].upper() or asset_query in asset["symbol"].upper():
                target_asset = asset
                break
        
        if not target_asset:
            await update.message.reply_text(
                f"❌ لم أجد الزوج: {asset_query}\n"
                f"📝 استخدم: /chart EURUSD أو /chart BTC"
            )
            return
        
        await send_chart_for_asset(update, target_asset)
    else:
        # عرض قائمة الأزواج (فوركس + أسهم فقط)
        keyboard = []
        forex_assets = [a for a in ASSETS_TO_MONITOR if a["category"] == "Forex"]
        stocks_assets = [a for a in ASSETS_TO_MONITOR if a["category"] == "Stocks"]
        
        # فوركس
        row = []
        for asset in forex_assets[:4]:
            row.append(InlineKeyboardButton(asset["name"], callback_data=f"chart_{asset['symbol']}"))
        keyboard.append(row)
        row = []
        for asset in forex_assets[4:]:
            row.append(InlineKeyboardButton(asset["name"], callback_data=f"chart_{asset['symbol']}"))
        keyboard.append(row)
        
        # أسهم
        if stocks_assets:
            row = []
            for asset in stocks_assets[:5]:
                row.append(InlineKeyboardButton(asset["name"], callback_data=f"chart_{asset['symbol']}"))
            keyboard.append(row)
            if len(stocks_assets) > 5:
                row = []
                for asset in stocks_assets[5:]:
                    row.append(InlineKeyboardButton(asset["name"], callback_data=f"chart_{asset['symbol']}"))
                keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 اختر الزوج لعرض الرسم البياني:\n\n"
            "أو استخدم: /chart EURUSD",
            reply_markup=reply_markup
        )


async def send_chart_for_asset(update, asset_info):
    """توليد وإرسال شارت لزوج محدد"""
    symbol = asset_info["symbol"]
    name = asset_info["name"]
    
    # إرسال رسالة انتظار
    if hasattr(update, 'message') and update.message:
        wait_msg = await update.message.reply_text(f"⏳ جاري توليد شارت {name}...")
    elif hasattr(update, 'callback_query'):
        wait_msg = await update.callback_query.message.reply_text(f"⏳ جاري توليد شارت {name}...")
    else:
        wait_msg = None
    
    try:
        # جلب البيانات
        data = fetch_forex_data(symbol, name)
        
        if data is None or data.empty or len(data) < 30:
            if wait_msg:
                await wait_msg.edit_text(f"❌ لا توجد بيانات كافية لـ {name}")
            return
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # حساب المؤشرات
        df_ta = calculate_all_indicators(data.copy())
        
        if df_ta is None or df_ta.empty:
            if wait_msg:
                await wait_msg.edit_text(f"❌ خطأ في حساب المؤشرات لـ {name}")
            return
        
        # توليد إشارة (إن وجدت)
        signal = generate_signal_for_asset(df_ta)
        
        signal_dir = None
        entry_price = None
        support = None
        resistance = None
        
        entry_time = datetime.now().strftime('%H:%M')
        
        if signal:
            signal_dir = signal["direction"]
            entry_price = signal["close"]
            support = signal.get("support")
            resistance = signal.get("resistance")
        
        # توليد الشارت
        chart_path = generate_chart(
            df_ta, name,
            signal_direction=signal_dir,
            entry_price=entry_price,
            support=support,
            resistance=resistance,
            entry_time=entry_time
        )
        
        if chart_path and os.path.exists(chart_path):
            # إرسال الصورة
            caption = f"📊 {name} - M1\n"
            if signal:
                direction_emoji = "🟢 CALL ↑" if signal_dir == "CALL" else "🔴 PUT ↓"
                caption += f"🎯 إشارة: {direction_emoji}\n"
                caption += f"🕓 وقت الدخول: {entry_time}\n"
                caption += f"💪 القوة: {signal['confirmations']}/12\n"
            else:
                caption += "⏸ لا توجد إشارة حالياً"
            
            if hasattr(update, 'message') and update.message:
                await update.message.reply_photo(
                    photo=open(chart_path, 'rb'),
                    caption=caption
                )
            elif hasattr(update, 'callback_query'):
                await update.callback_query.message.reply_photo(
                    photo=open(chart_path, 'rb'),
                    caption=caption
                )
            
            # حذف الملف المؤقت
            os.remove(chart_path)
            
            if wait_msg:
                await wait_msg.delete()
        else:
            if wait_msg:
                await wait_msg.edit_text(f"❌ خطأ في توليد الشارت لـ {name}")
    
    except Exception as e:
        logger.error(f"خطأ في إرسال الشارت: {e}")
        if wait_msg:
            await wait_msg.edit_text(f"❌ خطأ: {str(e)[:100]}")


# ═══════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ═══════════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN غير محدد!")
        print("❌ خطأ: يجب تعيين TELEGRAM_BOT_TOKEN")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        return

    # بناء التطبيق
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signals", get_signals))
    app.add_handler(CommandHandler("forex", forex_signals))
    app.add_handler(CommandHandler("crypto", crypto_signals))
    app.add_handler(CommandHandler("stocks", stocks_signals))
    app.add_handler(CommandHandler("best", best_pairs))
    app.add_handler(CommandHandler("market", market_overview))
    app.add_handler(CommandHandler("ml", ml_status))
    app.add_handler(CommandHandler("strategy", strategy_analysis))
    app.add_handler(CommandHandler("report", full_report))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CommandHandler("history", get_history))
    app.add_handler(CommandHandler("stats", get_stats))
    app.add_handler(CommandHandler("performance", asset_performance))
    app.add_handler(CommandHandler("risk", risk_status))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("win", record_win))
    app.add_handler(CommandHandler("loss", record_loss))
    app.add_handler(CommandHandler("chart", chart_command))

    # معالج الأزرار
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("✅ البوت V2 يعمل - ML + استراتيجيات متقدمة")
    print("✅ PocketOption Pro Bot V2 يعمل بنجاح!")
    print("🧠 محرك التعلم الآلي: مفعّل")
    print("🎯 6 استراتيجيات متقدمة: مفعّلة")
    print("📡 في انتظار الرسائل...")

    # تشغيل البوت
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
