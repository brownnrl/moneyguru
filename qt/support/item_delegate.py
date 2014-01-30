# -*- coding: utf-8 -*-
# Created By: Virgil Dupras
# Created On: 2010-01-07
# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from collections import namedtuple

from PyQt4.QtCore import QRect, QSize
from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QStyle

ItemDecoration = namedtuple('ItemDecoration', 'pixmap onClickCallable')

class ItemDelegate(QStyledItemDelegate):
    #--- Virtual
    def _get_decorations(self, index, isSelected):
        # Must return a list of ItemDecoration for each little image you want to put at the right
        # side of the cell. If you want them to be clickable, set onClickCallable with an argument-
        # less function.
        return []

    def _get_value_painter(self, index):
        return None
    
    def _prepare_paint_options(self, option, index):
        # Don't set option directly in `paint` but here. This way, there won't be any trouble with
        # option being overwritten.
        pass
    
    #--- Overrides

    def sizeHint(self, option, index):
        value_painter = self._get_value_painter(index)
        if value_painter is None:
            return QStyledItemDelegate.sizeHint(self, option, index)
        decs = self._get_decorations(index, bool(option.state & QStyle.State_Selected))
        pix_widths = [dec.pixmap.width() for dec in decs]
        size = value_painter.sizeHint(option, index)
        size.setWidth(size.width() + sum(pix_widths))
        return size

    def handleClick(self, index, pos, itemRect, selected):
        decorations = self._get_decorations(index, selected)
        currentRight = itemRect.right()
        for dec in decorations:
            pixmap = dec.pixmap
            if pos.x() >= currentRight - pixmap.width():
                dec.onClickCallable()
                break
            currentRight -= pixmap.width()
    
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        # I don't know why I have to do this. option.version returns 4, but still, when I try to
        # access option.features, boom-crash. The workaround is to force a V4.
        option = QStyleOptionViewItemV4(option)
        decorations = self._get_decorations(index, bool(option.state & QStyle.State_Selected))
        if decorations:
            option.decorationPosition = QStyleOptionViewItemV4.Right
            decorationWidth = sum(dec.pixmap.width() for dec in decorations)
            decorationHeight = max(dec.pixmap.height() for dec in decorations)
            option.decorationSize = QSize(decorationWidth, decorationHeight)
            option.features |= QStyleOptionViewItemV4.HasDecoration
        self._prepare_paint_options(option, index)
        QStyledItemDelegate.paint(self, painter, option, index)
        xOffset = 0
        for dec in decorations:
            pixmap = dec.pixmap
            x = option.rect.right() - pixmap.width() - xOffset
            y = option.rect.center().y() - (pixmap.height() // 2)
            rect = QRect(x, y, pixmap.width(), pixmap.height())
            painter.drawPixmap(rect, pixmap)
            xOffset += pixmap.width()
        value_painter = self._get_value_painter(index)
        if value_painter is not None:
            value_option = QStyleOptionViewItemV4(option)
            rect = value_option.rect
            rect = QRect(rect.left(), rect.top(), rect.width() - xOffset, rect.height())
            value_option.rect = rect
            value_painter.paint(painter, value_option, index)
    
    def setModelData(self, editor, model, index):
        # This call below is to give a chance to the editor to tweak its content a little bit before
        # we send it to the model.
        if hasattr(editor, 'prepareDataForCommit'):
            editor.prepareDataForCommit()
        QStyledItemDelegate.setModelData(self, editor, model, index)


class ColumnDelegate(object):

    def __init__(self, column_name, model):
        self._column_name = column_name
        self._model = model

    @property
    def column_name(self):
        return self._column_name

    def sizeHint(self, option, index):
        pass

    def _get_data_from_index(self, index):
        pass

    def _paint_column_data(self, painter, option, column_data):
        pass

    def paint(self, column_name, painter, option, index):

        column_data = self._get_data_from_index(index)

        if column_data is None:
            return

        self._paint_column_data(column_name, painter, option, column_data)