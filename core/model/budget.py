# Copyright 2019 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html
from collections import defaultdict
from datetime import date

from core.util import extract, first, flatten

from .date import DateRange, ONE_DAY
from .recurrence import Recurrence, DateCounter, RepeatType, get_repeat_type_desc
from .transaction import Transaction
from ._ccore import Transaction as _Transaction


class BudgetSpawn(_Transaction):

    def __init__(self, recurrence, ref, recurrence_date, date):
        super().__init__(3, date, ref.description, ref.payee, ref.checkno, None, None)
        self.recurrence_date = recurrence_date
        self.ref = ref
        self.change(splits=ref.splits)
        for split in self.splits:
            split.reconciliation_date = None
        self.balance()

        # Placeholder values, putting down some thoughts, I will remove these
        # comments or clean them up when the

        # It would be nice to hold a reference to the original Budget
        self.reference = recurrence

        self.difference_in_budget = 0
        self.carry_amount = 0

        # This flag and budget amount will trigger an exception record when
        # they are edited.  Carry reset will trigger a recook from this period
        # in order to recalculate the carry amounts.
        self.carry_reset = False

        # Amount to allocate to this budget within this period.
        # When the user changes this amount, if it is the most recent
        # value by date out of the current exceptions, then
        # that will be that amount will become the new default
        # moving forward maybe by updating the associated Budget through
        # the reference).
        self._budget_amount = None

        # Flags to indicate if we should reference back to the parent list for
        # these values.
        self._is_budget_amount_set = False
        self._is_amount_set = False

    # --- Override
    def change(self, *args, **kwargs):

        attrs = ('budget_amount', 'carry_reset', 'difference_in_period')

        if any(attr in kwargs for attr in attrs):
            for attr in attrs:
                setattr(self, attr, kwargs[attr])
                del kwargs[attr]

        if 'amount' in kwargs:
            self._is_amount_set = True

        super().change(*args, **kwargs)

    @property
    def budget_amount(self):
        if self._is_budget_amount_set:
            return self._budget_amount
        else:
            return self.reference.budget_amount_for_date(self.date)

    @budget_amount.setter
    def budget_amount(self, value):
        self._budget_amount = value
        self._is_budget_amount_set = True

    @property
    def amount(self):
        if self._is_amount_set:
            return super().amount
        else:
            return self.reference.budget_amount_for_date(self.date)



def prorate_amount(amount, spread_over_range, wanted_range):
    """Returns the prorated part of ``amount`` spread over ``spread_over_range`` for the ``wanted_range``.

    For example, if 100$ are spead over a range that lasts 10 days (let's say between the 10th and
    the 20th) and that there's an overlap of 4 days between ``spread_over_range`` and
    ``wanted_range`` (let's say the 16th and the 26th), the result will be 40$. Why? Because each
    day is worth 10$ and we're wanting the value of 4 of those days.

    :param amount: :class:`Amount`
    :param spread_over_range: :class:`.DateRange`
    :param wanted_range: :class:`.DateRange`
    """
    if not spread_over_range:
        return 0
    intersect = spread_over_range & wanted_range
    if not intersect:
        return 0
    rate = intersect.days / spread_over_range.days
    return amount * rate

