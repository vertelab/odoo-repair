{
    'name': 'Repair: Work Order Bridge',
    'version': '18.0.0.3.0',
    'summary': 'Give every repair a work order carrier so it can be planned',
    'category': 'Manufacturing/Repair',
    'description': """
Repair: Work Order Bridge
=========================

A repair order is the case: intake, receipt, the customer's matter, warranty
and material consumption. It has no work order, so it cannot be planned
alongside manufacturing.

This module gives the repair a **work order carrier**: a manufacturing order
is created automatically for the repair, and its operation becomes the
``mrp.workorder`` that gets planned. The repair itself stays the case; the
work order becomes the planning unit.

Because the repair's work order *is* an ``mrp.workorder``, it shows up in the
Gantt views, the week planner and the assignment board together with
manufacturing work orders. No separate planning view is built here.

Features
--------

* Automatic manufacturing order when a repair is created
* Explicit, unlinkable link between repair and manufacturing order
* Smart buttons in both directions
* Mirrored planning fields: assigned technician, planned start and finish,
  responsible user and status

Material consumption stays on the repair order, following Odoo standard. This
module adds no material logic of its own.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-repair',
    'depends': [
        'repair',
        'mrp',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_order_views.xml',
        'wizard/repair_late_confirm_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workorder_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
