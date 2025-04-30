#!/bin/bash

# TradingView Webhook - Bitget Bot AWS EC2 Deploy Script
# ====================================================

echo "=========================================="
echo "TradingView Webhook - Bitget Bot Deploy Tool"
echo "=========================================="

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

echo -e "${YELLOW}Bu script, TradingView webhook uygulamanızı AWS EC2'ye deploy edecektir.${NC}"
echo -e "${YELLOW}Devam etmek için ENTER tuşuna basın veya çıkmak için CTRL+C tuşlarına basın.${NC}"
read

# EC2 sunucusunun güncel olduğundan emin ol
echo -e "\n${GREEN}[1/9]${NC} Sistem güncelleniyor..."
sudo apt update && sudo apt upgrade -y

# Gerekli paketleri kur
echo -e "\n${GREEN}[2/9]${NC} Gerekli paketler kuruluyor..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Uygulama klasörü oluştur
echo -e "\n${GREEN}[3/9]${NC} Uygulama klasörü hazırlanıyor..."
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}Uygulama klasörü zaten mevcut, güncelleniyor...${NC}"
    cd "$APP_DIR"
    git pull || echo -e "${RED}Git repository bulunamadı. Klasör temizlenip baştan oluşturulacak.${NC}"
    
    if [ $? -ne 0 ]; then
        cd ..
        sudo rm -rf "$APP_DIR"
        git clone https://github.com/YOUR_USERNAME/tradingview-webhook-bot.git "$APP_NAME"
        cd "$APP_DIR"
    fi
else
    echo -e "${YELLOW}Uygulama klasörü oluşturuluyor...${NC}"
    
    # Not: Gerçek bir repository kullanımında buraya GitHub repo URL'sini koymalısınız
    # git clone https://github.com/YOUR_USERNAME/tradingview-webhook-bot.git "$APP_NAME"
    
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
fi

# Mevcut uygulamayı kopyala
echo -e "\n${GREEN}[4/9]${NC} Uygulama dosyaları kopyalanıyor..."
read -p "Lütfen uygulama dosyalarının bulunduğu yerel dizin yolunu girin: " LOCAL_APP_PATH

# Uygulama dosyalarını kopyala
rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' "$LOCAL_APP_PATH/" "$APP_DIR/"

# Python sanal ortamı oluştur
echo -e "\n${GREEN}[5/9]${NC} Python sanal ortamı oluşturuluyor..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate

# Gerekli kütüphaneleri kur
echo -e "\n${GREEN}[6/9]${NC} Python kütüphaneleri kuruluyor..."
pip install -r requirements.txt || (echo "requirements.txt bulunamadı, gerekli kütüphaneleri manuel olarak kuruyorum..." && pip install flask flask-login bitget-api requests python-telegram-bot gunicorn)

# Systemd servis dosyasını oluştur
echo -e "\n${GREEN}[7/9]${NC} Systemd servis dosyası oluşturuluyor..."

cat << EOF | sudo tee /etc/systemd/system/${SYSTEMD_SERVICE_NAME}.service
[Unit]
Description=TradingView Webhook Bitget Bot
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/gunicorn --bind 127.0.0.1:${APP_PORT} app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Nginx yapılandırması
echo -e "\n${GREEN}[8/9]${NC} Nginx yapılandırması oluşturuluyor..."

cat << EOF | sudo tee "$NGINX_CONF"
server {
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Nginx sembolik bağlantı oluştur ve yapılandırmayı test et
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
sudo nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}Nginx yapılandırma hatalı. Lütfen kontrol edin.${NC}"
    exit 1
fi

# Servisleri başlat
echo -e "\n${GREEN}[9/9]${NC} Servisler başlatılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable ${SYSTEMD_SERVICE_NAME}
sudo systemctl start ${SYSTEMD_SERVICE_NAME}
sudo systemctl restart nginx

# SSL sertifikası al
echo -e "\n${GREEN}[Bonus]${NC} SSL sertifikası ayarlanıyor..."
echo -e "${YELLOW}Not: Bu işlem için domain'in DNS kayıtlarının EC2 sunucunuzun IP adresine yönlendirilmiş olması gerekiyor.${NC}"

read -p "SSL sertifikası almak için domain DNS ayarlarını yaptınız mı? (E/h): " SSL_CONFIRM
SSL_CONFIRM=${SSL_CONFIRM:-E}

if [[ $SSL_CONFIRM == "E" || $SSL_CONFIRM == "e" ]]; then
    sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}SSL sertifikası alınamadı. DNS ayarlarınızı kontrol edin ve daha sonra şu komutu çalıştırın:${NC}"
        echo -e "${YELLOW}sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}${NC}"
    else
        echo -e "${GREEN}SSL sertifikası başarıyla yapılandırıldı!${NC}"
    fi
else
    echo -e "${YELLOW}SSL sertifikasını daha sonra şu komutla manuel olarak yapılandırabilirsiniz:${NC}"
    echo -e "${YELLOW}sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}${NC}"
fi

# Özet
echo -e "\n${GREEN}==================== KURULUM TAMAMLANDI ====================${NC}"
echo -e "${GREEN}TradingView Webhook - Bitget Bot başarıyla kuruldu!${NC}"
echo -e "Web uygulaması şu adreste çalışıyor: https://${DOMAIN}"
echo
echo -e "${YELLOW}Uygulama Bilgileri:${NC}"
echo -e "Uygulama Dizini: ${APP_DIR}"
echo -e "Systemd Servis: ${SYSTEMD_SERVICE_NAME}.service"
echo -e "Nginx Yapılandırması: ${NGINX_CONF}"
echo
echo -e "${YELLOW}Yararlı Komutlar:${NC}"
echo -e "Uygulama Durumunu Kontrol Et: ${GREEN}sudo systemctl status ${SYSTEMD_SERVICE_NAME}${NC}"
echo -e "Uygulamayı Yeniden Başlat: ${GREEN}sudo systemctl restart ${SYSTEMD_SERVICE_NAME}${NC}"
echo -e "Nginx'i Yeniden Başlat: ${GREEN}sudo systemctl restart nginx${NC}"
echo -e "Log Dosyalarını Görüntüle: ${GREEN}sudo journalctl -u ${SYSTEMD_SERVICE_NAME}${NC}" 