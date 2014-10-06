/* 
Copyright 2014 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import "MGAccountSheetView.h"
#import "HSOutlineView.h"
#import "MGBalanceSheet.h"
#import "MGBalanceGraph.h"

@interface MGNetWorthView : MGAccountSheetView
{
    MGBalanceSheet *balanceSheet;
}
/* Public */
- (BOOL)canShowSelectedAccount;
- (void)toggleExcluded;
@end