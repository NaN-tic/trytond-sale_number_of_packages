# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.tools import grouped_slice

__all__ = ['Product', 'ProductPack']
__metaclass__ = PoolMeta


class Product:
    __name__ = 'product.product'
    normalized_number_of_packages = fields.Function(fields.Integer(
            'Normalized number of packages', states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'get_quantity', searcher='search_quantity')
    forecast_normalized_number_of_packages = fields.Function(
        fields.Integer('Forecast Normalized number of packages', states={
                'invisible': ~Eval('package_required', False),
                }, depends=['package_required']),
        'get_quantity', searcher='search_quantity')

    @classmethod
    def _quantity_context(cls, name):
        if name.endswith('normalized_number_of_packages'):
            quantity_fname = name.replace('normalized_number_of_packages',
                'number_of_packages')
            context = super(Product, cls)._quantity_context(quantity_fname)
            context['normalized_number_of_packages'] = True
            return context
        return super(Product, cls)._quantity_context(name)


class ProductPack:
    __name__ = 'product.pack'

    @classmethod
    def __setup__(cls):
        super(ProductPack, cls).__setup__()
        cls._error_messages.update({
                'change_product': ('You cannot change the Product for '
                    'a packaging which is associated to moves or sales.'),
                'change_qty': ('You cannot change the Quantity by Package for '
                    'a packaging which is associated to moves or sales.'),
                'delete_packaging': ('You cannot delete a packaging which is '
                    'associated to moves or sales.'),
                })

    @classmethod
    def check_no_move(cls, packagings, error):
        SaleLine = Pool().get('sale.line')
        for sub_packagings in grouped_slice(packagings):
            sale_lines = SaleLine.search([
                    ('sale.state', 'not in', ['draft', 'cancel']),
                    ('package', 'in', [t.id for t in sub_packagings]),
                    ],
                limit=1, order=[])
            if sale_lines:
                cls.raise_user_error(error)
        super(ProductPack, cls).check_no_move(packagings, error)
