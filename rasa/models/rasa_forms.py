from odoo import api, models, fields
from . import json_fields

class RasaForms(models.Model):
    _name = "rasa_forms"
    _description = "rasa_forms"

    name = fields.Char()
    rasa_response_id = fields.Many2one("rasa_response")
    question_ids = fields.One2many("rasa_form_questions","form_id")


class RasaFormQuestions(models.Model):
    _name = "rasa_form_questions"
    _description = "rasa_form_questions"

    name = fields.Text()
    regex = fields.Text()
    form_id = fields.Many2one("rasa_forms")
