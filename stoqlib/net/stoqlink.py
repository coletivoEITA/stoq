# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2015 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##  Author(s): Stoq Team <stoq-devel@async.com.br>
##

import datetime
import decimal
import json

from kiwi.currency import currency
from storm.expr import Sum, Join

from stoqlib.database.expr import Date, DateTrunc
from stoqlib.domain.sale import Sale, SaleItem, SaleView
from stoqlib.domain.sellable import Sellable


def default(obj):
    """Default JSON serializer."""
    if isinstance(obj, currency):
        return str(obj)
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    raise TypeError("Type %r serializable" % type(obj))


def _collect_timeline(store):
    today = datetime.date.today()
    sales = store.find(SaleView, Date(SaleView.confirm_date) == today)
    items = []
    for i in sales:
        items.append(dict(type='sale', identifier=str(i.identifier),
                          when=i.confirm_date, value=i.total))
    items = sorted(items, key=lambda i: i['when'], reverse=True)
    return items


def collect_link_statistics(store):
    one_week = datetime.date.today() - datetime.timedelta(days=7)
    query = Date(Sale.confirm_date) >= one_week

    # Sale chart
    columns = (DateTrunc(u'day', Sale.confirm_date), Sum(Sale.total_amount))
    sale_data = store.find(columns, query)
    sale_data.group_by(columns[0])

    # Best selling
    tables = [Sellable,
              Join(SaleItem, SaleItem.sellable_id == Sellable.id),
              Join(Sale, SaleItem.sale_id == Sale.id)]
    columns = (Sellable.description, Sum(SaleItem.quantity),
               Sum(SaleItem.quantity * SaleItem.price))
    product_data = store.using(*tables).find(columns, query).order_by(-columns[2])
    product_data.group_by(Sellable.description)

    data = dict(
        sales_total=store.find(Sale, query).sum(Sale.total_amount),
        sales_count=store.find(Sale, query).count(),
        best_selling=list(product_data),
        sales_chart=list(sale_data),
        timeline=_collect_timeline(store),
        timestamp=datetime.datetime.now())
    return json.dumps(data, default=default)
