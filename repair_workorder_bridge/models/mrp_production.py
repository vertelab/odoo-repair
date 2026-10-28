# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from .repair_order import SKIP_SYNC


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # ``repair_order_ids`` is deliberately not called ``repair_ids`` and the
    # counter is not called ``repair_count``: ``mrp_repair`` (auto_install)
    # already defines ``repair_count`` and ``action_view_repair_orders`` on
    # this model, resolving them through ``procurement_group_id``. Two modules
    # declaring the same field name on the same model works only by accident of
    # load order, so the bridge keeps its own names.
    bridge_repair_ids = fields.One2many(
        'repair.order', 'production_id', string='Carried Repairs',
    )
    bridge_repair_count = fields.Integer(
        compute='_compute_bridge_repair_count', string='Carried Repair Count',
    )

    @api.depends('bridge_repair_ids')
    def _compute_bridge_repair_count(self):
        for production in self:
            production.bridge_repair_count = len(production.bridge_repair_ids)

    def action_view_carried_repairs(self):
        """Open the repairs carried by this manufacturing order.

        Core's ``action_view_repair_orders`` resolves the link through
        ``procurement_group_id``/``move_dest_ids`` and therefore only finds
        repairs that created a need. This one uses the explicit
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
        """Mirror a changed responsible user onto the repairs, and let the
        repairs follow a changed state."""
        res = super().write(vals)
        if self.env.context.get(SKIP_SYNC):
            return res
        if 'user_id' in vals:
            for production in self:
                repairs = production.bridge_repair_ids
                if repairs:
                    repairs.with_context(**{SKIP_SYNC: True}).write(
                        {'user_id': vals['user_id'] or False}
                    )
        if 'state' in vals:
            self.bridge_repair_ids._sync_state_from_production()
        return res
