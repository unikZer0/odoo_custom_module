{
    "name": "Payment Slip2Go",
    "version": "1.0.0",
    "category": "Accounting",
    "summary": "Slip2Go payment provider",
    "license": "LGPL-3",
    "depends": ["base", "payment", "account", "website", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/payment_slip2go_provider_data.xml",
        "views/payment_slip2go_provider_views.xml",
        "views/payment_slip2go_templates.xml",
    ],
    "assets": {
        "website.assets_frontend": [
            "payment_slip2go/static/src/js/scan_and_post.js",
        ],
    },
    "installable": True,
    "application": False,
}
