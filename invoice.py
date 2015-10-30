# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pyson import Bool, Eval
from trytond.pool import PoolMeta

__all__ = ['InvoiceLine']
__metaclass__ = PoolMeta


class InvoiceLine:
    __name__ = 'account.invoice.line'
    package = fields.Many2One('product.pack', 'Packaging', domain=[
            ('product.products', 'in', [Eval('product')]),
            ],
        states={
            'invisible': ~Bool(Eval('product')),
            },
        depends=['product'])
    number_of_packages = fields.Integer('Number of packages', states={
            'invisible': ~Bool(Eval('product')),
            },
        depends=['product'])

    @fields.depends('number_of_packages', 'package')
    def on_change_number_of_packages(self):
        result = {}
        if self.number_of_packages != None:
            if self.package and self.package.qty:
                result['quantity'] = self.number_of_packages * self.package.qty
            else:
                result['quantity'] = None
        else:
            result['quantity'] = None
        return result
