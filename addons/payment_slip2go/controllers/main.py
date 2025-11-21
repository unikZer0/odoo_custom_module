
import json
import logging

import requests

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from ..utils.promptpay import promptpay_qr_base64

_logger = logging.getLogger(__name__)


class Slip2GoPaymentController(http.Controller):

    @http.route(
        [
            "/payment/slip2go/pay/<int:invoice_id>",
            "/invoice/<int:invoice_id>/pay/slip2go",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def slip2go_pay(self, invoice_id, access_token=None, **kwargs):
        invoice = self._get_invoice(invoice_id, access_token)
        if not invoice:
            return request.not_found()

        provider = self._get_provider()
        amount = float(invoice.amount_residual)

        merchant_name = provider.company_id.name or provider.name
        merchant_city = invoice.company_id.city or "BANGKOK"
        qr_base64, qr_payload = promptpay_qr_base64(
            provider.slip2go_promptpay_id,
            amount=amount,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
        )

        transaction = (
            request.env["slip2go.transaction"]
            .sudo()
            .search(
                [
                    ("invoice_id", "=", invoice.id),
                    ("state", "in", ["draft", "pending"]),
                ],
                limit=1,
            )
        )
        if transaction:
            transaction.write({"qr_payload": qr_payload, "amount": amount})
        else:
            transaction = (
                request.env["slip2go.transaction"]
                .sudo()
                .create(
                    {
                        "invoice_id": invoice.id,
                        "provider_id": provider.id,
                        "qr_payload": qr_payload,
                        "amount": amount,
                        "state": "pending",
                    }
                )
            )

        # ensure portal links keep working for public users
        if not access_token and request.env.user == request.website.user_id:
            access_token = invoice._portal_ensure_token()

        return request.render(
            "payment_slip2go.payment_page",
            {
                "invoice": invoice,
                "provider": provider,
                "qr_base64": qr_base64,
                "qr_payload": qr_payload,
                "transaction": transaction,
                "access_token": access_token,
            },
        )

    @http.route("/payment/slip2go/verify", type="json", auth="public", csrf=False)
    def slip2go_verify(self, access_token=None, **kwargs):
        invoice_id = kwargs.get("invoice_id")
        qr_data = kwargs.get("qr")
        transaction_id = kwargs.get("transaction_id")
        image_data = kwargs.get("image")
        image_name = kwargs.get("filename")
        image_mimetype = kwargs.get("mimetype")

        if not invoice_id:
            return {"status": "failed", "message": "Missing invoice reference."}

        invoice = self._get_invoice(invoice_id, access_token)
        if not invoice:
            return {"status": "failed", "message": "Invoice not found or unauthorized."}

        provider = self._get_provider()

        transaction_model = request.env["slip2go.transaction"].sudo()
        transaction = (
            transaction_model.browse(int(transaction_id)) if transaction_id else transaction_model
        )
        if transaction and transaction.exists():
            transaction.ensure_one()
            if transaction.invoice_id.id != invoice.id:
                return {"status": "failed", "message": "Transaction mismatch."}
        else:
            transaction = request.env["slip2go.transaction"].sudo().create(
                {
                    "invoice_id": invoice.id,
                    "provider_id": provider.id,
                    "state": "pending",
                }
            )

        if image_data:
            attachment = self._create_attachment(
                invoice, image_data, image_name, image_mimetype
            )
            transaction.write({"slip_attachment_id": attachment.id})
        else:
            attachment = transaction.slip_attachment_id

        qr_payload = qr_data or transaction.qr_payload
        if not qr_payload:
            return {"status": "failed", "message": "QR payload is required."}

        payload = {"payload": {"qrCode": qr_payload}}
        if attachment:
            payload["payload"]["slipImage"] = attachment.datas

        _logger.info(
            "Slip2Go verify payload invoice=%s tx=%s payload=%s",
            invoice.id,
            transaction.id,
            payload,
        )
        try:
            data = self._call_slip2go(provider, "/api/verify-slip/qr-code/info", payload)
            _logger.info(
                "Slip2Go verify response invoice=%s tx=%s status=%s body=%s",
                invoice.id,
                transaction.id,
                data.get("status"),
                data,
            )
        except requests.RequestException as exc:
            _logger.exception("Slip2Go verify call failed")
            return {"status": "failed", "message": str(exc)}

        amount = self._extract_amount(data.get("amount"), invoice.amount_residual)
        transaction.write(
            {
                "qr_payload": qr_payload,
                "response_data": json.dumps(data),
                "acquirer_reference": data.get("acquirer_ref") or data.get("transactionId"),
                "amount": amount,
            }
        )

        normalized_status = self._normalize_status(data.get("status"))
        if normalized_status in {"success", "verified", "paid", "done"}:
            transaction.action_mark_verified()
            try:
                transaction.action_register_payment()
            except UserError as exc:
                return {"status": "failed", "message": exc.name or str(exc)}
            return {"status": "ok", "message": "Slip verified. Thank you!"}

        transaction.action_mark_rejected(data.get("message"))
        return {
            "status": "failed",
            "message": data.get("message") or "Slip2Go rejected the slip.",
        }

    @http.route(
        "/payment/slip2go/webhook", type="json", auth="none", csrf=False, methods=["POST"]
    )
    def slip2go_webhook(self, **payload):
        provider = self._get_provider()
        data = request.jsonrequest or payload

        if not self._is_valid_webhook(provider, data):
            _logger.warning("Slip2Go webhook rejected: bad signature")
            return {"status": "error", "message": "unauthorized"}

        invoice_ref = (
            data.get("invoice_ref")
            or data.get("invoice_id")
            or data.get("reference")
            or data.get("name")
        )
        if not invoice_ref:
            return {"status": "error", "message": "missing invoice reference"}

        invoice = (
            request.env["account.move"]
            .sudo()
            .search(
                [
                    "|",
                    ("name", "=", invoice_ref),
                    ("payment_reference", "=", invoice_ref),
                ],
                limit=1,
            )
        )
        if not invoice:
            _logger.warning("Slip2Go webhook invoice not found: %s", invoice_ref)
            return {"status": "error", "message": "invoice_not_found"}

        amount = self._extract_amount(data.get("amount"), invoice.amount_residual)
        transaction = (
            request.env["slip2go.transaction"]
            .sudo()
            .create(
                {
                    "invoice_id": invoice.id,
                    "provider_id": provider.id,
                    "qr_payload": data.get("qr_payload"),
                    "acquirer_reference": data.get("acquirer_ref") or data.get("transactionId"),
                    "response_data": json.dumps(data),
                    "amount": amount,
                    "state": "pending",
                }
            )
        )

        normalized_status = self._normalize_status(data.get("status"))
        if normalized_status in {"success", "verified", "paid", "done"}:
            transaction.action_mark_verified()
            transaction.action_register_payment()
            return {"status": "ok"}

        transaction.action_mark_rejected(data.get("message"))
        return {"status": "ignored"}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_invoice(self, invoice_id, access_token=None):
        invoice = request.env["account.move"].sudo().browse(int(invoice_id))
        if not invoice or not invoice.exists():
            return None

        if access_token:
            return invoice if invoice._portal_ensure_token() == access_token else None

        if request.env.user == request.website.user_id:
            return None
        return invoice

    def _get_provider(self):
        provider = (
            request.env["payment.provider"].sudo().search([("code", "=", "slip2go")], limit=1)
        )
        if not provider:
            raise UserError("Slip2Go provider not configured.")
        if not provider.slip2go_secret:
            raise UserError("Configure the Slip2Go secret.")
        if not provider.slip2go_promptpay_id:
            raise UserError("Configure PromptPay ID on the Slip2Go provider.")
        return provider

    def _call_slip2go(self, provider, endpoint, payload):
        api_url = (provider.slip2go_api_url or "http://flask:5000").rstrip("/")
        url = f"{api_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {provider.slip2go_secret}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    def _create_attachment(self, invoice, data_url, filename, mimetype):
        encoded = data_url
        if "," in data_url:
            header, encoded = data_url.split(",", 1)
            if not mimetype and ":" in header:
                mimetype = header.split(";")[0].split(":")[1]

        if not filename:
            filename = f"{invoice.name}_slip.png"
        if not mimetype:
            mimetype = "application/octet-stream"

        attachment = request.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "datas": encoded,
                "mimetype": mimetype,
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )
        return attachment

    def _normalize_status(self, status):
        if status is True:
            return "success"
        if status is False or status is None:
            return "failed"
        return str(status).lower()

    def _is_valid_webhook(self, provider, data):
        header_sig = request.httprequest.headers.get("X-Slip2Go-Secret")
        auth_header = request.httprequest.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header else ""
        provided = header_sig or token or data.get("secret")
        return provided and provided == provider.slip2go_secret

    def _extract_amount(self, raw_amount, fallback):
        if raw_amount in (None, False):
            return fallback
        try:
            return float(raw_amount)
        except (TypeError, ValueError):
            return fallback
