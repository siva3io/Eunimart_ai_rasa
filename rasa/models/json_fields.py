# -*- coding: utf-8 -*-

from odoo.fields import Field
from psycopg2.extras import Json


class JsonField(Field):
    """
    Represents a postgresql Json column (JSON values are mapped to the Python equivalent type of list/dict).
    """

    def read(self, records):
        """ Read the value of ``self`` on ``records``, and store it in cache. """
        raise NotImplementedError("Method read() undefined on %s" % self)

    type = 'json'  # Odoo type of the field (string)
    column_type = ('json', 'json')  # database column type (idents, spec)

    def convert_to_column(self, value, record, values=None, validate=True):
        """ Convert ``value`` from the ``write`` format to the SQL format. """
        # By default the psycopg2 driver does not know how to map dict/list to postgresql json types
        # We need to convert it to the right db type when inserting in the db
        # see https://www.psycopg.org/docs/extras.html
        if value is None or value is False:
            return None
        else:
            return Json(value)