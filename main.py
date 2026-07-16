"""
بوت إشارات Pocket Option - الإصدار المتقدم
بوت تليجرام احترافي لتحليل الأسواق وتوليد إشارات التداول
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
    # إنشاء إعدادات المستخدم
    get_user_settings(user_id)

    welcome_msg = (
        "╔══════════════════════════════╗\n"
        "║  ⟪❁ PocketOption Pro Bot ❁⟫  ║\n"
        "╚══════════════════════════════╝\n\n"
        "مرحباً بك في بوت إشارات التداول الاحترافي 🎯\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 المواصفات:\n"
        "• مدة الصفقة: 1 دقيقة ⏰\n"
        "• 12+ مؤشر فني للتحليل\n"
        "• تحليل Multi-Timeframe\n"
        "• نظام تقييم جودة الإشارات (A/B/C)\n"
        "• إدارة مخاطر ذكية\n"
        "• مارتينجيل وحدة واحدة فقط\n"
        "• نسبة أقل من 80% ملغية ⭕\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 الأوامر الرئيسية:\n\n"
        "📊 التحليل والإشارات:\n"
        "/signals - إشارات تداول جديدة\n"
        "/best - أفضل الأزواج حالياً\n"
        "/market - حالة السوق العامة\n\n"
        "🔔 الإشارات التلقائية:\n"
        "/auto_on - تفعيل الإشارات التلقائية\n"
        "/auto_off - إيقاف الإشارات التلقائية\n\n"
        "📈 السجل والإحصائيات:\n"
        "/history - سجل الصفقات\n"
        "/stats - إحصائيات الأداء\n"
        "/performance - أداء الأزواج\n\n"
        "💰 إدارة المخاطر:\n"
        "/risk - حالة إدارة المخاطر\n"
        "/win - تسجيل صفقة رابحة ✅\n"
        "/loss - تسجيل صفقة خاسرة ❌\n\n"
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
        "⟪❁ المساعدة ❁⟫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 أوامر الإشارات:\n"
        "/signals - توليد إشارات CALL/PUT\n"
        "/best - أفضل الفرص المتاحة الآن\n"
        "/market - نظرة عامة على السوق\n"
        "/auto_on - إشارات تلقائية\n"
        "/auto_off - إيقاف التلقائي\n\n"
        "📋 أوامر السجل:\n"
        "/history - آخر 10 صفقات\n"
        "/stats - الإحصائيات ونسبة النجاح\n"
        "/performance - أداء كل زوج\n"
        "/win - تسجيل ربح لآخر صفقة\n"
        "/loss - تسجيل خسارة لآخر صفقة\n\n"
        "💰 إدارة المخاطر:\n"
        "/risk - عرض حالة المخاطرة\n\n"
        "⚙️ الإعدادات:\n"
        "/settings - عرض وتعديل الإعدادات\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 المؤشرات المستخدمة (12+):\n"
        "RSI | MACD | EMA | Bollinger\n"
        "Stochastic | CCI | Williams%R\n"
        "ADX | Parabolic SAR | Ichimoku\n"
        "Price Action | Candle Patterns\n"
        "Support/Resistance | Trend Strength\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 نظام التقييم:\n"
        "🅰️ Grade A: إشارة ممتازة (10+/12)\n"
        "🅱️ Grade B: إشارة جيدة (8-9/12)\n"
        "©️ Grade C: إشارة مقبولة (6-7/12)\n\n"
        "⚠️ تداول بمسؤولية!"
    )
    await update.message.reply_text(help_msg)


# ═══════════════════════════════════════════════════════════════
# أمر /signals - توليد الإشارات
# ═══════════════════════════════════════════════════════════════

async def get_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # فحص حدود المخاطرة
    risk_check = check_risk_limits(user_id)
    if risk_check["should_stop"]:
        await update.message.reply_text(
            f"⛔ تم إيقاف التداول اليوم\n\n"
            f"السبب: {risk_check['reason']}\n\n"
            f"💡 يُنصح بالراحة والعودة غداً"
        )
        return

    await update.message.reply_text("⏳ جاري تحليل الأسواق بـ 12 مؤشر فني...")

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals = await analyze_all_assets(user_id, min_conf)

    if signals:
        for sig_msg in signals:
            await update.message.reply_text(sig_msg)
            await asyncio.sleep(0.5)

        # حساب حجم الصفقة المقترح
        rm = RiskManager(user_id)
        trade_info = rm.calculate_trade_amount()

        summary_msg = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ تم توليد {len(signals)} إشارة\n\n"
            f"💰 المبلغ المقترح: ${trade_info['suggested_amount']}\n"
        )
        if trade_info['is_martingale']:
            summary_msg += f"📌 مارتينجيل (مضاعفة وحدة)\n"

        summary_msg += (
            f"\n⚠️ نسبة أقل من 80% ملغية\n"
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
            "• البيانات غير متاحة مؤقتاً\n\n"
            "جرّب بعد دقائق أو فعّل /auto_on"
        )


async def analyze_all_assets(user_id=0, min_conf=None):
    """تحليل جميع الأصول وإرجاع قائمة الإشارات"""
    signals_list = []
    now = get_local_time()

    if min_conf is None:
        min_conf = MIN_CONFIRMATIONS

    for asset_info in ASSETS_TO_MONITOR:
        if len(signals_list) >= MAX_SIGNALS_PER_REQUEST:
            break

        symbol = asset_info["symbol"]
        name = asset_info["name"]

        try:
            # جلب البيانات
            data = fetch_forex_data(symbol, name)

            if data is None or data.empty or len(data) < 30:
                continue

            # تسطيح الأعمدة
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # حساب المؤشرات
            df_ta = calculate_all_indicators(data.copy())

            if df_ta is None or df_ta.empty:
                continue

            # توليد الإشارة
            signal = generate_signal_for_asset(df_ta, min_conf_override=min_conf)

            if signal:
                signal_time = now + timedelta(minutes=len(signals_list) * 2 + 1)
                time_str = signal_time.strftime("%H:%M")

                # تنسيق الإشارة
                direction_emoji = "🟢 CALL ↑" if signal["direction"] == "CALL" else "🔴 PUT ↓"
                conf = signal["confirmations"]
                total = signal["total_indicators"]
                strength_bar = "█" * conf + "░" * (total - conf)
                reasons_str = " | ".join(signal["reasons"][:4])

                sig_msg = (
                    f"╔═══════════════════════╗\n"
                    f"║   SIGNAL 1M {signal['grade_emoji']}        ║\n"
                    f"╚═══════════════════════╝\n\n"
                    f"📊 الزوج: {name}\n"
                    f"🕓 الوقت: {time_str}\n"
                    f"⏳ المدة: M1\n"
                    f"🎯 الاتجاه: {direction_emoji}\n\n"
                    f"💪 القوة: [{strength_bar}] {conf}/{total}\n"
                    f"📈 التقييم: {signal['grade_emoji']} {signal['grade_desc']}\n"
                    f"📋 الأسباب: {reasons_str}\n"
                )

                if signal.get("sr_bonus"):
                    sig_msg += f"🎯 {signal['sr_bonus']}\n"

                signals_list.append(sig_msg)

                # حفظ في قاعدة البيانات
                try:
                    Trade.create(
                        user_id=user_id,
                        asset=name,
                        signal_type=signal["direction"],
                        entry_price=signal["close"],
                        confirmations=conf,
                        grade=signal["grade"],
                        reasons=", ".join(signal["reasons"]),
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

    await update.message.reply_text(f"⏳ جاري تحليل {category_name} بـ 12 مؤشر فني...")

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals_list = []
    now = get_local_time()

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
            signal = generate_signal_for_asset(df_ta, min_conf_override=min_conf)
            if signal:
                signal_time = now + timedelta(minutes=len(signals_list) * 2 + 1)
                time_str = signal_time.strftime("%H:%M")
                direction_emoji = "🟢 CALL ↑" if signal["direction"] == "CALL" else "🔴 PUT ↓"
                conf = signal["confirmations"]
                total = signal["total_indicators"]
                strength_bar = "█" * conf + "░" * (total - conf)
                reasons_str = " | ".join(signal["reasons"][:4])

                sig_msg = (
                    f"╔═══════════════════════╗\n"
                    f"║   SIGNAL 1M {signal['grade_emoji']}        ║\n"
                    f"╚═══════════════════════╝\n\n"
                    f"📊 الأصل: {name}\n"
                    f"🕓 الوقت: {time_str}\n"
                    f"⏳ المدة: M1\n"
                    f"🎯 الاتجاه: {direction_emoji}\n\n"
                    f"💪 القوة: [{strength_bar}] {conf}/{total}\n"
                    f"📈 التقييم: {signal['grade_emoji']} {signal['grade_desc']}\n"
                    f"📋 الأسباب: {reasons_str}\n"
                )
                if signal.get("sr_bonus"):
                    sig_msg += f"🎯 {signal['sr_bonus']}\n"
                signals_list.append(sig_msg)

                try:
                    Trade.create(
                        user_id=user_id, asset=name,
                        signal_type=signal["direction"],
                        entry_price=signal["close"],
                        confirmations=conf, grade=signal["grade"],
                        reasons=", ".join(signal["reasons"]),
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
        await update.message.reply_text(f"✅ تم توليد {len(signals_list)} إشارة من {category_name}")
    else:
        await update.message.reply_text(
            f"⏸ لا توجد إشارات قوية في {category_name} حالياً\n\n"
            "💡 جرّب بعد دقائق أو فعّل /auto_on"
        )


async def forex_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إشارات الفوركس فقط"""
    await analyze_by_category(update, context, "Forex", "أزواج الفوركس 💱")


