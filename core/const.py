# Created By: Virgil Dupras
# Created On: 2008-09-14
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "HS" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/hs_license

NOEDIT = object()
DATE_FORMAT_FOR_PREFERENCES = '%d/%m/%Y'

# These constants are in sync with the GUI
class PaneType(object):
    NetWorth = 0
    Profit = 1
    Transaction = 2
    Account = 3
    Schedule = 4
    Budget = 5
    Cashculator = 6
    Empty = 100
