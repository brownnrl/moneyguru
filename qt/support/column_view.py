__author__ = 'nelson'

from .item_delegate import ColumnDelegate

from collections import namedtuple

from PyQt4.QtCore import QRectF, QSize, Qt
from PyQt4.QtGui import QStyleOptionViewItemV4, QStyle, QTextOption

# Simple named tuple to separate the currency from the value
DisplayAmount = namedtuple('DisplayAmount', 'currency value')

class AmountColumnDelegate(ColumnDelegate):

    def _get_data_from_index(self, index):
        if not index.isValid():
            return None
        column = self._model.columns.column_by_index(index.column())
        if column.name != self._column_name:
            return None
        amount = getattr(self._model[index.row()], column.name).split(" ")
        if len(amount) == 2:
            return DisplayAmount(amount[0], amount[1])
        return DisplayAmount("", amount[0])

    def _get_amount_text_widths(self, amount, option):
        """
        Used by both sizeHint and paintEvent to determine size of the column and
        what to write to the cells
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
