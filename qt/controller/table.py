# Created By: Virgil Dupras
# Created On: 2009-11-01
# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtGui import QFontMetrics

from qtlib.table import Table as TableBase

from ..support.completable_edit import DescriptionEdit, PayeeEdit, AccountEdit
from ..support.column_view import AmountColumnDelegate
from ..support.date_edit import DateEdit
from ..support.item_delegate import ItemDelegate

DATE_EDIT = 'date_edit'
DESCRIPTION_EDIT = 'description_edit'
PAYEE_EDIT = 'payee_edit'
ACCOUNT_EDIT = 'account_edit'

AMOUNT_PAINTER = 'amount_painter'

EDIT_TYPE2COMPLETABLE_EDIT = {
    DESCRIPTION_EDIT: DescriptionEdit,
    PAYEE_EDIT: PayeeEdit,
    ACCOUNT_EDIT: AccountEdit
}

class TableDelegate(ItemDelegate):
    def __init__(self, model):
        ItemDelegate.__init__(self)
        self._model = model
        self._column_painters = {}
        for column in self._model.columns.column_list:
            if column.painter == AMOUNT_PAINTER:
                self._column_painters[column.name] = AmountColumnDelegate(column.name, self._model)
    
    def createEditor(self, parent, option, index):
        column = self._model.columns.column_by_index(index.column())
        editType = column.editor
        if editType is None:
            return ItemDelegate.createEditor(self, parent, option, index)
        elif editType == DATE_EDIT:
            return DateEdit(parent)
        elif editType in EDIT_TYPE2COMPLETABLE_EDIT:
            return EDIT_TYPE2COMPLETABLE_EDIT[editType](self._model.completable_edit, parent)

    def sizeHint(self, option, index):
        column = self._model.columns.column_by_index(index.column())

        if column.name not in self._column_painters:
            return ItemDelegate.sizeHint(self, option, index)

        size_hint = self._column_painters[column.name].sizeHint(option, index)

        if size_hint is None:
            return ItemDelegate.sizeHint(self, option, index)

        return size_hint

    def paint(self, painter, option, index):
        # Paint cells as we normally would
        ItemDelegate.paint(self, painter, option, index)

        column = self._model.columns.column_by_index(index.column())

        if column.name not in self._column_painters:
            return

        column_painter = self._column_painters[column.name]

        column_data = column_painter._get_data_from_index(index)

        if column_data is None:
            return

        column_painter._paint_column_data(painter, option, column_data)


class Table(TableBase):
    def __init__(self, model, view):
        TableBase.__init__(self, model, view)
        self.tableDelegate = TableDelegate(self.model)
        self.view.setItemDelegate(self.tableDelegate)
        self._updateFontSize()
        from ..app import APP_INSTANCE
        APP_INSTANCE.prefsChanged.connect(self.appPrefsChanged)

    def _updateFontSize(self):
        from ..app import APP_INSTANCE
        font = self.view.font()
        font.setPointSize(APP_INSTANCE.prefs.tableFontSize)
        self.view.setFont(font)
        fm = QFontMetrics(font)
        self.view.verticalHeader().setDefaultSectionSize(fm.height()+2)

    def appPrefsChanged(self):
        self._updateFontSize()
    
