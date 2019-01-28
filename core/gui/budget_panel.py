# Copyright 2019 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html
import datetime
import weakref

from core.util import first
from core.trans import tr

from ..exception import OperationAborted
from ..model.recurrence import RepeatType
from ..model.budget import BudgetPlan
from .base import GUIPanel
from .selectable_list import GUISelectableList
# from .schedule_panel import WithScheduleMixIn, REPEAT_OPTIONS_ORDER # Dual recurrence

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

class BudgetPanel(GUIPanel): #, WithScheduleMixIn): TODO: Solve dual recurrence later
    def __init__(self, mainwindow):
        GUIPanel.__init__(self, mainwindow)
        self.account_list = AccountList(weakref.proxy(self))


        # TODO: Dual recurrence
        # self.schedule = mainwindow.document.budgets # for WithScheduleMixIn
        # self.create_repeat_type_list()

    # --- Override
    def _load(self):
        self._new()

    def _new(self):
        self._load_budget_plan(BudgetPlan(datetime.date.today(), RepeatType.Yearly, RepeatType.Monthly))

        # TODO: Dual Recurrence
        """
        self._refresh_repeat_types()
        self.repeat_type_list.select(REPEAT_OPTIONS_ORDER.index(self.schedule.repeat_type))
        self.view.refresh_repeat_every()
        """

    def _save(self):
        self.document.change_budget_plan(self.budget_plan)
        self.mainwindow.revalidate()

    # --- Private
    def _load_budget_plan(self, budget_plan):
        if budget_plan is None:
            raise OperationAborted
        self._accounts = [a for a in self.document.accounts if a.is_income_statement_account()]
        if not self._accounts:
            msg = tr("Income/Expense accounts must be created before budgets can be set.")
            raise OperationAborted(msg)
        self.budget_plan = budget_plan

    @property
    def start_date(self):
        return self.app.format_date(self.budget_plan.start_date)

    @start_date.setter
    def start_date(self, value):
        try:
            date = self.app.parse_date(value)
            self.budget_plan.start_date = date
        except ValueError:
            pass
