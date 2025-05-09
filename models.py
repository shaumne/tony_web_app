from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username, is_admin=False):
        self.id = username
        self.username = username
        self.is_admin = is_admin

class Config:
    def __init__(self, **kwargs):
        self.bitget_api_key = kwargs.get('bitget_api_key', '')
        self.bitget_secret_key = kwargs.get('bitget_secret_key', '')
        self.bitget_passphrase = kwargs.get('bitget_passphrase', '')
        self.telegram_bot_token = kwargs.get('telegram_bot_token', '')
        self.telegram_chat_id = kwargs.get('telegram_chat_id', '')
        self.leverage = kwargs.get('leverage', 5)
        self.order_size_percentage = kwargs.get('order_size_percentage', 10)
        self.max_daily_trades = kwargs.get('max_daily_trades', 10)
        self.max_open_positions = kwargs.get('max_open_positions', 10)
        self.enable_trading = kwargs.get('enable_trading', True)
        self.enable_tp_sl = kwargs.get('enable_tp_sl', False)
        self.enable_webhook_close_signals = kwargs.get('enable_webhook_close_signals', False)
        self.atr_period = kwargs.get('atr_period', 14)
        self.atr_tp_multiplier = kwargs.get('atr_tp_multiplier', 2.5)
        self.atr_sl_multiplier = kwargs.get('atr_sl_multiplier', 3.0)

class Position:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.symbol = kwargs.get('symbol', '')
        self.direction = kwargs.get('direction', '')
        self.size = kwargs.get('size', '0')
        self.entry_price = kwargs.get('entry_price', '0')
        self.exit_price = kwargs.get('exit_price', '0')
        self.open_time = kwargs.get('open_time', '')
        self.close_time = kwargs.get('close_time', '')
        self.closed = kwargs.get('closed', False)
        
    def calculate_pnl(self):
        if not self.closed:
            return 0
            
        entry = float(self.entry_price)
        exit_price = float(self.exit_price)
        size = float(self.size)
        
        if self.direction == 'long':
            return (exit_price - entry) * size
        else:  # short
            return (entry - exit_price) * size 