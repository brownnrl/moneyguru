# Copyright 2019 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

from .testutil import eq_

from ..const import AccountType
from .base import TestApp, with_app

#-- for unit tests
from datetime import date
from ..model._ccore import AccountList
from .base import Amount
from core.model.budget import Budget, BudgetList

# -- Account with budget
def app_account_with_budget(monkeypatch):
    # 4 days left to the month, 100$ monthly budget
    monkeypatch.patch_today(2008, 1, 27)
    app = TestApp()
    app.add_account('Some Income', account_type=AccountType.Income)
    app.add_budget('Some Income', '100')
    return app

@with_app(app_account_with_budget)
def test_budget_amount_flow_direction(app):
    # When the budgeted account is an income, the account gets in the *from* column
    app.show_tview()
    eq_(app.ttable[0].from_, 'Some Income')

@with_app(app_account_with_budget)
def test_dont_replace_split_instances_needlessly(app):
    # The bug was that during budget cooking, all spawns, including those before the cooked date
    # range, would have their split re-created with new amounts. Because of this, going back in
    # the date range would cause cached entries to be "bumped out" of the transaction. This
    # would result in the shown account to be displayed in the "Transfer" column.
    app.show_pview()
    app.istatement.selected = app.istatement.income[0]
    app.show_account()
    eq_(app.etable[0].transfer, '')
    app.drsel.select_next_date_range()
    app.drsel.select_prev_date_range()
    eq_(app.etable[0].transfer, '') # It shouldn't be set to "Some Income"

@with_app(app_account_with_budget)
def test_save_and_load(app):
    # There was a crash when loading a targetless budget
    newapp = app.save_and_load() # no crash
    newapp.show_bview()
    eq_(len(newapp.btable), 1)

@with_app(app_account_with_budget)
def test_set_budget_again(app):
    # There was a bug where setting the amount on a budget again wouldn't invert that amount
    # in the case of an income-based budget.
    app.show_bview()
    app.btable.select([0])
    bpanel = app.mw.edit_item()
    bpanel.amount = '200'
    bpanel.save()
    app.show_tview()
    eq_(app.ttable[0].from_, 'Some Income')

@with_app(app_account_with_budget)
def test_delete_account(app):
    # When deleting an income or expense account, delete all budgets associated
    # with it as well.
    app.show_pview()
    app.istatement.selected = app.istatement.income[0]
    app.istatement.delete()
    arpanel = app.get_current_panel()
    arpanel.save() # don't reassign
    app.show_bview()
    eq_(len(app.btable), 0) # the budget has been removed

@with_app(app_account_with_budget)
def test_delete_account_and_reassign(app):
    # When reassigning an account on deletion, change budgets instead of
    # deleting it.
    app.add_account('other expense', account_type=AccountType.Expense)
    app.istatement.selected = app.istatement.income[0]
    app.istatement.delete()
    arpanel = app.get_current_panel()
    arpanel.account_list.select(2) # other expense
    arpanel.save()
    app.show_bview()
    eq_(app.btable[0].account, 'other expense')

# --- Income with budget in past
def app_income_with_budget_in_past(monkeypatch):
    monkeypatch.patch_today(2009, 11, 16)
    app = TestApp()
    app.add_account('expense', account_type=AccountType.Expense)
    app.add_budget('expense', '100', start_date='01/09/2009')
    return app

@with_app(app_income_with_budget_in_past)
def test_spawns_dont_linger(app):
    # If the budget hasn't been spent in the past, we don't continue to spawn transactions for
    # it once we went past the spawn's end date.
    app.show_tview()
     # Only the spawns for november and december, NOT, september and october.
    eq_(app.ttable.row_count, 2)

# --- Expense with budget and txn
def app_budget_with_expense_and_txn(monkeypatch):
    monkeypatch.patch_today(2008, 1, 27)
    app = TestApp()
    app.add_account('Some Expense', account_type=AccountType.Expense)
    app.add_budget('Some Expense', '100')
    app.add_txn(date='27/01/2008', to='Some Expense', amount='42')
    return app

@with_app(app_budget_with_expense_and_txn)
def test_budget_transaction_is_adjusted(app):
    # Adding a transaction affects the next budget transaction
    eq_(app.ttable[1].amount, '58.00')
    eq_(app.ttable[2].amount, '100.00')

@with_app(app_budget_with_expense_and_txn)
def test_busted_budget_spaws_dont_show_up(app):
    # When a budget is busted, don't show the spawn
    app.ttable[0].amount = '142'
    app.ttable.save_edits()
    eq_(app.ttable.row_count, 12)
    eq_(app.ttable[1].date, '29/02/2008')


# --- Two budgets from same account
def app_two_budgets_from_same_account(monkeypatch):
    # XXX this mock is because the test previously failed because we were currently on the last
    # day of the month. TODO: Re-create the last-day condition and fix the calculation bug
    monkeypatch.patch_today(2009, 8, 20)
    app = TestApp()
    app.drsel.select_month_range()
    app.add_account('income', account_type=AccountType.Income)
    app.add_txn(from_='income', amount='25') # This txn must not be counted twice in budget calculations!
    app.add_budget('income', '100')
    app.add_budget('income', '100')
    return app

