from odoo import models, fields, api

class PaymentTransactionSlip2Go(models.Model):
    _inherit = 'payment.transaction'

    slip2go_transaction_id = fields.Char("Slip2Go Transaction ID", readonly=True)
    slip2go_bank_code = fields.Char("Bank Code", readonly=True)

    @api.model
    def process_slip2go_callback(self, data):
        """Legacy method for backward compatibility. Use _process_notification_data instead."""
        provider = self.env['payment.provider'].search([('code', '=', 'slip2go')], limit=1)
        if provider:
            provider._process_notification_data(data)
        return True
