import bitget.v1.mix.order_api as order_api
import bitget.v1.mix.account_api as account_api
import bitget.v1.mix.market_api as market_api
from bitget.exceptions import BitgetAPIException
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
        self.config = config
        
        # Initialize API clients
        self.order_api = order_api.OrderApi(api_key, secret_key, passphrase)
        self.account_api = account_api.AccountApi(api_key, secret_key, passphrase)
        self.market_api = market_api.MarketApi(api_key, secret_key, passphrase)
        
        logger.info("Bitget handler initialized")
    
    def get_account_balance(self, coin='USDT'):
        """Get account balance for specified coin
        
        Args:
            coin (str): Coin symbol, default is USDT
            
        Returns:
            float: Account balance
        """
        try:
            response = self.account_api.account("umcbl", coin)
            if response and 'data' in response:
                return float(response['data'].get('available', 0))
            return 0
        except BitgetAPIException as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            return 0
    
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
            
            response = self.market_api.detail(symbol)
            if response and 'data' in response:
                return float(response['data'].get('last', 0))
            return 0
        except BitgetAPIException as e:
            logger.error(f"Failed to get symbol price: {str(e)}")
            return 0
    
    def set_leverage(self, symbol, leverage):
        """Set leverage for the symbol
        
        Args:
            symbol (str): Trading pair symbol
            leverage (int): Leverage value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format symbol to Bitget format if needed
            if not symbol.endswith('_UMCBL'):
                symbol = f"{symbol}_UMCBL"
            
            params = {
                "symbol": symbol,
                "marginCoin": "USDT",
                "leverage": str(leverage)
            }
            
            response = self.account_api.leverage(params)
            return response and 'data' in response
        except BitgetAPIException as e:
            logger.error(f"Failed to set leverage: {str(e)}")
            return False
    
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
            
            # Get account balance
            balance = self.get_account_balance('USDT')
            if balance <= 0:
                logger.error("Insufficient balance to place order")
                return None
            
            # Calculate order size based on percentage
            order_size_percentage = self.config.get('order_size_percentage', 10)
            order_amount = balance * (order_size_percentage / 100)
            
            # Get current price
            current_price = self.get_symbol_price(symbol)
            if current_price <= 0:
                logger.error(f"Failed to get price for {symbol}")
                return None
            
            # Set leverage
            leverage = self.config.get('leverage', 5)
            self.set_leverage(formatted_symbol, leverage)
            
            # Calculate size in contracts
            # Note: For simplicity, assuming 1 contract = $1 * leverage
            # This calculation may vary based on the symbol and exchange rules
            size = (order_amount * leverage) / current_price
            size = round(size, 4)  # Adjust precision as needed
            
            params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "side": side,
                "orderType": order_type,
                "size": str(size),
                "timeInForceValue": "normal"
            }
            
            if order_type == "limit":
                params["price"] = str(current_price)
            
            logger.info(f"Placing {side} order for {formatted_symbol}, size: {size}")
            response = self.order_api.placeOrder(params)
            
            logger.info(f"Order placed successfully: {response}")
            return response
            
        except BitgetAPIException as e:
            logger.error(f"Failed to place order: {str(e)}")
            return None
    
    def get_open_positions(self):
        """Get all open positions
        
        Returns:
            list: List of open positions
        """
        try:
            response = self.account_api.positions("umcbl", "USDT")
            if response and 'data' in response:
                return response['data']
            return []
        except BitgetAPIException as e:
            logger.error(f"Failed to get open positions: {str(e)}")
            return [] 