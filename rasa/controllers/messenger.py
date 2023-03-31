# -*- coding: utf-8 -*-
import ast
import base64
import json
# import json
import logging
import os
import random
import re
# import threading

import requests
import uuid
from odoo.http import route, Controller, request
from google.cloud import translate_v2

# import googlemaps

# from kafka import KafkaConsumer

logger = logging.getLogger('odoo')

BROKERS = '20.193.149.244:9091'
TOPICS = 'private.ai.chatbot'
# PHONE_ID = '1234'
PHONE_ID = '104020782504080'
VERSION = 'v15.0'
WHATSAPP_URL = "https://graph.facebook.com/{}/{}/messages".format(VERSION, PHONE_ID)
TOKEN = 'Bearer EAAFTJxZAqTY0BAOaWI3F32Va7QY7v1KHzZCo2ZAguAT4lpB4xnlrGgnnrNVS21Yc4oSZAYuEpzfdtouZC5xuNhhvWgy3ehKmQVLpott1uLNWXbZAZCnrNq2vd7udeBZAqtvhCCA8bkcMkxsoOzTSGKH8MDurnTkOSLuKm5kr2zjhPZAvETcDZBYVKS'
HEADERS = {'Content-Type': 'application/json', 'Authorization': TOKEN}
SIVA_URL = "https://datalabs.siva3.io"

