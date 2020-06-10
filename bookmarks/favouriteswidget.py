# -*- coding: utf-8 -*-
"""Classes responsible for viewing and editing items marked as favourites.

"""
from PySide2 import QtWidgets, QtCore, QtGui

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.threads as threads
import bookmarks.settings as settings

from bookmarks.basecontextmenu import BaseContextMenu
from bookmarks.delegate import FilesWidgetDelegate
from bookmarks.fileswidget import FilesModel
from bookmarks.fileswidget import FilesWidget
import _scandir as _scandir


class FavouritesWidgetContextMenu(BaseContextMenu):
    def __init__(self, index, parent=None):
        super(FavouritesWidgetContextMenu, self).__init__(index, parent=parent)
        self.index = index

        self.add_control_favourites_menu()

        if index.isValid():
            self.add_remove_favourite_menu()
            self.add_separator()
            #
            self.add_reveal_item_menu()
            self.add_copy_menu()
        #
        self.add_separator()
        #
        self.add_sort_menu()
        self.add_collapse_sequence_menu()
        #
        self.add_separator()
        #
        self.add_refresh_menu()


class FavouritesModel(FilesModel):
    """The model responsible for displaying the saved favourites."""

    queue_type = threads.FavouriteInfoQueue
    thumbnail_queue_type = threads.FavouriteThumbnailQueue

    def __init__(self, parent=None):
        super(FavouritesModel, self).__init__(parent=parent)
        common.create_temp_dir()

    @property
    def parent_path(self):
        return common.get_favourite_parent_paths() + (u'.',)

    def _entry_iterator(self, path):
        """We're using the saved keys to find and return the DirEntries
        corresponding to the saved favourites.

        """
        favourites = settings.local_settings.favourites()

        d = []

        for k in favourites:
            file_info = QtCore.QFileInfo(k)
            _path = file_info.path()
            
            if not QtCore.QFileInfo(_path).exists():
                continue

            for entry in _scandir.scandir(_path):
                path = entry.path.replace(u'\\', u'/').lower()
                if path == k:
                    d.append(entry)
                    continue
                _k = common.proxy_path(path)
                if k.lower() == _k.lower():
                    d.append(entry)

        for entry in d:
            yield entry

    def task_folder(self):
        return u'.'


class DropIndicatorWidget(QtWidgets.QWidget):
    """Widgets responsible for drawing an overlay."""

    def __init__(self, parent=None):
        super(DropIndicatorWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """Paints the indicator area."""
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(common.INDICATOR_WIDTH())
        painter.setPen(pen)
        painter.setBrush(common.FAVOURITE)
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            self.rect(),
            u'Drop to add bookmark',
            QtCore.Qt.AlignCenter,
            common.FAVOURITE
        )
        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super(DropIndicatorWidget, self).show()


class FavouritesWidget(FilesWidget):
    """The widget responsible for showing all the items marked as favourites."""
    SourceModel = FavouritesModel
    Delegate = FilesWidgetDelegate
    ContextMenu = FavouritesWidgetContextMenu

    def __init__(self, parent=None):
        super(FavouritesWidget, self).__init__(parent=parent)
        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()
        self.setWindowTitle(u'Favourites')
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def set_model(self, *args):
        super(FavouritesWidget, self).set_model(*args)
        self.favouritesChanged.connect(
            self.model().sourceModel().modelDataResetRequested)
        self.favouritesChanged.connect(
            lambda: log.debug('favouritesChanged -> modelDataResetRequested', self))

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return True
    #

    def inline_icons_count(self):
        return 3

    def toggle_item_flag(self, index, flag, state=None):
        super(FavouritesWidget, self).toggle_item_flag(
            index, common.MarkedAsFavourite, state=False)
        # super(FavouritesWidget, self).toggle_item_flag(
        #     index, common.MarkedAsArchived, state=True)

    def dragEnterEvent(self, event):
        if event.source() == self:
            return

        if event.mimeData().hasUrls():
            self.indicatorwidget.show()
            return event.accept()
        self.indicatorwidget.hide()

    def dragLeaveEvent(self, event):
        self.indicatorwidget.hide()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Event responsible for adding the dropped file to the favourites."""
        self.indicatorwidget.hide()

        if event.source() == self:
            return  # Won't allow dropping an item from itself

        mime = event.mimeData()
        if not mime.hasUrls():
            return

        event.accept()
        favourites = settings.local_settings.favourites()

        for url in mime.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())
            path = file_info.filePath().lower()

            if file_info.suffix().lower() == u'favourites':
                common.import_favourites(source=path)
            else:
                k = common.proxy_path(path).lower()
            favourites.append(k)
        settings.local_settings.setValue(
            u'favourites', sorted(list(set(favourites))))
        self.favouritesChanged.emit()

    def showEvent(self, event):
        super(FavouritesWidget, self).showEvent(event)
        self.model().sourceModel().modelDataResetRequested.emit()
