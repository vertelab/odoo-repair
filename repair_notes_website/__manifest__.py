{
    'name': 'Sale: Webshop Description',
    'version': '18.0.0.1.0',
    'summary': 'Sale order webshop description',
    'category': 'Sales',
    'description': """
        This module allows customers to add description from webshop to sale order.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-sale/sale_order_webshop_description',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-sale',
    'depends': ['sale', 'website_sale'],
    'data': [
        'views/template.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'repair_notes_website/static/src/js/website_sale.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}