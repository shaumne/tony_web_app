#!/bin/bash

# TradingView Webhook - SSL ile Yeniden Başlatma Script
# ====================================================

# Gerekli değişkenler
APP_NAME="tradingview-webhook-bot"
APP_DIR="/home/ubuntu/$APP_NAME"
SYSTEMD_SERVICE_NAME="tradingview-webhook-bot"
DOMAIN="cryptosynapse.pro"
APP_PORT=5000
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"

# Renk kodları
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== TradingView Webhook Uygulamasını SSL İle Yeniden Başlatma =====${NC}"

# SSL sertifika kontrolü
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo -e "${RED}SSL sertifikaları bulunamadı. Önce SSL sertifikası alınması gerekiyor.${NC}"
    
    read -p "SSL sertifikasını şimdi almak istiyor musunuz? (E/h): " SSL_CONFIRM
    SSL_CONFIRM=${SSL_CONFIRM:-E}
    
    if [[ $SSL_CONFIRM == "E" || $SSL_CONFIRM == "e" ]]; then
        echo -e "${YELLOW}SSL sertifikası alınıyor...${NC}"
        sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}SSL sertifikası alınamadı. Lütfen DNS ayarlarınızı kontrol edin.${NC}"
            exit 1
        else
            echo -e "${GREEN}SSL sertifikası başarıyla alındı!${NC}"
        fi
    else
        echo -e "${RED}SSL sertifikası olmadan devam edilemiyor. İşlem iptal edildi.${NC}"
        exit 1
    fi
fi

# SSL sertifika yollarını al
SSL_CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
SSL_KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

# app.py dosyasında SSL ayarlarını kontrol et
if [ -f "$APP_DIR/app_ssl.py" ]; then
    echo -e "${YELLOW}app_ssl.py dosyası zaten mevcut. Üzerine yazılacak.${NC}"
fi

# Gunicorn servis yapılandırmasını güncelle
echo -e "\n${GREEN}[1/4]${NC} Gunicorn servis yapılandırması güncelleniyor..."

# NOT: Burada değişiklik yapıyoruz. Artık Gunicorn SSL ile değil HTTP üzerinden çalışacak,
# SSL terminasyonu Nginx tarafında yapılacak. Bu daha güvenli ve yaygın bir yaklaşımdır.
cat << EOF | sudo tee /etc/systemd/system/${SYSTEMD_SERVICE_NAME}.service
[Unit]
Description=TradingView Webhook Bitget Bot
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:${APP_PORT} app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Systemd servis dosyası güncellendi.${NC}"

# Nginx yapılandırmasını kontrol et ve güncelle
echo -e "\n${GREEN}[2/4]${NC} Nginx yapılandırması güncelleniyor..."

# HTTPS yönlendirmesi ve diğer güvenlik ayarları ile Nginx yapılandırmasını güncelle
cat << EOF | sudo tee "$NGINX_CONF"
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN} www.${DOMAIN};

    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Hata giderme için zaman aşımı sürelerini artır
        proxy_connect_timeout 75s;
        proxy_read_timeout 300s;
    }
}
EOF

echo -e "${GREEN}Nginx yapılandırması güncellendi.${NC}"

# Nginx yapılandırmasını test et
echo -e "\n${GREEN}[3/4]${NC} Nginx yapılandırması test ediliyor..."
sudo nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}Nginx yapılandırma hatalı. Lütfen kontrol edin.${NC}"
    exit 1
fi

# Debug için loglama ayarlarını güncelle
echo -e "\n${YELLOW}Hata ayıklama için Flask debug modunu etkinleştiriliyor...${NC}"

# Uygulama log dosyası oluştur
sudo touch /var/log/tradingview-webhook.log
sudo chown ubuntu:ubuntu /var/log/tradingview-webhook.log

# Gunicorn için error log ekleyin
cat << EOF | sudo tee -a /etc/systemd/system/${SYSTEMD_SERVICE_NAME}.service
Environment="PYTHONUNBUFFERED=1"
StandardOutput=append:/var/log/tradingview-webhook.log
StandardError=append:/var/log/tradingview-webhook.log
EOF

# Servisleri yeniden başlat
echo -e "\n${GREEN}[4/4]${NC} Servisler yeniden başlatılıyor...${NC}"
sudo systemctl daemon-reload
sudo systemctl restart ${SYSTEMD_SERVICE_NAME}
sudo systemctl restart nginx

# Servislerin durumunu kontrol et
echo -e "\n${YELLOW}Servislerin durumu kontrol ediliyor...${NC}"
echo -e "${YELLOW}Nginx durumu:${NC}"
sudo systemctl status nginx --no-pager

echo -e "\n${YELLOW}Gunicorn servis durumu:${NC}"
sudo systemctl status ${SYSTEMD_SERVICE_NAME} --no-pager

# Webhook URL'sini kontrol et ve bilgi ver
echo -e "\n${GREEN}==================== YENİDEN BAŞLATMA TAMAMLANDI ====================${NC}"
echo -e "${GREEN}TradingView Webhook - Bitget Bot başarıyla SSL ile yeniden başlatıldı!${NC}"
echo -e "Web uygulaması şu adreste çalışıyor: https://${DOMAIN}"
echo
echo -e "${YELLOW}TradingView Alert Ayarları İçin:${NC}"
echo -e "Webhook URL: ${GREEN}https://${DOMAIN}/webhook${NC}"
echo -e "İçerik Tipi: application/json"
echo -e "Örnek Alert Mesajı: BTCUSDT/long/open veya BTCUSDT/short/close"
echo
echo -e "${YELLOW}Sorun Giderme:${NC}"
echo -e "1. Hata loglarını kontrol et:"
echo -e "   ${GREEN}sudo journalctl -u ${SYSTEMD_SERVICE_NAME} -f${NC}"
echo -e "   ${GREEN}sudo tail -f /var/log/nginx/error.log${NC}"
echo -e "   ${GREEN}sudo tail -f /var/log/tradingview-webhook.log${NC}"
echo
echo -e "2. Uygulamayı manuel başlatmayı dene:"
echo -e "   ${GREEN}cd $APP_DIR && source venv/bin/activate && python app.py${NC}"
echo
echo -e "3. SSL bağlantısını test et:"
echo -e "   ${GREEN}curl -k https://localhost${NC}"
echo
echo -e "4. Webhook'u manuel test et:"
echo -e "   ${GREEN}curl -X POST -H \"Content-Type: application/json\" -d '{\"signal\":\"BTCUSDT/long/open\"}' https://${DOMAIN}/webhook${NC}"
echo
echo -e "${YELLOW}Yararlı Komutlar:${NC}"
echo -e "Uygulama Durumunu Kontrol Et: ${GREEN}sudo systemctl status ${SYSTEMD_SERVICE_NAME}${NC}"
echo -e "Uygulamayı Yeniden Başlat: ${GREEN}sudo systemctl restart ${SYSTEMD_SERVICE_NAME}${NC}"
echo -e "Log Dosyalarını Görüntüle: ${GREEN}sudo journalctl -u ${SYSTEMD_SERVICE_NAME} -f${NC}" 