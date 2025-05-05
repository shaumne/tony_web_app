from app import app
 
if __name__ == '__main__':
    # SSL sertifikalarını kullanarak HTTPS üzerinden çalıştır
    app.run(debug=True, host='0.0.0.0', port=5000, 
            ssl_context=('ssl/cert.pem', 'ssl/key.pem')) 