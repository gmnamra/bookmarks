# -*- coding: utf-8 -*-
"""``delegates.py`` defines the visual appearance of the ``BaseListWidget``
subclasses.

``BaseDelegate`` holds most of the functions used to draw the background and
visual indicators.

``BookmarksWidgetDelegate``, ``AssetsWidgetDelegate``, ``FilesWidgetDelegate``

"""
import re
from functools import wraps
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.images as images

TINT_THUMBNAIL_BACKGROUND = True
ROW_HEIGHT = common.ROW_HEIGHT
BOOKMARK_ROW_HEIGHT = common.BOOKMARK_ROW_HEIGHT
ASSET_ROW_HEIGHT = common.ASSET_ROW_HEIGHT
SMALL_FONT_SIZE = common.SMALL_FONT_SIZE
MEDIUM_FONT_SIZE = common.MEDIUM_FONT_SIZE
LARGE_FONT_SIZE = common.LARGE_FONT_SIZE

regex_remove_version = re.compile(
    ur'(.*)(v)([\[0-9\-\]]+.*)', flags=re.IGNORECASE | re.UNICODE)
regex_remove_bracket = re.compile(
    ur'[\[\]]*', flags=re.IGNORECASE | re.UNICODE)


BackgroundRect = 0
IndicatorRect = 1
ThumbnailRect = 2
AssetNameRect = 3
AssetDescriptionRect = 4
AddAssetRect = 5
TodoRect = 6
RevealRect = 7
ArchiveRect = 8
FavouriteRect = 9
DataRect = 10
BookmarkPropertiesRect = 11


