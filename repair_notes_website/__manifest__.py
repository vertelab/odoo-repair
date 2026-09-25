{
    'name': 'Sale: Webshop Description',
    'version': '18.0.0.1.0',
    'summary': 'Sale order webshop description.',
    'category': 'Sales',
    'description': '''
Webshop Description
===================

    This module allows customers to add description from webshop to sale order.

    Features:

        - Web integration: Exposes HTTP endpoints for external systems.
        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on sale.order, sale.order.line.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-repair/repair_notes_website',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-sale',
    'depends': ['sale', 'website_sale', 'repair'],
    'data': [
        'views/sale_order_views.xml',
        'views/template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'repair_notes_website/static/src/js/website_sale.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}