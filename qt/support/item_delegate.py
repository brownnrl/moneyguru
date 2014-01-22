# -*- coding: utf-8 -*-
# Created By: Virgil Dupras
# Created On: 2010-01-07
# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from collections import namedtuple
from collections import defaultdict

from PyQt4.QtCore import QRect, QSize
from PyQt4.QtCore import Qt, QPoint
from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QStyle
from PyQt4.QtGui import QFont, QPixmap, QPainter

from hscommon.currency import BUILTIN_CURRENCY_CODES

ItemDecoration = namedtuple('ItemDecoration', 'pixmap onClickCallable')

class ItemDelegate(QStyledItemDelegate):
    #--- Virtual
    def _get_decorations(self, index, isSelected):
        # Must return a list of ItemDecoration for each little image you want to put at the right
        # side of the cell. If you want them to be clickable, set onClickCallable with an argument-
        # less function.
        return []
    
    def _prepare_paint_options(self, option, index):
        # Don't set option directly in `paint` but here. This way, there won't be any trouble with
        # option being overwritten.
        pass
    
    #--- Overrides
    def handleClick(self, index, pos, itemRect, selected):
        decorations = self._get_decorations(index, selected)
        currentRight = itemRect.right()
        for dec in decorations:
            pixmap = dec.pixmap
            if pos.x() >= currentRight - pixmap.width():
                dec.onClickCallable()
                break
            currentRight -= pixmap.width()
    
    def paint(self, painter, option, index, align_right=True):
        self.initStyleOption(option, index)
        # I don't know why I have to do this. option.version returns 4, but still, when I try to
        # access option.features, boom-crash. The workaround is to force a V4.
        option = QStyleOptionViewItemV4(option)
        decorations = self._get_decorations(index, bool(option.state & QStyle.State_Selected))
        if decorations:
            option.decorationPosition = QStyleOptionViewItemV4.Right \
                                          if align_right \
                                          else QStyleOptionViewItemV4.Left
            decorationWidth = sum(dec.pixmap.width() for dec in decorations)
            decorationHeight = max(dec.pixmap.height() for dec in decorations)
            option.decorationSize = QSize(decorationWidth, decorationHeight)
            option.features |= QStyleOptionViewItemV4.HasDecoration
        self._prepare_paint_options(option, index)
        QStyledItemDelegate.paint(self, painter, option, index)
        xOffset = 0
        for dec in decorations:
            pixmap = dec.pixmap
            if not align_right:
                x = option.rect.left()
                y = option.rect.center().y() - (pixmap.height() // 2)
            else:
                x = option.rect.right() - pixmap.width() - xOffset
                y = option.rect.center().y() - (pixmap.height() // 2)
            rect = QRect(x, y, pixmap.width(), pixmap.height())
            painter.drawPixmap(rect, pixmap)
            xOffset += pixmap.width()
    
    def setModelData(self, editor, model, index):
        # This call below is to give a chance to the editor to tweak its content a little bit before
        # we send it to the model.
        if hasattr(editor, 'prepareDataForCommit'):
            editor.prepareDataForCommit()
        QStyledItemDelegate.setModelData(self, editor, model, index)

def paint_currency_code(code):
    pix = QPixmap(12*3, 15)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.drawText(pix.rect(), Qt.AlignLeft, code)

    return pix

def generate_currency_pix_maps():
    return_pixs = []
    
    for code in BUILTIN_CURRENCY_CODES:
        pix = paint_currency_code(code)
        return_pixs.append((code, pix))

    return return_pixs

class CurrencyPixs:
    def __init__(self):
        self.currency_pixs = generate_currency_pix_maps()
        uknown_code = paint_currency_code(' ? ')
        self.currency_decorations = defaultdict(lambda: uknown_code)
        for code, pix in self.currency_pixs:
            self.currency_decorations[code] = ItemDecoration(pix, lambda: None)

