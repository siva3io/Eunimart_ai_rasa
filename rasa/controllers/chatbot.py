# -*- coding: utf-8 -*-
# import ast
# import json
# import psycopg2
import random
from odoo import tools
from odoo import http
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.mail.controllers.bus import MailChatController


# from requests import models


class ChatSessionController(LivechatController):

    def odoo_session(self):
        mail_channel_vals = {
            'channel_last_seen_partner_ids': [],
            'livechat_active': True,
            'livechat_operator_id': 3,
            'livechat_channel_id': 1,
            'anonymous_name': False,
            'country_id': False,
            'channel_type': 'livechat',
            'name': 'RasaChat',
            'public': 'private',
        }
        mail_channel = http.request.env["mail.channel"].with_context(mail_create_nosubscribe=False).sudo().create(
            mail_channel_vals)
        # {'channel_last_seen_partner_ids': [(...)], 'livechat_active': True, 'livechat_operator_id': 3, 'livechat_channel_id': 1, 'anonymous_name': False, 'country_id': False, 'channel_type': 'livechat', 'name': 'Administrator Administrator', 'public': 'private'}
        return mail_channel

    @http.route('/rasachatbot/create_session', type="json", auth='public', cors="*", method=['GET'])
    def create_session(self, **kwargs):
        payload = http.request.jsonrequest
        session_data = self.odoo_session()
        auth_status = False
        try:
            bearer_token = payload["token"]
            user_id = payload["user_id"]
            auth_status = http.request.env["rasa_chat"].sudo().test_bearer_token(bearer_token)
        except:
            pass
        if not auth_status:
            bearer_token = "NULL"
            user_id = "NULL"
        # auth_response = http.request.env["rasa_chat"].sudo().user_login(mobile_no)
        # if auth_response:
        #     otp_verification_status = http.request.env["rasa_chat"].sudo().verify_otp(auth_response["data"]["id"])
        #     if otp_verification_status:
        #         auth_status = True
        #         bearer_token = otp_verification_status['data']['token']
        #     if not auth_response['data']['new_user']:
        #         chat_history = http.request.env["rasa_chat"].sudo().get_chat_history(mobile_no)
        # session_data = super(ChatSessionController, self).get_session(channel_id = 1, anonymous_name="Visitor", previous_operator_id=2, **kwargs)
        access_token = http.request.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token, session_data['uuid'])
        if not rasa_session:
            access_token = http.request.env["rasa_chat"].sudo().get_access_token()
            if not access_token:
                return False
            rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token, session_data['uuid'])
        response = {
            "odoo_session_id": session_data['id'],
            "conversation_id": session_data['uuid'],
            "authentication": auth_status,
            "message": "session created!"
        }
        http.request.env["rasa_chat"].sudo().store_session(response, bearer_token, user_id)
        if auth_status:
            chat_history = http.request.env["rasa_chat"].sudo().get_chat_history(user_id)
            response["chat_history"] = chat_history
        return response

    @http.route('/rasachatbot/whatsapp/conversation_id', type="json", auth='public', cors="*", method=['GET'])
    def get_session_whatsapp(self, **kwargs):
        payload = http.request.jsonrequest
        mobile_no = payload["mobile"]
        conversation_id = http.request.env["rasa_chat"].sudo().get_conversation_id(mobile_no)
        if conversation_id:
            bearer_token = http.request.env["rasa_chat"].sudo().get_bearer_token(conversation_id)
            if http.request.env["rasa_chat"].sudo().test_bearer_token(bearer_token):
                return conversation_id
        session_data = self.odoo_session()
        access_token = http.request.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token, session_data['uuid'])
        if not rasa_session:
            access_token = http.request.env["rasa_chat"].sudo().get_access_token()
            if not access_token:
                return False
            rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token, session_data['uuid'])
        response = {
            "odoo_session_id": session_data['id'],
            "conversation_id": session_data['uuid']
        }
        login = http.request.env["rasa_chat"].sudo().user_login(mobile_no)
        user_id = login["data"]['id']
        verification = http.request.env["rasa_chat"].sudo().verify_otp(id=user_id, otp='666666')
        bearer_token = verification["data"]["token"]
        user_id = login["data"]['id']
        http.request.env["rasa_chat"].sudo().store_session(response, bearer_token, user_id, 'Whatsapp', mobile_no)
        return session_data['uuid']


