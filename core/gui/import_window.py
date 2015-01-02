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

from core.plugin import ImportActionPlugin, ImportBindPlugin
from core.document import ImportDocument
from core.model.account import Account
from core.model.entry import Entry
from collections import namedtuple
from copy import copy

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
        if selected_pane is None:
            return

        import_document = selected_pane.import_document
        for txn in transactions:
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

class ReferenceBind(ImportBindPlugin):

    def match_entries(self,
                      target_account,
                      document,
                      import_document,
                      existing_entries,
                      imported_entries):
        matches = []
        import_reference2entry = {}
        for import_entry in (e for e in imported_entries if e.reference):
            import_reference2entry[import_entry.reference] = import_entry

        for existing_entry in existing_entries:
            if existing_entry.reference in import_reference2entry:
                import_entry = import_reference2entry[existing_entry.reference]
                if existing_entry.reconciled:
                    import_entry.will_import = False

                del import_reference2entry[existing_entry.reference]
            else:
                import_entry = None

            if import_entry is not None and not existing_entry.reconciled:
                matches.append((existing_entry, import_entry, 0.99))

        return matches


class EquivalenceBind(ImportBindPlugin):

    @staticmethod
    def _splits_equal(existing_splits, import_splits):
        splits_equal = len(import_splits) == len(existing_splits)

        if splits_equal:
            for index, import_split in enumerate(import_splits):
                existing_split = existing_splits[index]

                if (existing_split.account is None) != (import_split.account is None):
                    return False

                if import_split.amount.value != existing_split.amount.value or \
                   import_split.account.name.lower() != existing_split.account.name.lower():
                    return False

        return True

    def match_entries(self, target_account, document, import_document, existing_entries, imported_entries):

        matches = []
        for import_entry in imported_entries:

            confidence = 0.9

            for existing_entry in existing_entries:

                # We can not bind automatically if there is an impact on the
                # date, target account, or amount

                if existing_entry.amount != import_entry.amount:
                    continue
                if existing_entry.date != import_entry.date:
                    continue
                if existing_entry.account.name.lower() != target_account.name.lower():
                    continue

                splits_equal = len(existing_entry.transaction.splits) == len(import_entry.transaction.splits) and\
                    existing_entry.transaction.amount.value == import_entry.transaction.amount.value

                if not splits_equal:
                    continue

                # Is there another existing entry on the same attributes as above?
                if len([e for e in existing_entries if
                        e.date == existing_entry.date and
                        e.amount.value == existing_entry.amount.value and
                        e.account.name.lower() == existing_entry.account.name.lower()]) > 1:
                    confidence -= 0.2

                if existing_entry.description != import_entry.description:
                    confidence -= 0.1
                if existing_entry.payee != import_entry.payee:
                    confidence -= 0.1
                if existing_entry.checkno != import_entry.checkno:
                    confidence -= 0.1

                if confidence == 0.9:
                    # Nothing has changed about this entry, there isn't another duplicate
                    # already, so we are pretty confident that it's the same transaction.
                    import_entry.will_import = False
                matches.append((existing_entry, import_entry, confidence))
                break
        return matches

EntryProbability = namedtuple('EntryProbability', 'existing imported probability')

