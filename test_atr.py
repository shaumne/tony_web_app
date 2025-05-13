import requests
import pandas as pd

def get_binance_ohlcv(symbol='BTCUSDT', interval='15m', limit=100):
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_atr(df, period=14):
    df['previous_close'] = df['close'].shift(1)
    df['tr'] = df[['high', 'low', 'previous_close']].apply(
        lambda x: max(
            x['high'] - x['low'],
            abs(x['high'] - x['previous_close']),
            abs(x['low'] - x['previous_close'])
        ), axis=1
    )
    # Wilder's ATR (RMA)
    df['ATR'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
    return df

def get_current_price(symbol='BTCUSDT'):
    """Get current market price"""
    url = 'https://api.binance.com/api/v3/ticker/price'
    params = {'symbol': symbol}
    response = requests.get(url, params=params)
    data = response.json()
    return float(data['price'])

def calculate_tp_sl(symbol='BTCUSDT', atr_period=14, atr_tp_multiplier=2.5, atr_sl_multiplier=3.0, position_type='long'):
    """Calculate TP/SL based on current price and ATR
    
    Args:
        symbol (str): Trading pair (e.g. 'BTCUSDT')
        atr_period (int): ATR calculation period
        atr_tp_multiplier (float): ATR multiplier for Take Profit
        atr_sl_multiplier (float): ATR multiplier for Stop Loss
        position_type (str): Position type ('long' or 'short')
        
    Returns:
        dict: Calculated values (entry, tp, sl, atr)
    """
    # Get OHLCV data
    df = get_binance_ohlcv(symbol, limit=atr_period+50)
    
    # Calculate ATR
    df = calculate_atr(df, atr_period)
    atr = df['ATR'].iloc[-1]
    
    # Get current price
    current_price = get_current_price(symbol)
    
    # Calculate TP/SL
    if position_type.lower() == 'long':
        tp_price = current_price + (atr * atr_tp_multiplier)
        sl_price = current_price - (atr * atr_sl_multiplier)
        tp_direction = "UP"
        sl_direction = "DOWN"
    else:  # short
        tp_price = current_price - (atr * atr_tp_multiplier)
        sl_price = current_price + (atr * atr_sl_multiplier)
        tp_direction = "DOWN"
        sl_direction = "UP"
    
    result = {
        'symbol': symbol,
        'position_type': position_type,
        'current_price': current_price,
        'atr': atr,
        'tp_price': tp_price,
        'sl_price': sl_price,
        'tp_distance': abs(tp_price - current_price),
        'sl_distance': abs(sl_price - current_price),
        'tp_percentage': (abs(tp_price - current_price) / current_price) * 100,
        'sl_percentage': (abs(sl_price - current_price) / current_price) * 100,
        'risk_reward_ratio': abs(tp_price - current_price) / abs(sl_price - current_price),
        'tp_direction': tp_direction,
        'sl_direction': sl_direction
    }
    
    return result

# Test
if __name__ == "__main__":
    # Test parameters
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    position_types = ['long', 'short']
    
    print("ATR-based TP/SL Calculation Test")
    print("="*50)
    
    for symbol in symbols:
        for position_type in position_types:
            print(f"\n{symbol} {position_type.upper()} position TP/SL:")
            print("-"*50)
            
            result = calculate_tp_sl(
                symbol=symbol,
                atr_period=14,
                atr_tp_multiplier=2.5,
                atr_sl_multiplier=3.0,
                position_type=position_type
            )
            
            print(f"Symbol: {result['symbol']}")
            print(f"Position Type: {result['position_type'].upper()}")
            print(f"Current Price: ${result['current_price']:.2f}")
            print(f"ATR(14): {result['atr']:.2f}")
            
            # TP with direction and percentage difference from current price
            tp_direction_sign = "+" if result['tp_direction'] == "UP" else "-"
            print(f"Take Profit: ${result['tp_price']:.2f} ({tp_direction_sign}{result['tp_percentage']:.2f}% from entry)")
            
            # SL with direction and percentage difference from current price
            sl_direction_sign = "+" if result['sl_direction'] == "UP" else "-"
            print(f"Stop Loss: ${result['sl_price']:.2f} ({sl_direction_sign}{result['sl_percentage']:.2f}% from entry)")
            
            print(f"Risk/Reward Ratio: {result['risk_reward_ratio']:.2f}")
    
    # Show ATR table for BTC only
    print("\n\nATR Values for BTCUSDT:")
    print("="*50)
    df = get_binance_ohlcv('BTCUSDT', limit=20)
    df = calculate_atr(df)
    # Format the dataframe for better display
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    df_display = df[['timestamp', 'close', 'tr', 'ATR']].tail(10)
    df_display['close'] = df_display['close'].map('${:.2f}'.format)
    df_display['tr'] = df_display['tr'].map('{:.2f}'.format)
    df_display['ATR'] = df_display['ATR'].map('{:.2f}'.format)
    print(df_display)
