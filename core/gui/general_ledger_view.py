# Copyright 2018 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

from core.trans import tr
from ..const import PaneType
from .general_ledger_table import GeneralLedgerTable
from .transaction_print import EntryPrint
from .transaction_view import TransactionViewBase

class GeneralLedgerView(TransactionViewBase):
    VIEW_TYPE = PaneType.GeneralLedger
    PRINT_TITLE_FORMAT = tr('General Ledger from {start_date} to {end_date}')
    PRINT_VIEW_CLASS = EntryPrint

    def __init__(self, mainwindow):
        TransactionViewBase.__init__(self, mainwindow)
        self.gltable = self.table = GeneralLedgerTable(parent_view=self)
        self.maintable = self.gltable
        self.columns = self.maintable.columns
        self.bind_messages(self.INVALIDATING_MESSAGES, self._refresh_totals)

    # --- Overrides
    def _revalidate(self):
        self.gltable._revalidate()

    def save_preferences(self):
        self.gltable.columns.save_columns()

    def show(self):
        TransactionViewBase.show(self)
        self.gltable.show()
        self._refresh_totals()

    # --- Private
    def _refresh_totals(self):
        selected, total, total_debit, total_credit = self.gltable.get_totals()
        total_debit_fmt = self.document.format_amount(total_debit)
        total_credit_fmt = self.document.format_amount(total_credit)
        msg = tr("{0} out of {1} selected. Debit: {2} Credit: {3}")
        self.status_line = msg.format(selected, total, total_debit_fmt, total_credit_fmt)

    # --- Event Handlers
    def document_changed(self):
        self.gltable._document_changed()

    def performed_undo_or_redo(self):
        self.gltable._performed_undo_or_redo()

    def filter_applied(self):
        self.gltable._filter_applied()

    def transaction_changed(self):
        self.gltable._item_changed()

    def transaction_deleted(self):
        self.gltable._item_deleted()

    def transactions_selected(self):
        self._refresh_totals()

    def date_range_changed(self):
        self.gltable._date_range_changed()
