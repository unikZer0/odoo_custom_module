from odoo import models, fields

class PaymentProviderSlip2Go(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('slip2go', "Slip2Go")],
        ondelete={'slip2go': 'set default'}
    )

    slip2go_api_key = fields.Char("Slip2Go API Key")
    slip2go_api_secret = fields.Char("Slip2Go API Secret")
    slip2go_bank_code = fields.Char("Default Bank Code")

    enable_promptpay = fields.Boolean("Enable QR PromptPay")
    promptpay_number = fields.Char("PromptPay Number")
