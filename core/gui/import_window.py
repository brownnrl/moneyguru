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

from core.document import Document

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
        for pane in panes:
            for transaction in pane.import_document.transactions:
                new = transaction.replicate()
                for split in new.splits:
                    split.amount = -split.amount
                pane.import_document.change_transaction(transaction, new)


class BaseSwapFields(ImportActionPlugin):

    def _switch_function(self, transaction):
        pass

    def perform_action(self, selected_pane, panes, transactions):
        for pane in panes:
            import_document = pane.import_document
            for txn in import_document.transactions.copy():
                new = txn.replicate()
                self._switch_function(new)
                import_document.change_transaction(txn, new)


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


class ImportDocument(Document):

    def __init__(self, app):
        Document.__init__(self, app)
        self.force_date_format = None

    @property
    def ahead_months(self):
        return 0

    def _get_dateformat(self):
        if self.force_date_format is None:
            return Document._get_dateformat()
        else:
            return self.force_date_format

    def _cook(self, from_date=None):
        self.select_all_transactions_range()
        self.oven.cook(from_date=self.date_range.start, until_date=self.date_range.end)


class AccountPane:
    def __init__(self, app, account, target_account, parsing_date_format):
        self.import_document = ImportDocument(app)
        self.import_document.force_date_format = parsing_date_format
        self.account = account
        self._selected_target = target_account
        self.name = account.name
        self.count = len(account.entries)
        self.matches = [] # [[ref, imported]]
        self.parsing_date_format = parsing_date_format
        self.max_day = 31
        self.max_month = 12
        self.max_year = 99 # 2 digits
        self.import_document.import_entries(account,
                                            account,
                                            [[entry, None] for entry in self.account.entries[:]])
        self.match_entries()


    def match_entries(self):
        self.account = self.import_document.accounts.find(self.name)
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
        self.match_entries()


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
                                       InvertAmountsPlugin()]
        self._always_import_action_plugins = []

        self._import_action_listeners = []
        self._add_plugin_listeners(self._import_action_plugins)
        self._recieve_plugins(self.app.plugins)

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

    def _collect_action_params(self, import_action, apply_to_all):
        if apply_to_all:
            panes = self.panes.copy()
        else:
            panes = [self.selected_pane]

        for p in panes.copy():
            entries = p.account.entries
            txns = dedupe(e.transaction for e in entries)
            if not import_action.can_perform_action(p, [p], txns):
                panes.remove(p)

        entries = flatten(p.account.entries for p in panes)
        txns = dedupe(e.transaction for e in entries)
        return panes, entries, txns

    def _perform_action(self, import_action, apply_to_all):
        if self.selected_pane is None:
            return
        panes, entries, txns = self._collect_action_params(import_action, apply_to_all)
        if panes:  # If there are no relevant panes, we shouldn't perform the action
            import_action.perform_action(self.selected_pane, panes, txns)

        for pane in panes:
            pane.match_entries()
        # Entries, I don't remember why, hold a copy of their split's amount. It has to be updated.
        #for entry in entries:
        #    entry.amount = entry.split.amount

        self.import_table.refresh()

    def _always_perform_actions(self):
        for plugin in self._always_import_action_plugins:
            self._perform_action(plugin, True)

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

    def _refresh_swap_list_items(self):
        if not self.panes:
            return

        # I think, possibly due to the "XXX should be replaced with _updated_selected...
        # comment that exists refresh panes, we aren't kicking off the seleced pane change
        # in time.  So we'll just tell it that the selected pane changed even if it hasn't.

        for index, plugin in enumerate(self._import_action_plugins):
            self._import_action_listeners[index].disconnect()
            plugin.on_selected_pane_changed(self.selected_pane)
            self._import_action_listeners[index].connect()
        names = [plugin.ACTION_NAME for plugin in self._import_action_plugins]
        self.swap_type_list[:] = names

    def _update_selected_pane(self):
        if self.selected_pane:
            self.selected_pane.match_entries()
        self.import_table.refresh()
        for plugin in self._import_action_plugins:
            plugin.on_selected_pane_changed(self.selected_pane)
        self._refresh_swap_list_items()
        self.view.update_selected_pane()
        self.view.set_swap_button_enabled(self.can_perform_swap())

    def _recieve_plugins(self, plugins):
        extended_plugins = [plugin() for plugin in plugins
                            if issubclass(plugin, ImportActionPlugin)]

        select_actions = [p for p in extended_plugins if not p.always_perform_action()]
        always_actions = [p for p in extended_plugins if p.always_perform_action()]

        self._import_action_plugins.extend(select_actions)
        self._add_plugin_listeners(select_actions)
        self._always_import_action_plugins.extend(always_actions)

    def _add_plugin_listeners(self, plugins):
        listeners = [Listener(plugin) for plugin in plugins
                     if not plugin.always_perform_action()]
        for listener in listeners:
            listener.bind_messages((ImportActionPlugin.action_name_changed,),
                                   lambda: self._refresh_swap_list_items())
            listener.connect()
            self._import_action_listeners.append(listener)

    #--- Override
    def _view_updated(self):
        self.connect()
        if self.document.can_restore_from_prefs():
            # See MainWindow._view_updated() comment.
            self.document_restoring_preferences()

    #--- Public

    def can_perform_swap(self):
        index = self.swap_type_list.selected_index
        import_action = self._import_action_plugins[index]
        panes, _, txns = self._collect_action_params(import_action, True)
        # We actually perform can_perform_action as part of the _collect_action_params
        # so we don't need to run the explicit check twice, just check to see if
        # the seleced pane was one of the "passing" panes.
        # Also, we consider having no panes unable to perform all actions (mimicing
        # prior implementation)
        if panes == []:
            return False

        return self.selected_pane in panes

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
            self.panes.append(AccountPane(self.app, account, target_account, parsing_date_format))
        # XXX Should replace by _update_selected_pane()?

        self._always_perform_actions()
        self._refresh_target_selection()
        self._refresh_swap_list_items()
        if self.selected_pane:
            self.selected_pane.match_entries()
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

