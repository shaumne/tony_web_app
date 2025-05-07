#!/usr/bin/env python
import logging
import json
import os
from bitget_handler import BitgetHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Konfigürasyon dosyasını oku
        with open('data/config.json', 'r') as f:
            config = json.load(f)
        
        # BitgetHandler'ı başlat
        handler = BitgetHandler(
            config['bitget_api_key'],
            config['bitget_secret_key'],
            config['bitget_passphrase'],
            config
        )
        
        # Hesap bakiyesini al
        balance = handler.get_account_balance('USDT')
        logger.info(f"Account balance: {balance} USDT")
        
        # Konfigürasyon değerlerini göster
        leverage = config['leverage']
        order_size_percentage = config['order_size_percentage']
        logger.info(f"Leverage setting: {leverage}x")
        logger.info(f"Order size percentage: {order_size_percentage}%")
        
        # Hesaplama detayları - kullanıcı isteği doğrultusunda doğrudan yüzde kullanılıyor
        symbol = "BTCUSDT"
        
        # Hesaplama: Doğrudan cüzdan bakiyesinin belirtilen yüzdesi
        order_amount = balance * (order_size_percentage / 100)
        
        logger.info(f"Order amount: ${order_amount:.2f} USDT ({order_size_percentage}% of {balance:.2f} USDT)")
        
        # Test siparişi oluşturmadan hesaplama yap
        current_price = handler.get_symbol_price(symbol)
        logger.info(f"Current {symbol} price: ${current_price}")
        
        # BTC lot size hesaplama
        size = order_amount / current_price
        size = max(0.001, round(size, 3))
        logger.info(f"Calculated order size: {size} BTC (${order_amount:.2f} USD)")
        
        # Leverage ayarını göster
        logger.info(f"Leverage is set to {leverage}x but doesn't affect position size calculation")
        logger.info(f"Position size is exactly {order_size_percentage}% of wallet as requested by user")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 