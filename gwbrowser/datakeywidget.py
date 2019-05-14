# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330, E1120

"""Contains the popup-widget associated with the FilesWidget tab. It is responsible
for letting the user pick a folder to get files from.

Data keys are subfolders inside the root of the asset folder. They are usually are
associated with a task or data-type eg, ``render``, ``comp``, ``textures``.

To describe the function of each folder we can define the folder and a description
in the common module.

"""

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common

from gwbrowser.delegate import paintmethod
from gwbrowser.baselistwidget import BaseModel
from gwbrowser.delegate import BaseDelegate
from gwbrowser.imagecache import ImageCache
from gwbrowser.threads import BaseThread
from gwbrowser.threads import BaseWorker
from gwbrowser.threads import Unique
from gwbrowser.basecontextmenu import BaseContextMenu


class DataKeyContextMenu(BaseContextMenu):
    """The context menu associated with the DataKeyView."""
    def __init__(self, index, parent=None):
        super(DataKeyContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()


class DataKeyWorker(BaseWorker):
    """Note: This thread worker is a duplicate implementation of the FileInfoWorker."""
    queue = Unique(999999)

    @QtCore.Slot(QtCore.QModelIndex)
    @classmethod
    def process_index(cls, index):
        """The actual processing happens here."""
        if not index.isValid():
            return

        if not index.data(QtCore.Qt.StatusTipRole):
            return

        count = 0
        for _, _, fileentries in common.walk(index.data(QtCore.Qt.StatusTipRole)):
            for _ in fileentries:
                count += 1
                if count > 999:
                    break

        # The underlying data can change whilst the calculating
        try:
            data = index.model().model_data()
            data[index.row()][common.TodoCountRole] = count
            index.model().dataChanged.emit(index, index)
        except Exception:
            return


class DataKeyThread(BaseThread):
    Worker = DataKeyWorker


class DataKeyViewDelegate(BaseDelegate):
    """The delegate used to paint the available subfolders inside the asset folder."""

    def __init__(self, parent=None):
        super(DataKeyViewDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        painter.setOpacity(0.5)
        self.paint_thumbnail(*args)
        painter.setOpacity(1)
        self.paint_name(*args)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, selected, _, _, _, _ = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - 1)
        rect.moveCenter(center)

        background = QtGui.QColor(common.BACKGROUND)
        color = common.BACKGROUND_SELECTED if selected or hover else background
        painter.setBrush(color)
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        painter, option, index, selected, _, _, _, _ = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.TEXT_SELECTED if selected else color

        font = QtGui.QFont(common.PrimaryFont)
        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH
            + rect.height()
        )
        rect.setRight(rect.right() - common.MARGIN)

        text = index.data(QtCore.Qt.DisplayRole).upper()
        width = 0
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        items = []
        # Adding an indicator for the number of items in the folder
        if index.data(common.TodoCountRole):
            if index.data(common.TodoCountRole) >= 999:
                text = u'999+ items'
            else:
                text = u'{} items'.format(
                    index.data(common.TodoCountRole))
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if hover else color
            items.append((text, color))

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.TEXT_SELECTED if selected else common.SECONDARY_TEXT
            color = common.TEXT_SELECTED if hover else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for text, color in items:
            width = common.draw_aliased_text(
                painter, common.SecondaryFont, rect, u'  |  ', QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, common.SEPARATOR)
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter, common.SecondaryFont, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, int(common.BOOKMARK_ROW_HEIGHT / 1.5))