class AccountPane:
    def __init__(self, bind_plugins, import_document, account, target_account, parsing_date_format):
        self.import_document = import_document
        self.bind_plugins = bind_plugins
        self.account = account
        self._selected_target = target_account
        self.name = account.name
        self.count = len(account.entries)
        self.matches = [] # [[ref, imported]]
        self.parsing_date_format = parsing_date_format
        self.max_day = 31
        self.max_month = 12
        self.max_year = 99 # 2 digits
        self._match_entries = dict()
        self._user_binds = dict()  # tracks binds / unbinds as indicated by the user.
        self._match_probabilties = dict()
        self.match_entries()

    def _remove_match(self, match):
        if match.existing in self._match_entries:
            del self._match_entries[match.existing]
        if match.imported in self._match_entries:
            del self._match_entries[match.imported]

    def _determine_best_matches(self, matches):

        def check_better(entry, probability):
            conflict = self._match_entries.get(entry, None)
            if conflict and conflict.probability < probability:
                self._remove_match(conflict)

        # Take existing entry that is recommended to be mapped to an import entry
        for existing_entry, imported_entry, probability in matches:
            check_better(existing_entry, probability)
            check_better(imported_entry, probability)

            if (existing_entry not in self._match_entries and
                imported_entry not in self._match_entries):
                new_match = EntryProbability(existing_entry, imported_entry, probability)
                self._match_entries[existing_entry] = new_match
                self._match_entries[imported_entry] = new_match


    def _convert_matches(self, import_entries, existing_entries):

        processed = set()

        def append_entry(entry, is_import):

            if entry in processed:
                return

            match_entry = self._match_entries.get(entry, None)

            if (match_entry and
                  match_entry.existing not in processed and
                  match_entry.imported not in processed):
                self.matches.append([match_entry.existing, match_entry.imported])
                processed.add(match_entry.existing)
                processed.add(match_entry.imported)

                if match_entry.existing.reconciled:
                    match_entry.imported.will_import = False
            elif is_import:
                self.matches.append([None, entry])
            elif not entry.reconciled:
                self.matches.append([entry, None])

            processed.add(entry)

        for (existing_entry, import_split), bound in self._user_binds.items():
            if bound:
                [import_entry] = [e for e in import_entries if e.split is import_split]
                self.matches.append([existing_entry, import_entry])
                processed.add(existing_entry)
                processed.add(import_entry)

        for existing_entry in existing_entries:
            append_entry(existing_entry, False)

        for import_entry in import_entries:
            append_entry(import_entry, True)

        for (existing_entry, import_split), bound in self._user_binds.items():
            if not bound:
                match = [[e, i] for [e, i] in self.matches if
                         e and i and
                         (e, i.split) == (existing_entry, import_split)]
                if match:
                    [[e, i]] = match
                    self.matches.remove([e, i])
                else:
                    continue
                if not e.reconciled:
                    self.matches.append([e, None])
                self.matches.append([None, i])


    def match_entries(self):
        self.account = self.import_document.accounts.find(self.name)
        import_entries = self.account.entries[:]
        if self.selected_target is not None:
            existing_entries = self.selected_target.entries[:]
        else:
            existing_entries = []

        self._match_entries.clear()
        self.matches = []

        for plugin in self.bind_plugins:
            matches = plugin.match_entries(self.selected_target,
                                           None,
                                           self.import_document,
                                           existing_entries,
                                           import_entries)

            self._determine_best_matches(matches)

        self._convert_matches(import_entries, existing_entries)
        self._sort_matches()

    def _sort_matches(self):
        self.matches.sort(key=lambda t: (t[0].date if t[0] is not None else t[1].date, t[0] is None))

    def bind(self, existing, imported):
        self._user_binds[(existing, imported.split)] = True  # Bind
        self.match_entries()

    def unbind(self, existing, imported):
        self._user_binds[(existing, imported.split)] = False  # Unbind
        self.match_entries()

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

        self._bind_plugins = [EquivalenceBind(),
                              ReferenceBind()] # TODO: Extend

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
            txns = dedupe(e.transaction for e in p.account.entries[:])
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

        self.selected_pane.import_document.cook()

        for pane in panes:
            pane.match_entries()

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

        name2account = pane.import_document.exported_accounts
        cached_txn = pane.import_document.cached_transactions

        def copy_account(acct):
            if acct is None:
                return None
            if acct.name not in name2account:
                copied_account = Account(acct.name, acct.currency, acct.type)
                copied_account.reference = acct.reference
                name2account[acct.name] = copied_account
                return copied_account
            else:
                return name2account[acct.name]

        def copy_transaction(txn):
            if txn not in cached_txn:
                new_txn = txn.replicate()
                cached_txn[txn] = new_txn
                return new_txn
            else:
                return pane.import_document.cached_transactions[txn]


        try:
            pane_account = copy_account(pane.account)

            new_matches = []

            for (e, ref) in matches:
                for indx, s in enumerate(e.transaction.splits):
                    if e.split is s:
                        split_indx = indx
                        break
                transaction = copy_transaction(e.transaction)
                for split in transaction.splits:
                    split.account = copy_account(split.account)

                split = transaction.splits[split_indx]
                new_entry = Entry(split, e.amount, e.balance, e.reconciled_balance, e.balance_with_budget)
                new_matches.append((new_entry, ref))


            if pane.selected_target is not None:
                # We import in an existing account, adjust all the transactions accordingly
                target_account = pane.selected_target
            else:
                target_account = pane_account # pane.account == new account

            self.document.import_entries(target_account, pane_account, new_matches)

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
        for pane in self.panes:
            pane.import_document.cook()

        if not hasattr(self.mainwindow, 'loader'):
            return

        # there are ramifications here to think about in terms of expected behavior.
        # old behavior is to store accounts without importing segregated by their respective
        # loader account lists...
        # self.import_document.clear()

        import_document = ImportDocument(self.app)

        self.refresh_targets()
        accounts = [a for a in self.mainwindow.loader.accounts if a.is_balance_sheet_account() and a.entries]

        parsing_date_format = DateFormat.from_sysformat(self.mainwindow.loader.parsing_date_format)
        import_document.accounts = self.mainwindow.loader.accounts
        import_document.transactions = self.mainwindow.loader.transactions
        import_document.schedules = self.mainwindow.loader.schedules
        import_document.budgets = self.mainwindow.loader.budgets
        import_document.oven = self.mainwindow.loader.oven
        import_document.cook()
        for account in accounts:
            target_account = None
            if self.mainwindow.loader.target_account is not None:
                target_account = self.mainwindow.loader.target_account
            elif account.reference:
                target_account = getfirst(
                    t for t in self.target_accounts if t.reference == account.reference
                )
            self.panes.append(AccountPane(self._bind_plugins,
                                          import_document,
                                          account,
                                          target_account,
                                          parsing_date_format))
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