class ChatController(MailChatController):

    def sequence_sort(self, responses, sorted_responses, sequence_next):
        if sequence_next == 0:
            return sorted_responses
        for response in responses:
            if response['sequence'] == sequence_next:
                sorted_responses.append(response)
                return self.sequence_sort(responses, sorted_responses, sequence_next=response['sequence_next'])

    def get_rasa_questions(self, mail_channel, odoo_response, uuid, rasa_question_id, response):

        rasa_question = http.request.env["rasa_response_questions"].sudo().search([("id", "=", rasa_question_id)])
        if rasa_question.html != '<p><br></p>':
            response["responses"].append({"html": rasa_question.html,
                                          "sequence": rasa_question.sequence,
                                          "sequence_next": rasa_question.sequence_next})
            body = rasa_question.html
        elif rasa_question.media_url:
            response["responses"].append({"media": rasa_question.media_url,
                                          "sequence": rasa_question.sequence,
                                          "sequence_next": rasa_question.sequence_next})
            body = '<a href="{0}">{0}</a>'.format(rasa_question.media_url)
        else:
            response["responses"].append({"text": rasa_question.name,
                                          "sequence": rasa_question.sequence,
                                          "sequence_next": rasa_question.sequence_next})
            body = tools.plaintext2html(rasa_question.name)
        # post a message without adding followers to the channel. email_from=False avoid to get author from email data
        message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )
        response = self.get_buttons(mail_channel, rasa_question, uuid, response)
        if rasa_question.payload_action:
            return self.get_responses(mail_channel, rasa_question.payload_action, uuid, entities=[], response=response)
        return response

    def get_responses(self, mail_channel, odoo_response, uuid, entities, response):
        rasa_question_ids = odoo_response.question_ids.ids
        if len(rasa_question_ids):
            # Check if the 'is_random_response' field True or False
            # If it's true, chooses the random question id and post the response
            # If it's False , Post all the responses 
            if odoo_response.is_random_response:
                random_question_id = random.choice(rasa_question_ids)
                response = self.get_rasa_questions(mail_channel, odoo_response, uuid, random_question_id, response)
            else:
                for question_id in rasa_question_ids:
                    response = self.get_rasa_questions(mail_channel, odoo_response, uuid, question_id, response)
                if len(response['responses']) > 1:
                    response['responses'] = self.sequence_sort(response['responses'], sorted_responses=[],
                                                               sequence_next=1)
        model = odoo_response.model_id
        if model:
            text = self.get_model_response(uuid, odoo_response)

            output_data = {"text": text}
            body = tools.plaintext2html(text)
            message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
            response["responses"].append(output_data)

        if odoo_response.payload_action:
            return self.get_responses(mail_channel, odoo_response.payload_action, uuid, entities, response)
        return response

    def get_buttons(self, mail_channel, rasa_question, uuid, response):
        """ Get the button ids and print the buttons """

        button_ids = rasa_question.rasa_response_question_button_ids.ids
        for button_id in button_ids:
            response_button = http.request.env["rasa_response_question_button"].sudo().search([("id", "=", button_id)])
            response["buttons"].append({
                "button_id": button_id,
                "text/title": response_button.display_name,
                "sequence": response_button.sequence,
                "sequence_next": response_button.sequence_next
            })
        if len(response["buttons"]) > 1:
            response['buttons'] = self.sequence_sort(response["buttons"], sorted_responses=[], sequence_next=1)
        return response

    def data_analytics(self, python_code, output_data):
        if python_code == "Avg by Channel":
            channel = {}
            for datum in output_data:
                if datum['channel_name'] in channel.keys():
                    channel[datum['channel_name']] += 1
                else:
                    channel[datum['channel_name']] = 1
            text = ""
            for key, value in channel.items():
                text += (key + " = " + str(value) + " Orders, ")
        return text

    def get_model_response(self, uuid, odoo_response, payload=''):
        model = odoo_response.model_id
        # domain = odoo_response.domain
        # for entity in entities:
        #     domain = domain.replace("__"+entity['entity']+"__",str(entity["value"]))
        # # output_fields = odoo_response.output_fields.ids
        parameter_list = []
        parameters = model.parameter_id.ids
        for parameter_id in parameters:
            parameter_data = http.request.env['rasa_api_parameter'].sudo().search([("id", "=", parameter_id)])
            parameter_list.append(parameter_data)

        output_data = http.request.env["rasa_chat"].sudo().get_data_from_golangdb(model, uuid, payload, parameter_list)
        # fields_list = list()
        if output_data == 'unauthorized':
            return "Please login to continue..."
        elif not output_data:
            return "Sorry, that is not a valid response. Please type a respone that is valid"
        else:
            python_code = odoo_response.python_code
            output_format = odoo_response.output_json
            output_python = odoo_response.output_python
            text = output_data
            if output_format:
                text = output_format['text']
                if python_code:
                    text = self.data_analytics(python_code, output_data)

                if output_python:
                    for field in output_python.split(','):
                        fields = field.split("$")
                        if len(fields) > 1:
                            replace_text = output_data
                            for element in fields:
                                if type(replace_text) == list:
                                    replace_text = replace_text[0]
                                replace_text = replace_text[element]
                        else:
                            replace_text = output_data[field]
                        text = text.replace("_field_" + str(field), replace_text)
            return text

    @http.route('/rasachatbot/post_message', type="json", auth="public", cors="*", method=["POST"])
    def post_message(self, **kwargs):
        payload = http.request.jsonrequest
        uuid = payload['conversation_id']
        message_content = payload["message_content"]

        # search the data related to uuid of the conversation 
        mail_channel = http.request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not mail_channel:
            return {"error_message": "Wrong Conservation Id."}

        access_token = http.request.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        history = mail_channel._channel_fetch_message(last_id=False, limit=20)

        # post a message to rasa chat
        rasa_response = http.request.env["rasa_chat"].sudo().post_message(access_token, uuid, message_content)
        if not rasa_response:
            access_token = http.request.env["rasa_chat"].sudo().get_access_token()
            if not access_token:
                response = {
                    "error_message": "Rasa Access token is missing."
                }
                return response
            rasa_response = http.request.env["rasa_chat"].sudo().post_message(access_token, uuid, message_content)
        # if not rasa_response:
        #     response = { "error_message" : "rasa response not able to identify intent." }
        #     return response

        # Get the intent of the message from rasa
        rasa_intent = http.request.env["rasa_chat"].sudo().get_intent(access_token, uuid)
        if not rasa_intent:
            response = {"error_message": "rasa intent api is not working."}
            return response
        rasa_message = False
        rasa_event_list = rasa_intent['events'][::-1]
        for rasa_event in rasa_event_list:
            if "parse_data" in rasa_event.keys():
                rasa_message = rasa_event
                break
        if not rasa_message:
            return {"conversation_id/uuid": uuid,
                    "responses": [{
                        "text": "Sorry, I am not sure how to respond to that. Type help for assistance.I did not quite understand that. Could you rephrase or type help for assistance?"
                    }]
                    }
        # rasa_message = rasa_intent['events'][len(rasa_intent['events'])-5]
        intent = rasa_message['parse_data']['intent']['name']
        entities = list()
        confidence = rasa_message['parse_data']['intent']['confidence']
        rasa_entities = len(rasa_message['parse_data']['entities'])
        response = {"conversation_id/uuid": uuid,
                    "responses": [{
                        "text": "Sorry, I am not sure how to respond to that. Type help for assistance.I did not quite understand that. Could you rephrase or type help for assistance?"
                    }]
                    }
        for entity in range(rasa_entities):
            entities.append({"entity": rasa_message['parse_data']['entities'][0]['entity'],
                             "confidence_entity": rasa_message['parse_data']['entities'][0]['confidence_entity'],
                             "value": rasa_message['parse_data']['entities'][0]['value']})
        # response["entities"] = entities
        response["responses"] = []
        response["buttons"] = []
        # Search and get the intent which matches the rasa intent 
        odoo_intent = http.request.env["rasa_intent"].sudo().search([("name", "=", intent)])
        if not odoo_intent:
            response['responses'].append({
                "text": "Sorry, I am not sure how to respond to that. Type help for assistance.I did not quite understand that. Could you rephrase or type help for assistance?"})
            return response

        # Get the response connected with the intent and it's questions's ids
        odoo_response = odoo_intent.rasa_response_id
        rasa_question_ids = odoo_response.question_ids.ids

        # # if no response in rasa_intent return response which RASA returned
        # if len(rasa_question_ids) == 0 and not model :
        #     response['responses'].append({ "text" : rasa_response[0]['text']  } )

        # return response

        # checking the confidence with threshold value, if it lesser than threshold value,
        # return not able to understand the message
        if confidence < odoo_intent.threshold_value:
            response['responses'].appned({
                "text": "Sorry, I am not sure how to respond to that. Type help for assistance.I did not quite "
                        "understand that. Could you rephrase or type help for assistance?"})
            return response

        chat_responses = self.get_responses(mail_channel, odoo_response, uuid, entities, response)
        response.update(chat_responses)

        post_chat = super(ChatController, self).mail_chat_post(uuid, message_content, **kwargs)
        http.request.env["rasa_chat"].sudo().store_chat(message_content, intent, confidence, response)
        return response

    @http.route('/rasachatbot/button_response', type="json", auth="public", cors="*", method=["POST"])
    def button_message(self, **kwargs):
        payload = http.request.jsonrequest
        uuid = payload['conversation_id']
        button_id = payload['button_id']

        mail_channel = http.request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not mail_channel:
            return {"error_message": "Wrong Conservation Id."}

        button_data = http.request.env["rasa_response_question_button"].sudo().search([("id", "=", button_id)])
        response = {
            "conversation_id/uuid": uuid,
            "button_id": button_id,
            "name": button_data.name,
            "responses": [],
            "buttons": []
        }
        if button_data.model_id:
            try:
                payload = payload["payload"]
            except:
                payload = ""
            text = self.get_model_response(uuid, button_data, payload)
            response["responses"].append({"text": text,
                                          "sequence": 1,
                                          "sequence_next": 2})

        response = self.get_responses(mail_channel, button_data.rasa_response_id, uuid, entities=[], response=response)
        if button_data.payload_action:
            response = self.get_responses(mail_channel, button_data.payload_action, uuid, entities=[],
                                          response=response)

        body = tools.plaintext2html(button_data.name)
        http.request.env["rasa_chat"].sudo().store_chat(button_data.name, button_data.rasa_response_id.display_name,
                                                        99.9, response)
        message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment')
        return response
