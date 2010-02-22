# Created By: Virgil Dupras
# Created On: 2008-07-05
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "HS" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/hs_license

from nose.tools import eq_
from hsutil.currency import CAD, EUR

from ..base import TestCase, TestSaveLoadMixin, TestQIFExportImportMixin, TestApp

class OneEntry(TestCase):
    def setUp(self):
        self.create_instances()
        self.add_account_legacy('first', currency=CAD)
        self.add_entry(transfer='second', increase='42')
    
    def test_add_gui_calls(self):
        # refresh() and start_editing() are called after a add()
        self.tpanel.load()
        self.clear_gui_calls()
        self.stable.add()
        self.check_gui_calls(self.stable_gui, ['refresh', 'start_editing', 'stop_editing'])
    
    def test_cancel_edits(self):
        # cancel_edits() sets edited to None and makes the right gui calls
        self.tpanel.load()
        self.stable[0].account = 'foo'
        self.clear_gui_calls()
        self.stable.cancel_edits()
        assert self.stable.edited is None
        self.check_gui_calls(self.stable_gui, ['refresh', 'stop_editing'])
    
    def test_changes_split_buffer_only(self):
        """Changes made to the split table don't directly get to the model until tpanel.save()"""
        self.tpanel.load()
        row = self.stable.selected_row
        row.debit = '40'
        self.stable.save_edits()
        # Now, let's force a refresh of etable
        self.mainwindow.select_balance_sheet()
        self.bsheet.selected = self.bsheet.assets[0]
        self.bsheet.show_selected_account()
        self.assertEqual(self.etable[0].increase, 'CAD 42.00')
    
    def test_completion(self):
        """Just make sure it works. That is enough to know SplitTable is of the right subclass"""
        self.assertEqual(self.stable.complete('s', 'account'), 'second')
    
    def test_completion_new_txn(self):
        # When completing an account from a new txn, the completion wouldn't work at all
        self.mainwindow.select_transaction_table()
        self.ttable.add()
        self.tpanel.load()
        self.assertEqual(self.stable.complete('f', 'account'), 'first')
    
    def test_load_tpanel_from_ttable(self):
        """When the tpanel is loaded form the ttable, the system currency is used"""
        self.mainwindow.select_transaction_table()
        self.tpanel.load() # no crash
        self.assertEqual(self.stable[0].debit, 'CAD 42.00')
    
    def test_memo(self):
        """It's possible to set a different memo for each split"""
        self.tpanel.load()
        row = self.stable.selected_row
        row.memo = 'memo1'
        self.stable.save_edits()
        self.stable.select([1])
        row = self.stable.selected_row
        row.memo = 'memo2'
        self.stable.save_edits()
        self.tpanel.save()
        self.tpanel.load()
        self.assertEqual(self.stable[0].memo, 'memo1')
        self.assertEqual(self.stable[1].memo, 'memo2')
    
    def test_set_wrong_values_for_attributes(self):
        """set_attribute_avlue catches ValueError"""
        self.tpanel.load()
        row = self.stable.selected_row
        row.debit = 'invalid'
        row.credit = 'invalid'
        # no crash occured
    

class OneTransactionBeingAdded(TestCase):
    def setUp(self):
        self.create_instances()
        self.mainwindow.select_transaction_table()
        self.ttable.add()
    
    def test_change_splits(self):
        """It's possible to change the splits of a newly created transaction"""
        # Previously, it would crash because of the 0 amounts.
        # At this moment, we have a transaction with 2 empty splits
        self.tpanel.load()
        self.stable[0].account = 'first'
        self.stable[0].credit = '42'
        self.stable.save_edits()
        self.stable.select([1])
        self.stable[1].account = 'second'
        self.stable.save_edits()
        self.tpanel.save()
        row = self.ttable[0]
        self.assertEqual(row.from_, 'first')
        self.assertEqual(row.to, 'second')
        self.assertEqual(row.amount, '42.00')
    
    def test_delete_split_with_none_selected(self):
        # don't crash when stable.delete() is called enough times to leave the table empty
        self.tpanel.load()
        self.stable.delete() # Unassigned 1
        self.stable.delete() # Unassigned 2
        try:
            self.stable.delete()
        except AttributeError:
            self.fail("When the table is empty, don't try to delete")
    

#--- Transaction with splits
def app_transaction_with_splits():
    app = TestApp()
    app.add_txn(from_='foo', to='bar', amount='42')
    app.mainwindow.edit_item()
    app.stable.add()
    app.stable[2].account = 'baz'
    app.stable[2].credit = '3'
    app.stable.save_edits()
    return app

def test_move_split():
    # It's possible to move splits around
    app = app_transaction_with_splits()
    # order of first 2 splits is not defined
    first_account = app.stable[0].account
    second_account = app.stable[1].account
    app.stable.move_split(1, 0)
    eq_(app.stable[0].account, second_account)
    eq_(app.stable.selected_indexes, [0])
    app.stable.move_split(1, 2)
    eq_(app.stable[2].account, first_account)
    eq_(app.stable.selected_indexes, [2])

def test_row_is_main():
    # Row.is_main return True if the split is one of the main splits.
    app = app_transaction_with_splits()
    assert app.stable[0].is_main
    assert app.stable[1].is_main
    assert not app.stable[2].is_main

#--- EUR account and EUR transfer
def app_eur_account_and_eur_transfer():
    app = TestApp()
    app.add_account('first', EUR)
    app.add_account('second', EUR)
    app.doc.show_selected_account()
    app.add_entry(transfer='first', increase='42') # EUR
    app.tpanel.load()
    return app

def test_amounts_display():
    # The amounts' currency are explicitly displayed.
    app = app_eur_account_and_eur_transfer()
    eq_(app.stable[0].debit, 'EUR 42.00')
    eq_(app.stable[1].credit, 'EUR 42.00')

def test_change_amount_implicit_currency():
    # When typing a currency-less amount, the transaction amount's currency is used.
    app = app_eur_account_and_eur_transfer()
    app.stable[0].debit = '64'
    eq_(app.stable[0].debit, 'EUR 64.00')

class OneTransactionWithMemos(TestCase, TestSaveLoadMixin, TestQIFExportImportMixin):
    # TestSaveLoadMixin: Make sure memos are loaded/saved
    # same for TestQIFExportImportMixin
    def setUp(self):
        self.create_instances()
        self.add_account_legacy('first')
        self.add_account_legacy('second')
        self.mainwindow.select_transaction_table()
        self.ttable.add()
        self.tpanel.load()
        self.stable[0].account = 'first'
        self.stable[0].memo = 'memo1'
        self.stable[0].credit = '42'
        self.stable.save_edits()
        self.stable.select([1])
        self.stable[1].account = 'second'
        self.stable[1].memo = 'memo2'
        self.stable.save_edits()
        self.tpanel.save()
    
