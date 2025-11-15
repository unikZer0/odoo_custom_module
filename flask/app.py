from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/slip2go', methods=['POST'])
def slip2go_webhook():
    data = request.json
    print("Webhook received:", data)
    return {"status": "okcc"}, 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
