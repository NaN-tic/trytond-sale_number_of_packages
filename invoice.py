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
        self.quantity = None
        if self.number_of_packages != None:
            if self.package and self.package.qty:
                self.quantity = self.number_of_packages * self.package.qty
