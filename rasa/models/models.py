# -*- coding: utf-8 -*-

# from email import header
# from requests.sessions import default_headers
from odoo import models, fields, api
from . import json_fields
import requests, json
import psycopg2

RASA_URL = "http://20.204.36.131:5002/api/"
RASA_USERNAME = "admin"
RASA_PASSWORD = "Eunimart@123"
CHATBOT_POSTGRES_DATABASE = "chatbot"
CHATBOT_POSTGRES_USER = "eunimart_chatbot_user"
CHATBOT_POSTGRES_PASSWORD = "985317c39708"
CHATBOT_POSTGRES_HOST = "chatbot-db.eunimart.com"
CHATBOT_POSTGRES_PORT = "5432"


class Rasa(models.Model):
    _name = "rasa_chat"
    _description = "rasa_chat"

    def get_access_token(self):
        url = RASA_URL + "auth"
        payload = json.dumps({
            "username": RASA_USERNAME,
            "password": RASA_PASSWORD
        })
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            response = json.loads(response.text)
            self.env['ir.config_parameter'].sudo().set_param("rasa.access.token", response['access_token'])
            return self.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        return False

    def create_conversation(self, access_token, uuid):
        url = RASA_URL + "conversations"
        payload = json.dumps({"sender_id": uuid})
        headers = {
            'Authorization': 'Bearer ' + str(access_token),
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 201:
            return json.loads(response.text)
        return False

    def post_message(self, access_token, sender_id, message):
        url = RASA_URL + "conversations/{}/messages".format(sender_id)
        payload = json.dumps({"message": message})
        headers = {
            'Authorization': 'Bearer ' + str(access_token),
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def get_intent(self, access_token, sender_id):
        url = RASA_URL + "conversations/{}".format(sender_id)
        payload = ""
        headers = {
            'Authorization': 'Bearer ' + str(access_token),
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def get_bearer_token(self, conversation_id):
        conn = psycopg2.connect(
            database=CHATBOT_POSTGRES_DATABASE, user=CHATBOT_POSTGRES_USER, password=CHATBOT_POSTGRES_PASSWORD,
            host=CHATBOT_POSTGRES_HOST, port=CHATBOT_POSTGRES_PORT
        )
        conn.autocommit = True
        # Creating a cursor object using the cursor() method
        cursor = conn.cursor()
        cursor.execute("SELECT bearer_token FROM chat_session WHERE conversation_id = '{}'".format(conversation_id))
        data = cursor.fetchone()
        try:
            return data[0]
        except:
            return False

    def get_conversation_id(self, mobile_no):
        conn = psycopg2.connect(
            database=CHATBOT_POSTGRES_DATABASE, user=CHATBOT_POSTGRES_USER, password=CHATBOT_POSTGRES_PASSWORD,
            host=CHATBOT_POSTGRES_HOST, port=CHATBOT_POSTGRES_PORT
        )
        conn.autocommit = True
        # Creating a cursor object using the cursor() method
        cursor = conn.cursor()
        cursor.execute(
            "SELECT conversation_id FROM chat_session WHERE mobile_no = '{}' ORDER BY created_at DESC LIMIT 1".format(
                mobile_no))
        data = cursor.fetchone()
        try:
            return data[0]
        except:
            return False

    def get_data_from_golangdb(self, apidata, uuid, payload, parameters):
        url = apidata.url
        example_payload = modified_payload = apidata.api_response_json
        if example_payload:
            for payload_key, payload_value in payload.items():
                if payload_key in example_payload.keys():
                    modified_payload[payload_key] = payload_value
            modified_payload = json.dumps(modified_payload)
        else:
            modified_payload = ""
        header = {'Content-Type': 'application/json'}
        if apidata.authentication:
            header["Authorization"] = "Bearer " + self.get_bearer_token(uuid)
        if len(parameters) and len(payload):
            for parameter in parameters:
                if parameter.parameter_type == "path":
                    url = url.format(payload[parameter.name])
        response = requests.request(apidata.http_method, url, headers=header, data=modified_payload)
        if response.status_code == 200:
            resposne = json.loads(response.text)
            return resposne["data"]
        if response.status_code == 401:
            return 'unauthorized'
        return False

    def store_session(self, response, bearer_token, user_id, media=False, mobile_no=False, new_user=False):
        conn = psycopg2.connect(
            database=CHATBOT_POSTGRES_DATABASE, user=CHATBOT_POSTGRES_USER, password=CHATBOT_POSTGRES_PASSWORD,
            host=CHATBOT_POSTGRES_HOST, port=CHATBOT_POSTGRES_PORT
        )
        conn.autocommit = True
        # Creating a cursor object using the cursor() method
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_session (odoo_session_id, conversation_id,mobile_no,bearer_token,new_user,media,user_id) VALUES ({},'{}','{}','{}',{},'{}','{}' )".format(
                response["odoo_session_id"], response["conversation_id"], mobile_no, bearer_token, new_user, media,
                user_id))
        conn.close()

    def store_chat(self, message_content, intent, confidence, response):
        conn = psycopg2.connect(
            database=CHATBOT_POSTGRES_DATABASE, user=CHATBOT_POSTGRES_USER, password=CHATBOT_POSTGRES_PASSWORD,
            host=CHATBOT_POSTGRES_HOST, port=CHATBOT_POSTGRES_PORT
        )
        conn.autocommit = True
        # Creating a cursor object using the cursor() method
        cursor = conn.cursor()
        user_id = "NULL"
        cursor.execute(
            "SELECT user_id FROM chat_session WHERE conversation_id = '{}'".format(response['conversation_id/uuid']))
        data = cursor.fetchone()
        if data:
            user_id = data[0]
        chat = [{"user": message_content, "intent": intent, "confidence": confidence},
                {"bot": response["responses"], "buttons": response["buttons"]}]
        cursor.execute(
            "INSERT INTO chat_history (conversation_id,line_text,mobile_no,user_id) VALUES ('{}','{}','NULL','{}')".format(
                response['conversation_id/uuid'], json.dumps(chat), user_id))
        conn.close()

    def get_chat_history(self, user_id):
        conn = psycopg2.connect(
            database=CHATBOT_POSTGRES_DATABASE, user=CHATBOT_POSTGRES_USER, password=CHATBOT_POSTGRES_PASSWORD,
            host=CHATBOT_POSTGRES_HOST, port=CHATBOT_POSTGRES_PORT
        )
        cursor = conn.cursor()
        chat_history = list()
        cursor.execute(
            "SELECT line_text FROM chat_history WHERE user_id = '{}' ORDER BY created_at DESC LIMIT 5".format(user_id))
        data = cursor.fetchall()
        if len(data):
            for chat in data[::-1]:
                message = {"sender": "user",
                           "msg": chat[0][0]['user']}
                bot_message = {"sender": "bot"}
                key = 1
                for bot_chat in chat[0][1]['bot']:
                    if key == 1:
                        bot_message["msg"] = bot_chat['text']
                    else:
                        bot_message["msg" + str(key)] = bot_chat["text"]
                    key += 1
                chat_history.append(message)
                chat_history.append(bot_message)
        return chat_history

    def user_login(self, mobile_no):
        url = "https://dev-api.eunimart.com/auth/user_login"
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({
            "login": mobile_no
        })
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def verify_otp(self, id, otp):
        url = "https://dev-api.eunimart.com/auth/verify_otp"
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({
            "id": id,
            "otp": otp
        })
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def test_bearer_token(self, bearer_token):
        url = "https://dev-api.eunimart.com/api/v1/webstores"
        headers = {'Content-Type': 'application/json',
                   "Authorization": "Bearer " + bearer_token, }
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            return True
        return False


class ChatbotUser(models.Model):
    _name = 'chatbot.user'
    _description = 'Chatbot User'

    name = fields.Char(string="Name", default="User")
    mobile_no = fields.Char(string="Mobile No")
    language = fields.Char(string="Language")
    latitude = fields.Char(string="Latitude")
    longitude = fields.Char(string="Longitude")
    location = json_fields.JsonField(string="Location Json", default={})
    user_type = fields.Char(string="User Type")
    bearer_token = fields.Char(string="Bearer Token")
    address_ids = fields.One2many('res.partner', 'user_id', string="Address")
    aadhar_no = fields.Char(string="Aadhar No")
    pan_no = fields.Char(string="Pan No")
    driving_license_no = fields.Char(string="Driving License No")
    passport_no = fields.Char(string="Passport No")
    gst_no = fields.Char(string="GST No")
    pincode = fields.Char(string="Pincode")
    city = fields.Char(string="City")
    state = fields.Char(string="State")
    country = fields.Char(string="Country")
    serviceable_area = fields.Char(string="Serviceable Area")
    rating = fields.Float(string="Rating")
    user_rating_ids = fields.One2many('user.rating', 'user_id', string="User Rating")
    rated_by_ids = fields.One2many('user.rating', 'rated_user_id', string="Rated By")
    seller_inventory_ids = fields.One2many('seller.inventory', 'user_id', string="Seller Inventory")
    working_hours = fields.Char(string="Working Hours")
    buyer_sale_order_ids = fields.One2many('sale.order', 'buyer_chatbot_user_id', string=" Buyer Sale Order")
    seller_sale_order_ids = fields.One2many('sale.order', 'seller_chatbot_user_id', string="Seller Sale Order")
    seller_sale_order_line_ids = fields.One2many('sale.order.line', 'seller_chatbot_user_id',
                                                 string="Seller Sale Order Lines")
    cart_so_id = fields.Many2one(comodel_name='sale.order', string="Cart Sale Order")
    active_context_data_id = fields.Many2one(comodel_name='rasa.context.data', string="Active Context Data")
    active_workflow_line_id = fields.Many2one(comodel_name='rasa.context.workflow.line', string="Active Workflow Line")
    active_rasa_response_id = fields.Many2one(comodel_name='rasa_response', string="Active Rasa Response")
    temporary_product_id = fields.Many2one(comodel_name='product.product', string="Temporary Product")
    temporary_product_price = fields.Float(string="Temporary Price")
    temporary_product_quantity = fields.Integer(string="Temporary Quantity")
    store_name = fields.Char(string="Store Name")
    store_image = fields.Binary(string="Store Image")
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    is_default_seller = fields.Boolean(string="Is Default Seller")

    # TODO: Check if these two fields are required
    # workflow_rasa_response_id = fields.Many2one(comodel_name='rasa_response', string="Workflow Rasa Response")
    # active_workflow_rasa_response_id = fields.Many2one(comodel_name='rasa_response',
    #                                                    string="Active Workflow Rasa Response")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    buyer_chatbot_user_id = fields.Many2one(comodel_name='chatbot.user', string="Buyer Chatbot User")
    seller_chatbot_user_id = fields.Many2one(comodel_name='chatbot.user', string="Seller Chatbot User")
    cart_chatbot_user_id = fields.One2many("chatbot.user", "cart_so_id", string="Cart Chatbot User")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    seller_chatbot_user_id = fields.Many2one(comodel_name='chatbot.user', string="Seller Chatbot User")
    status = fields.Selection([("draft", "Draft"), ("accepted", "Accepted"), ("rejected", "Rejected")],
                              default="draft", string="Status")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_id = fields.Many2one(comodel_name='chatbot.user', string="User")


class SellerInventory(models.Model):
    _name = 'seller.inventory'
    _description = 'Seller Inventory'

    name = fields.Char(string="Name")
    user_id = fields.Many2one(comodel_name='chatbot.user', string="User")
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    quantity = fields.Float(string="Quantity")
    price = fields.Float(string="Price")

    def get_seller_name(self, default_code):
        seller_name = ""
        seller_inventory_ids = self.env['seller.inventory'].search([('product_id.default_code', '=', default_code)])
        if seller_inventory_ids:
            seller_name = seller_inventory_ids[0].user_id.name
        return seller_name


class UserRating(models.Model):
    _name = 'user.rating'
    _description = 'User Rating'

    name = fields.Char(string="Name")
    user_id = fields.Many2one(comodel_name='chatbot.user', string="User")
    rated_user_id = fields.Many2one(comodel_name='chatbot.user', string="Rated User")
    rating = fields.Integer(string="Rating")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    seller_inventory_ids = fields.One2many('seller.inventory', 'product_id', string="Seller Inventory")
    default_seller_id = fields.Many2one('chatbot.user', string="Default Seller ID")

    # TODO: Write a cronjob to update default seller - Lowest Pricing Seller
    def get_seller(self):
        if self.seller_inventory_ids:
            return self.seller_inventory_ids[-1].user_id
        return self.env["chatbot.user"].sudo().search([("is_default_seller", "=", True)], limit=1)
