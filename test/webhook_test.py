#!/usr/bin/env python
import requests
import json
import time
import argparse

def send_webhook_signal(webhook_url, signal_type, pair="BTCUSDT", direction="long", action="open"):
    """
    TradingView benzeri bir webhook sinyali gönderir.
    
    signal_type: "basic" - basit bir payload gönderir (pair/direction/action formatında)
                 "tradingview" - TradingView formatında bir payload gönderir
                 "pipedream" - Pipedream formatında payload gönderir
    """
    if signal_type == "basic":
        # Flask uygulamasının beklediği formatta signal parametresi
        signal = f"{pair}/{direction}/{action}"
        payload = {"signal": signal}  # app.py'de "signal" anahtarı kullanılıyor
        headers = {'Content-Type': 'application/json'}
    elif signal_type == "pipedream":
        # Pipedream formatında payload
        # 'buy' action değeri long/open, başka bir değer short/close anlamına gelir
        pipe_action = "buy" if direction == "long" and action == "open" else "sell"
        payload = {
            "symbol": pair,
            "action": pipe_action
        }
        headers = {'Content-Type': 'application/json'}
    else:
        # TradingView formatında daha ayrıntılı bir payload
        payload = {
            "passphrase": "YOUR_SECRET_PASSPHRASE",  # Webhook güvenlik şifrenizi buraya girin
            "time": int(time.time()),
            "exchange": "binance",
            "ticker": pair,
            "bar": {
                "time": int(time.time()) - 60,
                "open": 45000.0,
                "high": 45100.0,
                "low": 44900.0,
                "close": 45050.0,
                "volume": 100.0
            },
            "strategy": {
                "position_size": 1.0 if direction == "long" else -1.0 if direction == "short" else 0.0,
                "order_action": "buy" if action == "open" and direction == "long" else 
                               "sell" if action == "open" and direction == "short" else 
                               "sell" if action == "close" and direction == "long" else "buy",
                "order_contracts": 1,
                "order_price": 45050.0,
                "alert_message": f"{pair}/{direction}/{action}"
            },
            "signal": f"{pair}/{direction}/{action}"  # Burada da "signal" anahtarını ekliyoruz
        }
        headers = {'Content-Type': 'application/json'}
    
    try:
        # JSON verisini gönder
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        
        print(f"STATUS CODE: {response.status_code}")
        print(f"RESPONSE: {response.text}")
        print(f"SENT DATA: {json.dumps(payload, indent=2)}")
        
        if response.status_code == 200:
            print(f"✅ Başarılı! Webhook sinyali gönderildi: {pair}/{direction}/{action}")
            return True
        else:
            print(f"❌ Hata! HTTP status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TradingView webhook test sinyali gönder')
    parser.add_argument('--url', type=str, required=True, help='Webhook URL\'si')
    parser.add_argument('--type', type=str, default='basic', choices=['basic', 'tradingview', 'pipedream'], 
                        help='Sinyal tipi (basic, tradingview veya pipedream)')
    parser.add_argument('--pair', type=str, default='BTCUSDT', help='İşlem çifti (örn. BTCUSDT)')
    parser.add_argument('--direction', type=str, default='long', choices=['long', 'short'], 
                        help='İşlem yönü (long veya short)')
    parser.add_argument('--action', type=str, default='open', choices=['open', 'close'], 
                        help='İşlem emri (open veya close)')
    
    args = parser.parse_args()
    
    print(f"🚀 {args.pair}/{args.direction}/{args.action} sinyali gönderiliyor...")
    send_webhook_signal(args.url, args.type, args.pair, args.direction, args.action) 