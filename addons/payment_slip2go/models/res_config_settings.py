
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    slip2go_api_url = fields.Char(
        "Slip2Go API URL",
        config_parameter="payment_slip2go.api_url",
        default="http://flask:5000",
    )
    slip2go_secret = fields.Char(
        "Slip2Go Secret Key",
        config_parameter="payment_slip2go.secret",
    )
    slip2go_bank_account = fields.Char(
        "Slip2Go Bank account",
        config_parameter="payment_slip2go.bank_account",
    )
    slip2go_promptpay_id = fields.Char(
        "Slip2Go PromptPay ID",
        config_parameter="payment_slip2go.promptpay_id",
    )
