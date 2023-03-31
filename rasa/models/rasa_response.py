from odoo import models, fields
from . import json_fields


class RasaResponse(models.Model):
    _name = "rasa_response"
    _description = "rasa_response"

    # ----------------------------------------
    # default_rasa_response = its context
    # acton_listen = open conversatin paylaod - Check of intent detection
    # action_attachment = open binary paylaod
    # action_end_conext_line = mark context line as completed
    # ----------------------------------------

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    is_random_response = fields.Boolean(string="Is Random Response", default=False)
    is_html_response = fields.Boolean(string="Is HTML Response")
    is_context = fields.Boolean(string="Is Context")
    is_context_question = fields.Boolean(string="Is Context Question")
    payload_action = fields.Char(string="Payload Action")
    seller_payload_action = fields.Char(string="Seller Payload Action")
    buyer_payload_action = fields.Char(string="Buyer Payload Action")
    question_ids = fields.One2many(comodel_name="rasa_response_questions", inverse_name="rasa_response_id")
    domain = fields.Char(string='Domain', default=[])
    model_id = fields.Many2one(comodel_name="rasa_apis", string="Model")
    python_code = fields.Char(string="Python Code")
    # output_fields = fields.Many2many("ir.model.fields", domain="[('model_id', '=', model_id)]")
    output_python = fields.Char(string="Output Python")
    output_json = json_fields.JsonField(string="Output Json", default={'text': ''})
    context_workflow_line_ids = fields.One2many(comodel_name="rasa.context.workflow.line",
                                                inverse_name="rasa_response_id")
    ondc_payload = fields.Char("ONDC Payload")
    attachment = fields.Binary("Image or Other Attachment")

# ---------- Flow ----------
#   1. User sends a message
#   2. Webook is called
#   3. Call API Odoo
#   4.1. DEFAULt - unregistered, registered_buyer, registered_seller, default_registered, [notify_order]
#   4.2. Context - if active_rasa_response_id elif active_context_data_id
