/* 
Copyright 2014 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import "PyEntryTable.h"
#import "MGEditableTable.h"

@interface MGEntryTable : MGEditableTable {}
- (id)initWithPyRef:(PyObject *)aPyRef tableView:(MGTableView *)aTableView;
- (void)initializeColumns;

/* Public */
- (PyEntryTable *)model;
@end
