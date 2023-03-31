# -*- coding: utf-8 -*-
{
    'name': "Rasa-ChatBot",

    'summary': """
        Rasa ChatBot""",

    'description': """
        ChatBot as a Service
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '15.0.0.5',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'mail',
                'mail_bot',
                'im_livechat',
                'product',
                'sale',
                'im_livechat_mail_bot'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rasa/static/json_field.js',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
