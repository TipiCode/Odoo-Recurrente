from odoo import models, fields

class RecurrentePaymentInstallment(models.Model):
    _name = "payment.installment_recurrente"
    _description = "Payment Installment Recurrente"

    name = fields.Char(string="Name")
