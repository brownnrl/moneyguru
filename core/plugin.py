# Created On: 2012/02/02
# Copyright 2014 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

"""API to create moneyGuru plugins.

This module was designed to allow developers to easily create plugins for moneyGuru. moneyGuru being
open source, we can already add anything anywhere, but the bar of entry for doing so can be high.

The goal here is to lower the bar of entry by having a simple API to do simple things. Many of the
classes below are either base classes or helper classes. If you want to develop a plugin, this is
the list of classes you can subclass:

* :class:`ReadOnlyTablePlugin`
* :class:`CurrencyProviderPlugin`
"""

from datetime import date

# Column is not used in this unit, but is imported to allow plugins to easily be able to import it.
from hscommon.gui.column import Column # noqa
from hscommon.currency import Currency, CurrencyNotSupportedException

from hscommon.notify import Broadcaster
from .gui.base import BaseView
from .gui.table import GUITable, Row
from .const import PaneType

class Plugin:
    """Base class for all plugins.

    By itself, it doesn't do much except offer common attributes to all plugins. Don't subclass
    this directly.
    """
    #: Display name of the plugin (for when we list plugins and stuff)
    NAME = ''
    #: Whether this plugin is a View, and thus should be in the plugin section of the New View tab.
    IS_VIEW = False

class ViewPlugin(Plugin):
    """Base class for viewable plugins.

    Once again, we don't subclass this directly. The way viewable plugin work is that the base
    system provides a couple of view "templates" to offer to the plugin developer, who is then able
    to fill the template with data within that template's bounds.

    This system is there to simplify the plugin developer's work, because otherwise he would have
    to manually code the Qt and Cocoa layers for each view plugin, which could get complicated.

    Subclasses :class:`.Plugin`.
    """
    IS_VIEW = True

    def __init__(self, mainwindow):
        #: The plugin's parent :class:`.MainWindow`.
        self.mainwindow = mainwindow
        #: The plugin's parent :class:`.Document`.
        self.document = mainwindow.document

class ReadOnlyTableRow(Row):
    """A :class:`.Row` with a simplified API for plugin developers."""
    def set_field(self, name, value, sort_value=None):
        """Set the value of an arbitrary field name in the row.

        :param str name: Name of the field to set.
        :param str value: Display value of the field.
        :param sort_value: Value to use for sorting.
        """
        setattr(self, name, value)
        if sort_value is not None:
            setattr(self, '_'+name, sort_value)


class ReadOnlyTable(GUITable):
    """A read-only table to be used in a :class:`.ViewPlugin`.

    It fetches its ``COLUMNS`` attribute (see :class:`.Columns`) directly from its parent plugin
    so that we don't have to subclass this table simply for defining columns.

    Subclasses :class:`.GUITable`.
    """
    def __init__(self, plugin):
        #: The parent plugin.
        self.plugin = plugin
        self.COLUMNS = plugin.COLUMNS
        GUITable.__init__(self, plugin.document)

    def _fill(self):
        self.plugin.fill_table()


class ReadOnlyTableView(BaseView):
    """View for :class:`.ReadOnlyTablePlugin`.

    A simple view containing a :class:`.ReadOnlyTable`, used by :class:`.ReadOnlyTablePlugin`.

    Subclasses :class:`.BaseView`.
    """
    VIEW_TYPE = PaneType.ReadOnlyTablePlugin

    def __init__(self, plugin):
        BaseView.__init__(self, plugin.mainwindow)
        self.plugin = plugin
        self.table = ReadOnlyTable(plugin)
        self.bind_messages(self.INVALIDATING_MESSAGES, self._revalidate)

    def _revalidate(self):
        self.table.refresh_and_show_selection()


class ReadOnlyTablePlugin(ViewPlugin):
    """A view plugin that contains a read-only table.

    To create a plugin from this, subclass it, fill :attr:`COLUMNS` and implement
    :meth:`fill_table`.

    Subclasses :class:`ViewPlugin`.
    """
    #: List of columns to be displayed in our table. See :class:`Columns`.
    COLUMNS = []

    def __init__(self, mainwindow):
        ViewPlugin.__init__(self, mainwindow)
        #: Instance of :class:`ReadOnlyTableView`
        self.view = ReadOnlyTableView(self)
        #: Instance of :class:`ReadOnlyTable`
        self.table = self.view.table

    def add_row(self):
        """Add a row to our table and return it.

        :rtype: :class:`ReadOnlyTableRow`
        """
        row = ReadOnlyTableRow(self.table)
        self.table.append(row)
        return row

    def fill_table(self):
        """Fills our table with its intended contents.

        Subclass this to add content to your table. The principle is rather simple: Add your rows
        with :meth:`add_row` and call :meth:`ReadOnlyTableRow.set_field` to set the contents of each
        row.
        """
        raise NotImplementedError()

