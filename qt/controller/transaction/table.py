# Created By: Virgil Dupras
# Created On: 2009-10-31
# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtCore import Qt, QRectF, QSize
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QStyle, QFontMetrics, QTextOption, QHeaderView, QStyleOptionViewItemV4
import os, string

from qtlib.column import Column
from ...support.item_delegate import ItemDecoration
from ..table import TableDelegate, DATE_EDIT, DESCRIPTION_EDIT, PAYEE_EDIT, ACCOUNT_EDIT
from ..table_with_transactions import TableWithTransactions

from core.gui.transaction_table import TotalRow


# Had to copy this to get the amount field with both currency and value information
try:
    if os.environ.get('USE_PY_AMOUNT'):
        raise ImportError()
    from core.model._amount import Amount
except ImportError:
    print("Using amount_ref")
    from core.model._amount_ref import Amount

class Del:
    """
    Del class for cleaning input:
    See http://stackoverflow.com/questions/1450897/python-removing-characters-except-digits-from-string
    """
    def __init__(self, keep):
        self.keep = dict((ord(c), c) for c in keep)

    def __getitem__(self, k):
        if k in self.keep:
            return k
        else:
            return None

class TransactionTableDelegate(TableDelegate):
    def __init__(self, model, view):
        TableDelegate.__init__(self, model)
        arrow = QPixmap(':/right_arrow_gray_12')
        arrowSelected = QPixmap(':/right_arrow_white_12')

        # The view is needed to set the column size.
        # I also use it to get the current font, but that might be available through
        # the option parameter... I don't know if this is the appropriate location
        # to set the column width.
        self._view = view
        amount_index = self._model.columns.column_by_name('amount').ordered_index
        self._view.horizontalHeader().setResizeMode(amount_index, QHeaderView.ResizeToContents)

        self._decoFromArrow = ItemDecoration(arrow, self._model.show_from_account)
        self._decoFromArrowSelected = ItemDecoration(arrowSelected, self._model.show_from_account)
        self._decoToArrow = ItemDecoration(arrow, self._model.show_to_account)
        self._decoToArrowSelected = ItemDecoration(arrowSelected, self._model.show_to_account)

        # Used to remove non-digit characters
        self._valid_chars = list(string.digits)
        self._valid_chars.extend([',', '.'])
        self._keep_chars = Del(self._valid_chars)
    
    def _get_decorations(self, index, isSelected):
        column = self._model.columns.column_by_index(index.column())
        if column.name == 'from':
            return [self._decoFromArrowSelected if isSelected else self._decoFromArrow]
        elif column.name == 'to':
            return [self._decoToArrowSelected if isSelected else self._decoToArrow]
        else:
            return []

    def _get_amount_from_index(self, index):
        """
        Used by both the sizeHint and paintEvent methods for fetching
        the current amount data from the model for the given index and
        making sure currency information is supported.
        """
        if not index.isValid():
            return None

        column = self._model.columns.column_by_index(index.column())

        if column.name != 'amount':
            return None

        row = self._model[index.row()]

        if not hasattr(row, 'transaction'):
            return None  # No information to work with

        if hasattr(row.transaction.amount, 'value'):
            amount = row.transaction.amount
        else:
            amount = Amount(row.transaction.amount, self._model.document.default_currency)

        return amount

    def _get_amount_texts(self, amount, option):
        """
        Used by both sizeHint and paintEvent to determine size of the column and
        what to write to the cells
        """
        do_paint_currency = amount.currency != self._model.document.default_currency
        # Use the currently formatted string just remove the currency information
        # for separate painting.
        val_string = self._model.document.format_amount(amount).translate(self._keep_chars)
        cur_code = amount.currency.code
        cur_width = option.fontMetrics.width(amount.currency.code) if do_paint_currency else 0
        val_width = option.fontMetrics.width(val_string)

        return cur_width, val_width, cur_code, val_string


    def sizeHint(self, option, index):
        """
        Used by Qt to set the column widths for the amount column
        """

        amount = self._get_amount_from_index(index)

        if amount is None:
            return TableDelegate.sizeHint(self, option, index)

        option = QStyleOptionViewItemV4(option)

        cur_width, val_width, _, _ = self._get_amount_texts(amount, option)

        return QSize(cur_width+val_width+5, option.fontMetrics.height())


    def _paint_amount(self, painter, option, amount, is_selected):
        """
        Paint the amount to the cell.
        """
        option = QStyleOptionViewItemV4(option)

        painter.setFont(self._view.font())

        cur_width, val_width, cur_code, val_string = self._get_amount_texts(amount, option)

        font_height = option.fontMetrics.height()

        do_paint_currency = cur_width > 0

        if is_selected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.black)

        if do_paint_currency:
            painter.drawText(QRectF(option.rect.left(),
                                    option.rect.top(),
                                    cur_width,
                                    font_height),
                             cur_code,
                             QTextOption(Qt.AlignVCenter))

        painter.drawText(QRectF(option.rect.right() - val_width,
                                option.rect.top(),
                                val_width,
                                font_height),
                         val_string,
                         QTextOption(Qt.AlignVCenter))



    def paint(self, painter, option, index):
        # Paint cells as we normally would
        TableDelegate.paint(self, painter, option, index)

        is_selected = bool(option.state & QStyle.State_Selected)

        amount = self._get_amount_from_index(index)

        if amount is None:
            return

        self._paint_amount(painter,
                           option,
                           amount,
                           is_selected)

    

class TransactionTable(TableWithTransactions):
    COLUMNS = [
        Column('status', 25, cantTruncate=True),
        Column('date', 86, editor=DATE_EDIT, cantTruncate=True),
        Column('description', 230, editor=DESCRIPTION_EDIT),
        Column('payee', 150, editor=PAYEE_EDIT),
        Column('checkno', 80),
        Column('from', 120, editor=ACCOUNT_EDIT),
        Column('to', 120, editor=ACCOUNT_EDIT),
        Column('amount', 100, alignment=Qt.AlignRight, cantTruncate=True),
        Column('mtime', 140),
    ]
    
    def __init__(self, model, view):
        TableWithTransactions.__init__(self, model, view)
        self.tableDelegate = TransactionTableDelegate(self.model, self.view)
        self.view.setItemDelegate(self.tableDelegate)
        self.view.sortByColumn(1, Qt.AscendingOrder) # sorted by date by default
        self.view.deletePressed.connect(self.model.delete)

    def _getData(self, row, column, role):
        if not isinstance(row, TotalRow) and role == Qt.DisplayRole and column.name == 'amount':
            return ""  # handled by the paint method in the delegate.
        else:

            return TableWithTransactions._getData(self, row, column, role)
