from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class Slip2GoCallbackController(http.Controller):

    @http.route('/slip2go/payment-confirm', type='json', auth='none', methods=['POST'], csrf=False)
    def slip2go_confirm(self, **kwargs):
        """Handle Slip2Go payment confirmation webhook."""
        try:
            data = request.jsonrequest
            _logger.info("Received Slip2Go callback: %s", data)

            # Get the provider
            provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'slip2go'),
                ('state', 'in', ['enabled', 'test'])
            ], limit=1)

            if not provider:
                _logger.error("Slip2Go provider not found")
                return {'status': 'error', 'message': 'Provider not found'}

            # Process the notification
            tx_sudo = provider._process_notification_data(data)
            
            if tx_sudo:
                _logger.info("Processed Slip2Go transaction %s with status %s", 
                           tx_sudo.reference, tx_sudo.state)
                return {'status': 'ok', 'transaction_id': tx_sudo.id}
            else:
                _logger.warning("No transaction found for Slip2Go callback")
                return {'status': 'error', 'message': 'Transaction not found'}

        except Exception as e:
            _logger.error("Error processing Slip2Go callback: %s", str(e))
            return {'status': 'error', 'message': str(e)}
