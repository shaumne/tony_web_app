# TradingView Webhook Test Aracı

Bu araç, TradingView'dan gelen webhook sinyallerini taklit ederek web uygulamanızı test etmenizi sağlar.

## Kurulum

Gerekli kütüphaneyi yükleyin:

```bash
pip install requests
```

## Kullanım

### Webhook Testi (JSON formatında)

```bash
python webhook_test.py --url "http://sizin-webhook-urliniz.com/webhook" --pair "BTCUSDT" --direction "long" --action "open"
```

Bu komut, webhook URL'nize `{"signal": "BTCUSDT/long/open"}` formatında bir JSON verisi gönderecektir.

### Parametreler

- `--url`: Webhook URL'niz (zorunlu)
- `--type`: Sinyal tipi, "basic" veya "tradingview" (varsayılan: "basic")
- `--pair`: İşlem çifti (varsayılan: "BTCUSDT")
- `--direction`: İşlem yönü, "long" veya "short" (varsayılan: "long")
- `--action`: İşlem emri, "open" veya "close" (varsayılan: "open")

### Örnekler

1. Long pozisyon açma sinyali:
```bash
python webhook_test.py --url "http://localhost:5000/webhook" --direction "long" --action "open"
```

2. Long pozisyon kapatma sinyali:
```bash
python webhook_test.py --url "http://localhost:5000/webhook" --direction "long" --action "close"
```

3. Short pozisyon açma sinyali:
```bash
python webhook_test.py --url "http://localhost:5000/webhook" --direction "short" --action "open"
```

4. Short pozisyon kapatma sinyali:
```bash
python webhook_test.py --url "http://localhost:5000/webhook" --direction "short" --action "close"
```

5. TradingView formatında ayrıntılı sinyal gönderme:
```bash
python webhook_test.py --url "http://localhost:5000/webhook" --type "tradingview" --direction "long" --action "open"
```

## Not

Bu araç, uygulamanızın TradingView webhook sinyallerini doğru işleyip işlemediğini test etmek için kullanılmalıdır. Testlerinizde, uygulamanızın beklenen davranışı gösterdiğinden emin olun:

1. Webhook'un doğru şekilde alındığını
2. Sinyal formatının doğru ayrıştırıldığını 
3. Bitget API ile işlem yapıldığını
4. Telegram bildirimi gönderildiğini

kontrolünü yapabilirsiniz.

## Sorun Giderme

- Flask uygulaması `{"signal": "BTCUSDT/long/open"}` formatında bir JSON verisi bekliyor.
- HTTP 400 hatası alıyorsanız, gönderdiğiniz JSON formatının doğru olduğundan emin olun.
- Webhook URL'nizin doğru olduğundan emin olun.
- Flask uygulamanızın çalıştığından emin olun.
- API anahtarlarınızın ve bağlantı bilgilerinizin doğru olduğundan emin olun. 