PATH = os.path.join(os.path.dirname(__file__), "../static/src/json/aicentral_eunimart_trans.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = PATH
# gmaps = googlemaps.Client()

BASE_URL = "http://localhost:8069"


class MessengerController(Controller):
    @staticmethod
    def drop_duplicated_letters(input_string):

        """ This function replaces the occurrence of a single letter for 3 or more times
            with 2 repeated letters.
            Ex: input string : attttta
                output string : atta """

        for letter in input_string:
            redundant_letter_pattern = letter + letter + letter
            input_string = re.sub(redundant_letter_pattern, letter + letter, input_string)
            final_string = input_string
        return final_string

    @staticmethod
    def replace_dynamic_text(text, data):
        for key, value in data.items():
            # Added Condition
            if key in text:
                text = text.replace(key, str(value))
        return text

    # @staticmethod
    # def get_pincode_google(lat, long):
    #     reverse_geocode_result = gmaps.reverse_geocode((lat, long))
    #     for address in reverse_geocode_result:
    #         for component in address['address_components']:
    #             if 'postal_code' in component['types']:
    #                 return component['long_name']

    @staticmethod
    def update_image(id, image_url=None, image_btext=None):
        exists = requests.get(SIVA_URL + "/images/" + id + ".jpg")
        if exists.status_code == 200:
            return SIVA_URL + "/images/" + id + ".jpg"
        else:
            if image_url:
                image_btext = requests.get(image_url).content
            base64_str = base64.b64encode(image_btext).decode('utf-8')
            res = requests.post((SIVA_URL + "/api/v1/base64_to_image"),
                                json={"base64_image": base64_str, "image_name": id})
            if res:
                return SIVA_URL + "/images/" + id + ".jpg"

    @staticmethod
    def call_elastic_search(query, size=5, page=0, offset=0):
        url = "https://datalabs.siva3.io/api/v1/internal/products/related_products?query={}&size={}&page={}&offset={}". \
            format(query, size, page, offset)
        response = requests.get(url)

        if response.status_code == 200:
            body = response.json()
            products = []
            dict_ = {
                "meta": {
                    "query": query,
                    "count": body.get('count'),
                    "page": page,
                    "size": size,
                    "offset": offset,
                },
                "products": products
            }
            if not body.get('count'):
                return dict_

            seller_inventory = request.env(su=True)['seller.inventory']
            prod_url = "https://datalabs.siva3.io/api/v1/internal/products/products/{}"
            for prod_id in body.get('ids'):
                product = requests.get(prod_url.format(prod_id)).json()
                if product:
                    image_url = "https://datalabs.siva3.io/images/no_image.jpg"
                    if product.get("images"):
                        try:
                            images = product.get('images', "")
                            images = images.strip("[]").split(",")
                            if images:
                                first_image = images[0].strip("'")
                                image_url = MessengerController.update_image(product.get('id'), first_image)
                        except Exception as exc:
                            logger.info("Exception in Loading Image", exc.__repr__())
                    products.append({
                        "id": product.get('id'),
                        "name": product.get('name'),
                        "image": image_url,
                        "price": product.get('value') or product.get("listed_value") or 503,
                        # FIXME: Price needs to be corrected,
                        "seller": seller_inventory.get_seller_name(product.get('id')) or "Siva Store",
                    })
            return dict_

    @staticmethod
    def translating_text(text, target=None, s_format='text'):
        translate_client = translate_v2.Client()
        if target:
            translated = translate_client.translate(text, format_=s_format, target_language=target)
            if translated and translated.get('translatedText'):
                return translated.get('translatedText')
            else:
                return text
        else:
            lang = translate_client.detect_language(text)
            if lang:
                return lang.get('language')
            else:
                return 'en'

    @staticmethod
    def image_to_text(reply):
        if reply.get('id'):
            whatsapp_file_url = "https://graph.facebook.com/{}/{}".format(VERSION, reply.get('id'))
            res = requests.get(whatsapp_file_url, headers=HEADERS)
            if res.status_code == 200:
                image = requests.get(res.json().get('url'), headers=HEADERS)
                new_url = MessengerController.update_image(uuid.uuid4().hex, None, image.content)
                if new_url:
                    res = requests.post(SIVA_URL + "/api/v1/internal/google/text_detection",
                                        json={"file_url": new_url, "headers": {}})
                    query = "dog"  # Fallback query
                    if res.status_code == 200:
                        response_json = res.json()
                        query_list = response_json.get("detected_text", [])
                        query = ' '.join(query_list)
                    logger.info(query + 'from image ' + new_url)
                    if not query:
                        res = requests.post(SIVA_URL + "/api/v1/internal/google/object_detection",
                                            json={"file_url": new_url, "headers": {}})
                        if res.status_code == 200:
                            response_json = res.json()
                            objects = response_json.get("detected_objects")
                            query = " ".join(obj[0] for obj in objects)
                            logger.info("Object detection " + query + 'from image ' + new_url)
                    return query

    @staticmethod
    def audio_to_text(reply, language_code):
        if reply.get('id'):
            whatsapp_url = "https://graph.facebook.com/{}/{}".format(VERSION, reply.get('id'))
            res = requests.get(whatsapp_url, headers=HEADERS)
            if res.status_code == 200:
                whatsapp_file_url = res.json().get('url')
                if whatsapp_file_url:
                    payload = {
                        "file_url": whatsapp_file_url,
                        "language_code": language_code,
                        "headers": HEADERS
                    }
                    res = requests.post(SIVA_URL + "/api/v1/internal/google/speech_to_text", json=payload)
                    if res.status_code == 200:
                        detection = res.json().get("detected_text")[0]
                        query = detection.get("transcript")
                        logger.info(query + 'from audio ' + whatsapp_file_url)
                        if not detection.get("detected_language_code", "").startswith("en"):
                            payload = {
                                "source_text": [query]
                            }
                            res = requests.post(SIVA_URL + "/api/v1/internal/google/translate", json=payload)
                            query = res.json().get("translated_text")
                        return query

    @staticmethod
    def process_message_text(user_id, text, target=None, translate=True, s_format='text'):
        if translate:
            text = MessengerController.translating_text(text, target, s_format)
        data = {
            '_user_id_': user_id.id,
            '_name_': user_id.name or "Guest",
        }
        return MessengerController.replace_dynamic_text(text, data)

    @staticmethod
    def update_user_context_data(user_id, reply):
        context_data_id = user_id.active_context_data_id
        context_data_line_id = context_data_id.context_line_ids.filtered(lambda x: not x.completed)[0:1]
        if context_data_line_id:
            context_data_line_id.write({'raw_data': reply})
        return context_data_line_id

    @staticmethod
    def messenger_post_message(user_id, message_dict):
        language = user_id.language or 'en'
        trans = True if language != 'en' else False
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user_id.mobile_no,
        }
        if message_dict.get('buttons'):
            if len(message_dict.get('buttons')) < 4:
                payload.update({
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": MessengerController.process_message_text(user_id, message_dict.get('text'),
                                                                             language, trans),
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": button.get('button_id'),
                                        "title": MessengerController.translating_text(button.get('button_text'),
                                                                                      language) if trans else button.get(
                                            'button_text'),
                                    }
                                } for button in message_dict.get('buttons')
                            ]
                        }
                    }
                })
            else:
                payload.update({
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": MessengerController.process_message_text(user_id, message_dict.get('text'),
                                                                             language, trans),
                        },
                        "footer": {
                            "text": "(Select an option from following list)"
                        },
                        "action": {
                            "button": "Select Option",
                            "sections": [
                                {
                                    "rows": [
                                        {
                                            "id": button.get('button_id'),
                                            "title": MessengerController.translating_text(button.get('button_text'),
                                                                                          language) if trans else button.get(
                                                'button_text'),
                                        } for button in message_dict.get('buttons')
                                    ]
                                }
                            ]
                        }
                    }
                })
        elif message_dict.get('text'):
            payload.update({
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": MessengerController.process_message_text(user_id, message_dict['text'],
                                                                     user_id.language or 'en'),
                }
            })
        elif message_dict.get('image'):
            payload.update({
                "type": "image",
                "image": {
                    "link": message_dict['image']
                }
            })
        elif message_dict.get('product_list'):
            payload.update({
                "type": "template",
                "template": {
                    "name": "buyer_product_search",
                    "language": {
                        "code": "en",
                        "policy": "deterministic"
                    },
                    "components": [
                        {
                            "type": "header",
                            "parameters": [
                                {
                                    "type": "image",
                                    "image": {
                                        "link": message_dict['product_list']['image']
                                    }
                                }
                            ]
                        },
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": message_dict['product_list']["name"] or "NA"
                                },
                                {
                                    "type": "text",
                                    "text": message_dict['product_list']["price"] or "NA"
                                },
                                {
                                    "type": "text",
                                    "text": message_dict['product_list']["seller"] or "Siva store"
                                }
                            ]
                        },
                        {
                            "type": "button",
                            "sub_type": "quick_reply",
                            "index": 0,
                            "parameters": [
                                {
                                    "type": "payload",
                                    "payload": message_dict['product_list']['id']
                                }
                            ]
                        },
                        {
                            "type": "button",
                            "sub_type": "quick_reply",
                            "index": 1,
                            "parameters": [
                                {
                                    "type": "payload",
                                    "payload": f"buy_now__{message_dict['product_list']['id']}"
                                }
                            ]
                        }
                    ]
                }
            })
        elif message_dict.get('seller_product_list'):
            payload.update({
                "type": "template",
                "template": {
                    "name": "seller_catalouge_search",
                    "language": {
                        "code": "en",
                        "policy": "deterministic"
                    },
                    "components": [
                        {
                            "type": "header",
                            "parameters": [
                                {
                                    "type": "image",
                                    "image": {
                                        "link": message_dict['seller_product_list']["image"] or "https://datalabs.siva3.io/images/no_image.jpg"
                                    }
                                }
                            ]
                        },
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": message_dict['seller_product_list']["name"] or "NA"
                                },
                                {
                                    "type": "text",
                                    "text": message_dict['seller_product_list']["price"] or "NA"
                                }
                            ]
                        },
                        {
                            "type": "button",
                            "sub_type": "quick_reply",
                            "index": 0,
                            "parameters": [
                                {
                                    "type": "payload",
                                    "payload": message_dict['seller_product_list']['id']
                                }
                            ]
                        }
                    ]
                }
            })
        response = requests.post(WHATSAPP_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            pass

    @staticmethod
    def dynamic_action(user_id, action, model, fields, values, domain):
        if model:
            model = request.env(su=True)[model]
        if domain:
            domain = domain.replace('_user_id_', str(user_id.id))
            domain = ast.literal_eval(domain)
        if fields:
            fields = fields.split(',')
        if values:
            values = values.replace('_user_id_', str(user_id.id))
            values = values.split(',')
        if action == 'create':
            return model.create(values)
        elif action == 'write':
            values = dict(zip(fields, values))
            return model.search(domain).write(values)
        elif action == 'read':
            return model.search(domain).read(fields)
        elif action == 'unlink':
            return model.search(domain).unlink()
        elif 'elastic_search' in action:
            values = " ".join(values)
            product_list = MessengerController.call_elastic_search(values, *domain)
            # product_ids = model.search(domain).read(fields)
            if product_list['meta']['count'] == 0:
                values = MessengerController.drop_duplicated_letters(values)
                product_list = MessengerController.call_elastic_search(values, *domain)
                if product_list['meta']['count'] == 0:
                    return MessengerController.messenger_post_message(user_id, {
                        "text": "Oops! We couldn't find any related product!\n" +
                                "Try rephrasing the query or try with different product"
                    })
            seller = False
            if 'seller' in action:
                seller = True
            if product_list:
                MessengerController.messenger_post_message(user_id, {
                    "text": "We have found {} products for you. Please select one of them".format(
                        product_list['meta']['count']),
                })
                for product in product_list['products']:
                    # if seller:
                    if user_id.user_type == "seller":
                        MessengerController.messenger_post_message(user_id, {
                            'seller_product_list': product
                        })
                    else:
                        MessengerController.messenger_post_message(user_id, {
                            'product_list': product
                        })
                MessengerController.messenger_post_message(user_id, {
                    "text": "Didn't find what you were looking for?",
                    "buttons": [
                        {
                            "button_id": "{}:::{}:{}".format(action, product_list['meta']['query'],
                                                             [product_list['meta']['size'],
                                                              product_list['meta']['page'] + 1,
                                                              product_list['meta']['size'] * (
                                                                      product_list['meta'][
                                                                          'page'] + 1)]),
                            "button_text": "Load More"
                        }
                    ]
                })
            return False  # FixME: Change it for going to next context line
        elif action == "view_inventory_user":
            message = "You have the following inventory: "
            if len(user_id.seller_inventory_ids) == 0:
                message = "You have no products in your inventory."

            MessengerController.messenger_post_message(user_id, {"text": message})
            for inv_id in user_id.seller_inventory_ids:
                msg_payload = {
                    "text": f"{inv_id.name} - Rs.{inv_id.price} - {inv_id.quantity} items",
                    "buttons": [
                        {
                            "button_id": inv_id.product_id.default_code,
                            "button_text": "Update Inventory"
                        }
                    ]
                }
                MessengerController.messenger_post_message(user_id, msg_payload)
            return MessengerController.messenger_post_message(user_id, {
                "text": "You can continue browsing for other products if you don't want to update Inventory!"
            })
        elif action == "view_orders_seller":
            message = "You have the following orders: "
            if len(user_id.seller_sale_order_line_ids) == 0:
                message = "You have no orders."
            MessengerController.messenger_post_message(user_id, {"text": message})
            for line_id in user_id.seller_sale_order_line_ids:
                if line_id.status != "draft":
                    msg_payload = {
                        "text": f"{line_id.product_id.name} - Rs.{line_id.price_unit} - {line_id.product_uom_qty} items"
                    }
                    MessengerController.messenger_post_message(user_id, msg_payload)
            return
        elif action == "proceed_to_payment":
            total_payment = user_id.cart_so_id.amount_total
            if len(user_id.cart_so_id.order_line) == 0:
                return MessengerController.messenger_post_message(user_id, {
                    "text": "You have no products in your cart! Add some to continue."
                })
            return MessengerController.messenger_post_message(user_id, {
                "text": f"You can complete your payment of Rs. {total_payment} with following methods:\n",
                "buttons": [
                    {
                        "button_id": "complete_payment_cod",
                        "button_text": "Cash On Delivery"
                    }
                ]
            })
        elif action == "complete_payment_cod":
            user_id.cart_so_id.write({
                'state': 'sale',
                'buyer_chatbot_user_id': user_id.id
            })
            for product_line in user_id.cart_so_id.order_line:
                product = product_line.product_id
                message = "Hello! You have got a new order for {} of quantity {}"
                message = message.format(product.name, product_line.product_uom_qty)
                MessengerController.messenger_post_message(product_line.seller_chatbot_user_id, {
                    "text": message,
                    "buttons": [
                        {
                            "button_id": f"seller_accept_order__{product_line.id}",
                            "button_text": "Accept Order"
                        },
                        {
                            "button_id": f"seller_reject_order__{product_line.id}",
                            "button_text": "Reject Order"
                        }
                    ]
                })
            user_id.write({
                'cart_so_id': False
            })
            return MessengerController.messenger_post_message(user_id, {
                "text": "We have received your order! Your order will be confirmed once seller accepts your order!"
            })

        elif action.startswith("seller_accept_order__") or action.startswith("seller_reject_order__"):
            product_line_id = action.split("__")[-1]
            sale_order_line = request.env["sale.order.line"].sudo().search([('id', '=', product_line_id)], limit=1)
            mobile_no = sale_order_line.order_id.partner_id.mobile
            customer_id = request.env['chatbot.user'].sudo().search([('mobile_no', '=', mobile_no)], limit=1)
            seller_id = sale_order_line.seller_chatbot_user_id
            status = "accepted" if "accept" in action else "rejected"
            buttons = []
            seller_message_payload = None
            if sale_order_line.status != "draft":
                message = {
                    "text": f"Order has already been {sale_order_line.status}! Cannot update now!"
                }
                return MessengerController.messenger_post_message(user_id, message)
            sale_order_line.write({
                "status": status
            })
            quantity = sale_order_line.product_uom_qty
            name = sale_order_line.product_id.name
            seller_name = seller_id.store_name or seller_id.name
            if status == "accepted":
                seller_message_payload = {
                    "text": f"Thanks for accepting the order. You need to send {quantity} x {name} for {customer_id.name} at https://www.google.com/maps/search/?api=1&query={user_id.latitude},{user_id.longitude}! ",
                    "buttons": [{
                        "button_id": "view_orders_seller",
                        "button_text": "View Orders"
                    }]}
                message = f"Hurray! The {seller_name} has accepted your order of {quantity} x {name}!"
                buttons.append({
                    "button_id": f"track_order__{product_line_id}",
                    "button_text": "Track Order"
                })
            else:
                message = f"Opsss! The {seller_name} has rejected your order of {quantity} x {name}!"
            message_payload = {
                "text": message
            }
            if buttons:
                message_payload.update({"buttons": buttons})
            if seller_message_payload:
                MessengerController.messenger_post_message(user_id, seller_message_payload)
            return MessengerController.messenger_post_message(customer_id, message_payload)

        elif action.startswith("track_order__"):
            message_payload = {
                "text": "The seller is processing your order!\n You will get notified if seller updates the status!"
            }
            return MessengerController.messenger_post_message(user_id, message_payload)

        elif action == "view_or_update_cart":
            message = "You have the following in your cart: "
            buttons = [
                {
                    "button_id": "proceed_to_payment",
                    "button_text": "Proceed To Payment"
                }
            ]
            if len(user_id.cart_so_id.order_line) == 0:
                message = "You have no products in your cart!"
                buttons = []
            MessengerController.messenger_post_message(user_id, {
                "text": message
            })
            for product_line_id in user_id.cart_so_id.order_line:
                product = product_line_id.product_id
                quantity = int(product_line_id.product_uom_qty)
                msg_payload = {
                    "text":
                        f"{product.name} - "
                        f"Rs.{product_line_id.price_unit} - "
                        f"{quantity} x Rs.{product_line_id.price_unit} = Rs.{product_line_id.price_total}",
                    "buttons": [
                        {
                            "button_id": f"update__{product.default_code}",
                            "button_text": "Update Cart"
                        },
                        {
                            "button_id": f"delete__{product_line_id.id}",
                            "button_text": "Delete"
                        }
                    ]
                }
                MessengerController.messenger_post_message(user_id, msg_payload)
            message_payload = {
                "text": "You can continue to search if you want to add more products!",
            }
            if buttons:
                message_payload.update({"buttons": buttons})
            return MessengerController.messenger_post_message(user_id, message_payload)

        else:
            if action.startswith("delete__"):
                sale_order_line_id = action.replace("delete__", "")
                sale_order_line = request.env["sale.order.line"].sudo().search([('id', '=', sale_order_line_id)])
                sale_order_line.unlink()
                message = {
                    "text": "The product has been removed from your cart.",
                    "buttons": [
                        {
                            "button_id": "view_or_update_cart",
                            "button_text": "View / Update Cart"
                        },
                        {
                            "button_id": "proceed_to_payment",
                            "button_text": "Proceed To Payment"
                        }
                    ]
                }
                return MessengerController.messenger_post_message(user_id, message)

            elastic_product_id = action
            if action.startswith("update__"):
                elastic_product_id = action.replace("update__", "")
            elif action.startswith("buy_now__"):
                elastic_product_id = action.replace("buy_now__", "")
            prod_url = "https://datalabs.siva3.io/api/v1/internal/products/products/{}"
            response = requests.get(prod_url.format(elastic_product_id))


            if user_id.user_type == "seller":
                user_id.write({"temporary_product_id": product_data.id})
                price = product.get('value') or product.get("listed_value") or 503,
                if type('price') == tuple:
                    price = price[0]
                # FIXME: Price needs to be corrected
                MessengerController.messenger_post_message(user_id, {
                    "text": "Great! We suggest you to sell at Rs.{} ".format(price) +
                            "At what price would you like to sell this product?"
                })
            elif user_id.user_type == "buyer":
                partner_id = user_id.partner_id
                cart_sales_order = user_id.cart_so_id
                if not partner_id or not cart_sales_order:
                    partner_id = request.env["res.partner"].sudo().create({
                        "name": user_id.name,
                        "mobile": user_id.mobile_no,
                    })
                    user_id.write({"partner_id": partner_id.id})
                    cart_sales_order = request.env["sale.order"].sudo().create({
                        "name": "SO draft" + user_id.name,
                        "partner_id": partner_id.id,
                        "state": "draft"
                    })
                    user_id.write({"cart_so_id": cart_sales_order.id})
                existing_cart_product_line = request.env["sale.order.line"].sudo().search([
                    ("order_id", "=", cart_sales_order.id), ("product_id", "=", product_data.id)
                ], limit=1)
                logger.info("Existing Product is " + str(existing_cart_product_line))
                if existing_cart_product_line:
                    existing_cart_product_line.write({
                        "product_uom_qty": existing_cart_product_line.product_uom_qty + 1
                    })
                else:
                    cart_sales_order.write({"order_line": [
                        (0, 0, {
                            "product_id": product_data.id,
                            "price_unit": product.get('value') or product.get("listed_value") or 503,
                            # FIXME: Price needs to be corrected
                            "product_uom_qty": 1,  # Quantity is 1 by default,
                            "seller_chatbot_user_id": product_data.get_seller().id
                        })
                    ]})
                message = {
                    "text": "Great! You have added {} to your cart".format(product.get("name")),
                    "buttons": [
                        {
                            "button_id": "view_or_update_cart",
                            "button_text": "View / Update Cart"
                        },
                        {
                            "button_id": "proceed_to_payment",
                            "button_text": "Proceed To Payment"
                        }
                    ]
                }
                MessengerController.messenger_post_message(user_id, message)
                MessengerController.messenger_post_message(user_id, {
                    "text": "You can continue to search if you want to add more products!"
                })

    @staticmethod
    def context_data_dict(user_id, context_template_id):
        return {
            "name": context_template_id.name,
            "code": context_template_id.code,
            "mandatory": context_template_id.mandatory,
            "temporary": context_template_id.temporary,
            "priority": context_template_id.priority,
            "template_id": context_template_id.id,
            "user_id": user_id.id,
            "user_token": user_id.mobile_no,
            "context_line_ids": [(0, 0, {
                "sequence": line.sequence,
                "next_sequence": line.next_sequence,
                "python_code": line.python_code,
                "next_context_id": line.next_context_id.id,
                "rel_response_id": line.rel_response_id.id,
            }) for line in context_template_id.context_line_ids],
            "response_id": context_template_id.response_id,
            "rasa_nlu_path": context_template_id.rasa_nlu_path,
            "eda_context": context_template_id.eda_context,
        }

    @staticmethod
    def process_action(user_id, reply, message_type, line_id=False):
        python_code, payload_action = None, None
        if message_type == 'button_reply' or message_type == 'list_reply' or message_type == 'button':
            if len(reply) < 7:
                button_id = request.env['rasa_response_question_button'].sudo().browse(int(reply))
                python_code, payload_action = button_id.python_code, button_id.payload_action
            else:
                python_code, payload_action = reply, None
        elif message_type == 'text' or message_type == 'location':
            if user_id.temporary_product_id:
                if user_id.user_type == "seller" and not user_id.temporary_product_price:
                    try:
                        price = int(reply)
                    except:
                        return MessengerController.messenger_post_message(user_id, {
                            "text": f"I could not get the price value! Can you just specify the value alone?"
                        })
                    user_id.write({"temporary_product_price": price})
                    return MessengerController.messenger_post_message(user_id, {
                        "text": f"Ok You want to sell at Rs. {price}! How many items do you have?"
                    })
                elif not user_id.temporary_product_quantity:
                    try:
                        quantity = int(reply)
                    except:
                        return MessengerController.messenger_post_message(user_id, {
                            "text": f"I could not get the quantity value! Can you just specify the value alone?"
                        })
                    if user_id.user_type == "buyer":
                        sale_order_line = request.env["sale.order.line"].sudo().search([
                            ("order_id", "=", user_id.cart_so_id.id),
                            ("product_id", "=", user_id.temporary_product_id.id)
                        ], limit=1)
                        message = f"Yay! We have updated the quantity to {quantity}!"
                        if quantity == 0:
                            sale_order_line.unlink()
                            message = "The product has been removed from your cart"
                        else:
                            sale_order_line.write({
                                "product_uom_qty": quantity
                            })
                        user_id.write({
                            "temporary_product_id": False,
                        })
                        return MessengerController.messenger_post_message(user_id, {
                            "text": message,
                            "buttons": [
                                {
                                    "button_id": "view_or_update_cart",
                                    "button_text": "View / Update Cart"
                                },
                                {
                                    "button_id": "proceed_to_payment",
                                    "button_text": "Proceed To Payment"
                                }
                            ]
                        })

                    if user_id.user_type == "seller":
                        inv_product = request.env['seller.inventory'].sudo().search([
                            ("user_id", "=", user_id.id), ("product_id", "=", user_id.temporary_product_id.id)
                        ], limit=1, order="id desc")
                        if inv_product:
                            inv_product.write({
                                "quantity": quantity,
                                "price": user_id.temporary_product_price,
                            })
                        else:
                            request.env['seller.inventory'].sudo().create({
                                "name": user_id.temporary_product_id.name,
                                "product_id": user_id.temporary_product_id.id,
                                "quantity": quantity,
                                "price": user_id.temporary_product_price,
                                "user_id": user_id.id
                            })
                        MessengerController.messenger_post_message(user_id, {
                            "text": f"Ok You have {quantity} items to sell at Rs. {user_id.temporary_product_price}!"
                        })
                        user_id.write({
                            "temporary_product_id": False,
                            "temporary_product_quantity": 0,
                            "temporary_product_price": 0
                        })
                        MessengerController.messenger_post_message(user_id, {
                            "text": "We have successfully updated your inventory!"
                        })
                        msg_payload = {
                            "text": f"You have {len(user_id.seller_inventory_ids)} products in your Inventory!",
                            "buttons": [
                                {
                                    "button_id": "view_inventory_user",
                                    "button_text": "View Inventory"
                                }
                            ]
                        }
                        MessengerController.messenger_post_message(user_id, msg_payload)
                        return MessengerController.messenger_post_message(user_id, {
                            "text":
                                "You can continue browsing for other products if you don't want to update Inventory!"
                        })
                    # python_code, payload_action = line_id.python_code, None
            python_code, payload_action = line_id.python_code, None
        elif message_type == "audio":
            python_code, payload_action = line_id.python_code, None
            reply = MessengerController.audio_to_text(reply, user_id.language)
        if python_code:
            vals = python_code.split(':')
            model = fields = values = domain = ""
            if len(vals) == 5:
                action, model, fields, values, domain = vals
            else:
                action = vals[0]
            if reply:
                values = values.replace('_data_', reply)
            action = MessengerController.dynamic_action(user_id, action, model, fields, values, domain)
            if action:
                MessengerController.check_context_data(user_id, user_id.active_context_data_id, True)
            #     TODO : Move to next action in case of none
        if payload_action:
            MessengerController.check_payload(user_id, payload_action)

    @staticmethod
    def check_user(mobile_no):
        user_id = request.env['chatbot.user'].sudo().search([('mobile_no', '=', mobile_no)], limit=1)
        if not user_id:
            user_id = request.env['chatbot.user'].sudo().create({'mobile_no': mobile_no})
        return user_id

    @staticmethod
    def check_context_data(user_id, context_data_id, complete=False):
        context_data_line_id = context_data_id.context_line_ids.filtered(lambda x: not x.completed)[0:1]
        if context_data_line_id:
            if complete:
                context_data_line_id.completed = True
                MessengerController.check_context_data(user_id, context_data_id)
            else:
                rasa_response_id = context_data_line_id.rel_response_id
                MessengerController.check_rasa_response(user_id, rasa_response_id)
        else:
            context_data_id.completed = True
            line_sequence = user_id.active_workflow_line_id.sequence
            workflow_line_ids = user_id.active_rasa_response_id.context_workflow_line_ids.filtered(
                lambda x: x.sequence > line_sequence)
            MessengerController.check_workflow_line(user_id, workflow_line_ids)

    @staticmethod
    def get_context_data(user_id, context_template_id):
        context_data_id = request.env['rasa.context.data'].sudo().search([('user_id', '=', user_id.id),
                                                                          ('template_id', '=', context_template_id.id)],
                                                                         limit=1)
        if not context_data_id:
            values = MessengerController.context_data_dict(user_id, context_template_id)
            context_data_id = request.env['rasa.context.data'].sudo().create(values)
        user_id.active_context_data_id = context_data_id.id
        return context_data_id


    @staticmethod
    def check_rasa_response(user_id, rasa_response_id):
        if rasa_response_id.is_random_response:
            message = rasa_response_id.question_ids[
                random.randint(0, len(rasa_response_id.question_ids) - 1)]
            message_text = message.name
            message_dict = {
                "text": message_text,
            }
            if message.rasa_response_question_button_ids:
                message_dict = {"buttons": []}
                for button in message.rasa_response_question_button_ids:
                    message_dict["buttons"].append({
                        "button_id": button.id, "button_text": button.name
                    })
            MessengerController.messenger_post_message(user_id, message_dict)
        elif rasa_response_id.is_context and rasa_response_id.context_workflow_line_ids:
            MessengerController.check_workflow_line(user_id, rasa_response_id.context_workflow_line_ids)
        else:
            for message in rasa_response_id.question_ids:
                message_text = message.name
                message_dict = {
                    "text": message_text,
                }
                if message.rasa_response_question_button_ids:
                    message_dict["buttons"] = []
                    for button in message.rasa_response_question_button_ids:
                        message_dict["buttons"].append({
                            "button_id": button.id, "button_text": button.name
                        })
                MessengerController.messenger_post_message(user_id, message_dict)

    @staticmethod
    def check_payload(user_id, payload):
        rasa_response_id = request.env['rasa_response'].sudo().search([('code', '=', payload)], limit=1)
        if rasa_response_id:
            # TODO: Check if need to update or only in case of context
            user_id.active_rasa_response_id = rasa_response_id.id
            user_id.active_context_data_id = False
            user_id.active_workflow_line_id = False
            MessengerController.check_rasa_response(user_id, rasa_response_id)
        else:
            pass

    @staticmethod
    def check_user_context_data(user_id):
        context_data = request.env['rasa.context.data'].sudo().search([('user_id', '=', user_id.id)], limit=1)
        if not context_data:
            context_data = request.env['chatbot.user.context'].sudo().create({'user_id': user_id.id})
        return context_data

    # @route('/webhook', type='json', auth="public", methods=['POST'], csrf=False)
    @route('/messenger/receive/message', type='json', auth='public', cors='*', csrf=False, save_session=False)
    def messenger_receive_message(self, **kwargs):
        if kwargs.get('message'):
            message = kwargs.get('message')
            user_id = MessengerController.check_user(message.get('from'))
            message_type = message.get('type')
            if message_type == 'interactive':
                message = message.get(message_type)
                message_type = message.get('type')
                if message_type == 'button_reply' or 'list_reply':
                    reply = message.get(message_type)
                    line_id = None
                    if user_id.active_context_data_id:
                        line_id = MessengerController.update_user_context_data(user_id, reply)
                    MessengerController.process_action(user_id, reply.get('id'), message_type, line_id)
            elif message_type == 'button':
                reply = message.get(message_type)
                line_id = None
                if user_id.active_context_data_id:
                    line_id = MessengerController.update_user_context_data(user_id, reply)
                MessengerController.process_action(user_id, reply.get('payload'), message_type, line_id)
            elif user_id.active_context_data_id:
                reply = message.get(message_type)
                line_id = MessengerController.update_user_context_data(user_id, reply)
                if message_type == 'text':
                    MessengerController.process_action(user_id, reply.get('body'), message_type, line_id)
                elif message_type == 'location':
                    reply = str(reply['latitude']) + ',' + str(reply['longitude'])
                    MessengerController.process_action(user_id, reply, message_type, line_id)
                elif message_type == 'image':
                    MessengerController.process_action(user_id, reply, message_type, line_id)
                elif message_type == 'audio':
                    MessengerController.process_action(user_id, reply, message_type, line_id)
                # MessengerController.check_context_data(user_id, user_id.active_context_data_id)
            elif user_id.active_workflow_line_id:
                MessengerController.check_workflow_line(user_id, user_id.active_workflow_line_id)
            elif user_id.active_rasa_response_id:
                MessengerController.check_rasa_response(user_id, user_id.active_rasa_response_id)
            elif user_id.language:
                MessengerController.check_payload(user_id, 'default_registered')
            else:
                MessengerController.check_payload(user_id, 'unregistered')
                # unregistered, registered_buyer, registered_seller, default_registered
        else:
            pass
        return True

    @route('/api/v1/webhook/search', type='json', auth='public', cors='*', csrf=False, save_session=False)
    def webhook_search(self, **kwargs):
        # Simple Webhook code which will display data in logger
        logger.info("===Webhook Search Data: %s", kwargs)
        return True

    @route('/api/v1/webhook', type='json', auth='public', cors='*', csrf=False, save_session=False)
    def webhook(self, **kwargs):
        # Simple Webhook code which will display data in logger
        logger.info("====Webhook Data: %s", kwargs)
        return True

# # # call kafka_consumer_call method in thread
# def kafka_consumer_call(topic=TOPICS, servers=BROKERS):
#     print("Thread started")
#     consumer = KafkaConsumer(topic, bootstrap_servers=servers, auto_offset_reset='earliest',
#                              enable_auto_commit=True, group_id='data-science',
#                              value_deserializer=lambda x: json.loads(x.decode('utf-8')))
#     for message in consumer:
#         try:
#             message = message.value.get('entry')
#             if message and message[0].get('changes'):
#                 payload = {
#                     "jsonrpc": "2.0",
#                     "params": {
#                         "message": message[0].get('changes')[0].get('value').get("messages")[0]
#                     }
#                 }
#                 requests.post(BASE_URL + "/messenger/receive/message", json=payload)
#                 # self.messenger_receive_message(**message[0].get('changes')[0].get('value'))
#         except Exception as e:
#             logging.exception(e)
#
#
# kafka_thread = threading.Thread(target=kafka_consumer_call, args=())
# kafka_thread.start()
