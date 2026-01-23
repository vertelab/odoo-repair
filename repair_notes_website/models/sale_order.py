import logging

from odoo import api, models, fields, _
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super()._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        
        if values.get('line_id') and kwargs.get('repair_note'):
            line = self.env['sale.order.line'].sudo().browse(values['line_id'])

            if line.product_id.create_repair:
                line.repair_note = kwargs['repair_note']
        return values

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    repair_note = fields.Char(string="Repair Note")

    def _create_repair_order(self):
        new_repair_vals = []
        for line in self:
            # One RO for each line with at least a quantity of 1, quantities > 1 don't create multiple ROs
            if any(line.id == ro.sale_order_line_id.id for ro in line.order_id.sudo().repair_order_ids) and float_compare(line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) > 0:
                binded_ro_ids = line.order_id.sudo().repair_order_ids.filtered(lambda ro: ro.sale_order_line_id.id == line.id and ro.state == 'cancel')
                binded_ro_ids.action_repair_cancel_draft()
                binded_ro_ids._action_repair_confirm()
                continue
            if not line.product_template_id.sudo().create_repair or line.move_ids.sudo().repair_id or float_compare(line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) <= 0:
                continue

            order = line.order_id
            default_repair_vals = {
                'state': 'confirmed',
                'partner_id': order.partner_id.id,
                'sale_order_id': order.id,
                'sale_order_line_id': line.id,
                'picking_type_id': order.warehouse_id.repair_type_id.id,
                'internal_notes': line.repair_note,
            }
            if line.product_id.tracking == 'serial':
                vals = {
                    **default_repair_vals,
                    'product_id': line.product_id.id,
                    'product_qty': 1,
                    'product_uom': line.product_uom.id,
                }
                new_repair_vals.extend([vals] * int(line.product_uom_qty))
            elif line.product_id.type == 'consu':
                new_repair_vals.append({
                    **default_repair_vals,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                })
            else:
                new_repair_vals.append(default_repair_vals.copy())

        if new_repair_vals:
            self.env['repair.order'].sudo().create(new_repair_vals)