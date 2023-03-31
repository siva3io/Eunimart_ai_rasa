from odoo import api, models, fields


class RasaResponseQues(models.Model):
    _name = "rasa_response_questions"
    _description = "rasa_response_questions"
    _order = "sequence"

    name = fields.Char()
    code = fields.Char()
    rasa_response_question_button_ids = fields.One2many("rasa_response_question_button","rasa_response_question_id")
    rasa_response_id = fields.Many2one("rasa_response", "question_ids")
    payload_action = fields.Char("Payload Action")
    form_id = fields.Many2one("rasa_forms")
    media_url = fields.Char()
    html = fields.Html()
    sequence = fields.Integer()
    sequence_next = fields.Integer()
    alternative_response = fields.Text()
    ondc_payload = fields.Char("ONDC Payload")
    attachment = fields.Binary("Image or Other Attachment")
    