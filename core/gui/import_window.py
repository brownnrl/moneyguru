# Created By: Virgil Dupras
# Created On: 2008-08-07
# Copyright 2014 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

# To avoid clashing with "first" in the "first/second" pattern being all over the place in this
# unit, we rename our imported first() function here
from hscommon.util import flatten, dedupe, first as getfirst
from hscommon.trans import tr
from hscommon.notify import Listener

import logging

from ..exception import OperationAborted
from ..model.date import DateFormat
from .base import MainWindowGUIObject, LinkedSelectableList
from .import_table import ImportTable

from core.plugin import ImportActionPlugin

DAY = 'day'
MONTH = 'month'
YEAR = 'year'

class SwapType:
    DayMonth = 0
    MonthYear = 1
    DayYear = 2
    DescriptionPayee = 3
    InvertAmount = 4

def last_two_digits(year):
    return year - ((year // 100) * 100)

def swapped_date(date, first, second):
    attrs = {DAY: date.day, MONTH: date.month, YEAR: last_two_digits(date.year)}
    newattrs = {first: attrs[second], second: attrs[first]}
    if YEAR in newattrs:
        newattrs[YEAR] += 2000
    return date.replace(**newattrs)

def swap_format_elements(format, first, second):
    # format is a DateFormat
    swapped = format.copy()
    elems = swapped.elements
    TYPE2CHAR = {DAY: 'd', MONTH: 'M', YEAR: 'y'}
    first_char = TYPE2CHAR[first]
    second_char = TYPE2CHAR[second]
    first_index = [i for i, x in enumerate(elems) if x.startswith(first_char)][0]
    second_index = [i for i, x in enumerate(elems) if x.startswith(second_char)][0]
    elems[first_index], elems[second_index] = elems[second_index], elems[first_index]
    return swapped

class InvertAmountsPlugin(ImportActionPlugin):

    NAME = "Invert Amounts Import Action Plugin"
    ACTION_NAME = "Invert Amount"

    def perform_action(self, selected_pane, panes, transactions):
        for txn in transactions:
            for split in txn.splits:
                split.amount = -split.amount


class BaseSwapFields(ImportActionPlugin):

    def _switch_function(self, transaction):
        pass

    def perform_action(self, selected_pane, panes, transactions):
        for txn in transactions:
            self._switch_function(txn)


class SwapDescriptionPayeeAction(BaseSwapFields):

    ACTION_NAME = tr("Description <--> Payee")
    NAME = "Swap Description Payee Import Action Plugin"

    def _switch_function(self, txn):
        txn.description, txn.payee = txn.payee, txn.description


class BaseSwapDateFields(BaseSwapFields):

    def __init__(self):
        super().__init__()
        self._first_field = None
        self._second_field = None

    def _switch_function(self, transaction):
        transaction.date = swapped_date(transaction.date, self._first_field, self._second_field)

    def on_selected_pane_changed(self, selected_pane):
        self._change_name(selected_pane)

    def _change_name(self, selected_pane):
        if selected_pane is None:
            return

        basefmt = selected_pane.parsing_date_format
        swapped = swap_format_elements(basefmt, self._first_field, self._second_field)
        self.ACTION_NAME = "{} --> {}".format(basefmt.iso_format, swapped.iso_format)
        self.notify(self.action_name_changed)

    def can_perform_action(self, selected_pane, panes, transactions):
        try:
            for txn in transactions:
                swapped_date(txn.date, self._first_field, self._second_field)
            return True
        except ValueError:
            return False

    def perform_action(self, selected_pane, panes, transactions):
        super().perform_action(selected_pane, panes, transactions)
        # Now, lets' change the date format on these panes
        for pane in panes:
            basefmt = selected_pane.parsing_date_format
            swapped = swap_format_elements(basefmt, self._first_field, self._second_field)
            pane.parsing_date_format = swapped
        # We'll update our name to reflect the new date format
        self._change_name(selected_pane)


class SwapDayMonth(BaseSwapDateFields):

    ACTION_NAME = "<placeholder> Day <--> Month"

    NAME = "Swap Day and Month Import Action Plugin"

    def __init__(self):
        super().__init__()
        self._first_field = DAY
        self._second_field = MONTH


class SwapDayYear(BaseSwapDateFields):

    ACTION_NAME = "<placeholder> Day <--> Year"

    NAME = "Swap Day and Year Import Action Plugin"

    def __init__(self):
        super().__init__()
        self._first_field = DAY
        self._second_field = YEAR


class SwapMonthYear(BaseSwapDateFields):

    ACTION_NAME = "<placeholder> Month <--> Year"

    NAME = "Swap Month and Year Import Action Plugin"

    def __init__(self):
        super().__init__()
        self._first_field = MONTH
        self._second_field = YEAR


class AccountPane:
    def __init__(self, account, target_account, parsing_date_format):
        self.account = account
        self._selected_target = target_account
        self.name = account.name
        self.count = len(account.entries)
        self.matches = [] # [[ref, imported]]
        self.parsing_date_format = parsing_date_format
        self.max_day = 31
        self.max_month = 12
        self.max_year = 99 # 2 digits
        self._match_entries()

    def _match_entries(self):
        to_import = self.account.entries[:]
        reference2entry = {}
        for entry in (e for e in to_import if e.reference):
            reference2entry[entry.reference] = entry
        self.matches = []
        if self.selected_target is not None:
            entries = self.selected_target.entries
            for entry in entries:
                if entry.reference in reference2entry:
                    other = reference2entry[entry.reference]
                    if entry.reconciled:
                        other.will_import = False
                    to_import.remove(other)
                    del reference2entry[entry.reference]
                else:
                    other = None
                if other is not None or not entry.reconciled:
                    self.matches.append([entry, other])
        self.matches += [[None, entry] for entry in to_import]
        self._sort_matches()

    def _sort_matches(self):
        self.matches.sort(key=lambda t: t[0].date if t[0] is not None else t[1].date)

    def bind(self, existing, imported):
        [match1] = [m for m in self.matches if m[0] is existing]
        [match2] = [m for m in self.matches if m[1] is imported]
        match1[1] = match2[1]
        self.matches.remove(match2)

    def unbind(self, existing, imported):
        [match] = [m for m in self.matches if m[0] is existing and m[1] is imported]
        match[1] = None
        self.matches.append([None, imported])
        self._sort_matches()

    @property
    def selected_target(self):
        return self._selected_target

    @selected_target.setter
    def selected_target(self, value):
        self._selected_target = value
        self._match_entries()


class ImportWindow(MainWindowGUIObject):
    #--- View interface
    # close()
    # close_selected_tab()
    # refresh_tabs()
    # refresh_target_accounts()
    # set_swap_button_enabled(enabled: bool)
    # show()
    # update_selected_pane()
    #

    def __init__(self, mainwindow):
        MainWindowGUIObject.__init__(self, mainwindow)
        self._selected_pane_index = 0
        self._selected_target_index = 0
        self._import_action_plugins = [SwapDayMonth(),
                                       SwapMonthYear(),
                                       SwapDayYear(),
                                       SwapDescriptionPayeeAction(),
                                       InvertAmountsPlugin()]  # TODO : + plugins from plugin dir
        self._import_action_listeners = [Listener(plugin) for plugin in self._import_action_plugins]
        for index, listener in enumerate(self._import_action_listeners):
            listener.bind_messages((ImportActionPlugin.action_name_changed,),
                                   lambda idx=index: self._refresh_swap_list_items(idx))
            listener.connect()

        logging.debug(self._import_action_plugins)

        def setfunc(index):
            self.view.set_swap_button_enabled(self.can_perform_swap())
        self.swap_type_list = LinkedSelectableList(items=[
            plugin.ACTION_NAME for plugin in self._import_action_plugins
        ], setfunc=setfunc)
        self.swap_type_list.selected_index = SwapType.DayMonth
        self.panes = []
        self.import_table = ImportTable(self)

    #--- Private

    def _collect_action_params(self, apply_to_all):
        if apply_to_all:
            panes = self.panes
        else:
            panes = [self.selected_pane]
        entries = flatten(p.account.entries for p in panes)
        txns = dedupe(e.transaction for e in entries)
        return panes, entries, txns

    def _perform_action(self, import_action, apply_to_all):
        panes, entries, txns = self._collect_action_params(apply_to_all)
        import_action.perform_action(self.selected_pane, panes, txns)
        # Entries, I don't remember why, hold a copy of their split's amount. It has to be updated.
        for entry in entries:
            entry.amount = entry.split.amount
        self.import_table.refresh()

    def _refresh_target_selection(self):
        if not self.panes:
            return
        target = self.selected_pane.selected_target
        self._selected_target_index = 0
        if target is not None:
            try:
                self._selected_target_index = self.target_accounts.index(target) + 1
            except ValueError:
                pass

    def _refresh_swap_list_items(self, index=-1):
        if not self.panes:
            return

        if index != -1:
            import_action = self._import_action_plugins[index]
            self.swap_type_list[index] = import_action.ACTION_NAME
        else:
            names = [plugin.ACTION_NAME for plugin in self._import_action_plugins]
            self.swap_type_list[:] = names

    def _update_selected_pane(self):
        self.import_table.refresh()
        for plugin in self._import_action_plugins:
            plugin.on_selected_pane_changed(self.selected_pane)
        self._refresh_swap_list_items()
        self.view.update_selected_pane()
        self.view.set_swap_button_enabled(self.can_perform_swap())

    #--- Override
    def _view_updated(self):
        self.connect()
        if self.document.can_restore_from_prefs():
            # See MainWindow._view_updated() comment.
            self.document_restoring_preferences()

    #--- Public
    def can_perform_swap(self):
        index = self.swap_type_list.selected_index
        panes, _, txns = self._collect_action_params(True)
        import_action = self._import_action_plugins[index]
        return import_action.can_perform_action(self.selected_pane, panes, txns)

    def close_pane(self, index):
        was_selected = index == self.selected_pane_index
        del self.panes[index]
        if not self.panes:
            self.view.close()
            return
        self._selected_pane_index = min(self._selected_pane_index, len(self.panes) - 1)
        if was_selected:
            self._update_selected_pane()


    def import_selected_pane(self):
        pane = self.selected_pane
        matches = pane.matches
        matches = [(e, ref) for ref, e in matches if e is not None and getattr(e, 'will_import', True)]
        if pane.selected_target is not None:
            # We import in an existing account, adjust all the transactions accordingly
            target_account = pane.selected_target
        else:
            target_account = pane.account # pane.account == new account
        try:
            self.document.import_entries(target_account, pane.account, matches)
        except OperationAborted:
            pass
        else:
            self.close_pane(self.selected_pane_index)
            self.view.close_selected_tab()

    def perform_swap(self, apply_to_all=False):
        index = self.swap_type_list.selected_index
        import_action = self._import_action_plugins[index]
        self._perform_action(import_action, apply_to_all)

    def refresh_targets(self):
        self.target_accounts = [a for a in self.document.accounts if a.is_balance_sheet_account()]
        self.target_accounts.sort(key=lambda a: a.name.lower())

    def refresh_panes(self):
        if not hasattr(self.mainwindow, 'loader'):
            return
        self.refresh_targets()
        accounts = [a for a in self.mainwindow.loader.accounts if a.is_balance_sheet_account() and a.entries]
        parsing_date_format = DateFormat.from_sysformat(self.mainwindow.loader.parsing_date_format)
        for account in accounts:
            target_account = None
            if self.mainwindow.loader.target_account is not None:
                target_account = self.mainwindow.loader.target_account
            elif account.reference:
                target_account = getfirst(
                    t for t in self.target_accounts if t.reference == account.reference
                )
            self.panes.append(AccountPane(account, target_account, parsing_date_format))
        # XXX Should replace by _update_selected_pane()?
        self._refresh_target_selection()
        self._refresh_swap_list_items()
        self.import_table.refresh()

    def show(self):
        self.refresh_panes()
        self.view.refresh_target_accounts()
        self.view.refresh_tabs()
        self.view.show()

    #--- Properties
    @property
    def selected_pane(self):
        return self.panes[self.selected_pane_index] if self.panes else None

    @property
    def selected_pane_index(self):
        return self._selected_pane_index

    @selected_pane_index.setter
    def selected_pane_index(self, value):
        if value >= len(self.panes):
            return
        self._selected_pane_index = value
        self._refresh_target_selection()
        self._update_selected_pane()

    @property
    def selected_target_account(self):
        return self.selected_pane.selected_target

    @property
    def selected_target_account_index(self):
        return self._selected_target_index

    @selected_target_account_index.setter
    def selected_target_account_index(self, value):
        target = self.target_accounts[value - 1] if value > 0 else None
        self.selected_pane.selected_target = target
        self._selected_target_index = value
        self.import_table.refresh()

    @property
    def target_account_names(self):
        return [tr('< New Account >')] + [a.name for a in self.target_accounts]

    #--- Events
    def account_added(self):
        self.refresh_targets()
        self._refresh_target_selection()
        self.view.refresh_target_accounts()

    account_changed = account_added
    account_deleted = account_added

    def document_will_close(self):
        self.import_table.columns.save_columns()

    def document_restoring_preferences(self):
        self.import_table.columns.restore_columns()

