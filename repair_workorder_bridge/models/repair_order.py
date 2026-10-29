# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Context key used to stop the mirror hooks from calling each other. Without
# it, writing a field on the repair triggers the manufacturing order hook,
# which writes back on the repair, and so on.
SKIP_SYNC = 'repair_workorder_bridge_skip_sync'


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    production_id = fields.Many2one(
        'mrp.production', string='Work Order Carrier',
        copy=False, index=True, check_company=True,
        help="Manufacturing order that carries the work order for this repair. "
             "Created automatically; can be unlinked manually.",
    )
    work_order_count = fields.Integer(
        compute='_compute_work_order_count', string='Work Orders',
    )

    # Planning fields mirrored to the work order (design.md Beslut 6).
    #
    # ``schedule_date`` is deliberately not among them: it is the deadline the
    # customer was promised, not the planned start. Mirroring it would make the
    # two concepts collapse into one. See design.md Beslut 3.
    technician_id = fields.Many2one(
        'hr.employee', string='Assigned Technician', copy=False,
        help="Mirrored to the work order's assigned employee.",
    )
    planned_start = fields.Datetime(
        string='Planned Start', copy=False,
        help="Mirrored to the work order's planned start.",
    )
    planned_finished = fields.Datetime(
        string='Planned Finish', copy=False,
        help="Mirrored to the work order's planned finish.",
    )

    @api.depends('production_id')
    def _compute_work_order_count(self):
        for repair in self:
            repair.work_order_count = len(repair.production_id.workorder_ids)

    # ------------------------------------------------------------------
    # Automatic carrier (design.md Beslut 5)
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Give every repair a work order carrier.

        A repair order has no work order of its own, so it cannot be planned
        next to manufacturing. Creating the carrier up front means the repair
        is plannable from the moment it exists, instead of only after someone
        remembers to create a manufacturing order for it.

        The carrier is created without a BoM lookup when the product has none:
        ``mrp.production`` falls back to the product's bill of materials, and a
        repair product without routing yields no work order. That is a
        configuration problem, not a reason to refuse the repair -- the link is
        still useful (smart buttons, mirroring) and the user can add routing
        later.
        """
        repairs = super().create(vals_list)
        for repair in repairs:
            if not repair.production_id:
                repair._create_work_order_carrier()
        return repairs

    def _create_work_order_carrier(self):
        """Create the manufacturing order that carries this repair's work order."""
        self.ensure_one()
        if self.production_id:
            return self.production_id
        if not self.product_id:
            # Nothing to manufacture yet. The carrier is created when the
            # product is set; see ``write``.
            return self.env['mrp.production']
        production = self.env['mrp.production'].create(
            self._prepare_work_order_carrier_vals()
        )
        self.with_context(**{SKIP_SYNC: True}).write({'production_id': production.id})
        return production

    def _prepare_work_order_carrier_vals(self):
        """Values for the carrier manufacturing order.

        ``origin`` carries the repair number so the manufacturing order can be
        traced back to the case it belongs to, in the same way a manufacturing
        order created from a sale order carries the sale order name.

        ``bom_id`` is resolved here on purpose. ``mrp.production.create()``
        does not look up a bill of materials on its own -- the form view does
        it through an onchange. Without an explicit ``bom_id`` the carrier gets
        no routing, and without routing there is no work order to plan, which
        is the entire point of the bridge.

        ``_bom_find`` is not used: it filters on bill-of-materials type and on
        product type in a way that returns nothing for a service product, even
        when a valid bill of materials exists. A plain search does the job.
        """
        self.ensure_one()
        bom = self.env['mrp.bom'].search([
            '|', ('product_id', '=', self.product_id.id),
            '&', ('product_id', '=', False),
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ('company_id', 'in', [False, self.company_id.id]),
        ], order='sequence, id', limit=1)
        return {
            'product_id': self.product_id.id,
            'product_qty': self.product_qty or 1.0,
            'product_uom_id': self.product_uom.id or self.product_id.uom_id.id,
            'bom_id': bom.id if bom else False,
            'origin': self.name,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id or False,
        }

    def write(self, vals):
        """Create the carrier when the product is set after creation, and
        mirror planning changes onto the work order.

        The mirror is triggered here rather than through ``@api.depends``
        because the planning fields are plain stored fields with no compute:
        nothing would notice that they changed.
        """
        res = super().write(vals)
        if 'product_id' in vals:
            for repair in self:
                if not repair.production_id and repair.product_id:
                    repair._create_work_order_carrier()
        if {'technician_id', 'planned_start', 'planned_finished'} & set(vals):
            # Tell the mirror whether the end date was set explicitly in this
            # write. Without that, a repair that already has a planned finish
            # would keep its old end when only the start moves -- and Odoo
            # refuses a work order whose end is before its start.
            self.with_context(planned_finished_given='planned_finished' in vals)._sync_to_workorder()
        return res

    # ------------------------------------------------------------------
    # Unlinkable link (design.md Beslut 5, interpretation A)
    # ------------------------------------------------------------------

    def action_unlink_production(self):
        """Break the link to the carrier.

        Interpretation A: breaking the link is a deliberate exception to the
        rule that every repair gets a carrier. No new carrier is created
        afterwards -- otherwise the button would do nothing.
        """
        for repair in self:
            if not repair.production_id:
                raise UserError(_("This repair has no work order carrier."))
            production = repair.production_id
            repair.with_context(**{SKIP_SYNC: True}).write({'production_id': False})
            # The carrier exists only for this repair; leaving it behind would
            # litter the manufacturing order list with orphans.
            if not production.bridge_repair_ids and production.state == 'draft':
                production.unlink()

    def action_view_production(self):
        """Open the carrier manufacturing order."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_production(self):
        """Re-create the carrier after the link was broken.

        Breaking the link is deliberate and creates nothing afterwards -- the
        button would otherwise be pointless. This action is the explicit way
        back: the user asks for a carrier again.
        """
        for repair in self:
            if repair.production_id:
                raise UserError(_("This repair already has a work order carrier."))
            if not repair.product_id:
                raise UserError(_("Set a product before creating a work order carrier."))
            repair._create_work_order_carrier()

    # ------------------------------------------------------------------
    # Mirroring (design.md Beslut 6)
    # ------------------------------------------------------------------

    def _get_carrier_workorder(self):
        """Return the work order that represents this repair, if any.

        A carrier with several operations has several work orders. The repair
        is planned as the first one -- the operation that starts the work --
        because the planning views group per work order and a repair must not
        appear several times on the board.
        """
        self.ensure_one()
        return self.production_id.workorder_ids.sorted('sequence')[:1]

    def _sync_to_workorder(self):
        """Push the planning fields onto the carrier's work order.

        When only the planned start moves, the work order's end date is moved
        with it, keeping the duration. Odoo refuses a work order whose end is
        before its start (``mrp.workorder.write``), so writing the start alone
        would raise a message about the work order's end date -- a message that
        makes no sense to someone who only changed the repair's planned start.
        """
        if self.env.context.get(SKIP_SYNC):
            return
        finish_given = self.env.context.get('planned_finished_given')
        for repair in self:
            workorder = repair._get_carrier_workorder()
            if not workorder:
                continue
            values = {}
            if repair.technician_id:
                values['main_employee_id'] = repair.technician_id.id
            if repair.planned_start:
                values['date_start'] = repair.planned_start
                # Odoo requires both dates when the start moves: writing the
                # start alone makes it derive the duration from the *old* end
                # and raise "the planned end date cannot be prior to the
                # planned start". ``bypass_duration_calculation`` does not help,
                # the check runs before it. So the end is always sent, keeping
                # the duration unless the user gave an explicit end.
                if finish_given and repair.planned_finished:
                    values['date_finished'] = repair.planned_finished
                elif workorder.date_start and workorder.date_finished:
                    values['date_finished'] = (
                        workorder.date_finished
                        - workorder.date_start
                        + repair.planned_start
                    )
            elif repair.planned_finished:
                values['date_finished'] = repair.planned_finished
            if values:
                # ``bypass_duration_calculation`` keeps Odoo from recomputing
                # the end date from the operation's duration. Without it, a
                # start written without an end makes Odoo derive the duration
                # from the *old* end and raise "the planned end date cannot be
                # prior to the planned start".
                workorder.with_context(
                    **{SKIP_SYNC: True, 'bypass_duration_calculation': True}
                ).write(values)
                # The work order owns its end date: it derives it from the
                # operation's duration, so an end date we write may come back
                # different. Mirror the actual value so the repair does not
                # keep a planned finish the work order never accepted.
                repair.with_context(**{SKIP_SYNC: True}).write({
                    'planned_start': workorder.date_start,
                    'planned_finished': workorder.date_finished,
                })

    def _sync_from_workorder(self):
        """Pull the planning fields back from the carrier's work order."""
        if self.env.context.get(SKIP_SYNC):
            return
        for repair in self:
            workorder = repair._get_carrier_workorder()
            if not workorder:
                continue
            values = {}
            if workorder.main_employee_id and workorder.main_employee_id != repair.technician_id:
                values['technician_id'] = workorder.main_employee_id.id
            if workorder.date_start and workorder.date_start != repair.planned_start:
                values['planned_start'] = workorder.date_start
            if workorder.date_finished and workorder.date_finished != repair.planned_finished:
                values['planned_finished'] = workorder.date_finished
            if values:
                repair.with_context(**{SKIP_SYNC: True}).write(values)

    # ------------------------------------------------------------------
    # Status (design.md Beslut 6, interpretation C)
    # ------------------------------------------------------------------

    #: Manufacturing order state -> repair state. The repair follows the work.
    PRODUCTION_TO_REPAIR_STATE = {
        'draft': 'draft',
        'confirmed': 'confirmed',
        'progress': 'under_repair',
        'to_close': 'under_repair',
        'done': 'done',
        'cancel': 'cancel',
    }

    def _sync_state_from_production(self):
        """Let the repair follow the manufacturing order's state.

        Interpretation C: the repair follows the work, not the other way
        around. Closing the repair does **not** close the work order -- a
        repair can be finished administratively while the bench work lingers,
        and an open work order left behind on the week planner is exactly the
        clutter the bridge exists to avoid. The opposite direction is safe:
        when the work is done, the repair is done.

        ``button_mark_done()`` is not used in the other direction because a
        manufacturing order that has work orders refuses it with "You need to
        complete Quality Checks using the Shop Floor". A plannable repair
        always has routing, so that path is closed to us.
        """
        if self.env.context.get(SKIP_SYNC):
            return
        for repair in self:
            if not repair.production_id:
                continue
            target = self.PRODUCTION_TO_REPAIR_STATE.get(repair.production_id.state)
            if target and repair.state != target:
                repair.with_context(**{SKIP_SYNC: True}).write({'state': target})
