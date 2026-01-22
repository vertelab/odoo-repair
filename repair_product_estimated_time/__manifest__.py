{
    'name': 'Sale: Order Task Time Estimate',
    'version': '18.0.0.1.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'This module adds time estimate to product and sale order line then to task.',
    'category': 'Sales',
    'description': """
    This module adds time estimate to product and sale order line then to task.
    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-sale/sale_order_task_estimate_time',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-sale',
    'depends': ['sale', 'project', 'product'],
    'data': [
        'views/product_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}