def paintmethod(func):
    """@Decorator to save the painter state."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        args[1].save()
        res = func(self, *args, **kwargs)
        args[1].restore()
        return res
    return func_wrapper


class BaseDelegate(QtWidgets.QAbstractItemDelegate):
    """Base delegate containing methods to draw our list items."""

    def __init__(self, parent=None):
        super(BaseDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        raise NotImplementedError(
            '`paint()` is abstract and has to be overriden in the subclass!')

    def get_paint_arguments(self, painter, option, index, antialiasing=True):
        """A utility class for gathering all the arguments needed to paint
        the individual listelements.

        """
        if antialiasing:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=True)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=False)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=False)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        selected = option.state & QtWidgets.QStyle.State_Selected
        focused = option.state & QtWidgets.QStyle.State_HasFocus
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        flags = index.flags()
        favourite = flags & common.MarkedAsFavourite
        archived = flags & common.MarkedAsArchived
        active = flags & common.MarkedAsActive

        rectangles = self.get_rectangles(option.rect)
        font = common.font_db.primary_font()
        painter.setFont(font)
        metrics = QtGui.QFontMetricsF(font)

        cursor_position = self.parent().mapFromGlobal(QtGui.QCursor().pos())

        args = (
            rectangles,
            painter,
            option,
            index,
            selected,
            focused,
            active,
            archived,
            favourite,
            hover,
            font,
            metrics,
            cursor_position
        )
        return args

    def get_rectangles(self, rectangle):
        """Returns all the main rectangles of the row to paint and handle
        mouse-click events.

        """
        def rect():
            """Returns a rectangle with a separator."""
            r = QtCore.QRect(rectangle)
            return r.adjusted(0, 0, 0, -1)

        background_rect = rect()
        background_rect.setLeft(common.INDICATOR_WIDTH)
        background_rect.setRight(rect().right())

        indicator_rect = rect()
        indicator_rect.setWidth(common.INDICATOR_WIDTH)

        thumbnail_rect = rect()
        thumbnail_rect.setWidth(rect().height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        # Inline icons rect
        inline_icon_rects = []
        inline_icon_rect = rect()
        num_icons = self.parent().inline_icons_count()
        spacing = common.INDICATOR_WIDTH * 2
        center = inline_icon_rect.center()
        size = QtCore.QSize(common.INLINE_ICON_SIZE, common.INLINE_ICON_SIZE)
        inline_icon_rect.setSize(size)
        inline_icon_rect.moveCenter(center)
        inline_icon_rect.moveRight(rectangle.right() - spacing)

        offset = 0
        y = inline_icon_rect.y()
        for n in xrange(self.parent().inline_icons_count()):
            r = inline_icon_rect.translated(offset, 0)
            inline_icon_rects.append(r)
            offset -= inline_icon_rect.width() + spacing
        offset -= spacing

        data_rect = rect()
        data_rect.setLeft(thumbnail_rect.right() + spacing)
        data_rect.setRight(rectangle.right() + offset)

        null_rect = QtCore.QRect()

        return {
            BackgroundRect: background_rect,
            #
            IndicatorRect: indicator_rect,
            ThumbnailRect: thumbnail_rect,
            #
            FavouriteRect: inline_icon_rects[0] if num_icons > 0 else null_rect,
            ArchiveRect: inline_icon_rects[1] if num_icons > 1 else null_rect,
            RevealRect: inline_icon_rects[2] if num_icons > 2 else null_rect,
            TodoRect: inline_icon_rects[3] if num_icons > 3 else null_rect,
            AddAssetRect: inline_icon_rects[4] if num_icons > 4 else null_rect,
            BookmarkPropertiesRect: inline_icon_rects[5] if num_icons > 5 else null_rect,
            #
            DataRect: data_rect
        }

    def paint_name(self, *args):
        raise NotImplementedError(
            '`paint_name()` is abstract and needs to be overriden in the subclass!')

    def get_text_segments(self, index):
        raise NotImplementedError(
            '`get_text_segments()` is abstract and needs to be overriden in the subclass!')

    @paintmethod
    def paint_description_editor_background(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if index != self.parent().selectionModel().currentIndex():
            return
        if not self.parent().description_editor_widget.isVisible():
            return

        painter.setBrush(common.BACKGROUND_SELECTED)
        rect = QtCore.QRect(option.rect)
        rect.setLeft(rectangles[ThumbnailRect].right())
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints the thumbnails of asset and file-items.``"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        image = index.data(common.ThumbnailRole)
        if image is None:
            return

        rect = QtCore.QRect(rectangles[ThumbnailRect])

        # Background
        color = index.data(
            common.ThumbnailBackgroundRole) if TINT_THUMBNAIL_BACKGROUND else common.THUMBNAIL_BACKGROUND
        color = color if color else common.THUMBNAIL_BACKGROUND
        painter.setBrush(common.SEPARATOR)
        # painter.setOpacity(0.66)
        painter.drawRect(rect)

        # If this is the last item, there's not need painting this
        if index.row() < (index.model().rowCount() - 1):
            bottom_row_rect = QtCore.QRect(rectangles[ThumbnailRect])
            bottom_row_rect.setHeight(common.ROW_SEPARATOR)
            bottom_row_rect.moveTop(
                rectangles[ThumbnailRect].bottom() + common.ROW_SEPARATOR)
            painter.drawRect(bottom_row_rect)

        o = 1.0 if selected else 0.85
        # o = 1.0 if hover else o
        painter.setOpacity(o)

        # Image
        irect = QtCore.QRect(image.rect())
        if irect.width() > rect.width():
            irect.setWidth(rect.width())
        if irect.height() > rect.height():
            irect.setHeight(rect.height())
        irect.moveCenter(rect.center())

        # Image
        irect = QtCore.QRect(image.rect())
        if irect.width() > rect.width():
            irect.setWidth(rect.width())
        if irect.height() > rect.height():
            irect.setHeight(rect.height())
        irect.moveCenter(rect.center())
        painter.drawPixmap(irect, image, image.rect())

    def paint_thumbnail_drop_indicator(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        drop = self.parent()._thumbnail_drop
        if drop[1] and drop[0] == index.row():
            painter.setOpacity(0.6)
            painter.setBrush(common.SEPARATOR)
            painter.drawRect(option.rect)

            painter.setPen(common.ADD)
            font = common.font_db.secondary_font()
            painter.setFont(font)

            text = u'Drop image to add as thumbnail'
            painter.drawText(
                option.rect.marginsRemoved(QtCore.QMargins(18, 0, 18, 0)),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )

            o = 2
            rect = rectangles[ThumbnailRect].marginsRemoved(
                QtCore.QMargins(o, o, o, o))
            painter.drawRect(rect)

            pen = QtGui.QPen(common.ADD)
            pen.setWidthF(o)
            painter.setPen(pen)
            painter.setBrush(common.ADD)
            painter.setOpacity(0.5)
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'add', common.ADD, rect.height() * 0.5)
            painter.drawRect(rect)
            irect = pixmap.rect()
            irect.moveCenter(rect.center())
            painter.drawPixmap(irect, pixmap, pixmap.rect())

    @paintmethod
    def paint_background(self, *args):
        """Paints the background for all list items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[BackgroundRect])

        # Setting the opacity of the separator
        if index.row() != (self.parent().model().rowCount() - 1):
            painter.setOpacity(0.6667)
            color = common.SEPARATOR if archived else common.BACKGROUND
            painter.setBrush(color)
            painter.drawRect(rect)

        color = common.BACKGROUND_SELECTED if selected else common.BACKGROUND
        painter.setBrush(color)

        if index.row() != (self.parent().model().rowCount() - 1):
            _rect = QtCore.QRect(rect)
            _rect.setBottom(_rect.bottom() + common.ROW_SEPARATOR)
            _rect.setTop(_rect.bottom() - common.ROW_SEPARATOR)
            _rect.setLeft(rectangles[DataRect].left() - common.MARGIN)
            painter.setOpacity(0.666)
            painter.drawRect(_rect)

        painter.setOpacity(1.0)
        painter.drawRect(rect)


        # Active indicator
        if active:
            painter.setOpacity(0.7)
            painter.setBrush(common.FAVOURITE)
            painter.drawRect(rect)
            painter.setOpacity(1.0)
            painter.setPen(common.FAVOURITE)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(rect.marginsRemoved(QtCore.QMargins(1, 0, 1, 1)))

        # Hover indicator
        if hover:
            painter.setBrush(QtGui.QColor(255, 255, 255, 10))
            painter.drawRect(rect)

    @paintmethod
    def paint_inline_icons(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[FavouriteRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.TEXT if favourite else common.SEPARATOR
            color = common.SECONDARY_BACKGROUND if rect.contains(
                cursor_position) and not favourite else color
            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) and favourite else color
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'favourite', color, common.INLINE_ICON_SIZE)
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[ArchiveRect]
        if rect:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.ADD if archived else common.REMOVE
            color = color if rect.contains(
                cursor_position) else common.SEPARATOR

            if archived:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'check', common.ADD, common.INLINE_ICON_SIZE)
            else:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'remove', color, common.INLINE_ICON_SIZE)
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[RevealRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'reveal_folder', color, common.INLINE_ICON_SIZE)
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[TodoRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)

            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'todo', color, common.INLINE_ICON_SIZE)
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

            # Circular background
            size = 16
            count_rect = QtCore.QRect(0, 0, size, size)
            count_rect.moveCenter(rect.bottomRight())

            if index.data(common.TodoCountRole):
                painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
                if rect.contains(cursor_position):
                    color = common.TEXT_SELECTED
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        u'add', color, size)
                    painter.drawPixmap(count_rect, pixmap)
                else:
                    color = common.FAVOURITE
                    painter.setBrush(color)
                    painter.drawRoundedRect(
                        count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0)

                    text = unicode(index.data(common.TodoCountRole))
                    _font = common.font_db.primary_font(point_size=common.SMALL_FONT_SIZE)
                    _metrics = QtGui.QFontMetricsF(_font)
                    x = count_rect.center().x() - (_metrics.width(text) / 2.0) + 1
                    y = count_rect.center().y() + (_metrics.ascent() / 2.0)

                    painter.setBrush(common.TEXT)
                    path = QtGui.QPainterPath()
                    path.addText(x, y, _font, text)
                    painter.drawPath(path)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[AddAssetRect]
        if rect and not archived:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'add', common.ADD, rect.height())
                painter.drawPixmap(rect, pixmap)
            else:
                painter.setOpacity(0.666)
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'add', common.SECONDARY_BACKGROUND, rect.height())
                painter.drawPixmap(rect, pixmap)

        rect = rectangles[BookmarkPropertiesRect]
        if rect and not archived:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'settings', common.ADD, rect.height())
                painter.drawPixmap(rect, pixmap)
            else:
                painter.setOpacity(0.666)
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'settings', common.SECONDARY_BACKGROUND, rect.height())
                painter.drawPixmap(rect, pixmap)

    @paintmethod
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[IndicatorRect]
        color = common.FAVOURITE if selected else QtGui.QColor(0, 0, 0, 0)
        painter.setBrush(color)
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.moveLeft(rect.left() + rect.width())
        rect.setWidth(common.MARGIN)

        pixmap = images.ImageCache.get_rsc_pixmap(u'gradient', None, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_file_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.right())
        rect.setWidth(common.MARGIN)
        pixmap = images.ImageCache.get_rsc_pixmap(u'gradient', None, rect.height())
        painter.setOpacity(1.0)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.setWidth(common.MARGIN)
        rect.moveRight(rectangles[ThumbnailRect].right())
        pixmap = images.ImageCache.get_rsc_pixmap(u'gradient3', None, rect.height())
        painter.setOpacity(0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        rect.setWidth(common.MARGIN * 0.5)
        rect.moveRight(rectangles[ThumbnailRect].right())
        pixmap = images.ImageCache.get_rsc_pixmap(u'gradient3', None, rect.height())
        painter.setOpacity(0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_archived(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if archived:
            rect = QtCore.QRect(rectangles[IndicatorRect])
            rect.setRight(option.rect.right())
            painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50, 200)))
            painter.drawRect(rect)

    def sizeHint(self, option, index):
        raise NotImplementedError(
            '`sizeHint` has to be overriden in the subclass.')


class BookmarksWidgetDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the ``BookmarksWidgetItems`` should be painted."""
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_inline_icons(*args)
        self.paint_description_editor_background(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, *args):
        """We don't have descriptions for bookmark items."""
        return QtCore.QRect()

    def get_text_segments(self, index):
        """I'm using QPainterPaths to paint the text of each item. The functions
        returns a tuple of text and colour information to be used to mimick
        rich-text like colouring of individual text elements.

        """
        text = index.data(QtCore.Qt.DisplayRole)
        if not text:
            return {}

        d = {}
        d[len(d)] = (u'{}/{}'.format(
            index.data(common.ParentPathRole)[0],
            index.data(common.ParentPathRole)[1],
        ).upper().strip(), common.TEXT)
        d[len(d)] = (u'  |  ', common.FAVOURITE.darker(150))

        root_dirs = text.split(u'|')[-1].split(u'/')
        for idx, root_dir in enumerate(root_dirs):
            root_dir = root_dir.upper().strip()
            if idx == (len(root_dirs) - 1):
                d[len(d)] = (root_dir, common.TEXT)
                break
            else:
                d[len(d)] = (root_dir, common.TEXT)
            d[len(d)] = (u' / ', common.FAVOURITE.darker(150))
        return d

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        painter.setOpacity(0.9)
        if hover:
            painter.setOpacity(1.0)

        text_segments = self.get_text_segments(index)
        text = u''.join([text_segments[f][0] for f in text_segments])

        rect = rectangles[DataRect]
        rect.setLeft(rect.left() + common.MARGIN)

        o = common.INDICATOR_WIDTH

        text_width = metrics.width(text)
        r = QtCore.QRect(rect)
        r.setWidth(text_width)
        center = r.center()
        r.setHeight(metrics.height())
        r.moveCenter(center)

        r = r.marginsAdded(QtCore.QMargins(o * 2, o, o * 2, o))
        if (r.right() + o) > rect.right():
            r.setRight(rect.right() - o)
        painter.setBrush(common.FAVOURITE)

        pcolor = QtGui.QColor(
            255, 255, 255, 255) if active else common.FAVOURITE.darker(175)
        pen = QtGui.QPen(pcolor)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawRoundedRect(r, 3, 3)

        offset = 0
        painter.setPen(QtCore.Qt.NoPen)
        for segment in text_segments.itervalues():
            text, color = segment
            width = metrics.width(text)
            r = QtCore.QRect(rect)
            r.setWidth(width)
            center = r.center()
            r.setHeight(metrics.ascent())
            r.moveCenter(center)
            r.moveLeft(r.left() + offset)

            if r.left() >= rect.right():
                break

            if (r.right() + o) > rect.right():
                r.setRight(rect.right() - o)
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    r.width()
                )

            painter.setBrush(color)
            path = QtGui.QPainterPath()
            x = r.x()
            y = r.bottom()
            path.addText(x, y, font, text)
            painter.drawPath(path)

            offset += width

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        size = QtCore.QSize(1, BOOKMARK_ROW_HEIGHT)
        return size


class AssetsWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        # The index might still be populated...
        if index.data(QtCore.Qt.DisplayRole) is None:
            return
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_description_editor_background(*args)
        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, rectangles, index):
        """Returns the description area of an ``AssetsWidget`` item."""
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + common.MARGIN)

        font = common.font_db.primary_font()
        metrics = QtGui.QFontMetricsF(font)

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(name_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        return description_rect

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetsWidget``."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + common.MARGIN)

        # Name
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.TEXT_SELECTED if selected else color
        painter.setBrush(color)

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text = index.data(QtCore.Qt.DisplayRole)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            name_rect.width()
        )

        x = name_rect.left()
        y = name_rect.center().y() + (metrics.ascent() / 2.0)
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        painter.drawPath(path)

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(name_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )

        color = common.TEXT if hover else common.SECONDARY_TEXT
        painter.setBrush(color)

        text = index.data(common.DescriptionRole)
        text = text if text else u''
        font = common.font_db.primary_font(point_size=common.MEDIUM_FONT_SIZE - 0.5)
        painter.setFont(font)
        _metrics = QtGui.QFontMetricsF(font)
        text = _metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            description_rect.width()
        )

        if description_rect.contains(cursor_position):
            underline_rect = QtCore.QRect(description_rect)
            underline_rect.setTop(underline_rect.bottom())
            underline_rect.moveTop(underline_rect.top() + 1)
            painter.setOpacity(0.5)
            painter.setBrush(common.SEPARATOR)
            painter.drawRect(underline_rect)
            painter.setBrush(common.SECONDARY_TEXT)
            painter.setOpacity(1.0)

            text = u'Double-click to edit...' if not text else text

        x = description_rect.left()
        y = description_rect.center().y() + (metrics.ascent() / 2.0)
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        painter.drawPath(path)

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().ROW_SIZE


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""
    maximum_subdirs = 4

    def __init__(self, parent=None):
        super(FilesWidgetDelegate, self).__init__(parent=parent)
        self._clickable_rectangles = {}

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""

        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        if index.data(QtCore.Qt.DisplayRole) is None:
            return

        self.paint_background(*args)
        self.paint_thumbnail(*args)

        b_hidden = self.parent().buttons_hidden()
        p_role = index.data(common.ParentPathRole)
        if p_role and not b_hidden:
            self.paint_file_shadow(*args)
            # self.paint_thumbnail_shadow(*args)
            self.paint_name(*args)
        elif p_role and b_hidden:
            self.paint_simple_name(*args)

        if index.data(common.FileInfoLoaded):
            self.paint_archived(*args)
        self.paint_description_editor_background(*args)

        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)

        if self.parent().drag_source_index.isValid():
            self.paint_drag_source(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, rectangles, index):
        """The description rectangle of a file item."""
        if self.parent().buttons_hidden():
            return self.get_simple_description_rectangle(rectangles, index)
        clickable = self.get_clickable_rectangles(index, rectangles)
        if not clickable:
            return QtCore.QRect()
        return clickable[0][0]

    def get_clickable_rectangles(self, index, rectangles):
        """The clickable rectangles are cached when the item is painted.
        """
        if index.row() in self._clickable_rectangles:
            return self._clickable_rectangles[index.row()]
        return []

    @paintmethod
    def paint_name(self, *args):
        """Paints the subfolders and the filename of the current file inside the ``FilesWidget``."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        self._clickable_rectangles[index.row()] = []

        def draw_separator_line():
            _rect = QtCore.QRect(rectangles[DataRect])
            _rect.setWidth(common.ROW_SEPARATOR)
            _rect.moveLeft(rectangles[DataRect].right())
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.1)
            painter.drawRect(_rect)
            painter.setOpacity(1.0)

        def draw_segments(it, font, metrics, offset):
            x = 0

            rect = QtCore.QRect(rectangles[DataRect])
            rect.setRight(rectangles[DataRect].right() - common.MARGIN)

            o = 0.9 if selected else 0.8
            o = 1.0 if hover else o
            painter.setOpacity(o)
            painter.setPen(QtCore.Qt.NoPen)
            for v in it:
                text, color = v

                color = common.TEXT_SELECTED if selected else color
                color = common.TEXT if hover else color

                width = metrics.width(text)
                rect.setLeft(rect.right() - width)

                if (rectangles[DataRect].left()) >= rect.left():
                    rect.setLeft(
                        rectangles[DataRect].left())
                    text = metrics.elidedText(
                        text,
                        QtCore.Qt.ElideLeft,
                        rect.width()
                    )
                    width = metrics.width(text)
                    rect.setLeft(rect.right() - width)

                x = rect.center().x() - (width / 2.0) + 1
                y = rect.center().y() + offset

                painter.setBrush(color)
                path = QtGui.QPainterPath()
                path.addText(x, y, font, text)
                painter.drawPath(path)

                rect.translate(-width, 0)

            return x

        def draw_subdirs(text_edge):
            font = common.font_db.primary_font(point_size=common.SMALL_FONT_SIZE)
            metrics = QtGui.QFontMetricsF(font)

            subdir_rectangles = self.get_subdir_rectangles(
                index, rectangles, metrics)
            if not subdir_rectangles:
                return rectangles[DataRect].left()

            r = rectangles[DataRect]

            filter_text = self.parent().model().filter_text()
            rootdir = index.data(common.ParentPathRole)[-1]
            rootdirs = rootdir.split(u'/')

            if text_edge > rectangles[DataRect].left() + common.MARGIN:
                # Inner gray rectangle containing all other subfolder rectangles
                painter.setBrush(common.SEPARATOR)
                _r = QtCore.QRect(rectangles[DataRect])
                _r.setRight(
                    subdir_rectangles[-1][0].right() + (common.INDICATOR_WIDTH * 2))
                _r.setLeft(_r.left() - (common.INDICATOR_WIDTH * 2))
                if (_r.right() > (text_edge + common.INDICATOR_WIDTH * 2)):
                    _r.setRight(text_edge)
                if _r.left() < rectangles[DataRect].left():
                    o = 4
                    y = (option.rect.height() - common.ROW_HEIGHT) / 2
                    __r = _r.marginsRemoved(
                        QtCore.QMargins(o, o + y, o, o + y))

                if not hover and not selected and not active:
                    painter.setOpacity(0.3)
                    _r.setRight(text_edge + (common.INDICATOR_WIDTH * 2))
                    if (_r.right() - 64) > rectangles[DataRect].left():
                        painter.drawRect(_r)

                painter.setOpacity(1.0)
                if not hover and not selected and not active:
                    _r.setLeft(_r.right() - 64)
                    if _r.left() > rectangles[DataRect].left():
                        pixmap = images.ImageCache.get_rsc_pixmap(
                            'gradient4', common.BACKGROUND, 64)
                        painter.drawPixmap(_r, pixmap, pixmap.rect().marginsRemoved(
                            QtCore.QMargins(1, 1, 1, 1)))

                painter.setOpacity(0.6)
                painter.drawRoundedRect(__r, o, o)

            o = 0.6
            if not hover:
                o += -0.2
            painter.setOpacity(o)

            for n, val in enumerate(subdir_rectangles):
                r, text = val
                if r.left() > text_edge:
                    break
                if r.right() > text_edge:
                    r.setRight(text_edge - (common.INDICATOR_WIDTH * 2))
                    text = metrics.elidedText(
                        text,
                        QtCore.Qt.ElideRight,
                        r.width()
                    )
                    if not text:
                        continue

                # Background
                color = common.SEPARATOR if n == 0 else QtGui.QColor(
                    55, 55, 55)
                color = common.ADD if r.contains(cursor_position) else color

                if n >= len(rootdirs):
                    continue
                _subpath = rootdirs[n]
                f_subpath = u'"/' + _subpath + u'/"'
                if filter_text:
                    if f_subpath.lower() in filter_text.lower():
                        color = common.ADD

                painter.setBrush(color)
                painter.drawRoundedRect(QtCore.QRectF(r), 2.0, 2.0)
                self._clickable_rectangles[index.row()].append((r, text))

                if filter_text:
                    if f_subpath.lower() in filter_text.lower():
                        color = common.TEXT_SELECTED
                x = r.center().x() - (metrics.width(text) / 2.0) + 1
                y = r.center().y() + (metrics.ascent() / 2.0) - 1

                color = color.lighter(250)
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.NoPen)
                path = QtGui.QPainterPath()
                path.addText(x, y, font, text)
                painter.drawPath(path)
            return r.right()

        def draw_description(font, metrics, left_limit, right_limit, offset):
            left_limit += common.INDICATOR_WIDTH * 2
            color = common.TEXT_SELECTED if selected else common.ADD

            large_mode = option.rect.height() >= (common.ROW_HEIGHT * 2)
            if large_mode:
                left_limit = rectangles[DataRect].left()
                right_limit = rectangles[DataRect].right() - common.MARGIN
                font = common.font_db.primary_font()
                metrics = QtGui.QFontMetricsF(font)

            text = index.data(common.DescriptionRole)
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideLeft,
                right_limit - left_limit
            )
            width = metrics.width(text)

            x = right_limit - width
            y = rectangles[DataRect].center().y() + offset
            if large_mode:
                y += metrics.lineSpacing()

            rect = QtCore.QRect()
            rect.setHeight(metrics.height())
            center = QtCore.QPoint(rectangles[DataRect].center().x(), y)
            rect.moveCenter(center)
            rect.setLeft(left_limit)
            rect.setRight(right_limit)
            self._clickable_rectangles[index.row()].insert(0, (rect, text))

            if rectangles[DataRect].contains(cursor_position):
                rect = QtCore.QRect(rectangles[DataRect])
                rect.setHeight(1.0)
                rect.moveTop(y)
                rect.setLeft(left_limit)
                rect.setRight(right_limit)

                painter.setOpacity(0.3)
                painter.setBrush(common.SEPARATOR)
                painter.drawRect(rect)
                painter.setOpacity(1.0)
                color = common.TEXT_SELECTED

            painter.setBrush(color)
            path = QtGui.QPainterPath()
            path.addText(x, y, font, text)
            painter.drawPath(path)

        draw_separator_line()

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        font = common.font_db.primary_font(point_size=SMALL_FONT_SIZE)
        metrics = QtGui.QFontMetricsF(font)
        it = self.get_text_segments(index).itervalues()
        offset = 0

        left = draw_segments(it, font, metrics, offset)
        left_limit = draw_subdirs(left - common.MARGIN)

        it = self.get_filedetail_text_segments(index).itervalues()
        offset = metrics.ascent()
        font = common.font_db.primary_font(point_size=SMALL_FONT_SIZE - 1)
        metrics = QtGui.QFontMetricsF(font)
        right_limit = draw_segments(it, font, metrics, offset)
        draw_description(font, metrics, left_limit, right_limit, offset)

    @paintmethod
    def paint_simple_name(self, *args):
        """Paints an the current file-names in a simpler form, with only the
        filename and the description visible.

        """
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.INDICATOR_WIDTH * 2))

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text_segments = self.get_text_segments(index)
        painter.setPen(common.TEXT)
        painter.setBrush(QtCore.Qt.NoBrush)
        font = common.font_db.primary_font(point_size=SMALL_FONT_SIZE + 0.5)
        metrics = QtGui.QFontMetricsF(font)

        offset = 0

        o = 0.9 if selected else 0.8
        o = 1.0 if hover else o
        painter.setOpacity(o)
        painter.setPen(QtCore.Qt.NoPen)

        for k in sorted(text_segments, reverse=True):
            text, color = text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.width(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.INDICATOR_WIDTH))
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    r.width() - 6
                )

            x = r.center().x() - (metrics.width(text) / 2.0) + 1
            y = r.center().y() + (metrics.ascent() / 2.0)

            painter.setBrush(color)
            path = QtGui.QPainterPath()
            path.addText(x, y, font, text)
            painter.drawPath(path)

        # Description
        if not index.data(common.DescriptionRole):
            return

        font = common.font_db.secondary_font(point_size=SMALL_FONT_SIZE + 1.0)
        metrics = QtGui.QFontMetricsF(font)

        description_rect = QtCore.QRect(name_rect)
        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(description_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )

        painter.setOpacity(1.0)
        color = common.TEXT if hover else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if selected else color

        text = index.data(common.DescriptionRole)
        width = metrics.width(text)

        r = QtCore.QRect(description_rect)
        r.setWidth(width)

        if r.left() > rect.right():
            return
        if r.right() > (rect.right()):
            r.setRight(rect.right())
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideRight,
                r.width() - 6
            )

        x = r.center().x() - (metrics.width(text) / 2.0) + 1
        y = r.center().y() + (metrics.ascent() / 2.0)

        painter.setBrush(color)
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        painter.drawPath(path)

    def get_simple_description_rectangle(self, rectangles, index):
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.INDICATOR_WIDTH * 2))

        font = common.font_db.primary_font()
        metrics = QtGui.QFontMetricsF(font)

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text_segments = self.get_text_segments(index)
        font = common.font_db.primary_font(point_size=SMALL_FONT_SIZE + 0.5)
        metrics = QtGui.QFontMetricsF(font)

        offset = 0
        for k in sorted(text_segments, reverse=True):
            text, _ = text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.width(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.INDICATOR_WIDTH))

        font = common.font_db.secondary_font(point_size=SMALL_FONT_SIZE + 1.0)
        metrics = QtGui.QFontMetricsF(font)

        description_rect = QtCore.QRect(name_rect)
        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(description_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )

        return description_rect

    def get_text_segments(self, index):
        """FilesWidget item `DisplayRole`.
        segments associated with custom colors. It is used to paint the
        FilesWidget items' extension, name, and sequence.

        Args:
            index (QModelIndex): The index currently being painted..

        Returns:
            dict: A dictionary of tuples. (unicode, QtGui.QColor)

        """
        if not index.isValid():
            return []
        s = index.data(QtCore.Qt.DisplayRole)
        if not s:
            return []
        s = regex_remove_version.sub(ur'\1\3', s)
        d = {}
        # Item is a collapsed sequence
        match = common.is_collapsed(s)
        if match:
            # Suffix + extension
            s = match.group(3).split(u'.')
            s = u'.'.join(s[:-1]).upper() + u'.' + s[-1].lower()
            d[len(d)] = (s, common.TEXT)

            # Frame-range without the "[]" characters
            s = match.group(2)
            s = regex_remove_bracket.sub(u'', s)
            if len(s) > 17:
                s = s[0:8] + u'...' + s[-8:]
            if index.data(common.FramesRole) > 1:
                d[len(d)] = (s, common.REMOVE)
            else:
                d[len(d)] = (s, common.TEXT)

            # Filename
            d[len(d)] = (
                match.group(1).upper(), common.TEXT_SELECTED)
            return d

        # Item is a non-collapsed sequence
        match = common.get_sequence(s)
        if match:
            # The extension and the suffix
            if match.group(4):
                s = match.group(3).upper() + u'.' + match.group(4).lower()
            else:
                s = match.group(3).upper()
            d[len(d)] = (s, common.TEXT_SELECTED)

            # Sequence
            d[len(d)] = (match.group(
                2).upper(), common.SECONDARY_TEXT)

            # Prefix
            d[len(d)] = (
                match.group(1).upper(), common.TEXT_SELECTED)
            return d

        # Items is not collapsed and it isn't a sequence either
        s = s.split(u'.')
        if len(s) > 1:
            s = u'.'.join(s[:-1]).upper() + u'.' + s[-1].lower()
        else:
            s = s[0].upper()
        d[len(d)] = (s, common.TEXT_SELECTED)
        return d

    def get_filedetail_text_segments(self, index):
        d = {}

        if not index.data(common.FileInfoLoaded):
            d[len(d)] = (u'...', common.SECONDARY_TEXT)
            return d

        text = index.data(common.FileDetailsRole)
        texts = text.split(u';')
        for n, text in enumerate(reversed(texts)):
            d[len(d)] = (text, common.SECONDARY_TEXT)
            if n == (len(texts) - 1) and not index.data(common.DescriptionRole):
                break
            d[len(d)] = (u'  |  ', common.SECONDARY_BACKGROUND)
        return d

    def get_subdir_rectangles(self, index, rectangles, metrics):
        """Returns the available mode rectangles for FileWidget index."""
        arr = []

        o = 2
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setHeight(metrics.height() + (o * 2))
        rect.moveCenter(rectangles[DataRect].center())
        rect.moveLeft(rectangles[DataRect].left())

        subdirs = index.data(common.ParentPathRole)
        if not subdirs:
            return []

        offset = 0
        for n, text in enumerate(subdirs[-1].upper().split(u'/')):
            if not text:
                continue
            if n >= self.maximum_subdirs:
                break
            if len(text) > 36:
                text = text[0:16] + u'...' + text[-17:]
            width = metrics.width(text)
            rect.setWidth(width)
            rect = rect.marginsAdded(QtCore.QMargins(o * 3, 0, o * 3, 0))

            if rect.right() > rectangles[DataRect].right():
                rect.setRight(rectangles[DataRect].right())
            if rect.left() < rectangles[DataRect].left():
                rect.setLeft(rectangles[DataRect].left())

            arr.append((QtCore.QRect(rect), text))
            rect.moveLeft(rect.left() + rect.width() + (o * 5))
        return arr

    @paintmethod
    def paint_drag_source(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if index != self.parent().drag_source_index:
            return
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(
            option.rect.marginsRemoved(
                QtCore.QMargins(
                    common.INDICATOR_WIDTH, 0,
                    0, common.ROW_SEPARATOR)
            )
        )

        painter.setPen(common.BACKGROUND)
        font = common.font_db.secondary_font()
        painter.setFont(font)

        text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the first file    |    "Drag+Shift+Alt" grabs the parent folder'
        painter.drawText(
            option.rect.marginsRemoved(QtCore.QMargins(18, 0, 18, 0)),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
            text,
            boundingRect=option.rect,
        )

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().ROW_SIZE