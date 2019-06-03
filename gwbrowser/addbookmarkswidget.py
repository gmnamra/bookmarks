# -*- coding: utf-8 -*-
"""This module defines the ``AddBookmarksWidget`` and the supplemetary widgets
needed to select a **server**, **job** and **root** folder.

These three choices together (saved as a tuple) make up a **bookmark**.
The final path will, unsurprisingly, be a composite of the above, like so:
*server/job/root*. Eg.: **//network_server/my_job/shots.**

The actual bookmarks are stored, on Windows, in the *Registry* and are unique
to each users.

"""

import sys
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.gwscandir as gwscandir
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.delegate import BaseDelegate
from gwbrowser.delegate import paintmethod
from gwbrowser.settings import local_settings, Active
from gwbrowser.editors import ClickableLabel


custom_string = u'Select custom folder...'


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class for ``AddBookmarksWidget`` buttons."""

    def __init__(self, text, parent=None):
        super(PaintedButton, self).__init__(text, parent=parent)

    def paintEvent(self, event):
        """Paint event for smooth font display."""
        painter = QtGui.QPainter()
        painter.begin(self)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        color = common.TEXT if self.isEnabled() else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if hover else color

        bg_color = common.SECONDARY_TEXT if self.isEnabled() else QtGui.QColor(0, 0, 0, 20)
        painter.setBrush(bg_color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 2, 2)

        rect = QtCore.QRect(self.rect())
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH)
        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            self.text(),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            color
        )

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """Custom QLabe class for ``AddBookmarksWidget`` buttons."""

    def __init__(self, text, size=common.MEDIUM_FONT_SIZE, parent=None):
        super(PaintedLabel, self).__init__(text, parent=parent)
        self._font = QtGui.QFont(common.PrimaryFont)
        self._font.setPointSize(size)
        metrics = QtGui.QFontMetrics(self._font)
        self.setFixedHeight(metrics.height())
        self.setFixedWidth(metrics.width(text) + 2)

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        painter = QtGui.QPainter()
        painter.begin(self)
        color = common.TEXT
        common.draw_aliased_text(
            painter, self._font, self.rect(), self.text(), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        painter.end()


class ComboboxContextMenu(BaseContextMenu):
    """Small context menu to reveal the current choice in the explorer."""

    def __init__(self, index, parent=None):
        super(ComboboxContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()  # pylint: disable=E1120


class ComboboxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboboxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        self.paint_selection_indicator(*args)
        self.paint_name(*args)

    @paintmethod
    def paint_background(self, *args):
        painter, option, index, selected, _, _, _, _, _ = args

        if index.flags() == QtCore.Qt.NoItemFlags:
            return

        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - common.ROW_SEPARATOR)
        rect.moveCenter(center)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(option.rect)

        if selected:
            painter.setBrush(common.BACKGROUND_SELECTED)
        else:
            painter.setBrush(common.BACKGROUND)

        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints the DisplayRole of the items."""
        painter, option, index, _, _, _, _, _, hover = args
        disabled = index.flags() == QtCore.Qt.NoItemFlags

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        text = index.data(QtCore.Qt.DisplayRole)
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.SECONDARY_TEXT if disabled else color

        if text == custom_string:
            _rect = QtCore.QRect(option.rect)
            _rect.setTop(_rect.bottom() - 1)
            painter.setBrush(common.SEPARATOR)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(_rect)
        else:
            text = text.upper()

        width = common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            text,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            color
        )
        if index.data(common.DescriptionRole):
            rect.setLeft(rect.left() + width + common.INDICATOR_WIDTH)
            width = common.draw_aliased_text(
                painter,
                common.SecondaryFont,
                rect,
                u': {}'.format(index.data(common.DescriptionRole)),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                common.SECONDARY_TEXT
            )

    def sizeHint(self, option, index):
        """Returns the size of the combobox items."""
        return QtCore.QSize(
            self.parent().width(), common.ROW_HEIGHT * 0.66)


