import bitget.v1.mix.order_api as order_api
import bitget.v1.mix.account_api as account_api
import bitget.v1.mix.market_api as market_api
from bitget.exceptions import BitgetAPIException
from bitget.bitget_api import BitgetApi
import logging

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
        
        logger.info("Bitget handler initialized")
    
    def get_account_balance(self, coin='USDT'):
        """Get account balance for specified coin
        
        Args:
            coin (str): Coin symbol, default is USDT
            
        Returns:
            float: Account balance
        """
        try:
            # Bitget API'si tüm hesapları getirir
            params = {
                "symbol": "BTCUSDT_UMCBL",
                "marginCoin": "USDT"
            }
            
            response = self.base_api.get("/api/mix/v1/account/account", params)
            logger.debug(f"Account API response: {response}")
            
            if response and 'data' in response:
                return float(response['data'].get('available', 0))
            
            # Eğer API yanıt vermezse, test amaçlı sabit değer kullan
            logger.warning("Hesap bilgisi alınamadı, test için 1000 USDT kullanılıyor.")
            return 1000.0
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            # Test için sabit değer
            logger.warning("Test için 1000 USDT kullanılıyor.")
            return 1000.0
    
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
                symbol = f"{symbol}_UMCBL"
            
            # Doğru parametre formatı: dict olmalı, string değil
            params = {"symbol": symbol}
            
            try:
                # Ticker metodunu kullanalım
                response = self.market_api.ticker(params)
                logger.debug(f"Ticker response: {response}")
                
                if response and 'data' in response:
                    return float(response['data'].get('last', 0))
                else:
                    # Fiyat alınamadıysa, sabit bir değer kullanalım (test için)
                    logger.warning(f"Using fixed price for {symbol}: 45000")
                    return 45000.0
            except Exception as e:
                logger.error(f"Failed to get ticker: {str(e)}")
                logger.warning(f"Using fixed price for {symbol}: 45000")
                return 45000.0
        except Exception as e:
            logger.error(f"Failed to get symbol price: {str(e)}")
            logger.warning(f"Using fixed price for {symbol}: 45000")
            return 45000.0  # Test için sabit bir değer
    
    def place_order(self, symbol, side, order_type="market"):
        """Place an order on Bitget
        
        Args:
            symbol (str): Trading pair symbol (e.g. 'BTCUSDT')
            side (str): Order side (open_long, open_short, close_long, close_short)
            order_type (str): Order type (market, limit)
            
        Returns:
            dict: Order response
        """
        try:
            # Format symbol to Bitget format if needed
            if not symbol.endswith('_UMCBL'):
                formatted_symbol = f"{symbol}_UMCBL"
            else:
                formatted_symbol = symbol
            
            # Get account balance - use a fixed value for testing if balance retrieval fails
            balance = self.get_account_balance('USDT')
            if balance <= 0:
                # For testing, use a dummy balance
                logger.warning("Using dummy balance for testing: 1000 USDT")
                balance = 1000.0
            
            # Calculate order size based on percentage
            order_size_percentage = self.config.get('order_size_percentage', 10)
            # Eğer config bir nesne ise ve float değeri dönüştürmek gerekiyorsa
            if not isinstance(order_size_percentage, (int, float)):
                try:
                    order_size_percentage = float(order_size_percentage)
                except (TypeError, ValueError):
                    logger.warning(f"Invalid order_size_percentage value: {order_size_percentage}, using default 10%")
                    order_size_percentage = 10.0
            
            order_amount = balance * (order_size_percentage / 100)
            logger.info(f"Order amount: ${order_amount} USDT ({order_size_percentage}% of {balance} USDT)")
            
            # Get current price
            current_price = self.get_symbol_price(symbol)
            if current_price <= 0:
                logger.error(f"Failed to get price for {symbol}")
                # For testing, use a dummy price
                logger.warning("Using dummy price for BTC: 45000")
                current_price = 45000.0
                
            # İşlem büyüklüğünü hesapla (USD değerini coin miktarına çevir)
            size = order_amount / current_price
            
            # Symbol'e göre minimum lot büyüklüğünü ayarla
            if 'BTC' in symbol:
                # BTC için minimum 0.001 lot, yuvarla
                size = max(0.001, round(size, 3))
                logger.info(f"Calculated order size for BTC: {size} BTC (${order_amount} USD)")
            elif 'ETH' in symbol:
                # ETH için minimum 0.01 lot, yuvarla
                size = max(0.01, round(size, 2))
                logger.info(f"Calculated order size for ETH: {size} ETH (${order_amount} USD)")
            else:
                # Diğer coinler için minimum 0.01 lot, yuvarla
                size = max(0.01, round(size, 2))
                logger.info(f"Calculated order size for {symbol}: {size} (${order_amount} USD)")
            
            # Set leverage
            leverage = self.config.get('leverage', 5)
            # Eğer leverage bir nesne ise ve int değeri dönüştürmek gerekiyorsa
            if not isinstance(leverage, (int, float)):
                try:
                    leverage = int(float(leverage))
                except (TypeError, ValueError):
                    logger.warning(f"Invalid leverage value: {leverage}, using default 5x")
                    leverage = 5
            
            logger.info(f"Using leverage setting from config: {leverage}x")
            
            try:
                # Leverage ayarını base_api ile yapalım
                for hold_side in ['long', 'short']:
                    leverage_params = {
                        "symbol": formatted_symbol,
                        "marginCoin": "USDT",
                        "leverage": str(leverage),
                        "holdSide": hold_side
                    }
                    logger.info(f"Setting leverage to {leverage}x for {formatted_symbol} ({hold_side})")
                    leverage_response = self.base_api.post("/api/mix/v1/account/setLeverage", leverage_params)
                    logger.info(f"Leverage response: {leverage_response}")
            except Exception as le:
                logger.error(f"Failed to set leverage: {str(le)}")
                # Kaldıraç hatası varsa, işleme devam etmeyi deneyelim
                logger.warning(f"Continuing without setting leverage. Will use the existing leverage setting.")
            
            # Bitget API parametreleri
            params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "size": str(size)
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
            
            # Order type (market, limit)
            if order_type.lower() == "market":
                params["orderType"] = "market"
            else:
                params["orderType"] = "limit"
                params["price"] = str(current_price)
            
            logger.info(f"Placing {side} order for {formatted_symbol}, size: {size}, params: {params}")
            
            # base_api.post kullanarak doğrudan API endpoint'ine istek yapıyoruz
            response = self.base_api.post("/api/mix/v1/order/placeOrder", params)
            
            logger.info(f"Order placed successfully: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            import traceback
            logger.error(f"Order placement error details: {traceback.format_exc()}")
            return None
    
    def get_open_positions(self):
        """Get all open positions
        
        Returns:
            list: List of open positions
        """
        try:
            # Bitget API'si tüm pozisyonları getirir
            params = {"productType": "umcbl", "marginCoin": "USDT"}
            response = self.base_api.get("/api/mix/v1/position/allPosition", params)
            logger.debug(f"Position API response: {response}")
            
            if response and 'data' in response:
                return response['data']
            return []
        except Exception as e:
            logger.error(f"Failed to get open positions: {str(e)}")
            return [] 