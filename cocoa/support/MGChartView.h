/* 
Copyright 2014 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import "PyChart.h"
#import "MGPen.h"
#import "MGBrush.h"

@interface MGChartView : NSView <NSCopying>
{
    PyChart *model;
    NSColor *backgroundColor;
    NSColor *titleColor;
}
- (PyChart *)model;
- (void)setModel:(PyChart *)aModel;
- (NSDictionary *)fontAttributesForID:(NSInteger)aFontID;
- (MGPen *)penForID:(NSInteger)aPenID;
- (MGBrush *)brushForID:(NSInteger)aBrushID;
- (void)drawLineFrom:(NSPoint)aP1 to:(NSPoint)aP2 pen:(MGPen *)aPen;
- (void)drawRect:(NSRect)aRect pen:(MGPen *)aPen brush:(MGBrush *)aBrush;
- (void)drawPieWithCenter:(NSPoint)aCenter radius:(CGFloat)aRadius startAngle:(CGFloat)aStartAngle spanAngle:(CGFloat)aSpanAngle brush:(MGBrush *)aBrush;
- (void)drawPolygonWithPoints:(NSArray *)aPoints pen:(MGPen *)aPen brush:(MGBrush *)aBrush;
- (void)drawText:(NSString *)aText inRect:(NSRect)aRect withAttributes:(NSDictionary *)aAttrs;
@end