# -*- coding: utf-8 -*-
{
    'name': 'CleanGroup Operaciones',
    'version': '18.0.3.1.0',
    'category': 'Operaciones',
    'summary': 'Gestión de ubicaciones, horarios y órdenes de insumos',
    'description': """
        Gestiona ubicaciones de operación, asigna supervisores y empleados
        con horarios, y realiza órdenes de insumos con descuento automático
        de stock, firma digital a mano alzada, foto de entrega y generación de Remito PDF.
    """,
    'author': 'CleanGroup',
    'depends': [
        'base',
        'hr',
        'stock',
        'product',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequences.xml',
        'report/remito_report.xml',
        'report/remito_templates.xml',
        'views/hr_employee_views.xml',
        'views/stock_quant_views.xml',
        'views/cleangroup_location_views.xml',
        'views/cleangroup_employee_schedule_views.xml',
        'views/cleangroup_supply_order_views.xml',
        'views/cleangroup_dashboard_views.xml',
        'views/cleangroup_wizard_views.xml',
        'views/hr_employee_movement_report_views.xml',
        'views/cleangroup_menus.xml',
        'views/webclient_branding_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cleangroup_operations/static/src/css/signature_widget.css',
            'cleangroup_operations/static/src/css/cleangroup_brand.css',
            'cleangroup_operations/static/src/js/signature_widget.js',
            'cleangroup_operations/static/src/xml/signature_widget.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
