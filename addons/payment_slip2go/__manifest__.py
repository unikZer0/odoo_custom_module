{
    'name': 'Slip2Go Payment Acquirer',
    'version': '1.0',
    'summary': 'Payment Integration with Slip2Go including QR PromptPay',
    'author': 'You',
    'depends': [
        'base',
        'payment',
        'account',
        'portal',
        'website',
    ],
    'data': [
        'data/payment_provider_data.xml',
        'views/payment_slip2go_views.xml',
        # 'views/payment_slip2go_templates.xml',  # Commented out - template ID needs to be fixed for Odoo 17
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

