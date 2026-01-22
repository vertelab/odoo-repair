import logging
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)



class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Override to handle product description from website """
        values = super()._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        
        # If we have a line_id in the return values and a description in kwargs
        if values.get('line_id') and kwargs.get('product_description'):
            line = self.env['sale.order.line'].sudo().browse(values['line_id'])
            # Only update description for service products as per original logic intent (check XML template)
            # or if it's generally desired. The original code checked for service type.
            if line.product_id.type == 'service':
                line.name = kwargs['product_description']

        return values