class Budget(Recurrence):
    """Regular budget for a specific account.

    A budgets yields spawns with amounts depending on how much money we've already spent in our
    account. For example, if I have a monthly budget of 100$ for "Clothing", then the budget spawn
    for a month that has 25$ worth of clothing in it is going to be 75$. This only works in the
    future.

    Budgets work very similarly to recurrences, except that a twist must be applied to them so they
    can work properly. The twist is about the spawn's "recurrence" date and the effective date. The
    recurrence date must be at the beginning of the period, but the effective date must be at the end
    of it. The reason for it is that since recurrence are only cooked until a certain date (usually
    the current date range's end), but that the budget is affects the date range *prior* to it, the
    last budget of the date range will never be represented.

    All initialization variables are directly assigned to their corresponding attributes.

    Subclasses :class:`.Recurrence`.

    .. seealso:: :doc:`/forecast`
    """
    def __init__(self, account, amount, ref_date, repeat_type=RepeatType.Monthly):
        #: :class:`.Account` for which we budget. Has to be an income or expense.
        self.account = account
        #: ``str``. Freeform notes from the user.
        self.notes = ''
        self._previous_spawns = []
        self._spawns_in_past = []
        ref = Transaction(ref_date)
        # Represents the reference budget amount
        self.amount = amount
        Recurrence.__init__(self, ref, repeat_type, 1)

    def __repr__(self):
        return '<Budget %r %r>' % (self.account, self.amount)

    # --- Override
    def _create_spawn(self, ref, recurrence_date):
        # `recurrence_date` is the date at which the budget *starts*.
        # We need a date counter to see which date is next (so we can know when our period ends
        date_counter = DateCounter(recurrence_date, self.repeat_type, self.repeat_every, date.max)
        next(date_counter) # first next() is the start_date
        end_date = next(date_counter) - ONE_DAY
        spawn = BudgetSpawn(self, ref, recurrence_date=recurrence_date, date=end_date)
        # spawn.budget_amount = self.budget_amount_for_date(spawn.date)
        return spawn

    def get_spawns(self, end, transactions, consumedtxns):
        """Returns the list of transactions spawned by our budget.

        Works pretty much like :meth:`core.model.recurrence.Recurrence.get_spawns`, except for the
        extra arguments.

        :param transactions: Transactions that can affect our budget spawns' final amount.
        :type transactions: list of :class:`.Transaction`
        :param consumedtxns: Transactions that have already been "consumed" by a budget spawn in
                             this current round of spawning (one a budget "ate" a transaction, we
                             don't have it affect another). This set is going to be mutated
                             (augmented) by this method. All you have to do is start with an empty
                             set and pass it around for each call.
        :type consumedtxns: set of :class:`.Transaction`
        """
        account = self.account
        spawns = Recurrence.get_spawns(self, end)
        # Spawn in the past, but with 0 amounts
        # We iterate over past and current spawns to calculate carry amounts
        past_spawns = [spawn for spawn in spawns if spawn.date <= date.today()]
        spawns = [spawn for spawn in spawns if spawn.date > date.today()]
        relevant_transactions = set(t for t in transactions if account in t.affected_accounts())
        relevant_transactions -= consumedtxns
        carry_accum = 0 # Holder for the carry amounts
        for spawn in (past_spawns + spawns):
            budget_amount = spawn.budget_amount if account.is_debit_account() else - spawn.budget_amount
            affects_spawn = lambda t: spawn.recurrence_date <= t.date <= spawn.date
            wheat, shaft = extract(affects_spawn, relevant_transactions)
            relevant_transactions = shaft
            txns_amount = sum(t.amount_for_account(account, budget_amount.currency_code) for t in wheat)
            spawn.difference_in_budget = budget_amount - txns_amount
            if not spawn.carry_reset:
                spawn.carry_amount = carry_accum + spawn.difference_in_budget
                carry_accum = spawn.carry_amount
            else:
                spawn.carry_amount = spawn.difference_in_budget
                carry_accum = 0
            if abs(txns_amount) < abs(budget_amount):
                spawn_amount = budget_amount - txns_amount
                if spawn.amount_for_account(account, budget_amount.currency_code) != spawn_amount:
                    spawn.change(amount=spawn_amount, from_=account, to=None)
            else:
                spawn.change(amount=0, from_=account, to=None)
            consumedtxns |= set(wheat)
        for past_spawn in past_spawns:
            past_spawn.change(amount=0, from_=account, to=None)
        # Spawns in past is used for budget review and CRUD.
        self._spawns_in_past = past_spawns
        self._previous_spawns = spawns
        return self._previous_spawns

    @property
    def budget_period_spawns(self):
        """Returns a list all budget periods represented as spawns

        **Warning:** :meth:`get_spawns` must have been called as this function simply returns
        it's cached result inclusive of spawns which occur in the past.
        """
        return self._spawns_in_past + self._previous_spawns

    # --- Public
    def amount_for_date_range(self, date_range, currency):
        """Returns the budgeted amount for ``date_range``.

        That is, the pro-rated amount we're currently budgeting (with adjustments for transactions
        "consuming" the budget) for the date range.

        **Warning:** :meth:`get_spawns` must have been called until a date high enough to cover our
        date range. We're using previously generated spawns to compute that amount.

        :param date_range: The date range we want our budgeted amount for.
        :type date_range: :class:`.DateRange`
        :param currency: The currency of the returned amount. If the amount for the budget is
                         different, the exchange rate for the date of the beggining of the budget
                         spawn is used.
        :type currency: :class:`.Currency`
        :rtype: :class:`.Amount`
        """
        total_amount = 0
        for spawn in self._previous_spawns:
            amount = spawn.amount_for_account(self.account, currency)
            if not amount:
                continue
            my_start_date = max(spawn.recurrence_date, date.today() + ONE_DAY)
            my_end_date = spawn.date
            my_date_range = DateRange(my_start_date, my_end_date)
            total_amount += prorate_amount(amount, my_date_range, date_range)
        return total_amount

    def budget_amount_for_date(self, reference_date):
        if not reference_date or not self.date2exception:
            return self.amount
        if reference_date in self.date2exception:
            return self.date2exception[reference_date].budget_amount
        # Is the date at the far before or after the extent of defined dates
        exception_dates = sorted(self.date2exception.keys())
        first_exception_date = first(exception_dates)
        last_exception_date = first(reversed(exception_dates))
        if first_exception_date is None:
            return self.amount
        if reference_date < first_exception_date:
            return self.amount
        if reference_date > last_exception_date:
            last_budget_spawn = self.date2exception[last_exception_date]
            if last_budget_spawn:
                return last_budget_spawn.budget_amount
            else:
                return self.amount
        # Otherwise, we are somewhere in the middle of each
        for idx in range(len(exception_dates)-1):
            first_compare_date = exception_dates[idx]
            second_compare_date = exception_dates[idx+1]
            if first_compare_date < reference_date < second_compare_date:
                return self.date2exception[first_compare_date].budget_amount


