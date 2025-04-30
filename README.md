# TradingView to Bitget Trading Bot

A web application that processes TradingView webhook signals and executes trades on Bitget. It includes a responsive UI for configuration management and supports Telegram notifications.

## Features

- **TradingView Signal Integration**: Receive and process trading signals from TradingView via webhooks
- **Bitget Trading**: Automatically execute long/short orders on Bitget based on received signals
- **User Management**: Admin can add and remove users
- **Responsive UI**: Configure all trading parameters through a user-friendly interface
- **Telegram Notifications**: Receive notifications for each trade
- **Position Tracking**: View all open and closed positions
- **Security**: API keys are stored securely

## Technical Stack

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Trading API**: Bitget Python SDK
- **Notifications**: Telegram Bot API

## Prerequisites

- Python 3.8+
- Bitget API credentials (API key, Secret key, Passphrase)
- Telegram Bot token (optional, for notifications)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/tradingview-bitget-bot.git
   cd tradingview-bitget-bot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Configuration

1. **First Login**:
   - Default username: `admin`
   - Default password: `admin`
   - Important: Change the default password after login

2. **Bitget API Setup**:
   - Go to Settings
   - Enter your Bitget API credentials

3. **Telegram Notifications** (Optional):
   - Create a Telegram bot using [BotFather](https://t.me/BotFather)
   - Get your chat ID
   - Enter both in the Settings page

4. **Trading Parameters**:
   - Configure leverage, order size, and other trading parameters
   - Enable/disable trading as needed

## TradingView Setup

1. Create a TradingView alert with the following webhook URL:
   ```
   http://your-server-address:5000/webhook
   ```

2. Format the webhook message in JSON as:
   ```json
   {
     "signal": "BTCUSDT/long/open"
   }
   ```

3. Signal format: `{symbol}/{direction}/{action}`
   - `symbol`: Trading pair (e.g., BTCUSDT)
   - `direction`: long or short
   - `action`: open or close

## Security Notes

- Store the app behind a reverse proxy with HTTPS
- Use a strong password for the admin account
- Consider using environment variables for sensitive information in production

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Use at your own risk. The author is not responsible for any financial losses incurred from using this software. 