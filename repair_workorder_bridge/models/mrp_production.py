# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from .repair_order import SKIP_SYNC


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    repair_order_ids = fields.One2many(
        'repair.order', 'production_id', string='Repairs',
    )
    repair_count = fields.Integer(
        compute='_compute_repair_count', string='Repair Count',
    )

    @api.depends('repair_order_ids')
    def _compute_repair_count(self):
        for production in self:
            production.repair_count = len(production.repair_order_ids)

    def action_view_repair_orders(self):
        """Open the repairs carried by this manufacturing order.

        Core already has ``action_view_repair_orders``, but it resolves the
        link through ``procurement_group_id``/``move_dest_ids`` and therefore
        only finds repairs that created a need. This one uses the explicit
        ``production_id`` and finds every repair the bridge linked.
        """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'repair.action_repair_order_draft'
        )
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id}
        return action

    def write(self, vals):
        """Mirror a changed responsible user onto the repairs."""
        res = super().write(vals)
        if 'user_id' in vals and not self.env.context.get(SKIP_SYNC):
            for production in self:
                repairs = production.repair_order_ids
                if repairs:
                    repairs.with_context(**{SKIP_SYNC: True}).write(
                        {'user_id': vals['user_id'] or False}
                    )
        return res
