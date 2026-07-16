"""
قاعدة البيانات - إدارة الصفقات والإعدادات والإحصائيات
"""

from peewee import (
    SqliteDatabase, PostgresqlDatabase, Model,
    DateTimeField, CharField, FloatField, IntegerField, BooleanField
)
import os
import datetime
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# إعداد قاعدة البيانات
# ═══════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    try:
        db = PostgresqlDatabase(DATABASE_URL)
        logger.info("متصل بـ PostgreSQL")
    except Exception as e:
        logger.warning(f"فشل الاتصال بـ PostgreSQL: {e}, استخدام SQLite")
        db = SqliteDatabase("trades.db")
else:
    db = SqliteDatabase("trades.db")


# ═══════════════════════════════════════════════════════════════
# النماذج (Models)
# ═══════════════════════════════════════════════════════════════

class BaseModel(Model):
    class Meta:
        database = db


class Trade(BaseModel):
    """سجل الصفقات"""
    user_id = IntegerField(default=0)
    asset = CharField()
    signal_type = CharField()  # CALL or PUT
    entry_price = FloatField(default=0)
    confirmations = IntegerField(default=0)
    grade = CharField(default="C")  # A, B, C
    reasons = CharField(default="")
    result = CharField(default="pending")  # pending, win, loss
    amount = FloatField(default=0)  # مبلغ الصفقة
    timestamp = DateTimeField(default=datetime.datetime.now)


class UserSettings(BaseModel):
    """إعدادات المستخدم"""
    user_id = IntegerField(unique=True)
    auto_signals = BooleanField(default=False)
    min_confirmations = IntegerField(default=6)
    max_trades_per_day = IntegerField(default=30)
    preferred_assets = CharField(default="all")  # all أو قائمة مفصولة بفاصلة
    signal_interval = IntegerField(default=5)  # بالدقائق
    risk_level = CharField(default="medium")  # low, medium, high
    capital = FloatField(default=100)  # رأس المال
    notifications = BooleanField(default=True)
    max_daily_loss = FloatField(default=15)  # نسبة الخسارة اليومية القصوى
    max_consecutive_losses = IntegerField(default=3)
    created_at = DateTimeField(default=datetime.datetime.now)


class DailyStats(BaseModel):
    """إحصائيات يومية"""
    user_id = IntegerField(default=0)
    date = CharField()
    total_signals = IntegerField(default=0)
    wins = IntegerField(default=0)
    losses = IntegerField(default=0)
    win_rate = FloatField(default=0)
    profit_loss = FloatField(default=0)  # الربح/الخسارة بالدولار
    consecutive_losses = IntegerField(default=0)
    is_stopped = BooleanField(default=False)  # هل تم إيقاف التداول اليوم

    class Meta:
        database = db
        indexes = (
            (('user_id', 'date'), True),  # unique together
        )


class AssetPerformance(BaseModel):
    """أداء كل زوج عملات"""
    asset = CharField()
    total_trades = IntegerField(default=0)
    wins = IntegerField(default=0)
    losses = IntegerField(default=0)
    win_rate = FloatField(default=0)
    last_updated = DateTimeField(default=datetime.datetime.now)


# ═══════════════════════════════════════════════════════════════
# دوال التهيئة
# ═══════════════════════════════════════════════════════════════

def initialize_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    try:
        db.connect(reuse_if_open=True)
        db.create_tables([Trade, UserSettings, DailyStats, AssetPerformance], safe=True)
        # تحديث إعدادات المستخدمين القدامى
        try:
            UserSettings.update(min_confirmations=6).where(
                UserSettings.min_confirmations > 6
            ).execute()
        except Exception:
            pass
        logger.info("✅ تم تهيئة قاعدة البيانات")
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")


# ═══════════════════════════════════════════════════════════════
# دوال إعدادات المستخدم
# ═══════════════════════════════════════════════════════════════

def get_user_settings(user_id):
    """جلب إعدادات المستخدم أو إنشاء إعدادات افتراضية"""
    try:
        settings, created = UserSettings.get_or_create(user_id=user_id)
        return settings
    except Exception as e:
        logger.error(f"خطأ في جلب الإعدادات: {e}")
        return None


def update_user_setting(user_id, field, value):
    """تحديث إعداد محدد للمستخدم"""
    try:
        settings = get_user_settings(user_id)
        if settings:
            setattr(settings, field, value)
            settings.save()
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث الإعداد: {e}")
    return False


