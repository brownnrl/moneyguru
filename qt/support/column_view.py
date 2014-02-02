# -*- coding: utf-8 -*-
# Created By: Nelson Brown
# Created On: 2014-02-01
# Copyright 2014 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

__author__ = 'nelson'

from collections import namedtuple

from PyQt4.QtCore import QRectF, QSize, Qt
from PyQt4.QtGui import QStyleOptionViewItemV4, QStyle, QTextOption

import re
import logging

CURR_VALUE_RE = re.compile(r"([^\d]{3} )?(.*)")
# Simple named tuple to separate the currency from the value
DisplayAmount = namedtuple('DisplayAmount', 'currency value')

class AmountPainter:

    def __init__(self, attr_name, model):
        self._attr_name = attr_name
        self._model = model


    def _get_data_from_index(self, index):
        if not index.isValid():
            return None
        column = self._model.columns.column_by_index(index.column())
        if column.name != self._attr_name:
            return None
        amount = getattr(self._model[index.row()], column.name)

        amount = CURR_VALUE_RE.match(amount)

        if amount is None:
            logging.warning("Amount for column %s index row %s "
                            "with amount '%s' did not match regular "
                            "expression for amount painting." %
                            (column.name, index.row(), amount))
            return None

        amount = amount.groups()

        return DisplayAmount("" if amount[0] is None else amount[0].strip(), amount[1])
        """
        do_paint_currency = amount.currency != ""
        # Use the currently formatted string just remove the currency information
        # for separate painting.
        cur_width = option.fontMetrics.width(amount.currency) \
                        if do_paint_currency \
                        else option.fontMetrics.width("XXX")
        val_width = option.fontMetrics.width(amount.value)

        return cur_width, val_width

    def sizeHint(self, option, index):
        amount = self._get_data_from_index(index)
        if amount is None:
            return None
        option = QStyleOptionViewItemV4(option)
        cur_width, val_width = self._get_amount_text_widths(amount, option)
        # Add some extra spacing in between (15) and padding on sides (5,5)
        return QSize(5+cur_width+15+val_width+5, option.fontMetrics.height())

    def paint(self, painter, option, index):
        column_data = self._get_data_from_index(index)
        if column_data is None:
            return
        option = QStyleOptionViewItemV4(option)
        painter.setFont(option.font)
        cur_width, val_width = self._get_amount_text_widths(column_data, option)
        font_height = option.fontMetrics.height()
        do_paint_currency = cur_width > 0
        is_selected = bool(option.state & QStyle.State_Selected)
        is_active = bool(option.state & QStyle.State_Active)
        if is_selected and is_active:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.black)
        if do_paint_currency:
            painter.drawText(QRectF(4+option.rect.left(),
                                    option.rect.top(),
                                    cur_width,
                                    font_height),
                             column_data.currency,
                             QTextOption(Qt.AlignVCenter))
        painter.drawText(QRectF(option.rect.right() - val_width - 5,
                                option.rect.top(),
                                val_width,
                                font_height),
                         column_data.value,
                         QTextOption(Qt.AlignVCenter))
