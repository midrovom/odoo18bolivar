from odoo import fields, models


class AnalyticsSalesMove(models.Model):
    _name = 'analytics.sales.move'
    _description = 'Línea de ventas y devoluciones Analytics Sales'
    _order = 'date desc, id desc'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True, ondelete='cascade')
    source_key = fields.Char(required=True, index=True, copy=False, readonly=True)
    source_line_id = fields.Char(readonly=True, index=True)
    source_kind = fields.Selection([('api', 'API'), ('historico', 'Histórico Excel/CSV')], default='api', required=True)
    api_last_checked_at = fields.Datetime(string='Última consulta API de esta clave', readonly=True, index=True)
    api_last_checked_kind = fields.Selection([('annual', 'Ventas anuales'), ('monthly', 'Ventas mensuales')], string='Última API consultada', readonly=True)
    document_type = fields.Selection([('FA', 'Factura'), ('DE', 'Devolución')], required=True, index=True)
    document_number = fields.Char(required=True, index=True)
    invoice_display = fields.Char(string='Factura comercial')
    date = fields.Date(required=True, index=True)
    local_id = fields.Many2one('analytics.sales.local', string='Local (nlocal)', required=True, index=True, ondelete='restrict')
    seller = fields.Char(string='Vendedor', index=True)
    seller_code = fields.Char(string='Código vendedor', index=True)
    line_name = fields.Char(string='Línea de producto', index=True)
    brand = fields.Char(string='Marca', index=True)
    sku = fields.Char(string='SKU', index=True)
    modelo = fields.Char(string='Modelo', index=True)
    product_name = fields.Char(string='Descripción del producto')
    quantity = fields.Float(string='Unidades absolutas', required=True, digits=(16, 3))
    total_net = fields.Float(string='Valor absoluto neto', required=True, digits=(16, 2))
    # Cost is hidden at ORM field security level, as well as protected by model ACL.
    total_cost = fields.Float(string='Costo absoluto', digits=(16, 2), groups='analytics_sales.group_analytics_sales_admin')
    cost_known = fields.Boolean(default=False, groups='analytics_sales.group_analytics_sales_admin')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('analytics_sales_source_key_unique', 'unique(company_id, source_key)', 'La línea de origen ya está registrada para esta compañía.'),
        ('analytics_sales_units_nonnegative', 'CHECK(quantity >= 0)', 'La cantidad debe ser positiva.'),
        ('analytics_sales_net_nonnegative', 'CHECK(total_net >= 0)', 'El valor monetario absoluto debe ser positivo.'),
    ]
