# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import math
from sql import Null
from trytond.model import Model, fields, Check
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['Product', 'Lot', 'Move', 'ShipmentOut', 'Location']


class Product(metaclass=PoolMeta):
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
        context = super(Product, cls)._quantity_context(name)
        if name.endswith('normalized_number_of_packages'):
            context['normalized_number_of_packages'] = True
            context['number_of_packages'] = True
        return context


class Lot(metaclass=PoolMeta):
    __name__ = 'stock.lot'
    number_of_packages_multiplier = fields.Integer(
        'Number of Packages Multiplier', states={
            'invisible': ~Bool(Eval('package_qty')),
            }, depends=['package_qty'],
        help="How many packages of this lot should be used to supply a "
        "default package?")
    number_of_packages_divider = fields.Integer('Number of Packages Divider',
        states={
            'invisible': ~Bool(Eval('package_qty')),
            }, depends=['package_qty'],
        help="How many default packages should be used to supply a package of "
        "this lot?")
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
    def __setup__(cls):
        super(Lot, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('check_lot_number_of_packages_multiplier_pos',
                Check(t, (t.number_of_packages_multiplier == Null)
                    | (t.number_of_packages_multiplier > '0')),
                'Number of Packages Multiplier of Lot must be positive.'),
            ('check_lot_number_of_packages_divider_pos',
                Check(t, (t.number_of_packages_divider == Null)
                    | (t.number_of_packages_divider > '0')),
                'Number of Packages Divider of Lot must be positive.'),
            ]

    @classmethod
    def _quantity_context(cls, name):
        if name.endswith('normalized_number_of_packages'):
            quantity_fname = name.replace('normalized_number_of_packages',
                'number_of_packages')
            context = super(Lot, cls)._quantity_context(quantity_fname)
            context['normalized_number_of_packages'] = True
            return context
        return super(Lot, cls)._quantity_context(name)

    def compute_number_of_packages(self, normalized_number_of_packages):
        if not normalized_number_of_packages:
            return normalized_number_of_packages
        if self.number_of_packages_divider:
            return int(math.ceil(
                    normalized_number_of_packages
                    / float(self.number_of_packages_divider)))
        elif self.number_of_packages_multiplier:
            return (normalized_number_of_packages
                * self.number_of_packages_multiplier)
        return normalized_number_of_packages

    def compute_normalized_number_of_packages(self, number_of_packages):
        if not number_of_packages:
            return number_of_packages
        if self.number_of_packages_divider:
            return number_of_packages * self.number_of_packages_divider
        elif self.number_of_packages_multiplier:
            return int(math.ceil(
                    number_of_packages
                    / float(self.number_of_packages_multiplier)))
        return number_of_packages

    @classmethod
    def validate(cls, lots):
        super(Lot, cls).validate(lots)
        for lot in lots:
            lot.check_number_of_packages_multiplier_divisor()

    def check_number_of_packages_multiplier_divisor(self):
        if (self.number_of_packages_multiplier == None
                and self.number_of_packages_divider == None):
            return
        if (self.number_of_packages_multiplier == 1
                and self.number_of_packages_divider == 1):
            return
        if (self.number_of_packages_multiplier == 1
                and self.number_of_packages_divider != 1
                or self.number_of_packages_divider == 1
                and self.number_of_packages_multiplier != 1
                or self.number_of_packages_divider != None
                and self.number_of_packages_multiplier != None):
            raise UserError(gettext(
                'sale_number_of_packages.unexpected_number_of_packages_divider_multiplier',
                lot=self.rec_name))

    @classmethod
    def create(cls, vlist):
        for vals in vlist:
            if vals.get('number_of_packages_multiplier', 0) == 1:
                vals['number_of_packages_divider'] = 1
            elif vals.get('number_of_packages_divider', 0) == 1:
                vals['number_of_packages_multiplier'] = 1
            elif vals.get('number_of_packages_multiplier') != None:
                vals['number_of_packages_divider'] = None
            elif vals.get('number_of_packages_divider') != None:
                vals['number_of_packages_multiplier'] = None
        return super(Lot, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        args = []
        for records, vals in zip(actions, actions):
            if vals.get('number_of_packages_multiplier', 0) == 1:
                vals['number_of_packages_divider'] = 1
            elif vals.get('number_of_packages_divider', 0) == 1:
                vals['number_of_packages_multiplier'] = 1
            elif vals.get('number_of_packages_multiplier') != None:
                vals['number_of_packages_divider'] = None
            elif vals.get('number_of_packages_divider') != None:
                vals['number_of_packages_multiplier'] = None
            args.extend((records, vals))
        super(Lot, cls).write(*args)


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'


    @classmethod
    def assign_try(cls, moves, with_childs=True, grouping=('product',)):
        if not Transaction().context.get('assign_number_of_packages'):
            return super(Move, cls).assign_try(moves, with_childs=with_childs,
                grouping=grouping)
        assert grouping in (('product',), ('product', 'lot')), \
            "Unexpected grouping"
        package_lot_moves = []
        package_moves = []
        no_package_moves = []
        for move in moves:
            if move.internal_quantity < move.product.default_uom.rounding:
                continue
            if move.package or move.product.package_required:
                if not move.package:
                    raise UserError(gettext(
                        'sale_number_of_packages.package_required',
                        move=move.rec_name))
                if move.number_of_packages == None:
                    raise UserError(gettext(
                        'sale_number_of_packages.number_of_packages_required',
                        move=move.rec_name))
                if move.lot or move.product.lot_is_required(
                        move.from_location, move.to_location):
                    package_lot_moves.append(move)
                else:
                    package_moves.append(move)
            else:
                no_package_moves.append(move)
        success = True

        if package_lot_moves:
            success &= cls.assign_try_number_of_packages(package_lot_moves,
                with_childs, ('product', 'lot'))
        if package_moves:
            success &= cls.assign_try_number_of_packages(package_moves,
                with_childs, ('product', 'package'))
        if no_package_moves:
            success &= super(Move, cls).assign_try(no_package_moves,
                with_childs=with_childs, grouping=grouping)
        return success

    @classmethod
    def assign_try_number_of_packages(cls, moves, with_childs, grouping):
        pool = Pool()
        Package = pool.get('product.pack')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')
        Date = pool.get('ir.date')
        Location = pool.get('stock.location')
        Lot = pool.get('stock.lot')
        Move = pool.get('stock.move')

        Transaction().database.lock(Transaction().connection, cls._table)

        if with_childs:
            location2childs = {}
            location_ids = set()
            for move in moves:
                if move.from_location.id in location2childs:
                    continue
                childs = Location.search([
                        ('parent', 'child_of', [move.from_location.id]),
                        ])
                location2childs[move.from_location.id] = childs
                location_ids |= set([l.id for l in childs])
            location_ids = list(location_ids)
        else:
            location2childs = {m.from_location.id: [m.from_location]
                for m in moves}
            location_ids = location2childs.keys()

        product_ids = list(set([m.product.id for m in moves]))
        with Transaction().set_context(
                stock_date_end=Date.today(),
                stock_assign=True,
                number_of_packages=True):
            pbl = Product.products_by_location(
                location_ids=location_ids,
                grouping_filter=(product_ids,),
                grouping=grouping)

        pbl2 = {}
        id2lot = {}
        for key, n_packages in pbl.items():
            n_packages = int(n_packages)
            if n_packages <= 0:
                continue
            pbl2.setdefault(key[:-1], {})[key[-1]] = n_packages
            if grouping[-1] == 'lot' and key[-1]:
                id2lot[key[-1]] = None

        if grouping[-1] == 'lot':
            lots = Lot.browse(id2lot.keys())
            id2lot = {l.id: l for l in lots}

        def get_key(move, location):
            key = (location.id,)
            for field in grouping:
                value = getattr(move, field)
                if isinstance(value, Model):
                    value = value.id
                key += (value,)
            return key

        success = True
        to_write = []
        to_assign = []
        for move in moves:
            if move.state != 'draft':
                continue
            to_location = move.to_location
            location_n_packages = {}
            for location in location2childs[move.from_location.id]:
                key = get_key(move, location)
                subkey = key[:-1]
                key2 = key[-1]
                if key2 == None:  # move without lot/package
                    if subkey in pbl2:
                        if grouping[-1] == 'lot':
                            location_n_packages[location] = (
                                cls._sort_lots_to_pick([
                                    (id2lot[key2], n_packages)
                                    for key2, n_packages
                                    in pbl2[subkey].items()
                                    if key2]))
                        else:
                            location_n_packages[location] = [
                                (key2, n_packages)
                                for key2, n_packages
                                in pbl2[subkey].items()]
                elif subkey in pbl2 and key2 in pbl2[subkey]:
                    location_n_packages[location] = [
                        (key2, pbl2[subkey][key2]),
                        ]

            if grouping[-1] == 'lot':
                to_pick = move.pick_lot_number_of_packages(location_n_packages,
                    id2lot)
            else:
                to_pick = move.pick_package_number_of_packages(
                    location_n_packages)

            picked_n_packages = 0
            for _, _, _, n_packages in to_pick:
                picked_n_packages += n_packages

            not_picked_n_packages = 0
            if move.number_of_packages > picked_n_packages:
                success = False
                first = False
                not_picked_n_packages = (move.number_of_packages
                    - picked_n_packages)
            else:
                first = True

            picked_qty = 0.0
            for from_location, key, n_packages, _ in to_pick:
                values = {
                    'from_location': from_location.id,
                    'number_of_packages': n_packages,
                    }
                if key:
                    values[grouping[-1]] = key
                    if grouping[-1] == 'lot':
                        lot = Lot(key)
                        if not move.package or lot.package != move.package:
                            values['package'] = lot.package.id
                        values['quantity'] = Uom.compute_qty(
                            lot.product_uom,
                            n_packages * lot.package_qty,
                            move.uom)
                    elif key != move.package.id:
                        package = Package(key)
                        values['quantity'] = Uom.compute_qty(
                            package.uom,
                            n_packages * package.qty,
                            move.uom)
                if ('quantity' not in values and move.package
                        and move.package.qty):
                    values['quantity'] = Uom.compute_qty(
                        move.package.uom,
                        n_packages * move.package.qty,
                        move.uom)
                picked_qty += values.get('quantity', 0.0)

                if first:
                    to_write.extend(([move], values))
                    to_assign.append(move)
                    first = False
                else:
                    new_move, = cls.copy([move], default=values)
                    to_assign.append(new_move)

                from_subkey = get_key(move, from_location)[:-1]
                pbl2.setdefault(from_subkey, {}).setdefault(key, 0)
                pbl2[from_subkey][key] -= n_packages

                to_subkey = get_key(move, to_location)[:-1]
                pbl2.setdefault(to_subkey, {}).setdefault(key, 0)
                pbl2[to_subkey][key] += n_packages

            if not_picked_n_packages:
                to_write.extend(([move], {
                            'number_of_packages': not_picked_n_packages,
                            'quantity': (not_picked_n_packages*
                                move.package.qty)
                            }))
            if not_picked_n_packages <= 0 :
                success=True

        if to_write:
            Move.write(*to_write)
        if to_assign:
            Move.assign(to_assign)
        return success

    @classmethod
    def _sort_lots_to_pick(cls, lots_to_pick):
        """
        Receive a list of (lot, quantity) and return an ordered ist of
        (lot_id, quantity)
        """
        return [(x[0].id, x[1]) for x in lots_to_pick]

    def pick_package_number_of_packages(self, location_n_packages):
        """
        Pick the product across the location. Naive (fast) implementation.
        Return a list of tuple (location, package, n packages, n packages) for
        number of packages that can be picked.
        """
        to_pick = []
        needed_n_packages = self.number_of_packages
        for location, available_keys in location_n_packages.items():
            for (key, available_n_packages) in available_keys:
                if available_n_packages <= 0:
                    continue
                if needed_n_packages <= available_n_packages:
                    to_pick.append((
                            location,
                            key,
                            needed_n_packages,
                            needed_n_packages))
                    return to_pick
                else:
                    to_pick.append((
                            location,
                            key,
                            available_n_packages,
                            available_n_packages))
                    needed_n_packages -= available_n_packages
        # Force assignation for consumables:
        if self.product.consumable:
            to_pick.append((
                    self.from_location,
                    None,
                    needed_n_packages,
                    needed_n_packages))
            return to_pick
        return to_pick

    def pick_lot_number_of_packages(self, location_n_packages, id2lot):
        """
        Pick the product across the location. Naive (fast) implementation.
        Return a list of tuple
        (location, lot, n packages, normalized n packages) for number of
        packages that can be picked.
        """
        to_pick = []
        needed_n_packages = self.number_of_packages
        for location, available_keys in location_n_packages.items():
            for (lot_id, available_n_packages) in available_keys:
                if available_n_packages <= 0:
                    continue
                lot = id2lot[lot_id]
                lot_needed_n_packages = lot.compute_number_of_packages(
                    needed_n_packages)
                if lot_needed_n_packages <= available_n_packages:
                    to_pick.append((
                            location,
                            lot_id,
                            lot_needed_n_packages,
                            needed_n_packages,
                            ))
                    return to_pick
                else:
                    normalized_available_n_packages = (
                        lot.compute_normalized_number_of_packages(
                                available_n_packages))
                    to_pick.append((
                            location,
                            lot_id,
                            available_n_packages,
                            normalized_available_n_packages))
                    needed_n_packages -= normalized_available_n_packages
                    if needed_n_packages <= 0:
                        return to_pick
        # Force assignation for consumables:
        if self.product.consumable:
            to_pick.append((
                    self.from_location,
                    None,
                    needed_n_packages,
                    needed_n_packages))
            return to_pick
        return to_pick


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    @classmethod
    def pack(cls, shipments):
        with Transaction().set_context(
                no_check_quantity_number_of_packages=False):
            super(ShipmentOut, cls).pack(shipments)

    def _get_inventory_move(self, move):
        inventory_move = super(ShipmentOut, self)._get_inventory_move(move)
        inventory_move.origin = 'stock.move,%s' % move.id
        return inventory_move


    def _get_outgoing_move(self, move):
        Move = Pool().get('stock.move')
        outgoing_move = super(ShipmentOut, self)._get_outgoing_move(move)
        outgoing_move.lot = move.lot  # move to stock_lot?
        if move.package:
            outgoing_move.package = move.package
            outgoing_move.number_of_packages = move.number_of_packages
        if isinstance(move.origin, Move) and move.origin.origin:
            outgoing_move.origin = move.origin.origin
        else:
            # TODO: do another thing
            outgoing_move.origin = move
        return outgoing_move

    @classmethod
    def _sync_inventory_to_outgoing(cls, shipments, create=True, write=True):
        pool = Pool()
        Move = pool.get('stock.move')

        out_moves = []
        for shipment in shipments:
            outgoing = {}
            for move in shipment.outgoing_moves:
                if move.state == 'cancel':
                    continue
                outgoing.setdefault(move.product.id, [])
                outgoing[move.product.id].append(move)

            for move in shipment.inventory_moves:
                if move.state in ('cancel'):
                    continue
                out = outgoing.get(move.product.id)
                if not out:
                    out = move.origin
                    with Transaction().set_context(_stock_move_split=True):
                         out = Move.copy([out], default={
                            'number_of_packages':move.number_of_packages,
                            'quantity': move.quantity,
                            'package': move.package,
                            'lot': move.lot,})
                else:
                    out = out.pop()
                    out.number_of_packages = move.number_of_packages
                    out.quantity = move.quantity
                    out.lot = move.lot
                    out.package = move.package
                    out_moves.append(out)

        Move.save(out_moves)

    @classmethod
    def assign_try(cls, shipments):
        with Transaction().set_context(assign_number_of_packages=True):
            return super(ShipmentOut, cls).assign_try(shipments)


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'


    normalized_number_of_packages = fields.Function(
        fields.Integer('Normalized number of packages'),
        'get_number_of_packages')
    forecast_normalized_number_of_packages = fields.Function(
        fields.Integer('Forecast Normalized number of packages'),
        'get_number_of_packages')

    @classmethod
    def get_number_of_packages(cls, locations, name):
        if name.endswith('normalized_number_of_packages'):
            new_name = name.replace('normalized_number_of_packages',
                'number_of_packages')
            with Transaction().set_context(number_of_packages=True):
                return super(Location, cls).get_number_of_packages(
                    locations, new_name)
        else:
            return super(Location, cls).get_number_of_packages(
                    locations, name)
