from odoo import models, fields

class PaymentProviderSlip2Go(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("slip2go", "Slip2Go")],
        ondelete={"slip2go": "set default"},
    )

    slip2go_api_url = fields.Char(
        "Slip2Go API URL",
        default="http://flask:5000",
        help="Internal hostname or public URL that Odoo can reach.",
    )
    slip2go_secret = fields.Char(
        "Slip2Go Secret Key",
        help="Bearer token shared with Slip2Go for verifying requests.",
    )
    slip2go_bank_account = fields.Char(
        "Bank account (for display)",
        help="Shown on the payment page as a human readable reference.",
    )
    slip2go_promptpay_id = fields.Char(
        "PromptPay ID",
        help="Phone / PromptPay ID used to build the QR payload.",
    )
