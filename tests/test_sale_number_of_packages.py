# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class SaleNumberOfPackagesTestCase(ModuleTestCase):
    'Test Sale Number Of Packages module'
    module = 'sale_number_of_packages'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        SaleNumberOfPackagesTestCase
    ))
    return suite
