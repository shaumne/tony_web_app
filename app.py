from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import threading
import asyncio
import time
from datetime import datetime
import logging
import sys

from models import User, Config, Position
from bitget_handler import BitgetHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_in_production')

# Add current year to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize data files if they don't exist
def init_data_files():
    if not os.path.exists('data'):
        os.makedirs('data')
    
    if not os.path.exists('data/users.json'):
        with open('data/users.json', 'w') as f:
            json.dump({
                "admin": {
                    "password": generate_password_hash("admin"),
                    "is_admin": True
                }
            }, f)
    
    if not os.path.exists('data/config.json'):
        with open('data/config.json', 'w') as f:
            json.dump({
                "bitget_api_key": "",
                "bitget_secret_key": "",
                "bitget_passphrase": "",
                "telegram_bot_token": "",
                "telegram_chat_id": "",
                "leverage": 5,
                "order_size_percentage": 10,
                "max_daily_trades": 10,
                "max_open_positions": 3,
                "enable_trading": True
            }, f)
    
    if not os.path.exists('data/positions.json'):
        with open('data/positions.json', 'w') as f:
            json.dump([], f)

init_data_files()

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    with open('data/users.json', 'r') as f:
        users = json.load(f)
    
    if user_id in users:
        return User(user_id, users[user_id].get('is_admin', False))
    return None

# Bitget handler instance
bitget_handler = None

# Load configuration
def load_config():
    with open('data/config.json', 'r') as f:
        config_data = json.load(f)
    
    global bitget_handler
    if config_data.get('bitget_api_key') and config_data.get('bitget_secret_key') and config_data.get('bitget_passphrase'):
        bitget_handler = BitgetHandler(
            config_data['bitget_api_key'],
            config_data['bitget_secret_key'],
            config_data['bitget_passphrase'],
            config_data
        )
    
    return Config(**config_data)

# Telegram notification function
async def send_telegram_notification(message):
    config = load_config()
    if config.telegram_bot_token and config.telegram_chat_id:
        try:
            from telegram import Bot
            bot = Bot(token=config.telegram_bot_token)
            
            # Telegram chat_id formatını düzeltme
            chat_id = config.telegram_chat_id
            
            # Eğer chat_id sayısal bir değerse
            if chat_id.isdigit():
                # Grup ID'si için negatif değer kullanılması gerekiyor
                # 1002... ile başlayan ID'ler grup ID'leri, bunları negatife çeviriyoruz
                if chat_id.startswith("100"):
                    chat_id = "-" + chat_id
                    logger.info(f"Converting group ID to negative: {chat_id}")
            
            logger.info(f"Sending telegram with chat_id: {chat_id}")
            await bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Telegram notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")
            # Hata ayıklama için daha detaylı bilgi
            import traceback
            logger.error(f"Telegram hata detayları: {traceback.format_exc()}")
            
            # Kullanıcıya bilgi vermek için hata mesajı
            logger.error(f"Telegram bilgilerinizi kontrol edin. Bot token: {config.telegram_bot_token[:5]}... ve Chat ID: {config.telegram_chat_id}")
            logger.error("Telegram botunuzla bir kez mesajlaştığınızdan veya botu gruba eklediğinizden emin olun.")

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with open('data/users.json', 'r') as f:
            users = json.load(f)
        
        if username in users and check_password_hash(users[username]['password'], password):
            user = User(username, users[username].get('is_admin', False))
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    config = load_config()
    
    # Load positions
    with open('data/positions.json', 'r') as f:
        positions_data = json.load(f)
    
    positions = [Position(**pos) for pos in positions_data]
    
    # Hesap bakiyesini al
    account_balance = 0
    if bitget_handler:
        try:
            account_balance = bitget_handler.get_account_balance('USDT')
            logger.info(f"Account balance: {account_balance} USDT")
        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
    
    return render_template('dashboard.html', config=config, positions=positions, account_balance=account_balance)

@app.route('/history')
@login_required
def position_history():
    # Load positions
    with open('data/positions.json', 'r') as f:
        positions_data = json.load(f)
    
    # Filter closed positions
    closed_positions_data = [pos for pos in positions_data if pos.get('closed', False)]
    
    # Sort by close time, most recent first
    closed_positions_data.sort(key=lambda x: x.get('close_time', ''), reverse=True)
    
    # Calculate PnL for each position and total
    total_pnl = 0
    for pos in closed_positions_data:
        entry = float(pos.get('entry_price', 0))
        exit_price = float(pos.get('exit_price', 0))
        size = float(pos.get('size', 0))
        direction = pos.get('direction', '')
        
        if direction == 'long':
            pnl = (exit_price - entry) * size
        else:  # short
            pnl = (entry - exit_price) * size
            
        pos['pnl'] = round(pnl, 2)
        total_pnl += pnl
    
    return render_template('history.html', positions=closed_positions_data, total_pnl=round(total_pnl, 2))

