# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""Module defines a ListWidget used to represent the assets found in the root
of the `server/job/assets` folder.

The asset collector expects a asset to contain an identifier file,
in the case of the default implementation, a ``*.mel`` file in the root of the asset folder.
If the identifier file is not found the folder will be ignored!

Assets are based on maya's project structure and ``Browser`` expects a
a ``renders``, ``textures``, ``exports`` and a ``scenes`` folder to be present.

The actual name of these folders can be customized in the ``common.py`` module.

"""

from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.baselistwidget import BaseContextMenu
from mayabrowser.baselistwidget import BaseListWidget
import mayabrowser.editors as editors

import mayabrowser.settings as configparser
from mayabrowser.settings import local_settings
from mayabrowser.settings import AssetSettings
from mayabrowser.collector import AssetCollector
from mayabrowser.delegate import AssetWidgetDelegate


class AssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the AssetWidget."""

    def __init__(self, index, parent=None):
        super(AssetWidgetContextMenu, self).__init__(index, parent=parent)
        if index.isValid():
            self.add_thumbnail_menu()
        self.add_refresh_menu()


class AssetWidget(BaseListWidget):
    """Custom QListWidget for displaying the found assets inside the set ``path``.

    Parameters
    ----------
    bookmark_path : tuple
        A `Bookmark` made up of the server/job/root folders.

    """

    def __init__(self, bookmark, parent=None):
        self._bookmark = bookmark

        super(AssetWidget, self).__init__(parent=parent)

        self.setWindowTitle('Assets')
        self.setItemDelegate(AssetWidgetDelegate(parent=self))
        self._context_menu_cls = AssetWidgetContextMenu
        # Select the active item
        self.setCurrentItem(self.active_index())

    def set_bookmark(self, bookmark):
        self._bookmark = bookmark
        self.refresh()

    def activate_current_index(self):
        """Sets the current item item as ``active`` and
        emits the ``activeAssetChanged`` and ``activeFileChanged`` signals.

        """
        item = super(AssetWidget, self).activate_current_index()
        if not item:
            return

        file_info = QtCore.QFileInfo(item.data(QtCore.Qt.StatusTipRole))
        local_settings.setValue('activepath/asset', file_info.completeBaseName())
        self.activeAssetChanged.emit((
            self._bookmark[0],
            self._bookmark[1],
            self._bookmark[2],
            file_info.completeBaseName()
        ))

        local_settings.setValue('activepath/file', None)
        self.activeFileChanged.emit(None)

    def add_items(self):
        """Retrieves the assets found by the AssetCollector and adds them as
        QListWidgetItems.

        Note:
            The method adds the assets' parent folder to the QFileSystemWatcher to monitor
            file changes. Any directory change should trigger a refresh. This might
            have some performance implications. Needs testing!

        """
        for path in self.fileSystemWatcher.directories():
            self.fileSystemWatcher.removePath(path)
        self.clear()

        # Creating the folder for the settings if needed
        config_dir_path = '{}/.browser/'.format(
            '/'.join(self._bookmark))
        config_dir_path = QtCore.QFileInfo(config_dir_path)
        if not config_dir_path.exists():
            QtCore.QDir().mkpath(config_dir_path.filePath())


        server, job, root = self._bookmark
        if not any((server, job, root)):
            return

        path = '/'.join((server, job, root))

        self.fileSystemWatcher.addPath(path)
        collector = AssetCollector(path, parent=self)
        self.collector_count = collector.count
        items = collector.get_items(
            key=self.get_item_sort_order(),
            reverse=self.get_item_sort_order(),
            path_filter=self.get_item_filter()
        )

        for file_info in items:
            item = QtWidgets.QListWidgetItem()
            settings = AssetSettings(path, file_info.filePath())

            # Qt Roles
            item.setData(QtCore.Qt.DisplayRole, file_info.baseName())
            item.setData(QtCore.Qt.EditRole, item.data(QtCore.Qt.DisplayRole))
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())

            tooltip = u'{}\n\n'.format(file_info.baseName().upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n\n'.format(job.upper())
            tooltip += u'{}'.format(file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, tooltip)
            item.setData(
                QtCore.Qt.SizeHintRole,
                QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT))

            # Custom roles
            item.setData(common.ParentRole, (server, job, root))
            item.setData(common.DescriptionRole, settings.value(
                'config/description'))

            # Todos
            todos = settings.value('config/todos')
            if todos:
                count = len([k for k in todos if not todos[k]
                             ['checked'] and todos[k]['text']])
            else:
                count = 0
            item.setData(common.TodoCountRole, count)
            item.setData(common.FileDetailsRole, file_info.size())
            item.setData(common.FileModeRole, None)

            # Flags
            if settings.value('config/archived'):
                item.setFlags(item.flags() | configparser.MarkedAsArchived)
            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)
            # Active
            if file_info.baseName() == local_settings.value('activepath/asset'):
                item.setFlags(item.flags() | configparser.MarkedAsActive)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

    def show_todos(self):
        """Shows the ``TodoEditorWidget`` for the current item."""
        from mayabrowser.todoEditor import TodoEditorWidget
        index = self.currentIndex()
        widget = TodoEditorWidget(index, parent=self)
        pos = self.mapToGlobal(self.rect().topLeft())
        widget.move(pos.x() + common.MARGIN, pos.y() + common.MARGIN)
        widget.setMinimumWidth(640)
        widget.setMinimumHeight(800)
        # widget.resize(self.width(), self.height())
        common.move_widget_to_available_geo(widget)
        widget.show()

    def mousePressEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mousePressEvent(event)

        for n in xrange(2):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)
            # Beginning multi-toggle operation
            if bg_rect.contains(event.pos()):
                self.multi_toggle_pos = event.pos()
                if n == 0:
                    self.multi_toggle_state = not index.flags() & configparser.MarkedAsFavourite
                elif n == 1:
                    self.multi_toggle_state = not index.flags() & configparser.MarkedAsArchived
                self.multi_toggle_idx = n
                return True

        return super(AssetWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """In-line buttons are triggered here."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        idx = index.row()

        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mouseReleaseEvent(event)

        # Cheking the button
        if idx not in self.multi_toggle_items:
            for n in xrange(4):
                _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                    rect, common.INLINE_ICON_SIZE, n)
                if bg_rect.contains(event.pos()):
                    if n == 0:
                        self.toggle_favourite(item=self.itemFromIndex(index))
                        break
                    elif n == 1:
                        self.toggle_archived(item=self.itemFromIndex(index))
                        break
                    elif n == 2:
                        common.reveal(index.data(QtCore.Qt.StatusTipRole))
                    elif n == 3:
                        self.show_todos()

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

        super(AssetWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Multi-toggle is handled here."""
        if self.viewport().width() < 360.0:
            return super(AssetWidget, self).mouseMoveEvent(event)

        if self.multi_toggle_pos is None:
            super(AssetWidget, self).mouseMoveEvent(event)
            return

        app_ = QtWidgets.QApplication.instance()
        if (event.pos() - self.multi_toggle_pos).manhattanLength() < app_.startDragDistance():
            super(AssetWidget, self).mouseMoveEvent(event)
            return

        pos = event.pos()
        pos.setX(0)
        index = self.indexAt(pos)
        initial_index = self.indexAt(self.multi_toggle_pos)
        idx = index.row()

        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived

        # Filter the current item
        if index == self.multi_toggle_item:
            return

        self.multi_toggle_item = index

        # Before toggling the item, we're saving it's state

        if idx not in self.multi_toggle_items:
            if self.multi_toggle_idx == 0:  # Favourite button
                # A state
                self.multi_toggle_items[idx] = favourite
                # Apply first state
                self.toggle_favourite(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_state
                )
            if self.multi_toggle_idx == 1:  # Archived button
                # A state
                self.multi_toggle_items[idx] = archived
                # Apply first state
                self.toggle_archived(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_state
                )
        else:  # Reset state
            if index == initial_index:
                return
            if self.multi_toggle_idx == 0:  # Favourite button
                self.toggle_favourite(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_items.pop(idx)
                )
            elif self.multi_toggle_idx == 1:  # Favourite button
                self.toggle_archived(
                    item=self.itemFromIndex(index),
                    state=self.multi_toggle_items.pop(idx)
                )

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect, _, metrics = AssetWidgetDelegate.get_text_area(
            rect, common.PRIMARY_FONT)
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect, _, metrics = AssetWidgetDelegate.get_text_area(
            rect, common.SECONDARY_FONT)
        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        if description_rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            editors.ThumbnailEditor(index)
            return
        else:
            self.activate_current_index()
            return


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    bookmark = (local_settings.value('activepath/server'),
                local_settings.value('activepath/job'),
                local_settings.value('activepath/root')
                )
    app.w = AssetWidget(bookmark)
    app.w.show()
    app.exec_()
