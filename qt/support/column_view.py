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

from PyQt4.QtGui import (QStyleOptionViewItemV4,
                         QStyle,
                         QTextOption,
                         QBrush,
                         QFont,
                         QFontMetricsF,
                         QPalette)

import re
import logging

from hscommon.util import nonone

CURR_VALUE_RE = re.compile(r"([^\d]{3} )?(.*)")

# Simple named tuple to separate the currency from the value
DisplayAmount = namedtuple('DisplayAmount', 'currency value')

class Painter:

    paints_text = False

    def __init__(self, attr_name, model, call_super=False):
        self._attr_name = attr_name
        self._model = model
        self.call_super = call_super

    # virtual
    def _getDataFromIndex(self, index):
        """Retrieves model data.

        Retrieves the data from the model.

        Args:
            index - QModelIndex in the model

        Returns:
            getattr of the model by index and column name.
        """
        if not index.isValid():
            return None
        column = self._model.columns.column_by_index(index.column())
        if column.name != self._attr_name:
            return None
        return self._model[index.row()], column

    def _is_selected(self, option):
        return bool(option.state & QStyle.State_Selected)

    def sizeHint(self, option, index):
        """sizeHint returns a QSize of the required size to draw the value.

        Args:
            option - QStyleOptionViewItemV4 normally as passed to a paint event
            index - QModelIndex in the model

        Returns:
            QSize of the required size to draw the value.
        """
        value, column = self._getDataFromIndex(index)
        if value is None:
            return None
        option = QStyleOptionViewItemV4(option)
        value = getattr(value, column.name)
        return QSize(option.fontMetrics.width(value), option.fontMetrics.height())

    def pre_paint(self, option, index):
        pass

    def paint(self, painter, option, index):
        pass