class CurrencyProviderPlugin(Plugin):
    """Plugin allowing the creation of new currencies and the fetching of their rates.

    By subclassing this plugin, you can add new currencies to moneyGuru and also add a new source
    to fetch those currencies' exchange rates.

    Subclasses :class:`Plugin`
    """
    def __init__(self):
        Plugin.__init__(self)
        self.supported_currency_codes = set()
        for code, name, exponent, fallback_rate in self.register_currencies():
            Currency.register(code, name, exponent, latest_rate=fallback_rate)
            self.supported_currency_codes.add(code)

    def wrapped_get_currency_rates(self, currency_code, start_date, end_date):
        """Tries to fetch exchange rates for ``currency_code``.

        If our currency is supported by our plugin, we first try the "simple" fetching
        (:meth:`get_currency_rate_today`). If it's not implemented, we try the "complex" one
        (:meth:`get_currency_rates`). We return the result of the first method to work.

        If we can't get results, either because our currency isn't supported or because our
        implementation is incomplete, :exc:`.CurrencyNotSupportedException` is raised.

        This method isn't designed to be overriden.
        """
        if currency_code not in self.supported_currency_codes:
            raise CurrencyNotSupportedException()
        try:
            simple_result = self.get_currency_rate_today(currency_code)
            if simple_result is not None:
                return [(date.today(), simple_result)]
            else:
                return []
        except NotImplementedError:
            try:
                return self.get_currency_rates(currency_code, start_date, end_date)
            except NotImplementedError:
                raise CurrencyNotSupportedException()

    def register_currencies(self):
        """Override this and return a list of new currencies to support.

        The expected return value is a list of tuples ``(code, name, exponent, fallback_rate)``.

        ``exponent`` is the number of decimal numbers that should be displayed when formatting
        amounts in this currency.

        ``fallback_rate`` is the rate to use in case we can't fetch a rate. You can use the rate
        that is in effect when you write the plugin. Of course, it will become wildly innaccurate
        over time, but it's still better than a rate of ``1``.
        """
        raise NotImplementedError()

    def get_currency_rate_today(self, currency_code):
        """Override this if you have a 'simple' provider.

        If your provider doesn't give rates for any other date than today, overriding this method
        instead of get_currency_rate() is the simplest choice.

        ``currency_code`` is a string representing the code of the currency to fetch, 'USD' for
        example.

        Return a float representing the value of 1 unit of your currency in CAD.

        If you can't get a rate, return ``None``.

        This method is called asynchronously, so it won't block moneyGuru if it takes time to
        resolve.
        """

    def get_currency_rates(self, currency_code, start_date, end_date):
        """Override this if your provider gives rates for past dates.

        If your provider gives rates for past dates, it's better (although a bit more complicated)
        to override this method so that moneyGuru can have more accurate rates.

        You must return a list of tuples (date, rate) with all rates you can fetch between
        start_date and end_date. You don't need to have one item for every single date in the range
        (for example, most of the time we don't have values during week-ends), moneyGuru correctly
        handles holes in those values. Simply return whatever you can get.

        If you can't get a rate, return an empty list.

        This method is called asynchronously, so it won't block moneyGuru if it takes time to
        resolve.
        """
        raise NotImplementedError()


class ImportBindPlugin(Plugin):

    def match_entries(self, document, import_document, existing_entries, imported_entries):
        return []


class ImportActionPlugin(Plugin, Broadcaster):
    """
    Plugin allowing certain kinds of actions to be performed on import.

    By subclassing this plugin, you can add new currencies to moneyGuru and also add a new source
    to fetch those currencies' exchange rates.

    Subclasses :class:`Plugin`, :class:`Broadcaster`
    """

    # Signal to the import window to change the name in our drop down list
    action_name_changed = 'action_name_changed'

    # The name that appears in our drop down list
    ACTION_NAME = None

    def on_selected_pane_changed(self, selected_pane):
        """
        This method is called whenever the import window has changed it's selected pane.

        :param core.gui.import_window.AccountPane selected_pane: Currently selected pane or None if no pane selected
        """
        pass

    def always_perform_action(self):
        """
        Eventually, this will be used to query whether every single possible transaction should
        always have this action performed instead of using the single click 'Fix' button.
        """
        return False

    def can_perform_action(self, selected_pane, panes, transactions):
        """
        You shouldn't make any modifications to the provided transactions or panes.  But you can query the attributes
        inside these parameters to determine if the user is given the ability to use your action.

        :param core.gui.import_window.AccountPane selected_pane: Currently selected pane or None if no pane selected
        :param list panes: List of the panes currently open in the import window
        :param list transactions: A list of :class:`core.model.transaction.Transaction` objects (each row of the import table)
        """
        return True

    def perform_action(self, selected_pane, panes, transactions):
        """
        Go to town!  Most likely, you'll want to modify the transactions (changing the individual
        rows) but you can also look up interesting information about account names through the
        selected_pane or panes and their account attribute.

        :param core.gui.import_window.AccountPane selected_pane: Currently selected pane or None if no pane selected
        :param list panes: List of the panes currently open in the import window
        :param list transactions: A list of :class:`core.model.transaction.Transaction` objects (each row of the import table)
        """
        pass