class ComboboxView(QtWidgets.QListWidget):

    def __init__(self, parent=None):
        super(ComboboxView, self).__init__(parent=parent)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.setItemDelegate(ComboboxItemDelegate(self))
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.itemClicked.connect(self.hide)
        self.itemActivated.connect(self.hide)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()


class ComboboxButton(ClickableLabel):
    """Combobox responsible for picking a bookmark segment."""

    def __init__(self, itemtype, parent=None):
        super(ComboboxButton, self).__init__(parent=parent)
        self.type = itemtype
        self.context_menu_cls = ComboboxContextMenu
        self._view = ComboboxView(parent=self)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setFixedWidth(300)
        self.setMouseTracking(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)

        self.clicked.connect(self.show_view)

    @QtCore.Slot()
    def show_view(self):
        """Shows the list view."""
        self._view.show()

        x = self.window().rect().topLeft()
        x = self.window().mapToGlobal(x)

        pos = self.rect().topLeft()
        pos = self.mapToGlobal(pos)

        self._view.move(pos)
        self._view.setFixedWidth(
            self.window().width() - (pos.x() - x.x()) - common.MARGIN)
        self._view.setFocus(QtCore.Qt.PopupFocusReason)

    def view(self):
        """The view associated with the widget."""
        return self._view

    def contextMenuEvent(self, event):
        """Custom context menu event for the combobox widget."""
        index = self.view().item(self.view().currentRow())
        if not index:
            return
        if index.data(QtCore.Qt.DisplayRole) == custom_string:
            return

        widget = self.context_menu_cls(index, parent=self)

        rect = self.rect()
        widget.move(
            self.mapToGlobal(rect.bottomLeft()).x(),
            self.mapToGlobal(rect.bottomLeft()).y(),
        )

        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def paintEvent(self, event):
        """The ``ComboboxButton``'s paint event."""
        if event.rect() != self.rect():
            return

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        index = self.view().selectionModel().currentIndex()
        if not self.view().selectionModel().hasSelection():
            text = u'Click to select {}'.format(self.type)
            color = common.TEXT
        else:
            text = index.data(QtCore.Qt.DisplayRole)
            text = text.upper() if text else u'Click to select {}'.format(self.type)
            color = common.TEXT_SELECTED
        if hover:
            color = common.TEXT_SELECTED

        painter = QtGui.QPainter()
        painter.begin(self)

        rect = QtCore.QRect(self.rect())

        common.draw_aliased_text(
            painter,
            common.PrimaryFont,
            rect,
            text,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            color
        )

        painter.end()

    @QtCore.Slot(int)
    def pick_custom(self, index):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        if not index.isValid():
            return
        if not index.row() == 0:
            return

        parent = self.window()

        index = parent.pick_server_widget.view().selectionModel().currentIndex()
        server = index.data(QtCore.Qt.StatusTipRole)

        index = parent.pick_job_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        job = index.data(QtCore.Qt.DisplayRole)

        if not all((server, job)):
            return

        path = u'{}/{}'.format(server, job)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        res = dialog.getExistingDirectory(
            self,
            u'Pick the location of the assets folder',
            file_info.filePath(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks |
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons |
            QtWidgets.QFileDialog.HideNameFilterDetails |
            QtWidgets.QFileDialog.ReadOnly
        )

        # Didn't make a valid selection
        if not res:
            return

        if path.lower() not in res.lower():
            return

        index = self.view().model().index(0, 0)

        root = res.lower().replace(path.lower(), u'').strip(u'/')
        self.view().model().setData(
            index,
            root,
            role=QtCore.Qt.DisplayRole)

        self.view().model().setData(
            index,
            res,
            role=QtCore.Qt.StatusTipRole)

        parent.validate()


class AddJobWidgetButton(ClickableLabel):
    """The button responsible for showing the ``AddJobWidget``."""

    def __init__(self, parent=None):
        super(AddJobWidgetButton, self).__init__(parent=parent)
        self.clicked.connect(self.show_add_jobs_widget)
        pixmap = ImageCache.get_rsc_pixmap(
            u'todo_add', common.FAVOURITE, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

    @QtCore.Slot()
    def show_add_jobs_widget(self):
        """Slot connected to the clicked signal."""
        parent = self.window().pick_server_widget
        index = parent.view().selectionModel().currentIndex()
        if not index.isValid():
            return

        from gwbrowser.addjobwidget import AddJobWidget
        widget = AddJobWidget(index.data(
            QtCore.Qt.StatusTipRole), parent=self.parent())
        widget.exec_()

        w = self.parent().window()

        if widget.last_asset_added:
            sindex = w.pick_server_widget.view().selectionModel().currentIndex()
            w.add_jobs_from_server_folder(sindex)
            w.validate()
            last_asset_added = u'{}/{}'.format(
                sindex.data(QtCore.Qt.StatusTipRole),
                widget.last_asset_added
            )
            for n in xrange(w.pick_job_widget.view().model().rowCount()):
                index = w.pick_job_widget.view().model().index(n, 0)
                if index.data(QtCore.Qt.StatusTipRole).lower() == last_asset_added.lower():
                    w.pick_job_widget.view().selectionModel().setCurrentIndex(
                        index, QtCore.QItemSelectionModel.ClearAndSelect)
                    return


class AddBookmarksWidget(QtWidgets.QDialog):
    """Defines the widget used add a bookmark.

    A bookmark is made up of the *server*, *job* and *root* folders.
    All sub-widgets needed to make the choices are laid-out in this
    widget.

    """

    def __init__(self, parent=None):
        super(AddBookmarksWidget, self).__init__(parent=parent)
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None
        self.new_key = None

        self.setWindowTitle(u'Add bookmark')
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()
        self.initialize()

    def initialize(self):
        """Populates the comboboxes and selects the currently active items (if there's any)."""
        self.add_servers_from_config()
        self.select_saved_item(
            None, key=u'server', combobox=self.pick_server_widget)

        self.add_jobs_from_server_folder(
            self.pick_server_widget.view().selectionModel().currentIndex())
        self.select_saved_item(None, key=u'job', combobox=self.pick_job_widget)

        self.add_root_folders(
            self.pick_job_widget.view().selectionModel().currentIndex())
        self.select_saved_item(
            None, key=u'root', combobox=self.pick_root_widget)

        self.validate()
        self.adjustSize()

    def _createUI(self):
        """Creates the AddBookmarksWidget's ui and layout."""
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN,
            common.MARGIN,
            common.MARGIN,
            common.MARGIN
        )

        # top label
        label = PaintedLabel(u'Add bookmark', size=common.LARGE_FONT_SIZE)
        self.layout().addWidget(label, 0)

        self.pathsettings = QtWidgets.QWidget(parent=self)
        self.pathsettings.setObjectName(u'GWBrowserPathsettingsWidget')
        self.pathsettings.setMinimumWidth(300)
        QtWidgets.QVBoxLayout(self.pathsettings)
        self.pathsettings.layout().setContentsMargins(0, 0, 0, 0)
        self.pathsettings.layout().setSpacing(common.INDICATOR_WIDTH)
        self.pathsettings.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.pathsettings.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.pick_server_widget = ComboboxButton(u'server', parent=self)
        self.add_job_widget = AddJobWidgetButton(parent=self)
        self.pick_job_widget = ComboboxButton(u'job', parent=self)
        self.pick_root_widget = ComboboxButton(
            u'bookmark folder', parent=self)

        row = QtWidgets.QWidget(parent=self)
        row.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        row.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QHBoxLayout(row)

        self.ok_button = PaintedButton(u'Add bookmark')
        self.close_button = PaintedButton(u'Close')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.close_button, 1)

        # Adding it all together
        main_widget = QtWidgets.QWidget()
        main_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        main_widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        QtWidgets.QHBoxLayout(main_widget)

        self.label = QtWidgets.QLabel()
        label.setAlignment(QtCore.Qt.AlignJustify)
        label.setWordWrap(True)
        pixmap = ImageCache.get_rsc_pixmap(
            u'bookmark', common.SECONDARY_TEXT, 128)
        self.label.setPixmap(pixmap)

        main_widget.layout().addWidget(self.label)
        main_widget.layout().addSpacing(common.MARGIN)
        main_widget.layout().addWidget(self.pathsettings, 1)
        self.layout().addWidget(main_widget)

        # Server
        self.layout().addWidget(row)
        label = PaintedLabel(u'Server')
        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_server_widget)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Job
        label = PaintedLabel(u'Job')
        self.pathsettings.layout().addWidget(label)
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addWidget(self.pick_job_widget, 1)
        row.layout().addWidget(self.add_job_widget, 0)

        self.pathsettings.layout().addWidget(row)
        self.pathsettings.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Bookmarks folder
        label = PaintedLabel(u'Bookmark folder')
        self.pathsettings.layout().addWidget(label)
        self.pathsettings.layout().addWidget(self.pick_root_widget)

        # Bookmarks description
        text = u'<p style="font-size: {s}pt; color: rgba({},{},{},{}); font-family: "{f}"">'
        text += 'Folders containing assets are listed above. '
        text += 'To pick a custom folder use the "{c}" button.</p>'
        text = text.format(
            *common.TEXT.getRgb(),
            s=common.psize(common.SMALL_FONT_SIZE),
            f=common.SecondaryFont.family(),
            c=custom_string
        )
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignJustify)
        self.pathsettings.layout().addWidget(label)

    def _connectSignals(self):
        self.pick_server_widget.view().itemClicked.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemActivated.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemClicked.connect(
            self.pick_server_widget.repaint)
        self.pick_server_widget.view().itemActivated.connect(
            self.pick_server_widget.repaint)

        self.pick_server_widget.view().itemClicked.connect(
            self.add_jobs_from_server_folder)
        self.pick_server_widget.view().itemActivated.connect(
            self.add_jobs_from_server_folder)

        self.pick_server_widget.view().itemClicked.connect(
            functools.partial(self.select_saved_item, key='job', combobox=self.pick_job_widget))
        self.pick_server_widget.view().itemActivated.connect(
            functools.partial(self.select_saved_item, key='job', combobox=self.pick_job_widget))

        self.pick_server_widget.view().itemClicked.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))
        self.pick_server_widget.view().itemActivated.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))

        self.pick_job_widget.view().itemClicked.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))
        self.pick_job_widget.view().itemActivated.connect(
            lambda x: self.add_root_folders(
                self.pick_job_widget.view().selectionModel().currentIndex()))

        self.pick_job_widget.view().itemClicked.connect(
            functools.partial(self.select_saved_item, key='root', combobox=self.pick_root_widget))
        self.pick_job_widget.view().itemActivated.connect(
            functools.partial(self.select_saved_item, key='root', combobox=self.pick_root_widget))

        self.pick_server_widget.view().itemClicked.connect(self.validate)
        self.pick_server_widget.view().itemActivated.connect(self.validate)
        self.pick_job_widget.view().itemClicked.connect(self.validate)
        self.pick_job_widget.view().itemActivated.connect(self.validate)
        self.pick_root_widget.view().itemClicked.connect(self.validate)
        self.pick_root_widget.view().itemActivated.connect(self.validate)

        self.pick_root_widget.view().itemClicked.connect(
            lambda x: self.pick_root_widget.pick_custom(self.pick_root_widget.view().selectionModel().currentIndex()))
        self.pick_root_widget.view().itemActivated.connect(
            lambda x: self.pick_root_widget.pick_custom(self.pick_root_widget.view().selectionModel().currentIndex()))

        self.ok_button.pressed.connect(self.add_bookmark)
        self.close_button.pressed.connect(self.reject)

    @QtCore.Slot(int)
    def select_saved_item(self, index, key=None, combobox=None):
        """Sets the currently active job as the selected item."""

        def first_valid():
            """Returns the first selectable item's row number."""
            if not combobox.view().model().rowCount():
                return QtCore.QModelIndex()

            for idx in xrange(combobox.view().model().rowCount()):
                index = combobox.view().model().index(idx, 0)
                if index.flags() != QtCore.Qt.NoItemFlags:
                    return index
            return QtCore.QModelIndex()

        local_paths = Active.paths()
        if local_paths[key] is None or local_paths[key] == 'None':
            combobox.view().selectionModel().setCurrentIndex(
                first_valid(), QtCore.QItemSelectionModel.ClearAndSelect)
            return

        index = QtCore.QModelIndex()
        for n in xrange(combobox.view().model().rowCount()):
            index = combobox.view().model().index(n, 0)
            if not index.data(QtCore.Qt.StatusTipRole):
                continue
            if index.data(QtCore.Qt.StatusTipRole) in local_paths[key]:
                break

        if not index.isValid():
            combobox.view().selectionModel().setCurrentIndex(
                first_valid(), QtCore.QItemSelectionModel.ClearAndSelect)
            return

        combobox.view().selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        return

    @QtCore.Slot(int)
    def add_root_folders(self, index):
        """Adds the found root folders to the `pick_root_widget`."""
        self.pick_root_widget.view().clear()
        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        if not file_info.exists():
            return

        arr = []
        self.get_root_folder_items(index.data(
            QtCore.Qt.StatusTipRole), arr=arr)

        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        for entry in sorted(arr):
            entry = entry.replace(u'\\', u'/')
            item = QtWidgets.QListWidgetItem()
            name = entry.replace(index.data(
                QtCore.Qt.StatusTipRole), u'').strip(u'/')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.StatusTipRole, entry)
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disabling the item if it has already been added to the widget
            if entry.replace(u'\\', u'/') in bookmarks:
                item.setFlags(QtCore.Qt.NoItemFlags)

            self.pick_root_widget.view().addItem(item)

        # Adding a special custom button
        item = QtWidgets.QListWidgetItem()
        name = custom_string
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.StatusTipRole, None)
        item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
            common.WIDTH, common.ROW_BUTTONS_HEIGHT))
        self.pick_root_widget.view().insertItem(0, item)

    def get_root_folder_items(self, path, depth=4, count=0, arr=None):
        """Scans the given path recursively and returns all root-folder candidates.
        The recursion-depth is limited by the `depth`.

        Args:
            depth (int): The number of subfolders to scan.

        Returns:
            A list of QFileInfo items

        """
        path = path.replace(u'\\', u'/')
        if depth == count:
            return arr

        if [f for f in arr if path in f]:
            return arr
        try:
            for entry in gwscandir.scandir(path):
                if not entry.is_dir():
                    continue
                if entry.name.startswith(u'.'):
                    continue

                identifier_path = u'{}/{}'.format(
                    entry.path.replace(u'\\', u'/'),
                    common.ASSET_IDENTIFIER)

                if QtCore.QFileInfo(identifier_path).exists():
                    if not [f for f in arr if path in f]:
                        arr.append(path)
                    return arr
                self.get_root_folder_items(
                    entry.path, depth=depth, count=count + 1, arr=arr)
        except OSError as err:
            return arr
        return arr

    @QtCore.Slot(int)
    def validate(self):
        """Enables the ok button if the selected path is valid and has not been
        added already to the bookmarks widget.

        """
        if not self.pick_server_widget.view().selectionModel().currentIndex().isValid():
            self.ok_button.setText(u'Select server')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return

        if not self.pick_job_widget.view().selectionModel().currentIndex().isValid():
            self.ok_button.setText(u'Select job')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return

        index = self.pick_root_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return

        # Let's check if the path is valid
        server = self.pick_server_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.StatusTipRole)
        job = self.pick_job_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.DisplayRole)
        root = self.pick_root_widget.view().selectionModel(
        ).currentIndex().data(QtCore.Qt.DisplayRole)

        key = u'{}/{}/{}'.format(server, job, root)
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            self.ok_button.setText(u'Bookmark folder not set')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return
        if not file_info.isReadable():
            self.ok_button.setText(u'Cannot read folder')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return
        if not file_info.isWritable():
            self.ok_button.setText(u'Cannot write to folder')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return
        if file_info.isHidden():
            self.ok_button.setText(u'Folder is hidden')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return

        bookmarks = local_settings.value(u'bookmarks')
        bookmarks = bookmarks if bookmarks else {}

        if key in bookmarks:
            self.ok_button.setText(u'Bookmark added already')
            self.ok_button.setDisabled(True)
            self.ok_button.repaint()
            return

        self.ok_button.setText(u'Add bookmark')
        self.ok_button.setDisabled(False)
        self.ok_button.repaint()

    @QtCore.Slot()
    def add_bookmark(self):
        """The action to execute when the `Ok` button is pressed."""
        index = self.pick_server_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        server = index.data(QtCore.Qt.StatusTipRole)

        index = self.pick_job_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            return
        job = index.data(QtCore.Qt.DisplayRole)

        index = self.pick_root_widget.view().selectionModel().currentIndex()
        if not index.isValid():
            return

        if not index.data(QtCore.Qt.StatusTipRole):
            return

        root = index.data(QtCore.Qt.DisplayRole)

        if not all((server, job, root)):
            return

        key = u'{}/{}/{}'.format(server, job, root)
        sys.stderr.write(key)
        sys.stderr.write('\n')
        sys.stderr.write(index.data(QtCore.Qt.StatusTipRole))
        file_info = QtCore.QFileInfo(key)
        if not file_info.exists():
            return

        bookmark = {key: {u'server': server, u'job': job, u'root': root}}
        bookmarks = local_settings.value(u'bookmarks')

        if not bookmarks:
            local_settings.setValue(u'bookmarks', bookmark)
        else:
            bookmarks[key] = bookmark[key]
            local_settings.setValue(u'bookmarks', bookmarks)
            sys.stdout.write('# GWBrowser: Bookmark {} added\n'.format(key))

        # We will set the newly added Bookmark as the active item
        if self.parent():
            self.new_key = key
            self.parent().model().sourceModel().beginResetModel()
            self.parent().model().sourceModel().__initdata__()

        # Resetting the folder selection...
        self.add_root_folders(
            self.pick_job_widget.view().selectionModel().currentIndex())
        self.pick_root_widget.repaint()
        self.validate()
        self.validate()

    def activate_bookmark(self):
        """Selects and activates the newly added bookmark in the `BookmarksWidget`."""
        if not self.new_key:
            return

        for n in xrange(self.parent().model().rowCount()):
            index = self.parent().model().index(n, 0)
            if index.data(QtCore.Qt.StatusTipRole) == self.new_key:
                self.parent().selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.parent().scrollTo(index)
                self.parent().activate(index)
                self.new_key = None
                return
        self.new_key = None

    def add_servers_from_config(self):
        """Querries the `gwbrowser.common` module and populates the widget with
        the available servers.

        """
        self.pick_server_widget.view().clear()

        for server in common.Server.servers():
            file_info = QtCore.QFileInfo(server[u'path'])

            name = server[u'path'].split(u'/').pop()

            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(common.DescriptionRole, server[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            # Disable the item if it isn't available
            if not file_info.exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

            item.setData(common.FlagsRole, item.flags())
            self.pick_server_widget.view().addItem(item)

    @QtCore.Slot(int)
    def add_jobs_from_server_folder(self, item):
        """Querries the given folder and return all readable folder within.

        Args:
            qdir (type): Description of parameter `qdir`.

        Returns:
            type: Description of returned object.

        """
        self.pick_job_widget.view().clear()

        path = item.data(QtCore.Qt.StatusTipRole)
        for entry in sorted([f for f in gwscandir.scandir(path)], key=lambda x: x.name):
            if entry.name.startswith(u'.'):
                continue
            if entry.is_symlink():
                continue
            if not entry.is_dir():
                continue
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, entry.name)
            item.setData(QtCore.Qt.StatusTipRole,
                         entry.path.replace(u'\\', u'/'))
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.ROW_BUTTONS_HEIGHT))

            item.setData(common.FlagsRole, item.flags())

            self.pick_job_widget.view().addItem(item)

    def mousePressEvent(self, event):
        """Custom mouse event."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(self.rect().topLeft())

    def mouseReleaseEvent(self, event):
        """Custom mouse event."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddBookmarksWidget()
    w.exec_()
    # app.exec_()
