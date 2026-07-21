"""
مولّد الرسوم البيانية - شارت شموع احترافي مع المؤشرات
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import pandas as pd
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# إعدادات الرسم
plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#16213e'
plt.rcParams['axes.edgecolor'] = '#0f3460'
plt.rcParams['text.color'] = '#e0e0e0'
plt.rcParams['xtick.color'] = '#a0a0a0'
plt.rcParams['ytick.color'] = '#a0a0a0'
plt.rcParams['grid.color'] = '#0f3460'
plt.rcParams['grid.alpha'] = 0.3


def generate_chart(df, asset_name, signal_direction=None, entry_price=None, support=None, resistance=None, entry_time=None):
    """
    يولّد صورة شارت شموع احترافي مع المؤشرات
    
    Args:
        df: DataFrame مع بيانات OHLC والمؤشرات
        asset_name: اسم الزوج
        signal_direction: CALL أو PUT أو None
        entry_price: سعر الدخول
        support: مستوى الدعم
        resistance: مستوى المقاومة
    
    Returns:
        str: مسار ملف الصورة أو None
    """
    try:
        # أخذ آخر 50 شمعة
        chart_data = df.tail(50).copy()
        
        if len(chart_data) < 10:
            return None
        
        # إنشاء الرسم
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                         gridspec_kw={'height_ratios': [3, 1]},
                                         sharex=True)
        
        fig.patch.set_facecolor('#1a1a2e')
        
        # ═══ رسم الشموع ═══
        x = range(len(chart_data))
        
        for i, (idx, row) in enumerate(chart_data.iterrows()):
            open_price = float(row['Open'])
            close_price = float(row['Close'])
            high_price = float(row['High'])
            low_price = float(row['Low'])
            
            # لون الشمعة
            if close_price >= open_price:
                color = '#00e676'  # أخضر للصعود
                body_color = '#00e676'
            else:
                color = '#ff1744'  # أحمر للهبوط
                body_color = '#ff1744'
            
            # رسم الظل (الفتيل)
            ax1.plot([i, i], [low_price, high_price], color=color, linewidth=0.8)
            
            # رسم الجسم
            body_bottom = min(open_price, close_price)
            body_height = abs(close_price - open_price)
            
            if body_height == 0:
                body_height = (high_price - low_price) * 0.01
            
            rect = plt.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                facecolor=body_color, edgecolor=color, linewidth=0.5)
            ax1.add_patch(rect)
        
        # ═══ رسم EMA ═══
        if 'EMA_5' in chart_data.columns:
            ema5 = chart_data['EMA_5'].values
            ax1.plot(x, ema5, color='#ffeb3b', linewidth=1.2, label='EMA 5', alpha=0.9)
        
        if 'EMA_13' in chart_data.columns:
            ema13 = chart_data['EMA_13'].values
            ax1.plot(x, ema13, color='#ff9800', linewidth=1.2, label='EMA 13', alpha=0.9)
        
        if 'EMA_21' in chart_data.columns:
            ema21 = chart_data['EMA_21'].values
            ax1.plot(x, ema21, color='#e91e63', linewidth=1.2, label='EMA 21', alpha=0.9)
        
        # ═══ رسم مستويات الدعم والمقاومة ═══
        if support and support > 0:
            ax1.axhline(y=support, color='#00e676', linestyle='--', linewidth=1, alpha=0.7)
            ax1.text(len(chart_data) - 1, support, f' دعم {support:.5f}', 
                    color='#00e676', fontsize=8, va='bottom')
        
        if resistance and resistance > 0:
            ax1.axhline(y=resistance, color='#ff1744', linestyle='--', linewidth=1, alpha=0.7)
            ax1.text(len(chart_data) - 1, resistance, f' مقاومة {resistance:.5f}', 
                    color='#ff1744', fontsize=8, va='top')
        
        # ═══ سهم نقطة الدخول بالدقيقة ═══
        if signal_direction and entry_price:
            last_x = len(chart_data) - 1
            price_range = chart_data['High'].max() - chart_data['Low'].min()
            
            # وقت الدخول
            if entry_time:
                time_label = entry_time
            else:
                time_label = datetime.now().strftime('%H:%M')
            
            if signal_direction == "CALL":
                arrow_color = '#00e676'
                label = f'⬆ CALL\n🕓 {time_label}'
                ax1.annotate(label, xy=(last_x, entry_price),
                           xytext=(last_x - 5, entry_price - price_range * 0.15),
                           fontsize=11, fontweight='bold', color=arrow_color,
                           arrowprops=dict(arrowstyle='->', color=arrow_color, lw=2.5),
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a3a1a', edgecolor=arrow_color, alpha=0.8))
                # خط أفقي عند نقطة الدخول
                ax1.axhline(y=entry_price, color=arrow_color, linestyle=':', linewidth=1, alpha=0.6)
            else:
                arrow_color = '#ff1744'
                label = f'⬇ PUT\n🕓 {time_label}'
                ax1.annotate(label, xy=(last_x, entry_price),
                           xytext=(last_x - 5, entry_price + price_range * 0.15),
                           fontsize=11, fontweight='bold', color=arrow_color,
                           arrowprops=dict(arrowstyle='->', color=arrow_color, lw=2.5),
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='#3a1a1a', edgecolor=arrow_color, alpha=0.8))
                # خط أفقي عند نقطة الدخول
                ax1.axhline(y=entry_price, color=arrow_color, linestyle=':', linewidth=1, alpha=0.6)
        
        # ═══ إعدادات المحور الأول ═══
        ax1.set_title(f'📊 {asset_name} - M1', fontsize=14, fontweight='bold', 
                     color='#ffffff', pad=10)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.3)
        ax1.grid(True, alpha=0.2)
        ax1.set_ylabel('السعر', fontsize=10, color='#a0a0a0')
        
        # ═══ رسم RSI ═══
        if 'RSI' in chart_data.columns:
            rsi = chart_data['RSI'].values
            ax2.plot(x, rsi, color='#7c4dff', linewidth=1.5, label='RSI')
            ax2.axhline(y=70, color='#ff1744', linestyle='--', linewidth=0.8, alpha=0.5)
            ax2.axhline(y=30, color='#00e676', linestyle='--', linewidth=0.8, alpha=0.5)
            ax2.axhline(y=50, color='#ffffff', linestyle='-', linewidth=0.3, alpha=0.3)
            ax2.fill_between(x, 70, 100, alpha=0.1, color='#ff1744')
            ax2.fill_between(x, 0, 30, alpha=0.1, color='#00e676')
            ax2.set_ylim(0, 100)
            ax2.set_ylabel('RSI', fontsize=10, color='#a0a0a0')
            ax2.legend(loc='upper left', fontsize=9, framealpha=0.3)
            ax2.grid(True, alpha=0.2)
        
        # ═══ تنسيق المحور X ═══
        # عرض بعض التواريخ
        tick_positions = list(range(0, len(chart_data), max(1, len(chart_data) // 8)))
        tick_labels = []
        for pos in tick_positions:
            if pos < len(chart_data):
                idx = chart_data.index[pos]
                if hasattr(idx, 'strftime'):
                    tick_labels.append(idx.strftime('%H:%M'))
                else:
                    tick_labels.append(str(pos))
            else:
                tick_labels.append('')
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, fontsize=8)
        
        # ═══ إضافة معلومات ═══
        now = datetime.now()
        info_text = f"Pocket Option Pro Bot | {now.strftime('%Y-%m-%d %H:%M')}"
        fig.text(0.5, 0.01, info_text, ha='center', fontsize=8, color='#666666')
        
        plt.tight_layout()
        
        # حفظ الصورة
        chart_path = f"/tmp/chart_{asset_name.replace('/', '_')}_{now.strftime('%H%M%S')}.png"
        fig.savefig(chart_path, dpi=120, bbox_inches='tight', 
                   facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        
        return chart_path
        
    except Exception as e:
        logger.error(f"خطأ في توليد الشارت: {e}")
        plt.close('all')
        return None


def generate_quick_chart(df, asset_name):
    """
    شارت سريع بدون إشارة - فقط الشموع والمؤشرات
    """
    return generate_chart(df, asset_name)
