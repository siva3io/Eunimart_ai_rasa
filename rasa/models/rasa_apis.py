from odoo import api, models, fields
from . import json_fields

class GoAPIsList(models.Model):
    _name = "rasa_apis"
    _description = "List of APIs"

    name = fields.Char()
    description = fields.Char()
    module_name = fields.Char(string = "Module Name")
    http_method = fields.Selection([ ( "GET" , "GET" ),
                                     ( "POST" , "POST" ),
                                     ( "PUT" , "PUT" ),
                                     ( "DELETE" , "DELETE" ) ])
    url = fields.Char(default="https://dev-api.eunimart.com/",string="URL")
    authentication = fields.Boolean()
    parameter_id = fields.One2many("rasa_api_parameter","api_id")
    form_id = fields.Many2one("rasa_forms")
    api_response_json = json_fields.JsonField(string="API Response Json")


class APIParameters(models.Model):
    _name = "rasa_api_parameter"
    _description = "List of parameter of the particular API"

    name = fields.Char()
    description = fields.Char()
    data_type = fields.Selection([ ( "string" ,"string" ),
                                   ( "integer" ,"integer" ),
                                   ( "json" ,"json" ) ])
    is_required = fields.Boolean()
    parameter_type = fields.Selection([ ( "query" ,"query" ),
                                        ( "path" ,"path" ),
                                        ( "body" ,"body" ) ])
    api_id = fields.Many2one("rasa_apis")

    

    