class BudgetList(list):
    """Manage the collection of budgets of a document.

    This subclasses ``list`` and provides a few methods for getting stats for all budgets in the
    list.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_date = date.today()
        self.repeat_type = RepeatType.Monthly
        self.repeat_every = 1
        self.repeat_type_desc = get_repeat_type_desc(self.repeat_type, self.start_date)

    def amount_for_account(self, account, date_range, currency=None):
        """Returns the amount for all budgets for ``account``.

        In short, we sum up the result of :meth:`Budget.amount_for_date_range` calls.

        :param account: The account we want to count our budget for.
        :type account: :class:`.Account`
        :param date_range: The date range we want our budgeted amount for.
        :type date_range: :class:`.DateRange`
        :param currency: The currency of the returned amount. If ``None``, we use the currency of
                         ``account``.
        :type currency: :class:`.Currency`
        :rtype: :class:`.Amount`
        """
        if not date_range.future:
            return 0
        budgets = [b for b in self if b.account == account and b.amount]
        if not budgets:
            return 0
        currency = currency or account.currency
        amount = sum(b.amount_for_date_range(date_range, currency) for b in budgets)
        return amount

    def normal_amount_for_account(self, account, date_range, currency=None):
        """Normalized version of :meth:`amount_for_account`.

        .. seealso:: :meth:`core.model.account.Account.normalize_amount`
        """
        budgeted_amount = self.amount_for_account(account, date_range, currency)
        return account.normalize_amount(budgeted_amount)

    @property
    def budget_period_spawns(self):
        return flatten([b.budget_period_spawns for b in self])

    def get_spawns(self, until_date, txns):
        if not self:
            return []
        start_date = self.start_date
        repeat_type = self.repeat_type
        repeat_every = self.repeat_every
        # TODO: getter methods shouldn't change anything
        # This is just here until we can modify tests
        # And make the "universal budgeting periods"
        # work with the recurrence revert
        for budget in self:
            budget.start_date = start_date
            budget.repeat_type = repeat_type
            budget.repeat_every = repeat_every
        result = []
        # It's possible to have 2 budgets overlapping in date range and having the same account
        # When it happens, we need to keep track of which budget "consume" which txns
        account2consumedtxns = defaultdict(set)
        for budget in self:
            #if not budget.amount:
            #    continue
            consumedtxns = account2consumedtxns[budget.account]
            spawns = budget.get_spawns(until_date, txns, consumedtxns)
            spawns = [spawn for spawn in spawns if not spawn.is_null]
            result += spawns
        return result

