#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import argparse
import sys
import os

def send_webhook(url, signal_type, symbol="BTCUSDT", direction="long", action="open"):
    """Webhook sinyali gönder
    
    Args:
        url (str): Webhook URL'si
        signal_type (str): Sinyal tipi (basic, tradingview, pipedream)
        symbol (str): İşlem sembolü
        direction (str): İşlem yönü (long, short)
        action (str): İşlem tipi (open, close)
    """
    headers = {'Content-Type': 'application/json'}
    
    # Sinyal formatını hazırla
    if signal_type == "basic":
        # Temel sinyal formatı
        data = {
            "signal": f"{symbol}/{direction}/{action}"
        }
    elif signal_type == "tradingview":
        # TradingView formatı
        data = {
            "strategy": {
                "alert_message": f"{symbol}/{direction}/{action}"
            }
        }
    elif signal_type == "pipedream":
        # Pipedream formatı
        data = {
            "symbol": symbol,
            "action": direction if action == "open" else "close"
        }
    else:
        print(f"❌ Geçersiz sinyal tipi: {signal_type}")
        return False
    
    print(f"🚀 {symbol}/{direction}/{action} sinyali gönderiliyor...")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"STATUS CODE: {response.status_code}")
        print(f"RESPONSE: {json.dumps(response.json(), indent=2)}")
        print(f"\nSENT DATA: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print(f"✅ Başarılı! Webhook sinyali gönderildi: {symbol}/{direction}/{action}")
            return True
        else:
            print(f"❌ Hata! Webhook sinyali gönderilemedi: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Webhook test aracı')
    parser.add_argument('--url', type=str, required=True, help='Webhook URL')
    parser.add_argument('--type', type=str, default='basic', choices=['basic', 'tradingview', 'pipedream'], 
                        help='Sinyal tipi (basic, tradingview, pipedream)')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='İşlem sembolü')
    parser.add_argument('--direction', type=str, default='long', choices=['long', 'short'], help='İşlem yönü')
    parser.add_argument('--action', type=str, default='open', choices=['open', 'close'], help='İşlem tipi')
    
    args = parser.parse_args()
    
    success = send_webhook(
        args.url,
        args.type,
        args.symbol,
        args.direction,
        args.action
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 