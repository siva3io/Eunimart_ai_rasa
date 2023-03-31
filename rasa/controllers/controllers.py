# -*- coding: utf-8 -*-
from requests import models
from odoo import tools
from odoo import http
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.mail.controllers.bus import MailChatController
import random



class RasaController(LivechatController):

    @http.route('/im_livechat/get_session', type="json", auth='public', cors="*")
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, **kwargs):
        session_data = super(RasaController, self).get_session(channel_id, anonymous_name, previous_operator_id, **kwargs)
        access_token = http.request.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token,session_data['uuid'])
        if not rasa_session:
            access_token = http.request.env["rasa_chat"].sudo().get_access_token()
            if not access_token:
                return False   
            rasa_session = http.request.env["rasa_chat"].sudo().create_conversation(access_token,session_data['uuid'])
        return session_data


class RasaChatController(MailChatController):

    @http.route('/mail/chat_post', type="json", auth="public", cors="*")
    def mail_chat_post(self, uuid, message_content, **kwargs):
        post_chat = super(RasaChatController,self).mail_chat_post(uuid,message_content,**kwargs)
        mail_channel = http.request.env["mail.channel"].sudo().search([('uuid', '=', uuid)], limit=1)
        if not mail_channel:
            return False
        access_token = http.request.env['ir.config_parameter'].sudo().get_param('rasa.access.token')
        # post a message to rasa chat
        rasa_response = http.request.env["rasa_chat"].sudo().post_message(access_token,uuid,message_content)
        if not rasa_response:
            access_token = http.request.env["rasa_chat"].sudo().get_access_token()
            if not access_token:
                return False 
            rasa_response = http.request.env["rasa_chat"].sudo().post_message(access_token,uuid,message_content)
        # Get the intent of the message from rasa
        rasa_intent = http.request.env["rasa_chat"].sudo().get_intent(access_token,uuid)
        intent = rasa_intent['latest_message']['intent']['name']

        # Search and get the intent which matches the rasa intent 
        odoo_intent = http.request.env["rasa_intent"].sudo().search([("name","=",intent)])
        # Get the response connected with the intent and it's questions's ids
        rasa_questions_ids = odoo_intent.rasa_response_id.question_ids.ids

        # Check if the 'is_random_response' field True or False
        # If it's true, chooses the random question id and post the response
        # If it's False , Post all the responses 
        if odoo_intent.rasa_response_id.is_random_response:
            random_question_id = random.choice(rasa_questions_ids)
            rasa_question = http.request.env["rasa_response_questions"].sudo().search([("id","=",random_question_id)])
            # post a message without adding followers to the channel. email_from=False avoid to get author from email data
            body = tools.plaintext2html(rasa_question.name)
            message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(   
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
        else:
            for question_id in rasa_questions_ids:
                rasa_question = http.request.env["rasa_response_questions"].sudo().search([("id","=",question_id)])
                body = tools.plaintext2html(rasa_question.name)
                message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(   
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )

        # Get the button ids and print the buttons
        # button_ids = rasa_question.rasa_response_question_button_ids.ids
        # for button_id in button_ids:
        #     response_button = http.request.env["rasa_response_question_button"].sudo().search([("id","=",button_id)])
        #     body = tools.plaintext2html(response_button.name)
        #     # body = '<button type="button" > {} </button>'.format(response_button.name)
        #     message = mail_channel.with_context(mail_create_nosubscribe=True).message_post(   
        #         body=body
        #     )
        return message.id if message else False
