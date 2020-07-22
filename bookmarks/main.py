# -*- coding: utf-8 -*-
"""Bookmarks's main widget.

This is where the UI is assembled and signals & slots are connected.

"""
import os
import gc
import time
import functools
import subprocess
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.bookmark_db as bookmark_db
import bookmarks.images as images
import bookmarks.settings as settings
import bookmarks.threads as threads
import bookmarks.contextmenu as contextmenu
import bookmarks.listassets as listassets
import bookmarks.lists as lists
import bookmarks.listbookmarks as listbookmarks
import bookmarks.listfavourites as listfavourites
import bookmarks.listfiles as listfiles
import bookmarks.listcontrol as listcontrol


_instance = None


def instance():
    return _instance


@QtCore.Slot()
def show_window():
    """Shows/reveal the main window if it is not visible."""
    if not _instance:
        return
    _instance.showNormal()
    _instance.activateWindow()

    w = _instance.window()
    h = w.windowHandle()


class StatusBar(QtWidgets.QStatusBar):
    """Bookmarks's statusbar on the bottom of the window.

    """

    def __init__(self, height, parent=None):
        super(StatusBar, self).__init__(parent=parent)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setSizeGripEnabled(False)
        self.setFixedHeight(height)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        font, metrics = common.font_db.secondary_font(common.SMALL_FONT_SIZE())
        common.draw_aliased_text(
            painter,
            font,
            self.rect().marginsRemoved(QtCore.QMargins(
                common.INDICATOR_WIDTH(), 0, common.INDICATOR_WIDTH(), 0)),
            u'  {}  '.format(self.currentMessage()),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            common.TEXT
        )
        painter.end()


class TrayMenu(contextmenu.BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(TrayMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

        self.stays_on_top = False
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

        self.add_window_menu()
        self.add_separator()
        self.add_tray_menu()

    @contextmenu.contextmenu
    def add_tray_menu(self, menu_set):
        """Actions associated with the visibility of the widget."""
        active = self.parent().windowFlags() & QtCore.Qt.WindowStaysOnTopHint
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN())


        menu_set[u'Restore window...'] = {
            u'action': show_window
        }
        menu_set[u'separator1'] = {}
        menu_set[u'Quit'] = {
            u'action': self.parent().shutdown.emit
        }
        return menu_set


class MinimizeButton(common_ui.ClickableIconButton):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(MinimizeButton, self).__init__(
            u'minimize',
            (common.REMOVE, common.SECONDARY_TEXT),
            common.MARGIN() - common.INDICATOR_WIDTH(),
            description=u'Click to minimize the window...',
            parent=parent
        )


class CloseButton(common_ui.ClickableIconButton):
    """Button used to close/hide a widget or window."""

    def __init__(self, parent=None):
        super(CloseButton, self).__init__(
            u'close',
            (common.REMOVE, common.SECONDARY_TEXT),
            common.MARGIN() - common.INDICATOR_WIDTH(),
            description=u'Click to close the window...',
            parent=parent
        )


class HeaderWidget(QtWidgets.QWidget):
    """Horizontal widget for controlling the position of the widget active window."""
    widgetMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent=None):
        super(HeaderWidget, self).__init__(parent=parent)
        self.label = None
        self.closebutton = None
        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setFixedHeight(common.MARGIN() +
                            (common.INDICATOR_WIDTH() * 2))

        self._create_UI()

    def _create_UI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        menu_bar = QtWidgets.QMenuBar(parent=self)
        self.layout().addWidget(menu_bar)
        menu_bar.hide()
        menu = menu_bar.addMenu(common.PRODUCT)
        action = menu.addAction(u'Quit')
        action.triggered.connect(self.parent().shutdown)

        self.layout().addStretch()
        self.layout().addWidget(MinimizeButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)
        self.layout().addWidget(CloseButton(parent=self))
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)

    def mousePressEvent(self, event):
        """Custom ``movePressEvent``.
        We're setting the properties needed to moving the main window.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.move_in_progress = True
        self.move_start_event_pos = event.pos()
        self.move_start_widget_pos = self.mapToGlobal(
            self.geometry().topLeft())

    def mouseMoveEvent(self, event):
        """Moves the the parent window when clicked.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self.move_start_widget_pos:
            margins = self.window().layout().contentsMargins()
            offset = (event.pos() - self.move_start_event_pos)
            pos = self.window().mapToGlobal(self.geometry().topLeft()) + offset
            self.parent().move(
                pos.x() - margins.left(),
                pos.y() - margins.top()
            )
            bl = self.window().rect().bottomLeft()
            bl = self.window().mapToGlobal(bl)
            self.widgetMoved.emit(bl)

    def contextMenuEvent(self, event):
        """Shows the context menu associated with the tray in the header."""
        widget = TrayMenu(parent=self.window())
        pos = self.window().mapToGlobal(event.pos())
        widget.move(pos)
        common.move_widget_to_available_geo(widget)
        widget.show()


