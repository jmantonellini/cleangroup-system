from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    cleangroup_product_image = fields.Image(
        string='Imagen',
        related='product_id.image_128',
        readonly=True,
    )