class AmountPainter(Painter):

    paints_text = True

    # private functions
    def _getDataFromIndex(self, index):
        """Retrieves model amount data and converts it to a DisplayAmount.


        Retrieves the amount string from the model based on the column name.
        Uses a regular expression to parse this string, converting it into
        a DisplayAmount to be returned.

        Args:
            index - QModelIndex in the model

        Returns:
            None if the data is not in the model or the regular expression
            failed to parse the data.

            A DisplayAmount with currency and value information used to
            perform amount painting. For example:

            "MXN 432 321,01" -> DisplayAmount("MXN", "432 321,01")
        """
        data = Painter._getDataFromIndex(self, index)

        if not data:
            return

        amount, column = data

        amount = getattr(amount, column.name)

        amount = CURR_VALUE_RE.match(amount)

        if amount is None:
            logging.warning("Amount for column %s index row %s "
                            "with amount '%s' did not match regular "
                            "expression for amount painting.",
                            column.name, index.row(), amount)
            return None

        amount = amount.groups()

        return DisplayAmount(nonone(amount[0], "").strip(), amount[1])

    def _getAmountTextWidths(self, amount, option):
        """Converts DisplayAmount into a tuple of currency and value widths.

        Uses the option parameter to calculate the font width of the currency
        and value strings stored in the DisplayAmount amount parameter.  Returns
        these widths in a tuple, respectively.  Returns a value for the currency
        width as the width of the string 'XXX' used for alignment purposes in the
        paint method.

        Args:
            amount - DisplayAmount containing currency and value strings
            option - QStyleOptionViewItemV4 normally as passed to a paint event

        Returns:
            A tuple of the currency and value widths in the amount.
        """
        do_paint_currency = amount.currency != ""
        # Use the currently formatted string just remove the currency information
        # for separate painting.
        font_metrics = QFontMetricsF(option.font)
        cur_width = font_metrics.width(amount.currency) \
            if do_paint_currency \
            else font_metrics.width("XXX")
        val_width = font_metrics.width(amount.value)
        max_bearing = abs(font_metrics.leftBearing('f')) + abs(font_metrics.rightBearing('f'))

        if option.font.italic():
            if do_paint_currency:
                cur_width += max_bearing
            val_width += max_bearing

        return cur_width, val_width

    def sizeHint(self, option, index):
        """sizeHint returns a QSize of the required size to draw the amount.

        Returns the size to draw the currency, value, and some spacing in between.

        Args:
            option - QStyleOptionViewItemV4 normally as passed to a paint event
            index - QModelIndex in the model

        Returns:
            QSize of the required size to draw the amount
        """
        amount = self._getDataFromIndex(index)
        if amount is None:
            return None
        option = QStyleOptionViewItemV4(option)
        cur_width, val_width = self._getAmountTextWidths(amount, option)
        # Add some extra spacing in between (15) and padding on sides (5,5)
        return QSize(5+cur_width+25+val_width+5, option.fontMetrics.height())

    def paint(self, painter, option, index):
        """Paints the amount within the bounding box provided in the option parameter.

        Draws the currency left aligned and the value of the model amount right aligned.
        Some spacing between with left and right padding is also utilized.

        Args:
            painter - QPainter
            option - QStyleOptionViewItemV4
            index - QModelIndex in the model
        """
        column_data = self._getDataFromIndex(index)
        if column_data is None:
            return
        option = QStyleOptionViewItemV4(option)
        painter.setFont(option.font)
        cur_width, val_width = self._getAmountTextWidths(column_data, option)
        font_height = option.fontMetrics.height()
        do_paint_currency = cur_width > 0 and column_data.currency
        is_selected = self._is_selected(option)
        is_active = bool(option.state & QStyle.State_Active)
        palette_active = QPalette.Active if is_active else QPalette.Inactive
        palette_text = QPalette.HighlightedText if is_selected else QPalette.Text
        pen_color = option.palette.color(palette_active, palette_text)
        painter.setPen(pen_color)

        font_metrics = QFontMetricsF(option.font)

        def adjusted_rect(text, text_rect):
            left_bearing = font_metrics.leftBearing(text[0])
            right_bearing = font_metrics.rightBearing(text[-1])
            return text_rect.adjusted(0, 0, abs(left_bearing) + abs(right_bearing), 0)
        if do_paint_currency:
            text_rect = QRectF(4+option.rect.left(),
                               option.rect.top(),
                               cur_width,
                               font_height)
            # http://stackoverflow.com/questions/23737591/qpainter-drawtext-italic-writes-outside-of-the-rectangle
            if option.font.italic():
                text_rect = adjusted_rect(column_data.currency, text_rect)

            painter.drawText(text_rect,
                             column_data.currency,
                             QTextOption(Qt.AlignCenter | Qt.AlignVCenter))
        text_rect = QRectF(option.rect.right() - val_width - 5,
                           option.rect.top(),
                           val_width,
                           font_height)

        if option.font.italic():
            text_rect = adjusted_rect(column_data.value, text_rect)

        painter.drawText(text_rect,
                         column_data.value,
                         QTextOption(Qt.AlignLeft | Qt.AlignVCenter))


class ChangedPainter(Painter):

    def __init__(self, attr_name, model, call_super=True):
        Painter.__init__(self, attr_name, model, call_super)
        self._paints_text = False

    @property
    def paints_text(self):
        return self._paints_text

    def pre_paint(self, option, index):
        data, column = self._getDataFromIndex(index)

        if not hasattr(data, 'imported') or data.imported is None:
            return

        data = data.imported

        if data.changed(self._attr_name.replace('_import', '')):
            option.font.setWeight(QFont.Bold)
            option.font.setItalic(True)
            option.backgroundBrush = QBrush(Qt.yellow)


class AmountChangedPainter(Painter):

    paints_text = True

    def __init__(self, *args, **kwargs):
        Painter.__init__(self, *args, **kwargs)
        self.call_super = False
        self._changed_painter = ChangedPainter(self._attr_name, self._model)
        self._amount_painter = AmountPainter(self._attr_name, self._model)

    def sizeHint(self, option, index):
        return self._amount_painter.sizeHint(option, index)

    def pre_paint(self, option, index):
        self._changed_painter.pre_paint(option, index)

    def paint(self, painter, option, index):
        self._amount_painter.paint(painter, option, index)

