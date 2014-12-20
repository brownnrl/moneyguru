# Created By: Virgil Dupras
# Created On: 2009-11-01
# Copyright 2014 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from PyQt4.QtGui import QFontMetrics

from qtlib.table import Table as TableBase

from ..support.completable_edit import DescriptionEdit, PayeeEdit, AccountEdit
from ..support.column_view import AmountPainter, ChangedPainter, AmountChangedPainter
from ..support.date_edit import DateEdit
from ..support.item_delegate import ItemDelegate

NO_EDIT = 'no_edit'
DATE_EDIT = 'date_edit'
DESCRIPTION_EDIT = 'description_edit'
PAYEE_EDIT = 'payee_edit'
ACCOUNT_EDIT = 'account_edit'

# See #14, #15 Added to indicate an amount to be painted to a table
# with nicely aligned currency / value
AMOUNT_PAINTER = 'amount_painter'
# Extensions in #26
CHANGED_PAINTER = 'changed_painter'
AMOUNT_CHANGED_PAINTER = 'amount_changed_painter'

EDIT_TYPE2COMPLETABLE_EDIT = {
    DESCRIPTION_EDIT: DescriptionEdit,
    PAYEE_EDIT: PayeeEdit,
    ACCOUNT_EDIT: AccountEdit
}

# Painters were introduced in #14, #15 and extended in #26.
PAINTER_TYPE2PAINTER = {
    AMOUNT_PAINTER: AmountPainter,
    CHANGED_PAINTER: ChangedPainter,
    AMOUNT_CHANGED_PAINTER: AmountChangedPainter
}

class TableDelegate(ItemDelegate):
    def __init__(self, model):
        ItemDelegate.__init__(self)
        self._model = model
        self._column_painters = {}

        def set_painter(name, painter_class):
            self._column_painters[name] = painter_class(column.name, self._model)

        for column in self._model.columns.column_list:
            if column.painter in PAINTER_TYPE2PAINTER:
                set_painter(column.name, PAINTER_TYPE2PAINTER[column.painter])

    def _get_value_painter(self, index):
        column = self._model.columns.column_by_index(index.column())

        if column.name in self._column_painters:
            return self._column_painters[column.name]
    
    def createEditor(self, parent, option, index):
        column = self._model.columns.column_by_index(index.column())
        editType = column.editor
        if editType is None:
            return ItemDelegate.createEditor(self, parent, option, index)
        elif editType is NO_EDIT:
            return None
        elif editType == DATE_EDIT:
            return DateEdit(parent)
        elif editType in EDIT_TYPE2COMPLETABLE_EDIT:
            return EDIT_TYPE2COMPLETABLE_EDIT[editType](self._model.completable_edit, parent)


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
        # (#14, #15) When a new font was selected in the preferences panel,
        # the column would redraw but not resize appropriately.  A call
        # to resize(sizeHint()) was added on the update of the size info
        # in the custom drawing for the amount field.
        self.view.resize(self.view.sizeHint())

    def appPrefsChanged(self):
        self._updateFontSize()
