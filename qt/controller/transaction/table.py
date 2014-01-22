# Created By: Virgil Dupras
# Created On: 2009-10-31
# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QPixmap

from qtlib.column import Column
from ...support.item_delegate import ItemDecoration
from ...support.item_delegate import CurrencyPixs
from ..table import TableDelegate, DATE_EDIT, DESCRIPTION_EDIT, PAYEE_EDIT, ACCOUNT_EDIT
from ..table_with_transactions import TableWithTransactions

class TransactionTableDelegate(TableDelegate):


    def __init__(self, model):
        TableDelegate.__init__(self, model)
        arrow = QPixmap(':/right_arrow_gray_12')
        arrowSelected = QPixmap(':/right_arrow_white_12')
        # Generates a set of pixmaps for each currency type on initialization
        # I know we probably have a lot of containing class being created, so
        # there is a lot of redundant pixmaps being generated.  Just trying
        # to get something down on paper here.
        self._currency_pixs = CurrencyPixs()
        self._decoFromArrow = ItemDecoration(arrow, self._model.show_from_account)
        self._decoFromArrowSelected = ItemDecoration(arrowSelected, self._model.show_from_account)
        self._decoToArrow = ItemDecoration(arrow, self._model.show_to_account)
        self._decoToArrowSelected = ItemDecoration(arrowSelected, self._model.show_to_account)

    # I thought left aligned decorations might look nicer for the currencies
    # so this is here just to make that happen
    def paint(self, painter, option, index):
        column = self._model.columns.column_by_index(index.column())

        if column.name == 'amount':
            TableDelegate.paint(self, painter, option, index, align_right=False)
        else:
            TableDelegate.paint(self, painter, option, index, align_right=True)

    def _get_decorations(self, index, isSelected):
        column = self._model.columns.column_by_index(index.column())

        if column.name == 'from':
            return [self._decoFromArrowSelected if isSelected else self._decoFromArrow]
        elif column.name == 'to':
            return [self._decoToArrowSelected if isSelected else self._decoToArrow]
        # We check the overarching model to see if the current set of tranactions has
        # multiple currencies
        elif column.name == 'amount' and self._model.has_multiple_currencies:
            try:
                amount = self._model.rows[index.row()].transaction.amount
                if hasattr(amount, 'currency'):
                    # Lookup the generated pixmap by it's code
                    return [self._currency_pixs.currency_decorations[amount.currency.code]]
                else:
                    return []
            except IndexError:
                return []
        else:
            return []
    

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
        self.tableDelegate = TransactionTableDelegate(self.model)
        self.view.setItemDelegate(self.tableDelegate)
        self.view.sortByColumn(1, Qt.AscendingOrder) # sorted by date by default
        self.view.deletePressed.connect(self.model.delete)

    # Don't want to see the redundant currency information as text
    # at least not for the demo
    def _getData(self, row, column, role):
        if role in (Qt.DisplayRole, Qt.EditRole) and column.name == 'amount':
            if hasattr(row, 'transaction'):
                amount = row.transaction.amount
                if hasattr(amount, 'value'):
                    return "%.2f" % (amount.value,)

        return TableWithTransactions._getData(self, row, column, role)