class ToggleModeButton(QtWidgets.QWidget):
    """The button used to switch between syncronised and solo modes."""
    clicked = QtCore.Signal()
    message = QtCore.Signal(unicode)

    def __init__(self, size, parent=None):
        super(ToggleModeButton, self).__init__(parent=parent)
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.animation_value = 1.0
        self.animation = QtCore.QVariantAnimation(parent=self)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.5)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self.animation.setLoopCount(1)  # Loops for forever
        self.animation.setDirection(QtCore.QAbstractAnimation.Forward)
        self.animation.setDuration(1500)
        self.animation.valueChanged.connect(self.update)
        self.animation.finished.connect(self.reverse_direction)
        self.clicked.connect(self.toggle_mode)

    def statusTip(self):
        if settings.local_settings.current_mode() == common.SynchronisedMode:
            return u'Instance is syncronised. Click to toggle.'
        elif settings.local_settings.current_mode() == common.SoloMode:
            return u'Instance not synronised. Click to toggle.'
        return u'Invalid mode.'

    @QtCore.Slot()
    def reverse_direction(self):
        """ A bounce."""
        if self.animation.direction() == QtCore.QPropertyAnimation.Forward:
            self.animation.setDirection(QtCore.QPropertyAnimation.Backward)
        else:
            self.animation.setDirection(QtCore.QPropertyAnimation.Forward)
        self.animation.start()
        self.update()

    def toggle_mode(self):
        """Simply toggles the solo mode."""
        if settings.local_settings.current_mode() == common.SynchronisedMode:
            settings.local_settings.set_mode(common.SoloMode)
            self.animation.setCurrentTime(0)
            self.animation.start()
        elif settings.local_settings.current_mode() == common.SoloMode:
            settings.local_settings.set_mode(common.SynchronisedMode)
            self.animation.setCurrentTime(0)
            self.animation.stop()
        self.update()
        settings.local_settings.save_mode_lockfile()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtCore.Qt.NoBrush)

        color = common.REMOVE if settings.local_settings.current_mode() else common.ADD
        pen = QtGui.QPen(color)

        o = common.INDICATOR_WIDTH() * 1.5
        pen.setWidth(common.INDICATOR_WIDTH() * 0.66)
        painter.setPen(pen)
        painter.setOpacity(self.animation.currentValue())
        rect = QtCore.QRect(self.rect())
        rect = rect.marginsRemoved(QtCore.QMargins(o, o, o, o))
        center = self.rect().center()

        size = QtCore.QSize(rect.width() - (o), rect.height() - (o))
        rect.setSize(size * self.animation.currentValue())
        rect.moveCenter(center)
        c = rect.height() / 2.0
        painter.drawRoundedRect(rect, c, c)

        painter.end()

    def enterEvent(self, event):
        self.message.emit(self.statusTip())

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        cursor_position = self.mapFromGlobal(common.cursor.pos())
        if self.rect().contains(cursor_position):
            self.clicked.emit()

    def showEvent(self, event):
        if settings.local_settings.current_mode() == common.SoloMode:
            self.animation.setCurrentTime(0)
            self.animation.start()
            self.update()
        elif settings.local_settings.current_mode() == common.SynchronisedMode:
            self.animation.setCurrentTime(0)
            self.animation.stop()
            self.update()


