from email.policy import default
from odoo import api, models, fields
from . import json_fields


class RasaResponseQuesButton(models.Model):
    _name = "rasa_response_question_button"
    _description = "rasa_response_question_button"

    name = fields.Char()
    rasa_response_question_id = fields.Many2one("rasa_response_questions")
    payload_action = fields.Char("Payload Action")
    rasa_response_id = fields.Many2one("rasa_response")
    sequence = fields.Integer()
    sequence_next = fields.Integer()
    domain = fields.Char(default=[])
    model_id = fields.Many2one("rasa_apis")
    python_code = fields.Char()
    # output_fields = fields.Many2many("ir.model.fields", domain="[('model_id', '=', model_id)]")
    output_python = fields.Char()
    output_json = json_fields.JsonField(string="Output Json",default={ 'text' : '' })
    ondc_payload = fields.Char("ONDC Payload")
