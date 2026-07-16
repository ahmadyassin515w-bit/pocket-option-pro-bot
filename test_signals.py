import os
os.environ['TELEGRAM_BOT_TOKEN'] = 'test'

from data_provider import fetch_forex_data
from technical_analysis import calculate_all_indicators
from signals import generate_signal_for_asset, analyze_signal
from config import ASSETS_TO_MONITOR, MIN_CONFIRMATIONS
import pandas as pd

print(f'Config MIN_CONFIRMATIONS: {MIN_CONFIRMATIONS}')
print()

signals_found = 0
for asset in ASSETS_TO_MONITOR:
    symbol = asset['symbol']
    name = asset['name']
    df = fetch_forex_data(symbol, name)
    if df is None or df.empty or len(df) < 30:
        print(f'❌ {name}: No data')
        continue
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df_ta = calculate_all_indicators(df.copy())
    if df_ta is None or df_ta.empty:
        print(f'❌ {name}: TA failed')
        continue
    
    call_c, put_c, rc, rp = analyze_signal(df_ta)
    signal = generate_signal_for_asset(df_ta, min_conf_override=6)
    
    if signal:
        signals_found += 1
        print(f'✅ {name}: {signal["direction"]} {signal["grade_emoji"]} ({signal["confirmations"]}/12) - {", ".join(signal["reasons"][:4])}')
    else:
        print(f'⏸ {name}: CALL={call_c} PUT={put_c} (no signal)')

print(f'\n{"="*40}')
print(f'Total signals: {signals_found}/{len(ASSETS_TO_MONITOR)}')