# ═══════════════════════════════════════════════════════════════
# دوال الإحصائيات
# ═══════════════════════════════════════════════════════════════

def update_daily_stats(user_id, result, amount=0):
    """تحديث الإحصائيات اليومية"""
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        stats, created = DailyStats.get_or_create(
            user_id=user_id,
            date=today,
            defaults={'total_signals': 0, 'wins': 0, 'losses': 0}
        )

        stats.total_signals += 1

        if result == "win":
            stats.wins += 1
            stats.consecutive_losses = 0
            stats.profit_loss += amount
        elif result == "loss":
            stats.losses += 1
            stats.consecutive_losses += 1
            stats.profit_loss -= amount

        # حساب نسبة النجاح
        total_decided = stats.wins + stats.losses
        if total_decided > 0:
            stats.win_rate = (stats.wins / total_decided) * 100

        stats.save()
        return stats
    except Exception as e:
        logger.error(f"خطأ في تحديث الإحصائيات: {e}")
        return None


def get_daily_stats(user_id):
    """جلب إحصائيات اليوم"""
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        stats, created = DailyStats.get_or_create(
            user_id=user_id,
            date=today,
            defaults={'total_signals': 0, 'wins': 0, 'losses': 0}
        )
        return stats
    except Exception as e:
        logger.error(f"خطأ في جلب الإحصائيات: {e}")
        return None


def check_risk_limits(user_id):
    """
    فحص حدود المخاطرة - هل يجب إيقاف التداول؟
    
    Returns:
        dict مع حالة المخاطرة
    """
    try:
        settings = get_user_settings(user_id)
        stats = get_daily_stats(user_id)

        if not settings or not stats:
            return {"should_stop": False, "reason": ""}

        # فحص الخسائر المتتالية
        if stats.consecutive_losses >= settings.max_consecutive_losses:
            return {
                "should_stop": True,
                "reason": f"وصلت {stats.consecutive_losses} خسائر متتالية (الحد: {settings.max_consecutive_losses})"
            }

        # فحص نسبة الخسارة اليومية
        if settings.capital > 0:
            loss_pct = abs(min(stats.profit_loss, 0)) / settings.capital * 100
            if loss_pct >= settings.max_daily_loss:
                return {
                    "should_stop": True,
                    "reason": f"وصلت نسبة الخسارة اليومية {loss_pct:.1f}% (الحد: {settings.max_daily_loss}%)"
                }

        # فحص عدد الصفقات اليومية
        if stats.total_signals >= settings.max_trades_per_day:
            return {
                "should_stop": True,
                "reason": f"وصلت الحد الأقصى للصفقات اليومية ({settings.max_trades_per_day})"
            }

        return {"should_stop": False, "reason": ""}

    except Exception as e:
        logger.error(f"خطأ في فحص المخاطرة: {e}")
        return {"should_stop": False, "reason": ""}


# ═══════════════════════════════════════════════════════════════
# دوال أداء الأصول
# ═══════════════════════════════════════════════════════════════

def update_asset_performance(asset, result):
    """تحديث أداء زوج العملات"""
    try:
        perf, created = AssetPerformance.get_or_create(
            asset=asset,
            defaults={'total_trades': 0, 'wins': 0, 'losses': 0}
        )

        perf.total_trades += 1
        if result == "win":
            perf.wins += 1
        elif result == "loss":
            perf.losses += 1

        if perf.total_trades > 0:
            perf.win_rate = (perf.wins / perf.total_trades) * 100

        perf.last_updated = datetime.datetime.now()
        perf.save()
        return perf
    except Exception as e:
        logger.error(f"خطأ في تحديث أداء الأصل: {e}")
        return None


def get_best_performing_assets(limit=5):
    """جلب أفضل الأزواج أداءً"""
    try:
        assets = (AssetPerformance
                  .select()
                  .where(AssetPerformance.total_trades >= 5)
                  .order_by(AssetPerformance.win_rate.desc())
                  .limit(limit))
        return list(assets)
    except Exception as e:
        logger.error(f"خطأ في جلب أفضل الأصول: {e}")
        return []


def get_worst_performing_assets(limit=5):
    """جلب أسوأ الأزواج أداءً"""
    try:
        assets = (AssetPerformance
                  .select()
                  .where(AssetPerformance.total_trades >= 5)
                  .order_by(AssetPerformance.win_rate.asc())
                  .limit(limit))
        return list(assets)
    except Exception as e:
        logger.error(f"خطأ في جلب أسوأ الأصول: {e}")
        return []
