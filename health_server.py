from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
    <head><title>Telegram Bots Status</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>✅ Telegram Bots Active</h1>
        <p>SMS Forwarder Bot & Number Bot are running!</p>
        <p style="color: green; font-size: 24px;">🟢 ONLINE</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "ok", "bots": ["sms_forwarder", "number_bot"]}, 200

@app.route('/ping')
def ping():
    return "pong", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
