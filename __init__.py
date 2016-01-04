# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *
from .product import *
from .sale import *
from .stock import *


def register():
    Pool.register(
        InvoiceLine,
        Sale,
        SaleLine,
        Product,
        ProductPack,
        Lot,
        Move,
        ShipmentOut,
        Location,
        module='sale_number_of_packages', type_='model')
