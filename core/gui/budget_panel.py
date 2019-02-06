# Copyright 2019 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html
from datetime import datetime
import weakref

from core.util import first
from core.trans import tr

from ..exception import OperationAborted
from ..model.budget import Budget
from ..model.sort import ACCOUNT_SORT_KEY
from .base import GUIPanel
from .selectable_list import GUISelectableList

class AccountList(GUISelectableList):
    def __init__(self, panel):
        self.panel = panel
        GUISelectableList.__init__(self)

    def _update_selection(self):
        GUISelectableList._update_selection(self)
        account = self.panel._accounts[self.selected_index]
        self.panel.budget.account = account

    def refresh(self):
        self[:] = [a.name for a in self.panel._accounts]

class BudgetPanel(GUIPanel):
    def __init__(self, mainwindow):
        GUIPanel.__init__(self, mainwindow)
        self.account_list = AccountList(weakref.proxy(self))

    # --- Override
    def _load(self):
        budget = first(self.mainwindow.selected_budgets)
        self._load_budget(budget)

    def _new(self):
        self._load_budget(Budget(None, 0, datetime.today()))

    def _save(self):
        self.document.change_budget(self.original, self.budget)
        self.mainwindow.revalidate()

    # --- Private
    def _load_budget(self, budget):
        if budget is None:
            raise OperationAborted
        self.original = budget
        self.budget = budget.replicate()
        self._accounts = [a for a in self.document.accounts if a.is_income_statement_account()]
        if not self._accounts:
            msg = tr("Income/Expense accounts must be created before budgets can be set.")
            raise OperationAborted(msg)
        self._accounts.sort(key=ACCOUNT_SORT_KEY)
        self.account_list.refresh()
        self.account_list.select(self._accounts.index(budget.account) if budget.account is not None else 0)

    # --- Properties
    @property
    def amount(self):
        return self.document.format_amount(self.budget.amount)

    @amount.setter
    def amount(self, value):
        try:
            self.budget.amount = self.document.parse_amount(value)
        except ValueError:
            pass

    @property
    def notes(self):
        return self.budget.notes

    @notes.setter
    def notes(self, value):
        self.budget.notes = value