@with_app(app_two_budgets_from_same_account)
def test_both_budgets_are_counted(app):
    # The amount budgeted is the sum of all budgets, not just the first one.
    app.show_pview()
    eq_(app.istatement.income[0].budgeted, '175.00')

# --- Yearly buget with txn before current month
def app_yearly_budget_with_txn_before_current_month(monkeypatch):
    monkeypatch.patch_today(2009, 8, 24)
    app = TestApp()
    app.drsel.select_year_range()
    app.add_account('income', account_type=AccountType.Income)
    app.add_txn(date='01/07/2009', from_='income', amount='25')
    app.add_budget('income', '100', start_date='01/01/2009', repeat_type_index=3) # yearly
    return app

@with_app(app_yearly_budget_with_txn_before_current_month)
def test_entry_is_correctly_counted_in_budget(app):
    # The entry, although not in the current month, is counted in budget calculations
    app.show_pview()
    eq_(app.istatement.income[0].budgeted, '75.00')

@with_app(app_yearly_budget_with_txn_before_current_month)
def test_spawn_has_correct_date(app):
    # The spawn is created at the correct date, which is at the end of the year
    app.show_tview()
    # first txn is the entry on 01/07
    eq_(app.ttable[1].date, '31/12/2009')

# --- Scheduled txn and budget
def app_scheduled_txn_and_budget(monkeypatch):
    monkeypatch.patch_today(2009, 9, 10)
    app = TestApp()
    app.drsel.select_month_range()
    app.add_account('account', account_type=AccountType.Expense)
    app.add_schedule(start_date='10/09/2009', account='account', amount='1', repeat_type_index=2) # monthly
    app.add_budget('account', '10') # monthly
    return app

@with_app(app_scheduled_txn_and_budget)
def test_schedule_affects_budget(app):
    # schedule spawns affect the budget spawns
    app.show_tview()
    eq_(app.ttable[1].amount, '9.00') # 1$ has been removed from the budgeted 10


# --- Unit tests for the less heroic, more simple minded.

def fixed_date_feb_2019(monkeypatch):
    monkeypatch.patch_today(date(year=2019, month=2, day=20))

@with_app(fixed_date_feb_2019)
def test_budget_period_spawns_correct_number():
    account_list = AccountList('USD')
    expense = account_list.create('expense', 'USD', AccountType.Expense)
    start_date=date(year=2019, day=1, month=1)
    budget_list = BudgetList()
    budget_list.start_date = start_date
    budget = Budget(expense, 0, budget_list.start_date)
    budget_list.append(budget)
    spawns = budget_list.get_spawns(until_date=date(2019, day=1, month=12), txns=[])
    eq_(len(spawns), 0, "0 spawns because they have no value.")
    budget.amount = Amount(100, "USD")
    spawns = budget_list.get_spawns(until_date=date(2019, day=1, month=12), txns=[])
    eq_(len(spawns), 11, "11 spawns, culling 1 date which occurs in the past.")
    spawns = budget_list.budget_period_spawns
    eq_(len(spawns), 12, "We get 12 spawns!")


@with_app(fixed_date_feb_2019)
def test_budget_period_modification():
    account_list = AccountList('USD')
    expense = account_list.create('expense', 'USD', AccountType.Expense)
    start_date=date(year=2019, day=1, month=1)
    budget_list = BudgetList()
    budget_list.start_date = start_date
    budget = Budget(expense, Amount(1000, "USD"), budget_list.start_date)
    budget_list.append(budget)
    budget_list.get_spawns(until_date=date(2019, day=1, month=12), txns=[])
    spawns = budget_list.budget_period_spawns
    eq_(len(spawns), 12, "We get 12 spawns!")

    def mod_budget_amount(spawn, amount):
        spawn.budget_amount = amount
        budget.add_exception(spawn)

    # Make one budget amount more in the past.
    mod_budget_amount(spawns[0], Amount(10000, "USD"))
    # Make one budget amount less in the future.
    mod_budget_amount(spawns[5], Amount(100, "USD"))
    # Make one budget amount more in the future.
    mod_budget_amount(spawns[6], Amount(10000, "USD"))
    # Make one budget amount zero in the future.
    mod_budget_amount(spawns[7], Amount(0, "USD"))

    culled_spawns = budget_list.get_spawns(until_date=date(2019, day=1, month=12), txns=[])
    all_spawns = budget_list.budget_period_spawns

    eq_(len(culled_spawns), 10, "1 past and 1 zero amount culled")
    eq_(len(all_spawns), 12, "all budget periods still exist")
    eq_(spawns[0].budget_amount, Amount(10000, "USD"))
    # Make one budget amount less in the future.
    eq_(spawns[5].budget_amount, Amount(100, "USD"))
    # Make one budget amount more in the future.
    eq_(spawns[6].budget_amount, Amount(10000, "USD"))
    # Make one budget amount zero in the future.
    eq_(spawns[7].budget_amount, Amount(0, "USD"))
    for idx, spawn in enumerate(all_spawns):
        if idx not in (0, 5, 6, 7):
            eq_(spawn.budget_amount, Amount(1000, "USD"))
