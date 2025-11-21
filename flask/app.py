from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/webhook/slip2go', methods=['POST'])
def slip2go_webhook():
    """Example webhook endpoint (not used by Odoo verification yet)."""
    data = request.json
    print("Webhook received:", data)
    return jsonify({"status": "ok"}), 200


@app.route('/api/verify-slip/qr-code/info', methods=['POST'])
def verify_slip():
    """Endpoint called by Odoo to verify a Slip2Go QR payload.

    For now this is a stub that always returns success so the
    integration flow can be tested end-to-end.
    """
    data = request.json or {}
    print("Verify request:", data)
    # In a real implementation, you would validate the QR payload here.
    return jsonify({
        "status": "success",
        "message": "Slip verified (stub)",
    }), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
