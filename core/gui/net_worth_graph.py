# Created By: Virgil Dupras
# Created On: 2008-08-03
# Copyright 2014 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from hscommon.trans import tr
from ..model.date import DateRange
from .balance_graph import BalanceGraph
from .base import SheetViewNotificationsMixin

class NetWorthGraph(BalanceGraph, SheetViewNotificationsMixin):
    def __init__(self, networth_view):
        BalanceGraph.__init__(self, networth_view)
    
    def _balance_for_date(self, date):
        balances = (a.entries.balance(date=date, currency=self._currency) for a in self._accounts)
        return sum(balances)
    
    def _budget_for_date(self, date):
        date_range = DateRange(date.min, date)
        return self.document.budgeted_amount_for_target(None, date_range)
    
    def compute_data(self):
        accounts = set(a for a in self.document.accounts if a.is_balance_sheet_account())
        self._accounts = accounts - self.document.excluded_accounts
        self._currency = self.document.default_currency
        BalanceGraph.compute_data(self)
    
    #--- Event Handlers
    def accounts_excluded(self):
        self.compute()
        self.view.refresh()
    
    #--- Properties
    @property
    def title(self):
        return tr('Net Worth')
    
    @property
    def currency(self):
        return self.document.default_currency
    
