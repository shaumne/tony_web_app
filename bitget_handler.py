import bitget.v1.mix.order_api as order_api
import bitget.v1.mix.account_api as account_api
import bitget.v1.mix.market_api as market_api
from bitget.exceptions import BitgetAPIException
from bitget.bitget_api import BitgetApi
import logging
import time
from datetime import datetime
import asyncio
import requests
import pandas as pd

logger = logging.getLogger(__name__)

class BitgetHandler:
    """Handler class for Bitget API operations"""
    
    def __init__(self, api_key, secret_key, passphrase, config):
        """Initialize Bitget API client
        
        Args:
            api_key (str): Bitget API key
            secret_key (str): Bitget API secret key
            passphrase (str): Bitget API passphrase
            config (dict): Configuration dictionary
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # Eğer config bir dict değilse, nesne özelliklerini dict'e dönüştür
        if hasattr(config, '__dict__'):
            self.config = config.__dict__
        else:
            self.config = config
        
        # Config değerlerini logla
        logger.info(f"Initialized with config: leverage={self.config.get('leverage', 'not set')}, order_size_percentage={self.config.get('order_size_percentage', 'not set')}")
        
        # Initialize API clients
        self.order_api = order_api.OrderApi(api_key, secret_key, passphrase)
        self.account_api = account_api.AccountApi(api_key, secret_key, passphrase)
        self.market_api = market_api.MarketApi(api_key, secret_key, passphrase)
        self.base_api = BitgetApi(api_key, secret_key, passphrase)
        
        # Store last known position states
        self.last_position_states = {}
        
        logger.info("Bitget handler initialized")
    
    def get_account_balance(self, coin='USDT'):
        """Get account balance and details for specified coin
        
        Args:
            coin (str): Coin symbol, default is USDT
            
        Returns:
            tuple: (balance, equity, unrealized_pnl)
        """
        try:
            # Try to get account details using different endpoints
            try:
                # First try the account details endpoint
                params = {
                    "symbol": "BTCUSDT_UMCBL",
                    "marginCoin": "USDT"
                }
                response = self.base_api.get("/api/mix/v1/account/account", params)
                logger.info(f"Account API response: {response}")
                
                if response and 'data' in response:
                    data = response['data']
                    available = float(data.get('available', '0'))
                    equity = float(data.get('equity', '0'))
                    unrealized_pnl = float(data.get('unrealizedPL', '0'))
                    logger.info(f"Account details - Available: {available}, Equity: {equity}, Unrealized PnL: {unrealized_pnl}")
                    return available, equity, unrealized_pnl
            except Exception as e:
                logger.error(f"Error getting account details: {str(e)}")
            
            # If first attempt fails, try the simpler balance endpoint
            try:
                params = {"productType": "umcbl", "marginCoin": "USDT"}
                response = self.base_api.get("/api/mix/v1/account/accounts", params)
                logger.info(f"Balance API response: {response}")
                
                if response and 'data' in response:
                    for account in response['data']:
                        if account.get('marginCoin') == coin:
                            available = float(account.get('available', '0'))
                            equity = float(account.get('equity', '0'))
                            unrealized_pnl = float(account.get('unrealizedPL', '0'))
                            logger.info(f"Account details - Available: {available}, Equity: {equity}, Unrealized PnL: {unrealized_pnl}")
                            return available, equity, unrealized_pnl
            except Exception as e:
                logger.error(f"Error getting account balance: {str(e)}")
            
            # If both attempts fail, return zeros
            logger.warning("Could not get account details, returning zeros")
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 0.0, 0.0, 0.0
    
    def get_symbol_price(self, symbol):
        """Get current price for the symbol
        
        Args:
            symbol (str): Trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            float: Current price
        """
        try:
            # Format symbol to Bitget format if needed
            if not symbol.endswith('_UMCBL'):
                formatted_symbol = f"{symbol}_UMCBL"
            else:
                formatted_symbol = symbol
            
            logger.info(f"Getting price for formatted symbol: {formatted_symbol}")
            
            # Doğru parametre formatı: dict olmalı, string değil
            params = {"symbol": formatted_symbol}
            
            try:
                # Ticker metodunu kullanalım
                response = self.market_api.ticker(params)
                logger.debug(f"Ticker response: {response}")
                
                if response and 'data' in response:
                    price = float(response['data'].get('last', 0))
                    logger.info(f"Current price for {formatted_symbol}: {price}")
                    return price
                else:
                    # Fiyat alınamadıysa, alternatif bir endpoint deneyelim
                    try:
                        logger.info(f"Trying alternative endpoint for price")
                        alt_params = {"symbol": formatted_symbol}
                        alt_response = self.base_api.get("/api/mix/v1/market/ticker", alt_params)
                        logger.debug(f"Alternative ticker response: {alt_response}")
                        
                        if alt_response and 'data' in alt_response:
                            price = float(alt_response['data'].get('last', 0))
                            logger.info(f"Alternative price for {formatted_symbol}: {price}")
                            return price
                    except Exception as alt_e:
                        logger.error(f"Alternative price endpoint failed: {str(alt_e)}")
                    
                    # Yine başarısız olursa sabit değer kullan
                    logger.warning(f"Using fixed price for {formatted_symbol}: 45000")
                    return 45000.0
            except Exception as e:
                logger.error(f"Failed to get ticker: {str(e)}")
                logger.warning(f"Using fixed price for {symbol}: 45000")
                return 45000.0  # Test için sabit bir değer
        except Exception as e:
            logger.error(f"Failed to get symbol price: {str(e)}")
            logger.warning(f"Using fixed price for {symbol}: 45000")
            return 45000.0  # Test için sabit bir değer
    
    def place_order(self, symbol, side, order_type="market", close_size=None):
        """Place an order on Bitget
        
        Args:
            symbol (str): Trading pair symbol (e.g. 'BTCUSDT')
            side (str): Order side (open_long, open_short, close_long, close_short)
            order_type (str): Order type (market, limit)
            close_size (str, optional): Specific size to close, used for closing positions
        """
        try:
            # Format symbol to Bitget format if needed
            if not symbol.endswith('_UMCBL'):
                formatted_symbol = f"{symbol}_UMCBL"
            else:
                formatted_symbol = symbol
            
            logger.info(f"Placing order with formatted symbol: {formatted_symbol}")
            
            # If this is a close order and we have a specific size, use it
            if side.startswith("close_") and close_size:
                size = close_size
                logger.info(f"Using provided size for closing position: {size}")
            else:
                # Her işlem öncesi bakiyeyi yeniden al - önbelleklenmiş değer kullanma
                # Önce mevcut pozisyonları temizle
                self.last_position_states = {}
                
                # Bakiyeyi yeniden al
                balance, _, _ = self.get_account_balance('USDT')
                logger.info(f"Fresh account balance: {balance} USDT")
                
                if isinstance(balance, (int, float)) and balance <= 0:
                    logger.warning("Using dummy balance for testing: 1000 USDT")
                    balance = 1000.0
                
                order_size_percentage = self.config.get('order_size_percentage', 10)
                if not isinstance(order_size_percentage, (int, float)):
                    try:
                        order_size_percentage = float(order_size_percentage)
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid order_size_percentage value: {order_size_percentage}, using default 10%")
                        order_size_percentage = 10.0
                
                # Calculate exact order amount (this is what user wants to trade)
                order_amount = balance * (order_size_percentage / 100)
                logger.info(f"Order calculation:")
                logger.info(f"Balance: ${balance} USDT")
                logger.info(f"Order Size: {order_size_percentage}%")
                logger.info(f"Order Amount: ${order_amount} USDT")
                
                # Get current price
                current_price = self.get_symbol_price(symbol)
                logger.info(f"Current price for {symbol}: {current_price}")
                
                if current_price <= 0:
                    logger.warning("Using dummy price for BTC: 45000")
                    current_price = 45000.0
                    
                # Set leverage
                leverage = self.config.get('leverage', 5)
                if not isinstance(leverage, (int, float)):
                    try:
                        leverage = int(float(leverage))
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid leverage value: {leverage}, using default 5x")
                        leverage = 5
                
                # Apply leverage to order amount
                leveraged_amount = order_amount * leverage
                logger.info(f"Leveraged amount (with {leverage}x): ${leveraged_amount} USDT")
                
                # Calculate size in BTC (or other coin) with leveraged amount
                size = leveraged_amount / current_price
                logger.info(f"Final size for {symbol}: {size} (${leveraged_amount} USDT with {leverage}x leverage)")
            
            # Set leverage
            try:
                for hold_side in ['long', 'short']:
                    leverage_params = {
                        "symbol": formatted_symbol,
                        "marginCoin": "USDT",
                        "leverage": str(leverage),
                        "holdSide": hold_side
                    }
                    leverage_response = self.base_api.post("/api/mix/v1/account/setLeverage", leverage_params)
                    logger.info(f"Leverage {leverage}x set for {hold_side} side: {leverage_response}")
            except Exception as le:
                logger.warning(f"Error setting leverage: {str(le)}")
                logger.warning(f"Continuing without setting leverage. Will use the existing leverage setting.")
            
            # Ana emir parametreleri
            params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "size": str(size),
                "orderType": "market",  # Market emri
                "timeInForceValue": "normal",  # Normal zaman aşımı
                "reduceOnly": False,  # Sadece azaltma değil
                "postOnly": False,  # Sadece maker değil
                "triggerPrice": "",  # Tetikleme fiyatı (boş)
                "triggerType": "market_price",  # Piyasa fiyatı tetikleme
                "clientOid": str(int(time.time() * 1000))  # Benzersiz emir ID'si
            }
            
            # Add side parameter based on the action
            if side == "open_long":
                params["side"] = "open_long"
            elif side == "open_short":
                params["side"] = "open_short"
            elif side == "close_long":
                params["side"] = "close_long"
            elif side == "close_short":
                params["side"] = "close_short"
            
            # TP/SL değerlerini ana emirde ekle (sadece pozisyon açma emirleri için)
            if side.startswith("open_"):
                try:
                    atr_period = int(self.config.get('atr_period', 14))
                    atr_tp_multiplier = float(self.config.get('atr_tp_multiplier', 2.5))
                    atr_sl_multiplier = float(self.config.get('atr_sl_multiplier', 3.0))
                    atr = self.get_atr(formatted_symbol, atr_period)
                    if side == "open_long":
                        tp_price = current_price + (atr * atr_tp_multiplier)
                        sl_price = current_price - (atr * atr_sl_multiplier)
                    else:  # open_short
                        tp_price = current_price - (atr * atr_tp_multiplier)
                        sl_price = current_price + (atr * atr_sl_multiplier)
                    
                    # Fiyatları 0.1'in katı olacak şekilde yuvarla
                    tp_price = round(tp_price * 10) / 10
                    sl_price = round(sl_price * 10) / 10
                    
                    logger.info(f"ATR tabanlı TP/SL: TP={tp_price}, SL={sl_price}, ATR={atr}")
                    
                    # Bitget API'sine uygun TP/SL parametreleri
                    params["presetTakeProfitPrice"] = str(tp_price)
                    params["presetStopLossPrice"] = str(sl_price)
                    
                    logger.info(f"TP/SL parametreleri eklendi: {params}")
                except Exception as e:
                    logger.error(f"ATR tabanlı TP/SL hesaplanamadı: {str(e)}")
                    import traceback
                    logger.error(f"TP/SL hata detayları: {traceback.format_exc()}")
            
            logger.info(f"Placing {side} order for {formatted_symbol}, size: {size}, params: {params}")
            
            try:
                # Ana emri gönder
                response = self.base_api.post("/api/mix/v1/order/placeOrder", params)
                logger.info(f"Main order placed successfully: {response}")
                
                # Telegram bildirimi için mesaj oluştur
                if side.startswith("open_"):
                    # Response'dan size bilgisini al, yoksa params'dan kullan
                    order_size = params.get('size', '0')
                    
                    # Tek bir bildirim mesajı oluştur - hem emir hem pozisyon bilgilerini içeren
                    message = (
                        f"🔔 New {side.replace('open_', '').upper()} position opened\n"
                        f"Symbol: {formatted_symbol.replace('_UMCBL', '')}\n"
                        f"Entry Price: ${current_price:.2f}\n"
                        f"Size: {order_size}\n"
                        f"Order ID: {response['data']['orderId']}\n"
                    )
                    
                    # TP/SL bilgilerini ekle
                    if self.config.get('enable_tp_sl', False):
                        if side == "open_long":
                            tp_percentage = float(self.config.get('long_take_profit_percentage', 2.5))
                            sl_percentage = float(self.config.get('long_stop_loss_percentage', 1.5))
                            tp_price = round(current_price * (1 + tp_percentage / 100) * 10) / 10
                            sl_price = round(current_price * (1 - sl_percentage / 100) * 10) / 10
                            message += (
                                f"Take Profit: ${tp_price:.1f} (+{tp_percentage}%)\n"
                                f"Stop Loss: ${sl_price:.1f} (-{sl_percentage}%)"
                            )
                        else:  # open_short
                            tp_percentage = float(self.config.get('short_take_profit_percentage', 2.5))
                            sl_percentage = float(self.config.get('short_stop_loss_percentage', 1.5))
                            tp_price = round(current_price * (1 - tp_percentage / 100) * 10) / 10
                            sl_price = round(current_price * (1 + sl_percentage / 100) * 10) / 10
                            message += (
                                f"Take Profit: ${tp_price:.1f} (-{tp_percentage}%)\n"
                                f"Stop Loss: ${sl_price:.1f} (+{sl_percentage}%)"
                            )

                    # Tek bildirim gönder
                    asyncio.run(self.send_telegram_notification(message))

                return response
            except BitgetAPIException as be:
                logger.error(f"Bitget API error: {str(be)}")
                # API hata kodlarını kontrol et
                if hasattr(be, 'code') and be.code:
                    logger.error(f"Bitget error code: {be.code}")
                    if be.code == '40010':
                        logger.error("Insufficient balance error")
                    elif be.code == '40003':
                        logger.error("Invalid parameter error")
                    elif be.code == '45115':
                        logger.error("Price format error - should be multiple of 0.1")
                        # Market emri deneyelim
                        logger.info("Trying with market order instead...")
                        params["orderType"] = "market"
                        if "price" in params:
                            del params["price"]
                        try:
                            response = self.base_api.post("/api/mix/v1/order/placeOrder", params)
                            logger.info(f"Market order placed successfully: {response}")
                            return response
                        except Exception as me:
                            logger.error(f"Market order also failed: {str(me)}")
                
                # Telegram ile hata bildir
                error_message = f"❌ Bitget API error: {str(be)}"
                asyncio.run(self.send_telegram_notification(error_message))
                return {"error": str(be)}
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            import traceback
            logger.error(f"Order placement error details: {traceback.format_exc()}")
            # Telegram ile hata bildir
            error_message = f"❌ Order error: {str(e)}"
            try:
                asyncio.run(self.send_telegram_notification(error_message))
            except:
                pass
            return {"error": str(e)}
    
    def get_open_positions(self):
        """Get all open positions
        
        Returns:
            list: List of open positions
        """
        try:
            # Try different endpoints to get positions
            endpoints = [
                {
                    "path": "/api/mix/v1/position/allPosition",
                    "params": {"productType": "umcbl", "marginCoin": "USDT"}
                },
                {
                    "path": "/api/mix/v1/position/singlePosition",
                    "params": {"symbol": "BTCUSDT_UMCBL", "marginCoin": "USDT"}
                },
                {
                    "path": "/api/mix/v1/position/holds",
                    "params": {"productType": "umcbl", "marginCoin": "USDT"}
                }
            ]
            
            for endpoint in endpoints:
                try:
                    logger.info(f"Trying endpoint: {endpoint['path']} with params: {endpoint['params']}")
                    response = self.base_api.get(endpoint['path'], endpoint['params'])
                    logger.info(f"Raw position API response from {endpoint['path']}: {response}")
                    
                    if response and 'data' in response and response['data']:
                        # Convert single position response to list if needed
                        positions_data = response['data']
                        if not isinstance(positions_data, list):
                            positions_data = [positions_data]
                        
                        # Filter out positions with zero size and log details
                        positions = []
                        for pos in positions_data:
                            total_size = float(pos.get('total', '0'))
                            logger.info(f"Processing position: Symbol={pos.get('symbol')}, Size={total_size}, Side={pos.get('holdSide')}")
                            if total_size > 0:
                                positions.append(pos)
                        
                        if positions:
                            logger.info(f"Found {len(positions)} active positions using endpoint {endpoint['path']}")
                            return positions
                        else:
                            logger.info(f"No active positions found using endpoint {endpoint['path']}")
                    
                except Exception as e:
                    logger.error(f"Error with endpoint {endpoint['path']}: {str(e)}")
                    continue
            
            logger.warning("No positions found using any endpoint")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get open positions: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def send_telegram_notification(self, message):
        """Send notification to Telegram
        
        Args:
            message (str): Message to send
        """
        if self.config.get('telegram_bot_token') and self.config.get('telegram_chat_id'):
            try:
                from telegram import Bot
                bot = Bot(token=self.config['telegram_bot_token'])
                
                # Format chat_id
                chat_id = self.config['telegram_chat_id']
                
                # If chat_id is numeric
                if chat_id.isdigit():
                    # Group IDs need to be negative
                    if chat_id.startswith("100"):
                        chat_id = "-" + chat_id
                        logger.info(f"Converting group ID to negative: {chat_id}")
                
                logger.info(f"Sending telegram notification with chat_id: {chat_id}")
                await bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Telegram notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {str(e)}")
                import traceback
                logger.error(f"Telegram error details: {traceback.format_exc()}")
                logger.error(f"Please check your Telegram settings. Bot token: {self.config['telegram_bot_token'][:5]}... and Chat ID: {self.config['telegram_chat_id']}")
                logger.error("Make sure you have messaged your bot once or added it to your group.")

    def monitor_positions(self):
        """Continuously monitor open positions and update dashboard"""
        # İlk çalıştırmada pozisyonları yükle
        try:
            initial_positions = self.get_open_positions()
            for pos in initial_positions:
                pos_id = pos.get('positionId')
                if pos_id:
                    self.last_position_states[pos_id] = pos
            logger.info(f"Initialized position monitor with {len(initial_positions)} positions")
        except Exception as e:
            logger.error(f"Error initializing position monitor: {str(e)}")
        
        while True:
            try:
                # Önceki pozisyonları sakla
                previous_positions = {}
                for pos_id, pos in self.last_position_states.items():
                    previous_positions[pos_id] = pos
                
                # Güncel pozisyonları al
                current_positions = self.get_open_positions()
                
                # Güncel pozisyon ID'lerini topla
                current_position_ids = set()
                current_symbols = set()
                for pos in current_positions:
                    pos_id = pos.get('positionId')
                    symbol = pos.get('symbol', '')
                    if pos_id:
                        current_position_ids.add(pos_id)
                        current_symbols.add(symbol)
                        self.last_position_states[pos_id] = pos
                
                # Kapanan pozisyonları kontrol et (önceki pozisyonlarda var ama güncel pozisyonlarda yok)
                for pos_id, pos in previous_positions.items():
                    if pos_id not in current_position_ids:
                        # Pozisyon kapanmış, bildirim gönder
                        symbol = pos.get('symbol', '').replace('_UMCBL', '')
                        side = pos.get('holdSide', '').lower()
                        entry_price = float(pos.get('averageOpenPrice', '0'))
                        size = float(pos.get('total', '0'))
                        
                        # Pozisyon kapanma nedenini tahmin et
                        reason = "Unknown"
                        if float(pos.get('unrealizedPL', '0')) > 0:
                            reason = "Manual Close or Take Profit"
                        elif float(pos.get('unrealizedPL', '0')) < 0:
                            reason = "Manual Close or Stop Loss"
                        else:
                            reason = "Position Closed"
                        
                        # Güncel fiyatı al
                        try:
                            current_price = self.get_symbol_price(symbol)
                        except:
                            current_price = 0
                        
                        # Pozisyon kapanma bildirimini gönder
                        message = (
                            f"📊 Position Closed\n"
                            f"Symbol: {symbol}\n"
                            f"Direction: {side.upper()}\n"
                            f"Entry Price: ${entry_price:.2f}\n"
                            f"Close Price: ${current_price:.2f}\n"
                            f"Size: {size:.4f}\n"
                            f"Reason: {reason}\n"
                            f"Position ID: {pos_id}"
                        )
                        logger.info(f"Position closed: {symbol} {side} {size}")
                        asyncio.run(self.send_telegram_notification(message))
                        
                        # Kapanan pozisyonu son durumlardan kaldır
                        if pos_id in self.last_position_states:
                            del self.last_position_states[pos_id]
                
                # Check for TP/SL triggers by comparing with last known states
                for pos in current_positions:
                    pos_id = pos.get('positionId')
                    symbol = pos.get('symbol', '').replace('_UMCBL', '')
                    current_price = float(pos.get('marketPrice', '0'))
                    side = pos.get('holdSide', '').lower()
                    
                    # Get last known state
                    last_state = previous_positions.get(pos_id, {})
                    last_price = float(last_state.get('marketPrice', '0'))
                    
                    if last_price > 0 and current_price > 0:
                        # Check if TP was hit
                        if side == 'long' and current_price >= float(pos.get('presetTakeProfitPrice', '0')) > 0:
                            entry_price = float(pos.get('averageOpenPrice', '0'))
                            tp_price = float(pos.get('presetTakeProfitPrice', '0'))
                            unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                            size = float(pos.get('total', '0'))
                            
                            # Kar yüzdesini hesapla
                            profit_percentage = ((tp_price - entry_price) / entry_price) * 100
                            
                            message = (
                                f"🎯 Take Profit Triggered!\n"
                                f"Symbol: {symbol}\n"
                                f"Direction: {side.upper()}\n"
                                f"Entry Price: ${entry_price:.2f}\n"
                                f"TP Price: ${tp_price:.2f}\n"
                                f"Profit: ${unrealized_pnl:.2f} (+{profit_percentage:.2f}%)\n"
                                f"Size: {size:.4f}\n"
                                f"Reason: Automatic Take Profit"
                            )
                            asyncio.run(self.send_telegram_notification(message))
                            
                        elif side == 'short' and current_price <= float(pos.get('presetTakeProfitPrice', '0')) > 0:
                            entry_price = float(pos.get('averageOpenPrice', '0'))
                            tp_price = float(pos.get('presetTakeProfitPrice', '0'))
                            unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                            size = float(pos.get('total', '0'))
                            
                            # Kar yüzdesini hesapla
                            profit_percentage = ((entry_price - tp_price) / entry_price) * 100
                            
                            message = (
                                f"🎯 Take Profit Triggered!\n"
                                f"Symbol: {symbol}\n"
                                f"Direction: {side.upper()}\n"
                                f"Entry Price: ${entry_price:.2f}\n"
                                f"TP Price: ${tp_price:.2f}\n"
                                f"Profit: ${unrealized_pnl:.2f} (+{profit_percentage:.2f}%)\n"
                                f"Size: {size:.4f}\n"
                                f"Reason: Automatic Take Profit"
                            )
                            asyncio.run(self.send_telegram_notification(message))
                            
                        # Check if SL was hit
                        if side == 'long' and current_price <= float(pos.get('presetStopLossPrice', '0')) > 0:
                            entry_price = float(pos.get('averageOpenPrice', '0'))
                            sl_price = float(pos.get('presetStopLossPrice', '0'))
                            unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                            size = float(pos.get('total', '0'))
                            
                            # Zarar yüzdesini hesapla
                            loss_percentage = ((entry_price - sl_price) / entry_price) * 100
                            
                            message = (
                                f"🛑 Stop Loss Triggered!\n"
                                f"Symbol: {symbol}\n"
                                f"Direction: {side.upper()}\n"
                                f"Entry Price: ${entry_price:.2f}\n"
                                f"SL Price: ${sl_price:.2f}\n"
                                f"Loss: ${unrealized_pnl:.2f} (-{loss_percentage:.2f}%)\n"
                                f"Size: {size:.4f}\n"
                                f"Reason: Automatic Stop Loss"
                            )
                            asyncio.run(self.send_telegram_notification(message))
                            
                        elif side == 'short' and current_price >= float(pos.get('presetStopLossPrice', '0')) > 0:
                            entry_price = float(pos.get('averageOpenPrice', '0'))
                            sl_price = float(pos.get('presetStopLossPrice', '0'))
                            unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                            size = float(pos.get('total', '0'))
                            
                            # Zarar yüzdesini hesapla
                            loss_percentage = ((sl_price - entry_price) / entry_price) * 100
                            
                            message = (
                                f"🛑 Stop Loss Triggered!\n"
                                f"Symbol: {symbol}\n"
                                f"Direction: {side.upper()}\n"
                                f"Entry Price: ${entry_price:.2f}\n"
                                f"SL Price: ${sl_price:.2f}\n"
                                f"Loss: ${unrealized_pnl:.2f} (-{loss_percentage:.2f}%)\n"
                                f"Size: {size:.4f}\n"
                                f"Reason: Automatic Stop Loss"
                            )
                            asyncio.run(self.send_telegram_notification(message))
                    
                # Update positions in database or state management
                self.update_dashboard_positions(current_positions)
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                time.sleep(5)  # Wait before retrying

    def update_dashboard_positions(self, positions):
        """Update dashboard with current position information"""
        try:
            logger.info(f"Starting to format {len(positions)} positions for dashboard")
            formatted_positions = []
            
            for pos in positions:
                try:
                    # Log raw position data
                    logger.info(f"Processing position data: {pos}")
                    
                    # Basic position data
                    size = float(pos.get('total', '0'))
                    if size <= 0:
                        logger.warning(f"Skipping position with zero size: {pos.get('symbol')}")
                        continue
                    
                    entry_price = float(pos.get('averageOpenPrice', '0'))
                    current_price = float(pos.get('marketPrice', '0'))
                    unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                    
                    # PNL calculation
                    if entry_price > 0:
                        if pos.get('holdSide', '').lower() == 'long':
                            pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                        else:  # short position
                            pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                    else:
                        pnl_percentage = 0
                    
                    # Position value calculation
                    position_value = size * current_price
                    
                    # Liquidation price calculation
                    leverage = float(pos.get('leverage', '5'))
                    margin = position_value / leverage
                    maintenance_margin = float(pos.get('keepMarginRate', '0.004')) * position_value
                    
                    if pos.get('holdSide', '').lower() == 'long':
                        liquidation_price = entry_price * (1 - (1 / leverage) + maintenance_margin/position_value)
                    else:
                        liquidation_price = entry_price * (1 + (1 / leverage) - maintenance_margin/position_value)
                    
                    # Margin ratio calculation
                    margin_ratio = (maintenance_margin / margin) * 100 if margin > 0 else 0
                    
                    # Format position data
                    formatted_pos = {
                        'id': pos.get('positionId', ''),
                        'symbol': pos.get('symbol', '').replace('_UMCBL', ''),
                        'size': f"{size:.4f}",
                        'entry_price': f"${entry_price:.2f}",
                        'current_price': f"${current_price:.2f}",
                        'unrealized_pnl': f"${unrealized_pnl:.2f}",
                        'pnl_percentage': f"{pnl_percentage:.2f}%",
                        'position_value': f"${position_value:.2f}",
                        'side': pos.get('holdSide', '').upper(),
                        'leverage': f"{leverage}x",
                        'liquidation_price': f"${liquidation_price:.2f}",
                        'margin_mode': pos.get('marginMode', 'FIXED').upper(),
                        'margin_ratio': f"{margin_ratio:.2f}%",
                        'created_time': datetime.fromtimestamp(int(pos.get('cTime', '0'))/1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'achieved_profits': f"${float(pos.get('achievedProfits', '0')):.2f}",
                        'keep_margin_rate': f"{float(pos.get('keepMarginRate', '0.004'))*100:.3f}%"
                    }
                    
                    logger.info(f"Successfully formatted position: {formatted_pos['symbol']} {formatted_pos['side']} {formatted_pos['size']}")
                    formatted_positions.append(formatted_pos)
                except Exception as e:
                    logger.error(f"Error formatting individual position: {str(e)}")
                    logger.error(f"Problematic position data: {pos}")
                    continue
            
            # Sort positions by PNL
            if formatted_positions:
                formatted_positions.sort(key=lambda x: float(x['unrealized_pnl'].replace('$', '').replace(',', '')), reverse=True)
                logger.info(f"Successfully formatted {len(formatted_positions)} positions")
            else:
                logger.warning("No positions were formatted successfully")
            
            return formatted_positions
        except Exception as e:
            logger.error(f"Error formatting positions: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def get_atr(self, symbol, period=14):
        """Belirtilen sembol için ATR (Average True Range) hesaplar
        
        Args:
            symbol (str): İşlem çifti (örn. 'BTCUSDT_UMCBL')
            period (int): ATR periyodu (varsayılan: 14)
            
        Returns:
            float: Hesaplanan ATR değeri
        """
        try:
            # Sembolü düzelt
            binance_symbol = symbol.replace('_UMCBL', '')
            logger.info(f"ATR hesaplama başlatılıyor. Sembol: {binance_symbol}, Periyot: {period}")
            
            # Binance API'den mum verileri al
            url = f'https://api.binance.com/api/v3/klines'
            params = {
                'symbol': binance_symbol,
                'interval': '15m',
                'limit': period + 50  # Daha fazla veri alalım
            }
            
            logger.info(f"Binance API'den veri alınıyor: {url} params: {params}")
            response = requests.get(url, params=params)
            data = response.json()
            
            # Veri kontrolü
            if len(data) < period + 1:
                logger.warning(f"ATR hesaplaması için yeterli veri yok. İhtiyaç: {period+1}, Mevcut: {len(data)}")
                return 0.0
            
            # Pandas DataFrame'e dönüştür
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
            ])
            
            # Sadece gerekli sütunları al
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Veri tiplerini dönüştür
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # ATR hesaplama
            df['previous_close'] = df['close'].shift(1)
            df['tr'] = df[['high', 'low', 'previous_close']].apply(
                lambda x: max(
                    x['high'] - x['low'],
                    abs(x['high'] - x['previous_close']),
                    abs(x['low'] - x['previous_close'])
                ), axis=1
            )
            
            # Wilder's ATR (EMA with alpha=1/period)
            df['ATR'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
            
            # Son ATR değerini al
            atr_value = df['ATR'].iloc[-1]
            
            logger.info(f"Hesaplanan ATR ({period}) değeri: {atr_value}")
            return atr_value
                
        except Exception as e:
            logger.error(f"ATR hesaplaması başarısız oldu: {str(e)}")
            import traceback
            logger.error(f"Hata detayları: {traceback.format_exc()}")
            logger.warning(f"ATR hesaplanamadığı için varsayılan değer kullanılıyor: 0")
            return 0.0  # ATR hesaplanamazsa varsayılan değer 

    def get_position_history(self, limit=50, order="desc"):
        """Bitget API'sinden emir geçmişini al
        
        Args:
            limit (int): Alınacak kayıt sayısı (varsayılan: 50, maksimum: 100)
            order (str): Sıralama kuralı (desc: yeniden eskiye, asc: eskiden yeniye)
            
        Returns:
            list: İşlem geçmişi listesi
        """
        try:
            # Başlangıç ve bitiş zamanları (varsayılan: son 30 gün)
            current_time = int(time.time() * 1000)  # Şimdiki zaman (milisaniye)
            start_time = current_time - (30 * 24 * 60 * 60 * 1000)  # 30 gün öncesi
            
            logger.info(f"Zaman aralığı: {datetime.fromtimestamp(start_time/1000)} - {datetime.fromtimestamp(current_time/1000)}")
            
            # Sadece BTCUSDT için çalıştır (closed_order.py'deki gibi)
            symbol = "BTCUSDT_UMCBL"
            
            # API parametreleri (closed_order.py'deki gibi)
            params = {
                "symbol": symbol,
                "startTime": str(start_time),
                "endTime": str(current_time),
                "pageSize": str(limit)  # limit yerine pageSize kullan
            }
            
            logger.info(f"Requesting order history for {symbol} with params: {params}")
            
            try:
                # ordersHistory metodunu kullan (history değil!)
                response = self.order_api.ordersHistory(params)
                logger.info(f"Order history API response for {symbol}: {response}")
                
                if response and 'data' in response and 'orderList' in response['data']:
                    orders = response['data']['orderList']
                    logger.info(f"Retrieved {len(orders)} orders for {symbol}")
                    
                    # Emirleri formatla
                    formatted_positions = []
                    for order in orders:
                        try:
                            # Sadece tamamlanmış emirleri işle
                            state = order.get('state', '')
                            if state not in ['filled', 'partially_filled']:
                                continue
                            
                            # Temel emir verilerini al
                            order_id = order.get('orderId', '')
                            symbol_str = order.get('symbol', '').replace('_UMCBL', '')
                            size = float(order.get('size', '0'))
                            price = order.get('price')
                            avg_price = float(order.get('priceAvg', '0'))
                            fee = float(order.get('fee', '0'))
                            side = order.get('side', '')
                            
                            # Yön (direction) belirle
                            if 'open_long' in side:
                                direction = 'long'
                                action = 'open'
                            elif 'open_short' in side:
                                direction = 'short'
                                action = 'open'
                            elif 'close_long' in side:
                                direction = 'long'
                                action = 'close'
                            elif 'close_short' in side:
                                direction = 'short'
                                action = 'close'
                            else:
                                # Default değerler
                                direction = side
                                action = 'unknown'
                                logger.warning(f"Unknown side value: {side}")
                            
                            # PnL ve ücretleri hesapla
                            pnl = float(order.get('totalProfits', '0'))
                            
                            # Zaman bilgilerini formatlama
                            c_time = int(order.get('cTime', '0'))
                            u_time = int(order.get('uTime', '0'))
                            create_time = datetime.fromtimestamp(c_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                            update_time = datetime.fromtimestamp(u_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                            
                            # Emir objesini oluştur
                            formatted_order = {
                                'id': order_id,
                                'symbol': symbol_str,
                                'direction': direction,
                                'action': action,
                                'side': side,
                                'type': order.get('orderType', ''),
                                'price': avg_price,  # price değeri None olabileceği için her zaman avg_price kullan
                                'size': size,
                                'state': state,
                                'pnl': pnl,
                                'fee': fee,
                                'create_time': create_time,
                                'update_time': update_time,
                                'lever': order.get('leverage', '1'),
                                'price_avg': avg_price,
                                # Eşleştirme için ek alanlar
                                'open_order_id': order_id if action == 'open' else '',
                                'close_order_id': order_id if action == 'close' else '',
                                'open_fee': fee if action == 'open' else 0,
                                'close_fee': fee if action == 'close' else 0,
                                'open_time': create_time if action == 'open' else '',
                                'close_time': create_time if action == 'close' else '',
                                'entry_price': avg_price if action == 'open' else 0,
                                'exit_price': avg_price if action == 'close' else 0,
                                'closed': action == 'close'
                            }
                            
                            formatted_positions.append(formatted_order)
                            logger.info(f"Formatted order: {formatted_order['symbol']} {formatted_order['direction']} {formatted_order['side']}")
                        except Exception as e:
                            logger.error(f"Error formatting order: {str(e)}")
                            import traceback
                            logger.error(f"Error details: {traceback.format_exc()}")
                            continue
                    
                    # Tarihe göre sırala (en yeni en üstte)
                    if formatted_positions:
                        formatted_positions.sort(key=lambda x: x['update_time'], reverse=True)
                    
                    logger.info(f"Successfully formatted {len(formatted_positions)} orders")
                    return formatted_positions
                else:
                    logger.warning(f"No order history data found for {symbol}")
                    logger.warning(f"API response: {response}")
                    return []
            except Exception as e:
                logger.error(f"Error getting order history for {symbol}: {str(e)}")
                import traceback
                logger.error(f"Error details: {traceback.format_exc()}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get order history: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [] 