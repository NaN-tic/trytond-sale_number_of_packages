# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.modules.stock_number_of_packages.package import PackagedMixin

__all__ = ['SaleLine']


class SaleLine(PackagedMixin, metaclass=PoolMeta):
    __name__ = 'sale.line'

    def get_invoice_line(self):
        invoice_lines = super(SaleLine, self).get_invoice_line()
        if not invoice_lines:
            return invoice_lines
        if not self.package:
            return invoice_lines

        for invoice_line in invoice_lines:
            if invoice_line.type != 'line':
                continue

            if (self.sale.invoice_method == 'order' or
                    not self.product or
                    self.product.type == 'service' or
                    not getattr(invoice_line, 'stock_moves', None)):
                if not self.package or not self.number_of_packages:
                    continue
                invoice_line.package = self.package
                if invoice_line.quantity != abs(self.quantity):
                    number_of_packages = int(round(invoice_line.quantity /
                            self.package.qty))
                else:
                    number_of_packages = abs(self.number_of_packages)
            else:
                number_of_packages = 0
                packages = set()
                for move in invoice_line.stock_moves:
                    if move.package:
                        packages.add(move.package)
                    number_of_packages += move.number_of_packages or 0
                if len(packages) == 1:
                    invoice_line.package = packages.pop()
                invoice_line.number_of_packages = number_of_packages
        return invoice_lines

    def get_move(self, shipment_type):
        move = super(SaleLine, self).get_move(shipment_type)
        if not move:
            return
        if not self.package or not self.number_of_packages:
            return

        move.package = self.package
        # TODO: UoM?
        if move.quantity != abs(self.quantity):
            move.number_of_packages = int(
                round(move.quantity / self.package.qty))
        else:
            move.number_of_packages = self.number_of_packages
        return move

    @classmethod
    def validate(cls, records):
        super(SaleLine, cls).validate(records)
        for line in records:
            if line.sale.state not in ('draft', 'cancel'):
                line.check_package(line.quantity)
