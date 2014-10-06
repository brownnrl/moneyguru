/* 
Copyright 2014 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import "MGDateFieldEditor.h"
#import "MGFieldEditor.h"
#import "PyPanel.h"

@interface MGPanel : NSWindowController <NSWindowDelegate> {
    PyPanel *model;
    NSWindow *parentWindow;
    MGFieldEditor *customFieldEditor;
    MGDateFieldEditor *customDateFieldEditor;
}
- (id)initWithNibName:(NSString *)aNibName model:(PyPanel *)aModel parent:(NSWindowController *)aParent;
- (id)initWithModel:(PyPanel *)aModel parent:(NSWindowController *)aParent;
- (PyPanel *)model;
/* Virtual */
- (NSString *)completionAttrForField:(id)aField;
- (BOOL)isFieldDateField:(id)aField;
- (NSResponder *)firstField;
- (void)loadFields;
- (void)saveFields;
/* Public */
- (void)save;
/* Actions */
- (void)cancel:(id)sender;
- (void)save:(id)sender;
@end
