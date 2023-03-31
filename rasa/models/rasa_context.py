# -*- coding: utf-8 -*-

from odoo import models, fields
from . import json_fields


class RasaContextTemplate(models.Model):
    _name = 'rasa.context.template'
    _description = 'Rasa Context Template'

    # check_ : ex: check_auth

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    mandatory = fields.Boolean(string='Mandatory', default=False)
    temporary = fields.Boolean(string='Temporary', default=False, help='If checked, the context will be deleted')
    priority = fields.Integer(string='Priority', default=10, help='The lower the value, the higher the priority')
    context_line_ids = fields.One2many(comodel_name='rasa.context.template.line', inverse_name='template_id',
                                       string='Context Lines')
    response_id = fields.Many2one(comodel_name='rasa_response', string='Next Response')
    parent_id = fields.Many2one(comodel_name='rasa.context.template', string='Parent Template')
    child_ids = fields.One2many(comodel_name='rasa.context.template', inverse_name='parent_id',
                                string='Child Templates')
    rasa_nlu_path = fields.Char(string='Rasa NLU Path')
    eda_context = fields.Char(string='EDA Context', help='Extra Info to send with the data in EDAs')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code must be unique!'),
    ]


class RasaContextTemplateLine(models.Model):
    _name = 'rasa.context.template.line'
    _description = 'Rasa Context Template Line'
    _rec_name = 'rel_response_id'
    _order = 'sequence'

    template_id = fields.Many2one(comodel_name='rasa.context.template', string='Template')
    sequence = fields.Integer(string='Sequence')
    next_sequence = fields.Integer(string='Next Sequence')
    next_context_id = fields.Many2one(comodel_name='rasa.context.template', string='Next Context')
    python_code = fields.Text(string='Python Code')
    rasa_nlu_path = fields.Char(string='Rasa NLU Path', help="If path then action_listen")
    rel_response_id = fields.Many2one(comodel_name='rasa_response', string='Related Response', required=True,
                                      ondelete='cascade')
    next_response_id = fields.Many2one(comodel_name='rasa_response', string='Next Response')


class RasaContextData(models.Model):
    _name = 'rasa.context.data'
    _description = 'Rasa Context Data'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    mandatory = fields.Boolean(string='Mandatory', default=False)
    temporary = fields.Boolean(string='Temporary', default=False)
    priority = fields.Integer(string='Priority', default=10)
    template_id = fields.Many2one(comodel_name='rasa.context.template', string='Template')
    user_id = fields.Many2one(comodel_name='chatbot.user', string='Chatbot User', ondelete="cascade")
    user_token = fields.Char(string='User Token', required=True)
    context_line_ids = fields.One2many(comodel_name='rasa.context.data.line', inverse_name='data_id',
                                       string='Context Lines')
    completed = fields.Boolean(string='Completed', default=False)
    response_id = fields.Many2one(comodel_name='rasa_response', string='Response')
    rasa_nlu_path = fields.Char(string='Rasa NLU Path')
    eda_context = fields.Char(string='EDA Context', help='Extra Info to send with the data in EDAs')


class RasaContextDataLine(models.Model):
    _name = 'rasa.context.data.line'
    _description = 'Rasa Context Data Line'
    _rec_name = 'data_id'
    _order = 'sequence'

    data_id = fields.Many2one(comodel_name='rasa.context.data', string='Data')
    sequence = fields.Integer(string='Sequence')
    next_sequence = fields.Integer(string='Next Sequence')
    python_code = fields.Text(string='Python Code')
    next_context_id = fields.Many2one(comodel_name='rasa.context.template', string='Next Context')
    rel_response_id = fields.Many2one(comodel_name='rasa_response', string='Related Response', required=True,
                                      ondelete='cascade')
    raw_data = json_fields.JsonField(string='Raw Data')
    message = fields.Char(string='Message')
    completed = fields.Boolean(string='Completed', default=False)


class ContextWorkflow(models.Model):
    _name = 'rasa.context.workflow'
    _description = 'Rasa Context Workflow'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence')
    context_workflow_line_ids = fields.One2many(comodel_name="rasa.context.workflow.line",
                                                inverse_name="context_workflow_id")


class ContextWorkflowLine(models.Model):
    _name = 'rasa.context.workflow.line'
    _description = 'Rasa Context Workflow Line'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence')
    next_sequence = fields.Integer(string='Next Sequence')
    is_mandatory = fields.Boolean(string='Is Mandatory', default=False)
    is_generic = fields.Boolean(string='Is Generic', default=False)
    is_parametric = fields.Boolean(string='Is Parametric', default=False)
    is_query = fields.Boolean(string='Is Query', default=False)
    context_workflow_id = fields.Many2one(comodel_name="rasa.context.workflow", string="Context Workflow")
    context_template_id = fields.Many2one(comodel_name="rasa.context.template", string="Context Template")
    rasa_response_id = fields.Many2one(comodel_name="rasa_response", string="Rasa Response")


class EDAResponseManager(models.Model):
    _name = 'eda.response.manager'
    _description = 'EDA Response Manager'

    # {
    #    "context": "context_id",
    #    "user_token": "user_token",
    #    "data": "action, message_data, attachment_data,etc",
    #    "response": "",
    #    "data_science_ok",
    #    "technology_ok",
    #    "data_science_processing",
    #    "technology_processing"
    # }
    name = fields.Char(string='Response Code', required=True)
    response_id = fields.Many2one(comodel_name='rasa_response', string='Response')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name must be unique!'),
    ]


class RasaDataMapper(models.Model):
    _name = 'rasa.data.mapper'
    _description = 'Rasa Data Mapper'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    model_id = fields.Many2one(comodel_name='ir.model', string='Model')
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field', domain="[('model_id', '=', model_id)]")
    action_type = fields.Selection(
        selection=[('edit', 'Edit'), ('search', 'Search'), ('delete', 'Delete'), ('create', 'Create'),
                   ('function', 'Function')], string='Action',
        default='set')
    python_code = fields.Text(string='Python Code')
    ext_function = fields.Char(string='External Function')