class MainWidget(QtWidgets.QWidget):
    """Our super-duper main widget.

    Contains the list control bar with the tab buttons, the stacked widget
    containing the Bookmark-, Asset- and FileWidgets and the statusbar.

    """
    initialized = QtCore.Signal()
    terminated = QtCore.Signal()
    shutdown = QtCore.Signal()

    def __init__(self, parent=None):
        global _instance
        if _instance is not None:
            raise RuntimeError(
                '{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(MainWidget, self).__init__(parent=parent)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', None, common.ASSET_ROW_HEIGHT())
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self._contextMenu = None
        self._initialized = False
        self._frameless = False
        self.shortcuts = []

        self.headerwidget = None
        self.stackedwidget = None
        self.listbookmarks = None
        self.listcontrol = None
        self.listassets = None
        self.fileswidget = None
        self.listfavourites = None
        self.statusbar = None
        self.solo_button = None

        self.thread_monitor = None

        self.initializer = QtCore.QTimer(parent=self)
        self.initializer.setSingleShot(True)
        self.initializer.setInterval(1000)
        self.initializer.timeout.connect(self.initialize)

        self.init_progress = u'Loading...'

    def _create_UI(self):
        if self._frameless is True:
            o = common.INDICATOR_WIDTH()  # offset around the widget
        else:
            o = 0

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )

        self.headerwidget = HeaderWidget(parent=self)
        self.stackedwidget = lists.StackedWidget(parent=self)
        self.listbookmarks = listbookmarks.BookmarksWidget(parent=self)
        self.listassets = listassets.AssetsWidget(parent=self)
        self.fileswidget = listfiles.FilesWidget(parent=self)
        self.listfavourites = listfavourites.FavouritesWidget(parent=self)

        self.stackedwidget.addWidget(self.listbookmarks)
        self.stackedwidget.addWidget(self.listassets)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.listfavourites)

        # Setting the tab now before we do any more initialisation
        idx = settings.local_settings.value(u'widget/current_tab')
        idx = 0 if idx is None or False else idx
        idx = 0 if idx < 0 else idx
        idx = 3 if idx > 3 else idx
        self.stackedwidget._setCurrentIndex(idx)

        self.listcontrol = listcontrol.ListControlWidget(parent=self)

        self.layout().addWidget(self.headerwidget)
        self.headerwidget.setHidden(not self._frameless)
        self.headerwidget.setDisabled(not self._frameless)

        self.layout().addWidget(self.listcontrol)
        self.layout().addWidget(self.stackedwidget)

        height = common.MARGIN() + (common.INDICATOR_WIDTH() * 2)
        row = common_ui.add_row(None, padding=0, height=height, parent=self)
        row.layout().setSpacing(0)
        row.layout().setContentsMargins(0, 0, 0, 0)

        self.statusbar = StatusBar(height, parent=self)
        self.solo_button = ToggleModeButton(height, parent=self)
        self.solo_button.message.connect(
            lambda s: self.statusbar.showMessage(s, 4000))

        self.thread_monitor = threads.ThreadMonitor(parent=self)

        row.layout().addWidget(self.thread_monitor, 0)
        row.layout().addWidget(self.statusbar, 1)
        row.layout().addWidget(self.solo_button, 0)

    @QtCore.Slot()
    def initialize(self):
        """Slot connected to the ``initializer``.

        To make sure the widget is shown as soon as it is created, we're
        initiating the ui and the models with a little delay. Settings saved in the
        local_settings are applied after the ui is initialized and the models
        finished loading their data.

        """
        if self._initialized:
            return

        def emit_saved_states():
            for flag in (common.MarkedAsActive, common.MarkedAsActive, common.MarkedAsFavourite):
                b.filterFlagChanged.emit(flag, b.filter_flag(flag))
                a.filterFlagChanged.emit(flag, a.filter_flag(flag))
                f.filterFlagChanged.emit(flag, f.filter_flag(flag))
                ff.filterFlagChanged.emit(flag, ff.filter_flag(flag))

        settings.local_settings.touch_mode_lockfile()
        settings.local_settings.save_mode_lockfile()

        self.shortcuts = []

        self._create_UI()
        self._connect_signals()
        self._add_shortcuts()

        settings.local_settings.load_and_verify_stored_paths()

        # Proxy model
        b = self.listbookmarks.model()
        a = self.listassets.model()
        f = self.fileswidget.model()
        ff = self.listfavourites.model()

        b.filterTextChanged.emit(b.filter_text())
        a.filterTextChanged.emit(a.filter_text())
        f.filterTextChanged.emit(f.filter_text())
        ff.filterTextChanged.emit(ff.filter_text())

        emit_saved_states()

        b.sourceModel().modelDataResetRequested.emit()

        if settings.local_settings.value(u'firstrun') is None:
            settings.local_settings.setValue(u'firstrun', False)

        @QtCore.Slot(QtCore.QModelIndex)
        def update_window_title(index):
            if not index.isValid():
                return
            if not index.data(common.ParentPathRole):
                return
            p = list(index.data(common.ParentPathRole))
            s = u'/'.join(p)
            self.setWindowTitle(s.upper())

        for n in xrange(3):
            model = self.stackedwidget.widget(n).model().sourceModel()
            model.activeChanged.connect(update_window_title)
            model.modelReset.connect(
                functools.partial(update_window_title, model.active_index()))

        w_handle = self.window().windowHandle()
        w_handle.screenChanged.connect(self.screenChanged)

        self._initialized = True
        self.initialized.emit()

    @QtCore.Slot()
    def screenChanged(self):
        screen = self.window().windowHandle().screen()
        dpi = screen.logicalDotsPerInch()
        log.success(u'{}'.format(dpi))

    @QtCore.Slot()
    def terminate(self):
        """Terminates the main gracefully by stopping the associated
        threads.

        """
        def ui_teardown():
            settings.local_settings.server_mount_timer.stop()

            self.listcontrol.bookmarks_button.timer.stop()
            self.listcontrol.assets_button.timer.stop()
            self.listcontrol.files_button.timer.stop()
            self.listcontrol.favourites_button.timer.stop()

            self.listbookmarks.timer.stop()
            self.listassets.timer.stop()
            self.fileswidget.timer.stop()
            self.listfavourites.timer.stop()

            self.hide()
            self.setUpdatesEnabled(False)
            self.deleteLater()

            for widget in (
                self.listassets,
                self.fileswidget,
                self.listfavourites,
                self.listcontrol.task_folder_view
            ):
                try:
                    widget.removeEventFilter(self)
                    widget.hide()
                    widget.setUpdatesEnabled(False)
                    widget.blockSignals(True)

                    if hasattr(widget, 'timer'):
                        widget.timer.stop()
                    if hasattr(widget, 'request_visible_fileinfo_timer'):
                        widget.request_visible_fileinfo_timer.stop()
                    if hasattr(widget, 'request_visible_thumbnail_timer'):
                        widget.request_visible_thumbnail_timer.stop()
                    if hasattr(widget, 'queue_model_timer'):
                        widget.queue_model_timer.stop()
                    if hasattr(widget.model(), 'sourceModel'):
                        widget.model().sourceModel().deleteLater()
                    widget.model().deleteLater()
                    widget.deleteLater()

                    for child in widget.children():
                        child.deleteLater()
                except Exception as err:
                    log.error(u'Error occured deleteing the ui.')

            for widget in (self.listcontrol, self.headerwidget, self.stackedwidget, self.statusbar):
                widget.setUpdatesEnabled(False)
                widget.blockSignals(True)
                widget.hide()
                widget.deleteLater()
                for child in widget.children():
                    child.deleteLater()

            images.ImageCache.INTERNAL_MODEL_DATA = None

            settings.local_settings.deleteLater()
            settings.local_settings = None
            gc.collect()

        def close_database_connections():
            try:
                for k in bookmark_db.DB_CONNECTIONS:
                    bookmark_db.DB_CONNECTIONS[k].connection().close()
                    bookmark_db.DB_CONNECTIONS[k].deleteLater()
            except Exception:
                log.error('Error closing the database')

        def quit_threads():
            _threads = threads.THREADS.values()
            for thread in _threads:
                if thread.isRunning():
                    thread.stopCheckQueue.emit()
                    thread.resetQueue.emit()
                    thread.quit()
                    thread.wait()

            n = 0
            while any([thread.isRunning() for thread in _threads]):
                if n >= 20:
                    for thread in _threads:
                        thread.terminate()
                    break
                n += 1
                time.sleep(0.3)

        self.statusbar.showMessage(u'Closing down...')
        quit_threads()
        close_database_connections()
        ui_teardown()

        try:
            self.terminated.emit()
        except:
            pass

    def next_tab(self):
        n = self.stackedwidget.currentIndex()
        n += 1
        if n > (self.stackedwidget.count() - 1):
            self.listcontrol.listChanged.emit(0)
            return
        self.listcontrol.listChanged.emit(n)

    def previous_tab(self):
        n = self.stackedwidget.currentIndex()
        n -= 1
        if n < 0:
            n = self.stackedwidget.count() - 1
            self.listcontrol.listChanged.emit(n)
            return
        self.listcontrol.listChanged.emit(n)

    def add_shortcut(self, keys, targets, repeat=False, context=QtCore.Qt.WidgetWithChildrenShortcut):
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(keys), self)
        shortcut.setAutoRepeat(repeat)
        shortcut.setContext(context)
        for func in targets:
            shortcut.activated.connect(func)
        self.shortcuts.append(shortcut)

    def open_new_instance(self):
        try:
            if common.get_platform() == u'win':
                p = os.environ['BOOKMARKS_ROOT'] + \
                    os.path.sep + 'bookmarks.exe'
                subprocess.Popen(p)
        except KeyError:
            log.error(u'Could not open new instance')

    def _add_shortcuts(self):
        lc = self.listcontrol
        self.add_shortcut(
            u'Ctrl+N', (self.open_new_instance, ))
        self.add_shortcut(
            u'Ctrl+1', (lc.bookmarks_button.clicked, lc.bookmarks_button.update))
        self.add_shortcut(
            u'Ctrl+2', (lc.assets_button.clicked, lc.assets_button.update))
        self.add_shortcut(
            u'Ctrl+3', (lc.files_button.clicked, lc.files_button.update))
        self.add_shortcut(
            u'Ctrl+4', (lc.favourites_button.clicked, lc.favourites_button.update))
        #
        self.add_shortcut(
            u'Ctrl+M', (lc.generate_thumbnails_button.action, lc.generate_thumbnails_button.update))
        self.add_shortcut(
            u'Ctrl+F', (lc.filter_button.action, lc.filter_button.update))
        self.add_shortcut(
            u'Ctrl+G', (lc.collapse_button.action, lc.collapse_button.update))
        self.add_shortcut(
            u'Ctrl+Shift+A', (lc.archived_button.action, lc.archived_button.update))
        self.add_shortcut(
            u'Ctrl+Shift+F', (lc.favourite_button.action, lc.favourite_button.update))
        self.add_shortcut(
            u'Alt+S', (lc.slack_button.action, lc.slack_button.update))
        self.add_shortcut(
            u'Ctrl+H', (lc.simple_mode_button.action, lc.simple_mode_button.update))
        #
        self.add_shortcut(
            u'Alt+Right', (self.next_tab, ), repeat=True)
        self.add_shortcut(
            u'Alt+Left', (self.previous_tab, ), repeat=True)
        self.add_shortcut(
            u'Ctrl+Right', (self.next_tab, ), repeat=True)
        self.add_shortcut(
            u'Ctrl+Left', (self.previous_tab, ), repeat=True)
        #
        self.add_shortcut(
            u'Ctrl+P', (self.push_to_rv, ), repeat=False)

    def push_to_rv(self):
        """Pushes the selected footage to RV."""
        widget = self.stackedwidget.currentWidget()
        index = widget.currentIndex()
        if not index.isValid():
            return
        path = common.get_sequence_startpath(
            index.data(QtCore.Qt.StatusTipRole))
        common.push_to_rv(path)

    def _connect_signals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.listbookmarks
        a = self.listassets
        f = self.fileswidget
        ff = self.listfavourites
        lc = self.listcontrol
        l = lc.control_view()
        lb = lc.control_button()
        s = self.stackedwidget

        #####################################################
        self.shutdown.connect(self.terminate)
        #####################################################
        lc.bookmarks_button.clicked.connect(
            lambda: lc.listChanged.emit(0))
        lc.assets_button.clicked.connect(
            lambda: lc.listChanged.emit(1))
        lc.files_button.clicked.connect(
            lambda: lc.listChanged.emit(2))
        lc.favourites_button.clicked.connect(
            lambda: lc.listChanged.emit(3))

        #####################################################

        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().modelDataResetRequested)

        # * -> Listcontrol
        b.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        a.model().sourceModel().activeChanged.connect(
            l.model().modelDataResetRequested)
        f.model().sourceModel().modelDataResetRequested.connect(
            l.model().modelDataResetRequested)
        l.model().taskFolderChangeRequested.connect(lc.files_button.show_view)

        ff.favouritesChanged.connect(
            ff.model().sourceModel().modelDataResetRequested)
        #####################################################
        # Stacked widget navigation
        lc.listChanged.connect(s.setCurrentIndex)
        b.activated.connect(lambda: lc.listChanged.emit(1))
        # b.model().sourceModel().activeChanged.connect(lambda: lc.listChanged.emit(1))
        a.activated.connect(lambda: lc.listChanged.emit(2))
        # a.model().sourceModel().activeChanged.connect(lambda: lc.listChanged.emit(2))

        a.model().sourceModel().activeChanged.connect(l.model().check_task_folder)
        a.activated.connect(l.model().check_task_folder)
        lc.listChanged.connect(l.model().check_task_folder)

        # Control bar connections
        lc.taskFolderChanged.connect(f.model().sourceModel().taskFolderChanged)
        lc.taskFolderChanged.connect(lc.textChanged)
        f.model().sourceModel().taskFolderChanged.connect(lc.textChanged)
        #####################################################
        b.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().task_folder()) if f.model().sourceModel().task_folder() else 'Files')
        b.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().task_folder()) if f.model().sourceModel().task_folder() else 'Files')
        a.activated.connect(
            lambda: lc.textChanged.emit(f.model().sourceModel().task_folder()) if f.model().sourceModel().task_folder() else 'Files')
        a.model().sourceModel().activeChanged.connect(
            lambda x: lc.textChanged.emit(f.model().sourceModel().task_folder()) if f.model().sourceModel().task_folder() else 'Files')
        #####################################################
        lc.listChanged.connect(lb.update)
        lc.listChanged.connect(lc.update_buttons)

        s.currentChanged.connect(lc.update_buttons)
        s.currentChanged.connect(lc.bookmarks_button.update)

        f.model().sourceModel().dataTypeChanged.connect(lc.update_buttons)
        ff.model().sourceModel().dataTypeChanged.connect(lc.update_buttons)
        b.model().filterFlagChanged.connect(lc.update_buttons)
        a.model().filterFlagChanged.connect(lc.update_buttons)
        f.model().filterFlagChanged.connect(lc.update_buttons)
        ff.model().filterFlagChanged.connect(lc.update_buttons)
        b.model().filterTextChanged.connect(lc.update_buttons)
        a.model().filterTextChanged.connect(lc.update_buttons)
        f.model().filterTextChanged.connect(lc.update_buttons)
        ff.model().filterTextChanged.connect(lc.update_buttons)
        b.model().modelReset.connect(lc.update_buttons)
        a.model().modelReset.connect(lc.update_buttons)
        f.model().modelReset.connect(lc.update_buttons)
        ff.model().modelReset.connect(lc.update_buttons)

        b.model().modelReset.connect(lb.update)
        a.model().modelReset.connect(lb.update)
        f.model().modelReset.connect(lb.update)
        ff.model().modelReset.connect(lb.update)
        ########################################################################
        # Messages
        b.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Loading bookmarks...', 99999))
        b.model().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))

        a.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Loading assets...', 99999))
        a.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))
        a.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        f.model().modelAboutToBeReset.connect(
            lambda: self.statusbar.showMessage(u'Loading files...', 99999))
        f.model().modelReset.connect(lambda: self.statusbar.showMessage(u'', 99999))

        f.model().sourceModel().modelReset.connect(
            lambda: self.statusbar.showMessage(u'', 99999))
        b.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        a.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        f.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))
        ff.model().sourceModel().progressMessage.connect(
            lambda m: self.statusbar.showMessage(m, 99999))

        # Statusbar
        b.entered.connect(self.entered)
        a.entered.connect(self.entered)
        f.entered.connect(self.entered)
        ff.entered.connect(self.entered)
        l.entered.connect(self.entered)

        lc.bookmarks_button.message.connect(self.entered2)
        lc.assets_button.message.connect(self.entered2)
        lc.files_button.message.connect(self.entered2)
        lc.favourites_button.message.connect(self.entered2)
        lc.generate_thumbnails_button.message.connect(self.entered2)
        lc.filter_button.message.connect(self.entered2)
        lc.collapse_button.message.connect(self.entered2)
        lc.archived_button.message.connect(self.entered2)
        lc.simple_mode_button.message.connect(self.entered2)
        lc.favourite_button.message.connect(self.entered2)
        lc.slack_button.message.connect(self.entered2)

    def paintEvent(self, event):
        """Drawing a rounded background help to identify that the widget
        is in standalone mode."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(1.0)
        painter.setPen(pen)
        painter.setBrush(common.SEPARATOR.darker(110))

        if self._frameless is True:
            o = common.INDICATOR_WIDTH()
            rect = rect.marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.drawRoundedRect(rect, o * 3, o * 3)
        else:
            painter.drawRect(rect)

        if not self._initialized:
            font, metrics = common.font_db.primary_font(
                common.MEDIUM_FONT_SIZE())
            rect = QtCore.QRect(self.rect())
            align = QtCore.Qt.AlignCenter
            color = QtGui.QColor(255, 255, 255, 80)

            pixmaprect = QtCore.QRect(rect)
            center = pixmaprect.center()
            s = common.ASSET_ROW_HEIGHT() * 1.5
            o = common.MARGIN()

            pixmaprect.setWidth(s)
            pixmaprect.setHeight(s)
            pixmaprect.moveCenter(center)

            painter.setBrush(QtGui.QColor(0, 0, 0, 20))
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 20))
            painter.setPen(pen)

            painter.drawRoundedRect(
                pixmaprect.marginsAdded(
                    QtCore.QMargins(o * 3, o * 3, o * 3, o * 3)),
                o, o)

            pixmap = images.ImageCache.get_rsc_pixmap(
                u'icon_bw', None, s)
            painter.setOpacity(0.5)
            painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
            painter.setOpacity(1.0)

            rect.setTop(pixmaprect.bottom() + (o * 0.5))
            rect.setHeight(metrics.height())
            common.draw_aliased_text(
                painter, font, rect, self.init_progress, align, color)

        painter.end()

    @QtCore.Slot(QtCore.QModelIndex)
    def entered(self, index):
        """Displays an indexe's status tip in the statusbar."""
        if not index.isValid():
            return
        message = index.data(QtCore.Qt.StatusTipRole)
        self.statusbar.showMessage(message, timeout=1500)

    @QtCore.Slot(unicode)
    def entered2(self, message):
        """Displays a custom message in the statusbar"""
        if not message:
            return
        self.statusbar.showMessage(message, timeout=1500)

    def activate_widget(self, idx):
        """Method to change between views."""
        self.stackedwidget.setCurrentIndex(idx)

    def sizeHint(self):
        """The widget's default size."""
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())

    def showEvent(self, event):
        """Show event. When we first show the widget we will initialize it to
        load the models.

        """
        if not self._initialized:
            self.initializer.start()