class DataKeyView(QtWidgets.QListView):
    """The view responsonsible for displaying the available data-keys."""

    def __init__(self, parent=None, altparent=None):
        super(DataKeyView, self).__init__(parent=parent)
        self.altparent = altparent
        self._context_menu_active = False
        self.context_menu_cls = DataKeyContextMenu

        common.set_custom_stylesheet(self)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.clicked.connect(self.activated, type=QtCore.Qt.QueuedConnection)
        self.clicked.connect(self.hide, type=QtCore.Qt.QueuedConnection)
        self.clicked.connect(self.altparent.signal_dispatcher,
                             type=QtCore.Qt.QueuedConnection)
        self.parent().resized.connect(self.setGeometry)

        self.setModel(DataKeyModel())
        self.setItemDelegate(DataKeyViewDelegate(parent=self))
        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        """We're stopping events propagating back to the parent."""

    def hideEvent(self, event):
        """DataKeyView hide event."""
        self.parent().verticalScrollBar().setHidden(False)
        self.parent().removeEventFilter(self)
        self.altparent._filesbutton.repaint()

    def showEvent(self, event):
        """DataKeyView show event."""
        self.parent().verticalScrollBar().setHidden(True)
        self.parent().installEventFilter(self)

    def eventFilter(self, widget, event):
        if widget == self.parent():
            return True
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.75)
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            return
        super(DataKeyView, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        width = self.viewport().geometry().width()

        widget = self.context_menu_cls(index, parent=self)
        rect = self.visualRect(index)
        offset = self.visualRect(index).height() - common.INDICATOR_WIDTH
        widget.move(
            self.viewport().mapToGlobal(rect.bottomLeft()).x() + offset,
            self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
        )

        widget.setFixedWidth(width - offset)
        common.move_widget_to_available_geo(widget)

        self._context_menu_active = True
        widget.exec_()
        self._context_menu_active = False


class DataKeyModel(BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots."""

    def __init__(self, parent=None):
        super(DataKeyModel, self).__init__(parent=parent)
        self._bookmark = None

        # Note: the asset is stored as the `_active_item`
        self._datakey = None
        self.modelDataResetRequested.connect(self.__resetdata__)

        self.threads = {}
        for n in xrange(common.LTHREAD_COUNT):
            self.threads[n] = DataKeyThread()
            self.threads[n].start()

    def data_key(self):
        return u'default'

    def data_type(self):
        return common.FileItem

    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        # Empties the thread's queue
        DataKeyWorker.reset_queue()

        self._data[self.data_key()] = {
            common.FileItem: {}, common.SequenceItem: {}}

        rowsize = QtCore.QSize(
            common.WIDTH, int(common.BOOKMARK_ROW_HEIGHT / 2))

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()

        if not self._parent_item:
            self.endResetModel()
            return

        # Thumbnail image
        default_thumbnail = ImageCache.instance().get_rsc_pixmap(
            u'folder_sm',
            common.SECONDARY_TEXT,
            rowsize)
        default_thumbnail = default_thumbnail.toImage()

        parent_path = u'/'.join(self._parent_item)
        indexes = []
        entries = sorted(
            ([f for f in gwscandir.scandir(parent_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name in common.ASSET_FOLDERS:
                description = common.ASSET_FOLDERS[entry.name]
            else:
                description = common.ASSET_FOLDERS[u'misc']

            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            idx = len(data)
            data[idx] = {
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace(u'\\', u'/'),
                QtCore.Qt.ToolTipRole: description,
                QtCore.Qt.SizeHintRole: rowsize,
                #
                common.DefaultThumbnailRole: default_thumbnail,
                common.DefaultThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                common.ThumbnailRole: default_thumbnail,
                common.ThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                #
                common.FlagsRole: flags,
                common.ParentRole: None,
                #
                common.FileInfoLoaded: False,
                common.FileThumbnailLoaded: True,
                common.TodoCountRole: 0,
            }
            indexes.append(idx)

        self.endResetModel()
        DataKeyWorker.add_to_queue([self.index(f, 0) for f in indexes])

    @QtCore.Slot(QtCore.QModelIndex)
    def set_bookmark(self, index):
        """Stores the currently active bookmark."""
        if not index.isValid():
            self._bookmark = None
            return

        self._bookmark = index.data(common.ParentRole)

    @QtCore.Slot(unicode)
    def set_data_key(self, key):
        """Stores the currently active data key."""
        self._datakey = key

    @QtCore.Slot(int)
    def set_data_type(self, datatype):
        """Stores the currently active data type."""
        self._datatype = datatype