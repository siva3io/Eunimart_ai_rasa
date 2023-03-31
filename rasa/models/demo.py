# -*- coding: utf-8 -*-

from odoo import models, fields, api


# TODO: Remove if not required
class DemoProductData(models.Model):
    _name = "demo.product.data"
    _description = "Demo Product Data"

    name = fields.Char(string="Name")
    price = fields.Char(string="Price")
    short_description = fields.Text(string="Short Description")
    images = fields.Text(string="Images")
    rating = fields.Char(string="Rating")
    store_id = fields.Many2one("demo.store.data", string="Store")
    delivery = fields.Char(string="Delivery")
    speciality = fields.Char(string="Speciality")
    weight = fields.Char(string="Weight")
    ingredient_type = fields.Char(string="Ingredient Type")
    brand = fields.Char(string="Brand")
    ingredients = fields.Char(string="Ingredients")
    manufacturer = fields.Char(string="Manufacturer")
    package_information = fields.Char(string="Package Information")
    country_of_origin = fields.Char(string="Country of Origin")


class DemoStoreData(models.Model):
    _name = "demo.store.data"
    _description = "Demo Store Data"

    name = fields.Char(string="Name")
    demo_product_data_ids = fields.One2many(comodel_name="demo.product.data", inverse_name="store_id",
                                            string="Products")
