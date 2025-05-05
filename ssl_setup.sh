#!/bin/bash

# SSL kurulum ve konfigürasyon script'i
# Bu script self-signed sertifika oluşturur ve Flask uygulaması için yapılandırır
# Yazar: Claude AI
# Güncelleme: $(date)

# Renkli çıktı için
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonksiyonlar
check_command() {
    if ! command -v $1 &> /dev/null
    then
        echo -e "${RED}$1 komutu bulunamadı. Lütfen önce $1 paketini yükleyin.${NC}"
        exit 1
    fi
}

# Gerekli komutların kontrolü
echo -e "${YELLOW}Gerekli paketler kontrol ediliyor...${NC}"
check_command "openssl"

# Çalışma dizini oluşturma
SSL_DIR="./ssl"
mkdir -p $SSL_DIR
echo -e "${GREEN}SSL sertifikaları için dizin oluşturuldu: $SSL_DIR${NC}"

# Self-signed sertifika oluşturma
echo -e "${YELLOW}Self-signed SSL sertifikası oluşturuluyor...${NC}"
openssl req -x509 -newkey rsa:4096 -nodes -out "$SSL_DIR/cert.pem" -keyout "$SSL_DIR/key.pem" -days 365 -subj "/C=TR/ST=Turkey/L=Istanbul/O=MyOrganization/CN=localhost"
if [ $? -ne 0 ]; then
    echo -e "${RED}Sertifika oluşturulurken hata oluştu.${NC}"
    exit 1
fi

echo -e "${GREEN}Sertifikalar başarıyla oluşturuldu:${NC}"
echo -e "  ${YELLOW}Sertifika:${NC} $SSL_DIR/cert.pem"
echo -e "  ${YELLOW}Private Key:${NC} $SSL_DIR/key.pem"

# Python için SSL desteği ile Flask uygulamasını çalıştırma örneği app_ssl.py
echo -e "${YELLOW}Flask uygulaması için SSL destekli başlangıç dosyası oluşturuluyor...${NC}"

cat > "app_ssl.py" << 'EOF'
from app import app

if __name__ == '__main__':
    # SSL sertifikalarını kullanarak HTTPS üzerinden çalıştır
    app.run(debug=True, host='0.0.0.0', port=5000, 
            ssl_context=('ssl/cert.pem', 'ssl/key.pem'))
EOF

echo -e "${GREEN}SSL destekli Flask başlangıç dosyası oluşturuldu: app_ssl.py${NC}"

# Ngrok için ek bilgi
echo -e "\n${YELLOW}NGROK ile Geçici HTTPS Tüneli Oluşturma:${NC}"
echo -e "1. Ngrok'u https://ngrok.com adresinden indirin ve kurun"
echo -e "2. Ngrok tüneli oluşturmak için:"
echo -e "   ${YELLOW}ngrok http https://localhost:5000${NC}"
echo -e "3. Ngrok size geçici bir HTTPS URL'i verecektir, bunu TradingView webhook URL'i olarak kullanabilirsiniz"

# Uygulama başlatma talimatları
echo -e "\n${GREEN}Uygulamayı SSL ile başlatmak için:${NC}"
echo -e "   ${YELLOW}python app_ssl.py${NC}"

echo -e "\n${GREEN}İşlem tamamlandı! SSL yapılandırması hazır.${NC}"
echo -e "${YELLOW}Not: Bu self-signed sertifikalar tarayıcılarda güvenlik uyarısına neden olabilir, ama webhook'lar için sorun olmaz.${NC}" 