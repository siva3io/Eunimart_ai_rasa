from odoo import api, models, fields

class RasaIntent(models.Model):
    _name = "rasa_intent"
    _description = "rasa_intent"

    name = fields.Char()
    rasa_response_id = fields.Many2one("rasa_response")
    threshold_value = fields.Float()
    domain = fields.Char()
    company_ids = fields.Many2many("res.company")
    user_ids = fields.Many2many("res.users")
    intent_type = fields.Selection([
                                ("api","API"),
                                ("eunimart","Eunimart"), 
                                ("partners","Parents"),
                                ("all","All")  ])