@app.route('/close_position', methods=['POST'])
@login_required
def close_position():
    position_id = request.form.get('position_id')
    symbol = request.form.get('symbol')
    direction = request.form.get('direction')
    
    if not all([position_id, symbol, direction]):
        flash('Missing position information', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # İşlemi kapat
        side = f"close_{direction}"
        if bitget_handler:
            logger.info(f"Closing position {position_id} for {symbol} ({direction}) from dashboard")
            order_result = bitget_handler.place_order(symbol, side)
            
            # Pozisyonu güncelle
            with open('data/positions.json', 'r') as f:
                positions = json.load(f)
            
            # Pozisyonu bul
            position = None
            for pos in positions:
                if pos.get('id') == position_id:
                    position = pos
                    break
                    
            if position and order_result and order_result.get('data', {}).get('orderId'):
                # Sipariş sonucundan daha fazla bilgi almaya çalışalım
                logger.info(f"Close order result data: {order_result.get('data', {})}")
                
                # Size ve price bilgilerini doğru alanlarda arayalım
                exit_price = order_result['data'].get('price', '0')
                avg_price = order_result['data'].get('averagePrice', '0')
                
                # Eğer price değeri 0 ise market api ile güncel fiyatı alalım
                if float(exit_price) <= 0 or exit_price == '0':
                    current_price = bitget_handler.get_symbol_price(symbol)
                    exit_price = str(current_price)
                    logger.info(f"Using current market price for close {symbol}: {exit_price}")
                
                # Update position
                position['closed'] = True
                position['close_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                position['exit_price'] = exit_price if float(exit_price) > 0 else avg_price
                
                # Save updated positions
                with open('data/positions.json', 'w') as f:
                    json.dump(positions, f)
                
                # Send Telegram notification
                message = (
                    f"🔔 {direction.upper()} position manually closed from dashboard\n"
                    f"Symbol: {symbol}\n"
                    f"Entry Price: {position['entry_price']}\n"
                    f"Exit Price: {position['exit_price']}\n"
                    f"Size: {position['size']}\n"
                    f"Order ID: {order_result['data']['orderId']}"
                )
                asyncio.run(send_telegram_notification(message))
                
                flash(f"Successfully closed {direction.upper()} position for {symbol}", 'success')
            else:
                flash(f"Failed to close position or position not found", 'danger')
        else:
            flash('Bitget handler not initialized', 'danger')
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        flash(f"Error closing position: {str(e)}", 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not current_user.is_admin:
        flash('Only admins can access settings', 'danger')
        return redirect(url_for('dashboard'))
    
    config = load_config()
    
    if request.method == 'POST':
        updated_config = {
            "bitget_api_key": request.form.get('bitget_api_key'),
            "bitget_secret_key": request.form.get('bitget_secret_key'),
            "bitget_passphrase": request.form.get('bitget_passphrase'),
            "telegram_bot_token": request.form.get('telegram_bot_token'),
            "telegram_chat_id": request.form.get('telegram_chat_id'),
            "leverage": int(request.form.get('leverage', 5)),
            "order_size_percentage": float(request.form.get('order_size_percentage', 10)),
            "max_daily_trades": int(request.form.get('max_daily_trades', 10)),
            "max_open_positions": int(request.form.get('max_open_positions', 3)),
            "enable_trading": 'enable_trading' in request.form
        }
        
        with open('data/config.json', 'w') as f:
            json.dump(updated_config, f)
        
        # Reinitialize Bitget handler with new settings
        global bitget_handler
        bitget_handler = BitgetHandler(
            updated_config['bitget_api_key'],
            updated_config['bitget_secret_key'],
            updated_config['bitget_passphrase'],
            updated_config
        )
        
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', config=config)

@app.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Only admins can manage users', 'danger')
        return redirect(url_for('dashboard'))
    
    with open('data/users.json', 'r') as f:
        users = json.load(f)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required', 'danger')
            elif username in users:
                flash('Username already exists', 'danger')
            else:
                users[username] = {
                    "password": generate_password_hash(password),
                    "is_admin": False
                }
                
                with open('data/users.json', 'w') as f:
                    json.dump(users, f)
                
                flash('User added successfully', 'success')
        
        elif action == 'delete':
            username = request.form.get('delete_username')
            
            if username == current_user.id:
                flash('You cannot delete your own account', 'danger')
            elif username in users:
                del users[username]
                
                with open('data/users.json', 'w') as f:
                    json.dump(users, f)
                
                flash('User deleted successfully', 'success')
        
        return redirect(url_for('manage_users'))
    
    return render_template('users.html', users=users)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not request.json:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    
    logger.info(f"Received webhook data: {request.json}")
    
    config = load_config()
    if not config.enable_trading:
        logger.info("Trading is disabled. Ignoring webhook signal.")
        return jsonify({"status": "error", "message": "Trading is disabled"}), 200
    
    try:
        # Request.json verisinin formatını analiz et
        data = request.json
        logger.info(f"Processing webhook data: {data}")
        
        # Pipedream formatını kontrol et
        symbol = data.get("symbol", "")
        action = data.get("action", "").lower()
        
        # Sembol kontrolü
        if not symbol:
            # Eski format kontrolü - BTCUSDT/long/open gibi
            signal = None
            
            # 1. Webhook test aracından gelen doğrudan 'signal' alanı
            if 'signal' in data:
                signal = data['signal']
                logger.info(f"Found signal in 'signal' field: {signal}")
            
            # 2. TradingView'dan gelen 'strategy.alert_message' formatı
            elif 'strategy' in data and 'alert_message' in data['strategy']:
                signal = data['strategy']['alert_message']
                logger.info(f"Found signal in strategy.alert_message: {signal}")
            
            # 3. Doğrudan 'message' veya 'text' alanlarını deneyebiliriz
            elif 'message' in data:
                signal = data['message']
                logger.info(f"Found signal in 'message' field: {signal}")
            elif 'text' in data:
                signal = data['text']
                logger.info(f"Found signal in 'text' field: {signal}")
            
            # 4. TradingView'dan gelen JSON verisinde text message değeri arıyor olabiliriz
            elif any('/' in str(val) for val in data.values() if isinstance(val, str)):
                for key, value in data.items():
                    if isinstance(value, str) and '/' in value and len(value.split('/')) == 3:
                        signal = value
                        logger.info(f"Found signal in '{key}' field: {signal}")
                        break
            
            if not signal:
                logger.error(f"No signal found in webhook data: {data}")
                return jsonify({"status": "error", "message": "No signal provided"}), 400
            
            # Eski format işleme - BTCUSDT/long/open
            parts = signal.split('/')
            if len(parts) != 3:
                logger.error(f"Invalid signal format: {signal}")
                return jsonify({"status": "error", "message": "Invalid signal format"}), 400
            
            symbol, direction, action = parts
        else:
            # Pipedream format işleme - symbol ve action alanları
            # Long/Short ve Open/Close mantığı
            direction = "long" if action == "buy" else "short"
            trade_action = "open" if action == "buy" else "close"
            
            logger.info(f"Processed Pipedream format - Symbol: {symbol}, Direction: {direction}, Action: {trade_action}")
            
            # action değişkenini trade_action olarak değiştir (Pipedream uyumu)
            action = trade_action
        
        # Semboldeki ".P" ekini temizle
        if ".P" in symbol:
            original_symbol = symbol
            symbol = symbol.replace(".P", "")
            logger.info(f"Cleaned symbol from {original_symbol} to {symbol}")
        
        if not symbol or not direction or not action:
            logger.error(f"Invalid signal components after processing")
            return jsonify({"status": "error", "message": "Invalid signal components"}), 400
        
        if direction.lower() not in ['long', 'short']:
            logger.error(f"Invalid direction: {direction}")
            return jsonify({"status": "error", "message": "Invalid direction"}), 400
        
        if action.lower() not in ['open', 'close']:
            logger.error(f"Invalid action: {action}")
            return jsonify({"status": "error", "message": "Invalid action"}), 400
        
        # Process the signal in a separate thread to avoid blocking
        threading.Thread(target=process_signal, args=(symbol, direction.lower(), action.lower())).start()
        
        return jsonify({
            "status": "success", 
            "message": f"Signal received and processing: {symbol}/{direction}/{action}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        import traceback
        logger.error(f"Webhook error details: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

def process_signal(symbol, direction, action):
    if not bitget_handler:
        logger.error("Bitget handler not initialized. Please configure API keys.")
        return
    
    config = load_config()
    
    # Check daily trade limit
    with open('data/positions.json', 'r') as f:
        positions = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_trades = sum(1 for pos in positions if pos.get('open_time', '').startswith(today))
    
    if action == 'open' and today_trades >= config.max_daily_trades:
        logger.info(f"Daily trade limit reached ({config.max_daily_trades}). Ignoring signal.")
        asyncio.run(send_telegram_notification(f"⚠️ Daily trade limit reached. Ignoring {direction} {action} signal for {symbol}."))
        return
    
    # Check max open positions
    open_positions = sum(1 for pos in positions if not pos.get('closed', False))
    
    if action == 'open' and open_positions >= config.max_open_positions:
        logger.info(f"Maximum open positions limit reached ({config.max_open_positions}). Ignoring signal.")
        asyncio.run(send_telegram_notification(f"⚠️ Max open positions limit reached. Ignoring {direction} {action} signal for {symbol}."))
        return
    
    # Execute the trade
    try:
        if action == 'open':
            side = f"open_{direction}"
            order_result = bitget_handler.place_order(symbol, side)
            
            if order_result and order_result.get('data', {}).get('orderId'):
                order_id = order_result['data']['orderId']
                
                # Sipariş sonucundan daha fazla bilgi almaya çalışalım
                logger.info(f"Order result data: {order_result.get('data', {})}")
                
                # Size ve price bilgilerini doğru alanlarda arayalım
                # Bitget API'sinden dönen yanıta göre uyarlama yapıyoruz
                size = order_result['data'].get('size', '0')
                price = order_result['data'].get('price', '0')
                avg_price = order_result['data'].get('averagePrice', '0')
                
                # Eğer price değeri 0 ise market api ile güncel fiyatı alalım
                if float(price) <= 0 or price == '0':
                    current_price = bitget_handler.get_symbol_price(symbol)
                    price = str(current_price)
                    logger.info(f"Using current market price for {symbol}: {price}")
                
                # Save position
                new_position = {
                    "id": order_id,
                    "symbol": symbol,
                    "direction": direction,
                    "size": size,
                    "entry_price": price if float(price) > 0 else avg_price,
                    "open_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "closed": False
                }
                
                positions.append(new_position)
                
                with open('data/positions.json', 'w') as f:
                    json.dump(positions, f)
                
                # Send Telegram notification
                message = (
                    f"🔔 New {direction.upper()} position opened\n"
                    f"Symbol: {symbol}\n"
                    f"Entry Price: {new_position['entry_price']}\n"
                    f"Size: {new_position['size']}\n"
                    f"Order ID: {order_id}"
                )
                asyncio.run(send_telegram_notification(message))
                
                logger.info(f"Successfully opened {direction} position for {symbol}")
        
        elif action == 'close':
            # Find matching open positions
            matching_positions = [
                pos for pos in positions 
                if pos['symbol'] == symbol and 
                pos['direction'] == direction and 
                not pos.get('closed', False)
            ]
            
            if not matching_positions:
                logger.info(f"No matching open {direction} positions found for {symbol}")
                asyncio.run(send_telegram_notification(f"⚠️ No matching open {direction} positions found for {symbol} to close."))
                return
            
            for position in matching_positions:
                side = f"close_{direction}"
                order_result = bitget_handler.place_order(symbol, side)
                
                if order_result and order_result.get('data', {}).get('orderId'):
                    # Sipariş sonucundan daha fazla bilgi almaya çalışalım
                    logger.info(f"Close order result data: {order_result.get('data', {})}")
                    
                    # Size ve price bilgilerini doğru alanlarda arayalım
                    exit_price = order_result['data'].get('price', '0')
                    avg_price = order_result['data'].get('averagePrice', '0')
                    
                    # Eğer price değeri 0 ise market api ile güncel fiyatı alalım
                    if float(exit_price) <= 0 or exit_price == '0':
                        current_price = bitget_handler.get_symbol_price(symbol)
                        exit_price = str(current_price)
                        logger.info(f"Using current market price for close {symbol}: {exit_price}")
                    
                    # Update position
                    position['closed'] = True
                    position['close_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    position['exit_price'] = exit_price if float(exit_price) > 0 else avg_price
                    
                    # Save updated positions
                    with open('data/positions.json', 'w') as f:
                        json.dump(positions, f)
                    
                    # Send Telegram notification
                    message = (
                        f"🔔 {direction.upper()} position closed\n"
                        f"Symbol: {symbol}\n"
                        f"Entry Price: {position['entry_price']}\n"
                        f"Exit Price: {position['exit_price']}\n"
                        f"Size: {position['size']}\n"
                        f"Order ID: {order_result['data']['orderId']}"
                    )
                    asyncio.run(send_telegram_notification(message))
                    
                    logger.info(f"Successfully closed {direction} position for {symbol}")
    
    except Exception as e:
        error_message = f"Error executing trade: {str(e)}"
        logger.error(error_message)
        asyncio.run(send_telegram_notification(f"❌ {error_message}"))

# Add current year to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 