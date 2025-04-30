#!/usr/bin/env python
import asyncio
import json
import os
import sys
from telegram import Bot

# Bu dosyanın bulunduğu klasöre göre ana klasörü bulalım
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Ana klasörü Python yoluna ekleyelim
sys.path.append(parent_dir)

async def test_telegram_bot(token, chat_id):
    """Telegram botunuzu ve chat_id'yi test eder"""
    print(f"Token: {token[:6]}... ve Chat ID: {chat_id}")
    
    try:
        # Bot oluşturalım
        bot = Bot(token=token)
        
        # Bot bilgilerini alalım
        bot_info = await bot.get_me()
        print(f"Bot Bilgileri: {bot_info.username} (ID: {bot_info.id})")
        
        # Test mesajı gönderelim
        message_text = "🧪 Bu bir test mesajıdır. Webhook'unuz için Telegram bildirimleri çalışıyor!"
        
        # İlk olarak orijinal chat_id'yi deneyelim
        try:
            print(f"Orijinal chat_id ile deneniyor: {chat_id}")
            await bot.send_message(chat_id=chat_id, text="Chat ID test...")
            message = await bot.send_message(chat_id=chat_id, text=message_text)
            print(f"✅ Başarılı! Mesaj gönderildi. Mesaj ID: {message.message_id}")
            return True
        except Exception as e1:
            print(f"❌ Orijinal chat_id ile hata: {str(e1)}")
            
            # Eğer sayısal bir değerse, integer'a çevirelim
            if str(chat_id).isdigit():
                try:
                    int_chat_id = int(chat_id)
                    print(f"Integer chat_id ile deneniyor: {int_chat_id}")
                    message = await bot.send_message(chat_id=int_chat_id, text=message_text)
                    print(f"✅ Başarılı! Mesaj gönderildi. Mesaj ID: {message.message_id}")
                    return True
                except Exception as e2:
                    print(f"❌ Integer chat_id ile hata: {str(e2)}")
            
            # Eğer - ile başlamıyorsa, - ile başlayan versiyonunu deneyelim (grup ID'leri için)
            if not str(chat_id).startswith('-') and str(chat_id).isdigit():
                try:
                    neg_chat_id = -int(chat_id)
                    print(f"Negatif chat_id ile deneniyor: {neg_chat_id}")
                    message = await bot.send_message(chat_id=neg_chat_id, text=message_text)
                    print(f"✅ Başarılı! Mesaj gönderildi. Mesaj ID: {message.message_id}")
                    return True
                except Exception as e3:
                    print(f"❌ Negatif chat_id ile hata: {str(e3)}")
            
            # @ ile başlayan bir kullanıcı adı deneyelim
            try:
                username = f"@{chat_id}" if not chat_id.startswith('@') else chat_id
                print(f"Kullanıcı adı ile deneniyor: {username}")
                message = await bot.send_message(chat_id=username, text=message_text)
                print(f"✅ Başarılı! Mesaj gönderildi. Mesaj ID: {message.message_id}")
                return True
            except Exception as e4:
                print(f"❌ Kullanıcı adı ile hata: {str(e4)}")
                
            print("\n🔍 Çözüm Önerileri:")
            print("1. Botunuzla bir kez mesajlaşın veya botu grubunuza ekleyin")
            print("2. getUpdates API'sini kullanarak doğru chat_id'yi alın:")
            print(f"   curl https://api.telegram.org/bot{token}/getUpdates")
            print("3. Botunuzun mesaj alma izni olduğundan emin olun (BotFather'da ayarlanır)")
            
            return False
                
    except Exception as e:
        print(f"❌ Bot erişiminde genel hata: {str(e)}")
        return False

def read_config():
    """Yapılandırma dosyasını okur"""
    config_path = os.path.join(parent_dir, 'data', 'config.json')
    
    if not os.path.exists(config_path):
        print(f"❌ Yapılandırma dosyası bulunamadı: {config_path}")
        return None, None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        token = config.get('telegram_bot_token')
        chat_id = config.get('telegram_chat_id')
        
        if not token:
            print("❌ Telegram bot tokenı bulunamadı.")
            return None, None
        
        if not chat_id:
            print("❌ Telegram chat ID bulunamadı.")
            return None, None
        
        return token, chat_id
    
    except Exception as e:
        print(f"❌ Yapılandırma dosyası okuma hatası: {str(e)}")
        return None, None

async def main():
    """Ana işlev"""
    print("🤖 Telegram Bot Test Aracı")
    print("-------------------------")
    
    # Yapılandırma dosyasından verileri alalım
    token, chat_id = read_config()
    
    if not token or not chat_id:
        print("❌ Telegram ayarları eksik. Lütfen data/config.json dosyasını kontrol edin.")
        return
    
    # Telegram botunu test edelim
    await test_telegram_bot(token, chat_id)

if __name__ == "__main__":
    asyncio.run(main()) 