async def crypto_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إشارات العملات المشفرة فقط"""
    await analyze_by_category(update, context, "Crypto", "العملات المشفرة ₿")


async def stocks_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إشارات الأسهم الأمريكية فقط"""
    await analyze_by_category(update, context, "Stocks", "الأسهم الأمريكية 📈")


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

            signal = generate_signal_for_asset(df_ta, min_conf_override=6)  # حد أدنى أقل للمسح

            if signal:
                best_signals.append({
                    "name": name,
                    "signal": signal,
                })
        except Exception as e:
            logger.error(f"خطأ في مسح {name}: {e}")
            continue

    # ترتيب حسب القوة
    best_signals.sort(key=lambda x: x["signal"]["confirmations"], reverse=True)

    if best_signals:
        msg = (
            "⟪❁ أفضل الفرص المتاحة ❁⟫\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, item in enumerate(best_signals[:5], 1):
            sig = item["signal"]
            direction = "🟢 CALL" if sig["direction"] == "CALL" else "🔴 PUT"
            msg += (
                f"{i}. {item['name']}\n"
                f"   {direction} | {sig['grade_emoji']} | "
                f"القوة: {sig['confirmations']}/{sig['total_indicators']}\n\n"
            )

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

    for asset_info in ASSETS_TO_MONITOR[:8]:  # أول 8 أزواج
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

            # تحديد الاتجاه
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
    """وظيفة الإشارات التلقائية"""
    chat_id = context.job.chat_id
    user_id = context.job.data.get("user_id", 0) if context.job.data else 0

    # فحص حدود المخاطرة
    risk_check = check_risk_limits(user_id)
    if risk_check["should_stop"]:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⛔ تم إيقاف الإشارات التلقائية\n{risk_check['reason']}"
        )
        # إزالة الوظيفة
        context.job.schedule_removal()
        return

    settings = get_user_settings(user_id)
    min_conf = settings.min_confirmations if settings else MIN_CONFIRMATIONS

    signals = await analyze_all_assets(user_id, min_conf)

    if signals:
        now = get_local_time()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔔 إشارات تلقائية - {now.strftime('%H:%M')}\n━━━━━━━━━━━━━━━━━━━━━"
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

    # إزالة الوظائف القديمة
    current_jobs = context.job_queue.get_jobs_by_name(f"auto_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()

    # إضافة وظيفة جديدة
    context.job_queue.run_repeating(
        auto_signals_job,
        interval=interval * 60,
        first=10,
        chat_id=chat_id,
        name=f"auto_{chat_id}",
        data={"user_id": user_id}
    )

    # تحديث الإعدادات
    update_user_setting(user_id, "auto_signals", True)

    await update.message.reply_text(
        f"✅ تم تفعيل الإشارات التلقائية\n\n"
        f"📡 ستصلك إشارات كل {interval} دقائق\n"
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
# تسجيل النتائج
# ═══════════════════════════════════════════════════════════════

async def record_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل صفقة رابحة"""
    user_id = update.effective_user.id
    try:
        last_trade = (Trade.select()
                      .where(Trade.user_id == user_id, Trade.result == "pending")
                      .order_by(Trade.timestamp.desc())
                      .first())

        if not last_trade:
            # محاولة بدون فلتر user_id للتوافق مع الصفقات القديمة
            last_trade = (Trade.select()
                          .where(Trade.result == "pending")
                          .order_by(Trade.timestamp.desc())
                          .first())

        if last_trade:
            last_trade.result = "win"
            last_trade.save()

            # تحديث الإحصائيات
            rm = RiskManager(user_id)
            amount = rm.calculate_trade_amount()["suggested_amount"]
            update_daily_stats(user_id, "win", amount)
            update_asset_performance(last_trade.asset, "win")

            await update.message.reply_text(
                f"✅ تم تسجيل ربح!\n\n"
                f"📊 {last_trade.asset} | {last_trade.signal_type}\n"
                f"💪 {last_trade.confirmations}/12 | {last_trade.grade}\n"
                f"💰 +${amount:.2f}\n\n"
                f"🎉 أحسنت! استمر"
            )
        else:
            await update.message.reply_text("⚠️ لا توجد صفقة معلقة لتسجيلها.")
    except Exception as e:
        logger.error(f"خطأ win: {e}")
        await update.message.reply_text("❌ حدث خطأ في التسجيل.")


async def record_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل صفقة خاسرة"""
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

            # تحديث الإحصائيات
            rm = RiskManager(user_id)
            amount = rm.calculate_trade_amount()["suggested_amount"]
            stats = update_daily_stats(user_id, "loss", amount)
            update_asset_performance(last_trade.asset, "loss")

            msg = (
                f"❌ تم تسجيل خسارة\n\n"
                f"📊 {last_trade.asset} | {last_trade.signal_type}\n"
                f"💪 {last_trade.confirmations}/12 | {last_trade.grade}\n"
                f"💸 -${amount:.2f}\n"
            )

            # نصيحة المارتينجيل
            if stats and stats.consecutive_losses == 1:
                next_amount = amount * 2.2
                msg += f"\n📌 الصفقة القادمة: مارتينجيل ${next_amount:.2f}"

            # تحذير المخاطرة
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

        # إحصائيات اليوم
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_trades = Trade.select().where(Trade.timestamp >= today_start).count()
        today_wins = Trade.select().where(
            Trade.timestamp >= today_start, Trade.result == "win"
        ).count()
        today_losses = Trade.select().where(
            Trade.timestamp >= today_start, Trade.result == "loss"
        ).count()
        today_rate = (today_wins / (today_wins + today_losses) * 100) if (today_wins + today_losses) > 0 else 0

        # إحصائيات حسب الدرجة
        grade_a_wins = Trade.select().where(Trade.grade == "A", Trade.result == "win").count()
        grade_a_total = Trade.select().where(Trade.grade == "A", Trade.result != "pending").count()
        grade_a_rate = (grade_a_wins / grade_a_total * 100) if grade_a_total > 0 else 0

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
            f"🅰️ أداء Grade A: {grade_a_rate:.0f}%\n"
            f"   ({grade_a_wins}/{grade_a_total} صفقات)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 نصيحة: ركّز على إشارات Grade A و B"
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
                msg += f"   {i}. {asset.asset}: {asset.win_rate:.0f}% ({asset.wins}W/{asset.losses}L)\n"
            msg += "\n"

        if worst:
            msg += "⚠️ الأسوأ أداءً:\n"
            for i, asset in enumerate(worst, 1):
                msg += f"   {i}. {asset.asset}: {asset.win_rate:.0f}% ({asset.wins}W/{asset.losses}L)\n"
            msg += "\n"

        if not best and not worst:
            msg += "لا توجد بيانات كافية بعد.\nسجّل نتائج صفقاتك لبناء الإحصائيات.\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━━\n💡 تجنب الأزواج ذات الأداء الضعيف"

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"خطأ في أداء الأزواج: {e}")
        await update.message.reply_text("❌ حدث خطأ.")


# ═══════════════════════════════════════════════════════════════
# أمر /settings - الإعدادات
# ═══════════════════════════════════════════════════════════════

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings = get_user_settings(user_id)

    if not user_settings:
        await update.message.reply_text("❌ خطأ في جلب الإعدادات")
        return

    keyboard = [
        [
            InlineKeyboardButton(f"التأكيدات: {user_settings.min_confirmations}", callback_data="conf_header"),
        ],
        [
            InlineKeyboardButton("6", callback_data="conf_6"),
            InlineKeyboardButton("7", callback_data="conf_7"),
            InlineKeyboardButton("8", callback_data="conf_8"),
            InlineKeyboardButton("9", callback_data="conf_9"),
            InlineKeyboardButton("10", callback_data="conf_10"),
        ],
        [
            InlineKeyboardButton(f"⏰ الفترة: {user_settings.signal_interval} دقائق", callback_data="int_header"),
        ],
        [
            InlineKeyboardButton("3 دق", callback_data="interval_3"),
            InlineKeyboardButton("5 دق", callback_data="interval_5"),
            InlineKeyboardButton("10 دق", callback_data="interval_10"),
            InlineKeyboardButton("15 دق", callback_data="interval_15"),
        ],
        [
            InlineKeyboardButton(f"💰 المخاطرة: {user_settings.risk_level}", callback_data="risk_header"),
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

    # تجاهل أزرار العناوين
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
            return  # لا نرسل تقرير إذا لم يكن هناك صفقات

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
            f"💡 نصيحة الغد: "
        )

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
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CommandHandler("history", get_history))
    app.add_handler(CommandHandler("stats", get_stats))
    app.add_handler(CommandHandler("performance", asset_performance))
    app.add_handler(CommandHandler("risk", risk_status))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("win", record_win))
    app.add_handler(CommandHandler("loss", record_loss))

    # معالج الأزرار
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("✅ البوت يعمل...")
    print("✅ البوت يعمل بنجاح!")
    print("📡 في انتظار الرسائل...")

    # تشغيل البوت
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
