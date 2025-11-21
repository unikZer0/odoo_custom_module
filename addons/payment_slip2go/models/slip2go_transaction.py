
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Slip2goTransaction(models.Model):
    _name = "slip2go.transaction"
    _description = "Slip2Go Transaction"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        "Reference",
        default=lambda self: self.env["ir.sequence"].next_by_code("slip2go.tx") or "S2G",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    provider_id = fields.Many2one(
        "payment.provider",
        string="Payment Provider",
        default=lambda self: self.env["payment.provider"]
        .sudo()
        .search([("code", "=", "slip2go")], limit=1),
    )
    partner_id = fields.Many2one("res.partner", "Customer")
    invoice_id = fields.Many2one("account.move", "Invoice", required=True)
    amount = fields.Monetary("Amount", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", "Currency")
    slip_attachment_id = fields.Many2one("ir.attachment", "Slip Attachment")
    qr_payload = fields.Text("QR Payload")
    acquirer_reference = fields.Char("Acquirer Reference")
    response_data = fields.Text("Slip2Go Response (JSON)")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
            ("done", "Done"),
        ],
        default="draft",
        tracking=True,
    )
    verified_at = fields.Datetime("Verified At")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self.env["ir.sequence"].next_by_code("slip2go.tx") or "S2G"
            invoice = self.env["account.move"].browse(vals.get("invoice_id"))
            if invoice:
                vals.setdefault("partner_id", invoice.partner_id.id)
                vals.setdefault("currency_id", invoice.currency_id.id)
                vals.setdefault("company_id", invoice.company_id.id)
                vals.setdefault("amount", invoice.amount_residual)
        return super().create(vals_list)

    def action_set_pending(self):
        self.filtered(lambda tx: tx.state == "draft").write({"state": "pending"})

    def action_mark_verified(self):
        self.write(
            {"state": "verified", "verified_at": fields.Datetime.now()}
        )

    def action_mark_rejected(self, reason: str | None = None):
        self.write({"state": "rejected"})
        if reason and self.invoice_id:
            self.invoice_id.message_post(body=_("Slip2Go rejected: %s") % reason)

    def action_register_payment(self):
        for transaction in self:
            invoice = transaction.invoice_id
            if not invoice:
                raise UserError(_("No invoice linked to Slip2Go transaction."))

            if invoice.payment_state in ("paid", "in_payment"):
                invoice.message_post(
                    body=_("Slip2Go transaction %s received after payment.") % transaction.name
                )
                transaction.state = "done"
                continue

            journal = (
                transaction.provider_id.journal_id
                or invoice.journal_id
                or self.env["account.journal"]
                .sudo()
                .search(
                    [
                        ("type", "=", "bank"),
                        ("company_id", "=", transaction.company_id.id),
                    ],
                    limit=1,
                )
            )
            if not journal:
                raise UserError(
                    _("Configure a bank journal on the Slip2Go provider or invoice.")
                )

            payment_method_line = journal.inbound_payment_method_line_ids[:1]
            if not payment_method_line:
                raise UserError(
                    _("The journal %s must have at least one inbound payment method.") % journal.name
                )

            payment_register = (
                self.env["account.payment.register"]
                .sudo()
                .with_context(active_model="account.move", active_ids=invoice.ids)
                .create(
                    {
                        "payment_date": fields.Date.context_today(invoice),
                        "journal_id": journal.id,
                        "amount": transaction.amount or invoice.amount_residual,
                        "payment_method_line_id": payment_method_line.id,
                        "communication": f"Slip2Go {transaction.name}",
                    }
                )
            )
            payment_register.action_create_payments()

            invoice.message_post(
                body=_("Slip2Go payment registered (%s).") % transaction.name
            )
            transaction.state = "done"
