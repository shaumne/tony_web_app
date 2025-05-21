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
        self.enable_webhook_close_signals = kwargs.get('enable_webhook_close_signals', False)
        self.atr_period = kwargs.get('atr_period', 14)
        self.atr_tp_multiplier = kwargs.get('atr_tp_multiplier', 2.5)
        self.atr_sl_multiplier = kwargs.get('atr_sl_multiplier', 3.0)
        self.auto_position_switch = kwargs.get('auto_position_switch', True)

    def to_dict(self):
        return {
            'bitget_api_key': self.bitget_api_key,
            'bitget_secret_key': self.bitget_secret_key,
            'bitget_passphrase': self.bitget_passphrase,
            'telegram_bot_token': self.telegram_bot_token,
            'telegram_chat_id': self.telegram_chat_id,
            'leverage': self.leverage,
            'order_size_percentage': self.order_size_percentage,
            'max_daily_trades': self.max_daily_trades,
            'max_open_positions': self.max_open_positions,
            'enable_trading': self.enable_trading,
            'enable_webhook_close_signals': self.enable_webhook_close_signals,
            'atr_period': self.atr_period,
            'atr_tp_multiplier': self.atr_tp_multiplier,
            'atr_sl_multiplier': self.atr_sl_multiplier,
            'auto_position_switch': self.auto_position_switch
        }
        
    @staticmethod
    def from_dict(data):
        return Config(**data)

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