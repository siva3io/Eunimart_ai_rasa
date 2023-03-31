from odoo import fields, models


class RasaNotification(models.Model):
    _name = "rasa.notification"
    _description = "Rasa Notification"

    name = fields.Char(string='Name', required=True)
    input_code = fields.Char(string='Input Code', required=True)
    notification_code = fields.Char(string="Notification Code")
