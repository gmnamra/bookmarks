# -*- coding: utf-8 -*-

"""Defines the widgets needed to add and modify notes and todo-type annotions
for an Bookmark or an Asset.

`TodoEditorWidget` is the top widget. It reads the asset configuration file
and loads stored todo items. The todo items support basic HTML elements but
embedding media resources are not supported.

Methods:
    TodoEditorWidget.add_item(): Main function to add a new todo item.

"""
import json
import base64
import time
import functools
import re

from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.bookmark_db as bookmark_db
import gwbrowser.common as common
from gwbrowser.common_ui import add_row, ClickableIconButton, PaintedLabel
from gwbrowser.imagecache import ImageCache


NoHighlightFlag = 0b000000
HeadingHighlight = 0b000001
QuoteHighlight = 0b000010
ItalicsHighlight = 0b001000
BoldHighlight = 0b010000
PathHighlight = 0b100000


HIGHLIGHT_RULES = {
    u'url': {
        u're': re.compile(
            ur'((?:rvlink|file|http)[s]?:[/\\][/\\](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': PathHighlight
    },
    u'drivepath': {
        u're': re.compile(
            ur'((?:[a-zA-Z]{1})[s]?:[/\\](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': PathHighlight
    },
    u'uncpath': {
        u're': re.compile(
            ur'([/\\]{1,2}(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': PathHighlight
    },
    u'heading': {
        u're': re.compile(
            ur'^(?<!#)#{1,2}(?!#)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': HeadingHighlight
    },
    u'quotes': {
        u're': re.compile(
            # Group(2) captures the contents
            ur'([\"\'])((?:(?=(\\?))\3.)*?)\1',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': QuoteHighlight
    },
    u'italics': {
        u're': re.compile(
            ur'([\_])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': ItalicsHighlight
    },
    u'bold': {
        u're': re.compile(
            ur'([\*])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        u'flag': BoldHighlight
    },
}


class Lockfile(QtCore.QSettings):
    """Lockfile to prevent another user from modifying the database whilst
    an edit is in progress.

    """
    def __init__(self, index, parent=None):
        if index.isValid():
            p = u'/'.join(index.data(common.ParentPathRole)[0:3])
            f = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
            self.config_path = p + u'/.bookmark/' + f.baseName() + u'.lock'
        else:
            self.config_path = '/'

        super(Lockfile, self).__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )


class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
        """The highlighting cases are defined in the common module.
        In general we're tying to replicate the ``Markdown`` syntax rendering.

        Args:
            case (str): HIGHLIGHT_RULES dicy key.
            text (str): The text to assess.

        Returns:
            tuple: int, int, int

        """
        font = self.document().defaultFont()
        char_format = QtGui.QTextCharFormat()
        char_format.setFont(font)
        char_format.setFontWeight(QtGui.QFont.Normal)
        self.setFormat(0, len(text), char_format)

        _font = char_format.font()
        _foreground = char_format.foreground()
        _weight = char_format.fontWeight()
        _psize = char_format.font().pointSizeF()

        flag = NoHighlightFlag
        for case in HIGHLIGHT_RULES.itervalues():
            flag = flag | case[u'flag']

            if case[u'flag'] == HeadingHighlight:
                match = case[u're'].match(text)
                if match:
                    char_format.setFontPointSize(
                        font.pointSizeF() + ((3.0 - len(match.group(0))) * 4))
                    self.setFormat(0, len(text), char_format)

                    char_format.setForeground(QtGui.QColor(0, 0, 0, 80))
                    self.setFormat(match.start(0), len(
                        match.group(0)), char_format)

            if case[u'flag'] == PathHighlight:
                it = case[u're'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        grp = match.group(0)
                        if grp:
                            char_format.setAnchor(True)
                            char_format.setForeground(common.ADD)
                            char_format.setAnchorHref(grp)
                            self.setFormat(match.start(
                                0), len(grp), char_format)

            if case[u'flag'] == QuoteHighlight:
                it = case[u're'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in (u'\'', u'\"'):
                            grp = match.group(2)
                            if grp:
                                char_format.setAnchor(True)
                                char_format.setForeground(common.ADD)
                                char_format.setAnchorHref(grp)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 40))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            if case[u'flag'] == ItalicsHighlight:
                it = case[u're'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in u'_':
                            grp = match.group(2)
                            if grp:
                                flag == flag | ItalicsHighlight
                                char_format.setFontItalic(True)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            if case[u'flag'] == BoldHighlight:
                it = case[u're'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in u'*':
                            grp = match.group(2)
                            if grp:
                                char_format.setFontWeight(QtGui.QFont.Bold)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            char_format.setFont(_font)
            char_format.setForeground(_foreground)
            char_format.setFontWeight(_weight)


class TodoItemEditor(QtWidgets.QTextBrowser):
    """Custom QTextBrowser widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """

    def __init__(self, text, read_only=False, checked=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.setDisabled(checked)
        self.document().setDocumentMargin(common.MARGIN)

        self.highlighter = Highlighter(self.document())
        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)
        self.setReadOnly(False)
        self.verticalScrollBar().setFixedWidth(common.INDICATOR_WIDTH)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        if read_only:
            self.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse)
        else:
            self.setTextInteractionFlags(
                QtCore.Qt.TextEditorInteraction | QtCore.Qt.LinksAccessibleByMouse)

        metrics = QtGui.QFontMetricsF(self.document().defaultFont())
        metrics.width(u'   ')
        self.setTabStopWidth(common.MARGIN)

        self.setUndoRedoEnabled(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.document().setUseDesignMetrics(True)
        self.document().setHtml(text)
        self.document().contentsChanged.connect(self.contentChanged)
        self.anchorClicked.connect(self.open_url)

    @QtCore.Slot()
    def contentChanged(self):
        """Sets the height of the editor."""
        self.setFixedHeight(
            self.heightForWidth()
        )

    def get_minHeight(self):
        """Returns the desired minimum height of the editor."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(11.0)
        metrics = QtGui.QFontMetricsF(font)
        line_height = (metrics.lineSpacing()) * 1  # Lines tall
        return line_height

    def get_maxHeight(self):
        """Returns the desired minimum height of the editor."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(11.0)
        metrics = QtGui.QFontMetricsF(font)
        line_height = (metrics.lineSpacing()) * 35  # Lines tall
        return line_height

    def heightForWidth(self):
        """https://raw.githubusercontent.com/cameel/auto-resizing-text-edit/master/auto_resizing_text_edit/auto_resizing_text_edit.py"""
        document = self.document().clone()
        height = document.size().height()

        if height < self.get_minHeight():
            return self.get_minHeight()
        if height > self.get_maxHeight():
            return self.get_maxHeight()
        return height + 4

    def keyPressEvent(self, event):
        """I'm defining custom key events here, the default behaviour is pretty poor.

        In a dream-scenario I would love to implement most of the functions
        of how atom behaves.

        """
        cursor = self.textCursor()
        cursor.setVisualNavigation(True)

        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Backtab:
            cursor.movePosition(
                QtGui.QTextCursor.Start,
                QtGui.QTextCursor.MoveAnchor,
                cursor.position() - 4,
            )
            return
        super(TodoItemEditor, self).keyPressEvent(event)

    def dragEnterEvent(self, event):
        """Checking we can consume the content of the drag data..."""
        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

    def dropEvent(self, event):
        """Custom drop event to add content from mime-data."""
        index = self.parent().parent().parent().parent().parent().index
        if not index.isValid():
            return

        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

        mimedata = event.mimeData()
        self.insertFromMimeData(mimedata)

    def showEvent(self, event):
        self.setFixedHeight(self.heightForWidth())

        # Move the cursor to the end of the document
        cursor = QtGui.QTextCursor(self.document())
        cursor.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cursor)

        # Rehighlight the document to apply the formatting
        self.highlighter.rehighlight()

    def canInsertFromMimeData(self, mimedata):
        """Checks if we can insert from the given mime-type."""
        if mimedata.hasUrls():
            return True
        if mimedata.hasHtml():
            return True
        if mimedata.hasText():
            return True
        if mimedata.hasImage():
            return True
        return False

    # def insertFromMimeData(self, mimedata):
    #     """We can insert media using our image-cache - eg any image-content from
    #     the clipboard we will save into our cache folder.
    #
    #     """
    #     def href(url): return u'<a href="{url}">{name}</a>'.format(
    #         style=u'align:left;',
    #         url=url.toLocalFile(),
    #         name=QtCore.QFileInfo(url.toLocalFile()).fileName())
    #
    #     # We save our image into the cache for safe-keeping
    #     if mimedata.hasUrls():
    #         self.insertHtml(u'{}<br>'.format(href(url)))
    #
    #     elif mimedata.hasHtml():
    #         html = mimedata.html()
    #         self.insertHtml(u'{}<br>'.format(html))
    #     elif mimedata.hasText():
    #         text = mimedata.text()
    #         self.insertHtml(u'{}<br>'.format(text))

    def open_url(self, url):
        """We're handling the clicking of anchors here manually."""
        if not url.isValid():
            return
        file_info = QtCore.QFileInfo(url.url())
        if file_info.exists():
            common.reveal(file_info.filePath())
            QtGui.QClipboard().setText(file_info.filePath())
        else:
            QtGui.QDesktopServices.openUrl(url)


class RemoveNoteButton(ClickableIconButton):
    def __init__(self, parent=None):
        super(RemoveNoteButton, self).__init__(
            u'remove',
            (common.REMOVE, common.REMOVE),
            common.INLINE_ICON_SIZE * 0.66,
            description=u'Click to remove this note',
            parent=parent
        )
        self.clicked.connect(self.remove_note)

    def remove_note(self):
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Notes and Tasks')
        mbox.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        mbox.setIcon(QtWidgets.QMessageBox.NoIcon)
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        mbox.setText(
            u'Are you sure you want to remove this note?')
        res = mbox.exec_()
        if res == QtWidgets.QMessageBox.No:
            return

        editors_widget = self.parent().parent()
        idx = editors_widget.items.index(self.parent())
        row = editors_widget.items.pop(idx)
        editors_widget.layout().removeWidget(row)
        row.deleteLater()

    def _pixmap(self, type=QtCore.QEvent.Leave):
        return ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, self._size, opacity=1.0)


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the
    mime data. The data is populated with the `TodoEditor`'s text and the
    custom mime type (u'gwbrowser/todo-drag'). The latter is needed to accept the drag operation
    in the target drop widet.
    """

    def __init__(self, checked=False, parent=None):
        super(DragIndicatorButton, self).__init__(parent=parent)
        self.dragStartPosition = None

        self.setDisabled(checked)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setDisabled(self.isEnabled())

    def setDisabled(self, b):
        """Custom disabled function."""
        if b:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.TEXT_SELECTED, common.INLINE_ICON_SIZE * 0.66)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'drag_indicator', common.TEXT, common.INLINE_ICON_SIZE * 0.66)

        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """The drag operation is initiated here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        app = QtWidgets.QApplication.instance()
        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        parent_widget = self.parent()
        editor = parent_widget.findChild(TodoItemEditor)
        drag = QtGui.QDrag(parent_widget)

        # Setting Mime Data
        mime_data = QtCore.QMimeData()
        mime_data.setData(u'gwbrowser/todo-drag', QtCore.QByteArray(''))
        drag.setMimeData(mime_data)

        # Drag pixmap
        # Transparent image
        pixmap = QtGui.QPixmap(editor.size())
        editor.render(pixmap)
        # for x in xrange(image.width()):
        #     for y in xrange(image.height()):
        #         color = QtGui.QColor(image.pixel(x, y))
        #         color.setAlpha(150)
        #         image.setPixel(x, y, color.rgba())
        #
        # pixmap = QtGui.QPixmap()
        # pixmap = pixmap.fromImage(image)

        drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(0, pixmap.height() / 2.0))

        # Drag origin indicator
        pixmap = QtGui.QPixmap(parent_widget.size())

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 255)))
        painter.drawRect(pixmap.rect())
        painter.end()

        overlay_widget = QtWidgets.QLabel(parent=parent_widget)
        overlay_widget.setFixedSize(parent_widget.size())
        overlay_widget.setPixmap(pixmap)

        # Preparing the drag...
        parent_widget.parent().separator.setHidden(False)
        overlay_widget.show()

        # Starting the drag...
        drag.exec_(QtCore.Qt.CopyAction)

        # Cleanup after drag has finished...
        overlay_widget.close()
        overlay_widget.deleteLater()
        parent_widget.parent().separator.setHidden(True)


class CheckBoxButton(QtWidgets.QLabel):
    """Custom checkbox used for Todo Items."""

    clicked = QtCore.Signal(bool)

    def __init__(self, checked=False, parent=None):
        super(CheckBoxButton, self).__init__(parent=parent)
        self._checked = checked
        self._checked_pixmap = None
        self._unchecked_pixmap = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.set_pixmap(self._checked)
        self._entered = False
        self._connectSignals()

    def enterEvent(self, event):
        self._entered = True
        self.repaint()
        pixmap = self.pixmap()

    def leaveEvent(self, event):
        self._entered = False
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        if not self._entered and self.checked:
            painter.setOpacity(0.3)

        rect = self.pixmap().rect()
        rect.moveCenter(self.rect().center())

        painter.drawPixmap(rect, self.pixmap(), self.pixmap().rect())
        painter.end()

    @property
    def checked(self):
        return self._checked

    def _connectSignals(self):
        self.clicked.connect(self.set_pixmap)

    def set_pixmap(self, checked):
        if checked:
            pixmap = ImageCache.get_rsc_pixmap(
                u'check', common.BACKGROUND, 24)
            self.setPixmap(pixmap)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'check', common.ADD, 24)
            self.setPixmap(pixmap)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self._checked = not self._checked
        self.clicked.emit(self._checked)


class Separator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent=parent)
        pixmap = QtGui.QPixmap(QtCore.QSize(4096, 1))
        pixmap.fill(common.FAVOURITE)
        self.setPixmap(pixmap)

        self.setHidden(True)

        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.setFixedWidth(1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(u'gwbrowser/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Calling the parent's drop event, when the drop is on the separator."""
        self.parent().dropEvent(event)


class TodoEditors(QtWidgets.QWidget):
    """This is a convenience widget for storing the added todo items.

    As this is the container widget, it is responsible for handling the dragging
    and setting the order of the contained child widgets.

    Attributes:
        items (list):       The added todo items.

    """

    def __init__(self, parent=None):
        super(TodoEditors, self).__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.INDICATOR_WIDTH * 2)

        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat(u'gwbrowser/todo-drag'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Custom drag move event responsible for indicating the drop area."""
        # Move indicator
        idx, y = self._separator_pos(event)

        if y == -1:
            self.separator.setHidden(True)
            self.drop_target_index = -1
            event.ignore()
            return

        event.accept()
        self.drop_target_index = idx

        self.separator.setHidden(False)
        pos = self.mapToGlobal(QtCore.QPoint(self.geometry().x(), y))
        self.separator.move(pos)
        self.separator.setFixedWidth(self.width())

    def dropEvent(self, event):
        if self.drop_target_index == -1:
            event.ignore()
            return

        event.accept()

        # Drag from another todo list
        if event.source() not in self.items:
            text = event.source().findChild(TodoItemEditor).document().toHtml()
            self.parent().parent().parent().add_item(idx=0, text=text, checked=False)
            self.separator.setHidden(True)
            return

        # Change internal order
        self.setUpdatesEnabled(False)

        self.items.insert(
            self.drop_target_index,
            self.items.pop(self.items.index(event.source()))
        )
        self.layout().removeWidget(event.source())
        self.layout().insertWidget(self.drop_target_index, event.source(), 0)

        self.setUpdatesEnabled(True)

    def _separator_pos(self, event):
        """Returns the position of"""
        idx = 0
        dis = []

        y = event.pos().y()

        # Collecting the available hot-spots for the drag operation
        lines = []
        for n in xrange(len(self.items)):
            if n == 0:  # first
                line = self.items[n].geometry().top()
                lines.append(line)
                continue

            line = (
                self.items[n - 1].geometry().bottom() +
                self.items[n].geometry().top()
            ) / 2.0
            lines.append(line)

            if n == len(self.items) - 1:  # last
                line = ((
                    self.items[n - 1].geometry().bottom() +
                    self.items[n].geometry().top()
                ) / 2.0)
                lines.append(line)
                line = self.items[n].geometry().bottom()
                lines.append(line)
                break

        # Finding the closest
        for line in lines:
            dis.append(y - line)

        # Cases when items is dragged from another editor instance
        if not dis:
            return 0, 0

        idx = dis.index(min(dis, key=abs))  # The selected line
        if event.source() not in self.items:
            source_idx = idx + 1
        else:
            source_idx = self.items.index(event.source())

        if idx == 0:  # first item
            return (0, lines[idx])
        elif source_idx == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif (source_idx + 1) == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif source_idx < idx:  # moves up
            return (idx - 1, lines[idx])
        elif source_idx > idx:  # move down
            return (idx, lines[idx])


class TodoItemWidget(QtWidgets.QWidget):
    """The item-wrapper widget holding the checkbox, drag indicator and editor widgets."""

    def __init__(self, parent=None):
        super(TodoItemWidget, self).__init__(parent=parent)
        self.editor = None
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._createUI()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        o = common.INDICATOR_WIDTH
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.TEXT_SELECTED)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.end()


class TodoEditorWidget(QtWidgets.QDialog):
    """Main widget used to view and edit and add Notes and Tasks."""

    def __init__(self, index, parent=None):
        super(TodoEditorWidget, self).__init__(parent=parent)
        self.todoeditors_widget = None
        self._index = index

        self.read_only = False

        self.lock = Lockfile(self.index, parent=self)
        self.destroyed.connect(self.unlock)

        self.lockstamp = int(round(time.time() * 1000))
        self.save_timer = QtCore.QTimer(parent=self)
        self.save_timer.setInterval(5000)
        self.save_timer.setSingleShot(False)
        self.save_timer.timeout.connect(self.save_settings)

        self.refresh_timer = QtCore.QTimer(parent=self)
        self.refresh_timer.setInterval(30000)  # refresh every 30 seconds
        self.refresh_timer.setSingleShot(False)
        self.refresh_timer.timeout.connect(self.refresh)

        self.setWindowTitle(u'Notes & Tasks')
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._createUI()
        self.installEventFilter(self)

        self.init_lock()

    def _createUI(self):
        """Creates the ui layout."""
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN * 1.5
        self.layout().setSpacing(12.0)
        self.layout().setContentsMargins(o, o, o, o)

        # Top row
        height = 20
        row = add_row(None, height=height, parent=self)

        def paintEvent(event):
            painter = QtGui.QPainter()
            painter.begin(row)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 255))
            rect = row.rect()
            rect.setTop(rect.bottom())
            painter.drawRect(rect)
            painter.end()

        # row.paintEvent = paintEvent
        # Thumbnail
        self.add_button = ClickableIconButton(
            u'todo',
            (common.ADD, common.ADD),
            height,
            description=u'Click to add a new Todo item...',
            parent=self
        )

        # Name label
        text = u'Edit Notes and Tasks'
        label = PaintedLabel(text, color=common.BACKGROUND,
                             size=common.MEDIUM_FONT_SIZE, parent=self)

        row.layout().addWidget(self.add_button, 0)
        row.layout().addSpacing(common.INDICATOR_WIDTH * 2)
        row.layout().addWidget(label, 1)
        row.layout().addStretch(1)

        self.add_button.clicked.connect(lambda: self.add_item(idx=0))

        self.refresh_button = ClickableIconButton(
            u'refresh',
            (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
            height,
            description=u'Refresh...',
            parent=self
        )
        self.refresh_button.clicked.connect(self.refresh)
        row.layout().addWidget(self.refresh_button, 0)

        self.remove_button = ClickableIconButton(
            u'close',
            (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
            height,
            description=u'Refresh...',
            parent=self
        )
        self.remove_button.clicked.connect(self.close)
        row.layout().addWidget(self.remove_button, 0)

        # self.layout().addSpacing(common.INDICATOR_WIDTH)

        self.todoeditors_widget = TodoEditors(parent=self)
        self.setMinimumHeight(100)

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.todoeditors_widget)

        self.scrollarea.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.scrollarea.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(self.scrollarea)

        common.set_custom_stylesheet(self)

    def clear(self):
        for idx in reversed(xrange(len(list(self.todoeditors_widget.items)))):
            row = self.todoeditors_widget.items.pop(idx)
            for c in row.children():
                c.deleteLater()
            self.todoeditors_widget.layout().removeWidget(row)
            row.deleteLater()
            del row

    def refresh(self):
        """Populates the list from the database."""
        if not self.parent():
            return
        if not self.index.isValid():
            return
        if not self.index.data(common.FileInfoLoaded):
            return

        try:
            db = bookmark_db.get_db(self.index)

            if self.index.data(common.TypeRole) == common.FileItem:
                k = self.index.data(QtCore.Qt.StatusTipRole)
            elif self.index.data(common.TypeRole) == common.SequenceItem:
                k = common.proxy_path(self.index)

            v = db.value(k, u'notes')
        except:
            common.Log.error(u'Error getting notes')
            return

        if not v:
            return

        try:
            v = base64.b64decode(v)
            d = json.loads(v)
        except:
            common.Log.error(u'Error decoding notes from JSON')
            return

        if not v:
            return

        self.clear()

        try:
            for k, _ in enumerate(d):
                self.add_item(
                    text=d[unicode(k)][u'text'],
                    checked=d[unicode(k)][u'checked']
                )
        except:
            common.Log.error(u'Error adding notes')
            return

    @property
    def index(self):
        """The path used to initialize the widget."""
        return self._index

    def eventFilter(self, widget, event):
        """Using  the custom event filter to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            font = QtGui.QFont(common.SecondaryFont)
            font.setPointSizeF(common.MEDIUM_FONT_SIZE)
            painter.setFont(font)
            painter.setRenderHints(QtGui.QPainter.Antialiasing)

            rect = self.rect().marginsRemoved(QtCore.QMargins(4, 4, 4, 4))
            painter.setBrush(common.TEXT)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect, 8, 8)

            center = rect.center()
            rect.setWidth(rect.width() - common.MARGIN)
            rect.setHeight(rect.height() - common.MARGIN)
            rect.moveCenter(center)

            text = u'You can add a new note by clicking the add icon on the top.'
            text = text if not len(self.todoeditors_widget.items) else u''
            common.draw_aliased_text(
                painter, font, rect, text, QtCore.Qt.AlignCenter, common.SECONDARY_BACKGROUND)
            painter.end()
        return False

    def _get_next_enabled(self, n):
        hasEnabled = False
        for i in xrange(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[i]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                hasEnabled = True
                break

        if not hasEnabled:
            return -1

        # Finding the next enabled editor
        for _ in xrange(len(self.todoeditors_widget.items) - n):
            n += 1
            if n >= len(self.todoeditors_widget.items):
                return self._get_next_enabled(-1)
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                return n

    def key_tab(self):
        """Defining tabbing forward between items."""
        if not self.todoeditors_widget.items:
            return

        n = 0
        for n, item in enumerate(self.todoeditors_widget.items):
            editor = item.findChild(TodoItemEditor)
            if editor.hasFocus():
                break

        n = self._get_next_enabled(n)
        if n > -1:
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            editor.setFocus()
            self.scrollarea.ensureWidgetVisible(
                editor, ymargin=editor.height())

    def key_return(self,):
        """Control enter toggles the state of the checkbox."""
        for item in self.todoeditors_widget.items:
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if editor.hasFocus():
                if not editor.document().toPlainText():
                    idx = self.todoeditors_widget.items.index(editor.parent())
                    row = self.todoeditors_widget.items.pop(idx)
                    self.todoeditors_widget.layout().removeWidget(row)
                    row.deleteLater()
                checkbox.clicked.emit(not checkbox.checked)
                break

    def keyPressEvent(self, event):
        """Custom keypresses."""
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Escape:
            self.close()

        if shift_modifier:
            if event.key() == QtCore.Qt.Key_Tab:
                return True
            if event.key() == QtCore.Qt.Key_Backtab:
                return True

        if control_modifier:
            if event.key() == QtCore.Qt.Key_S:
                self.save_settings()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.add_button.clicked.emit()
                return True
            elif event.key() == QtCore.Qt.Key_Tab:
                self.key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Return:
                self.key_return()

    def add_item(self, idx=None, text=None, checked=False):
        """Creates a new widget containing the checkbox, editor and drag widgets.

        The method is responsible for adding the item the EditorsWidget layout
        and the EditorsWidget.items property.

        """
        def toggle_disabled(b, widget=None):
            widget.setDisabled(not b)

        item = TodoItemWidget(parent=self)
        item.layout().addSpacing(common.MARGIN)
        checkbox = CheckBoxButton(checked=not checked, parent=item)
        checkbox.setFocusPolicy(QtCore.Qt.NoFocus)
        drag = DragIndicatorButton(checked=False, parent=item)
        drag.setFocusPolicy(QtCore.Qt.NoFocus)
        editor = TodoItemEditor(
            text, read_only=self.read_only, checked=not checked, parent=item)
        editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        checkbox.clicked.connect(
            functools.partial(toggle_disabled, widget=editor))
        checkbox.clicked.connect(
            functools.partial(toggle_disabled, widget=drag))

        if not self.read_only:
            item.layout().addWidget(checkbox)
            item.layout().addSpacing(common.INDICATOR_WIDTH * 2)
            item.layout().addWidget(drag)
        else:
            checkbox.hide()
            drag.hide()
        item.layout().addWidget(editor, 1)

        if not self.read_only:
            remove = RemoveNoteButton(parent=item)
            remove.setFocusPolicy(QtCore.Qt.NoFocus)
            item.layout().addWidget(remove)
            item.layout().addSpacing(common.INDICATOR_WIDTH)

        if idx is None:
            self.todoeditors_widget.layout().addWidget(item, 0)
            self.todoeditors_widget.items.append(item)
        else:
            self.todoeditors_widget.layout().insertWidget(idx, item, 0)
            self.todoeditors_widget.items.insert(idx, item)

        checkbox.clicked.emit(checkbox._checked)
        editor.setFocus()
        item.editor = editor
        return item

    @QtCore.Slot()
    def save_settings(self):
        """Saves the current list of todo items to the assets configuration file."""
        if not self.index.isValid():
            return

        data = {}
        for n in xrange(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            checkbox = item.findChild(CheckBoxButton)
            if not editor.document().toPlainText():
                continue
            data[n] = {
                u'checked': not checkbox.checked,
                u'text': editor.document().toHtml(),
            }

        if self.index.data(common.TypeRole) == common.FileItem:
            k = self.index.data(QtCore.Qt.StatusTipRole)
        elif self.index.data(common.TypeRole) == common.SequenceItem:
            k = common.proxy_path(self.index)

        try:
            db = bookmark_db.get_db(self.index)
            v = json.dumps(data, ensure_ascii=False, encoding='utf-8')
            v = base64.b64encode(v.encode('utf-8'))
            db.setValue(k, u'notes', v)
        except:
            raise
        finally:
            todo_count = len([k for k in data if not data[k][u'checked']])
            self.index.model().setData(
                self.index,
                todo_count,
                role=common.TodoCountRole
            )

    def init_lock(self):
        """Creates a lock on the current file so it can't be edited by other users.
        It will also start the auto-save timer.
        """
        if not self.parent():
            return
        if not self.index.isValid():
            return

        v = self.lock.value(u'open')
        v = False if v is None else v
        v = v if isinstance(v, bool) else (
            False if v.lower() == 'false' else True)
        is_open = v

        stamp = self.lock.value(u'stamp')
        if stamp is not None:
            stamp = int(stamp)

        if not is_open:
            self.read_only = False
            self.add_button.show()
            self.refresh_button.hide()
            self.save_timer.start()
            self.refresh_timer.stop()

            self.lock.setValue(u'open', True)
            self.lock.setValue(u'stamp', self.lockstamp)
            return

        if stamp == self.lockstamp:
            self.read_only = False
            self.add_button.show()
            self.refresh_button.hide()
            self.save_timer.start()
            self.refresh_timer.stop()

            self.lock.setValue(u'stamp', self.lockstamp)
            return

        if stamp != self.lockstamp:
            self.read_only = True
            self.refresh_button.show()
            self.add_button.hide()
            self.save_timer.stop()
            self.refresh_timer.start()

    @QtCore.Slot()
    def unlock(self):
        """Removes the temporary lockfile on close"""
        if not self.parent():
            return
        if not self.index.isValid():
            return

        v = self.lock.value(u'open')
        v = False if v is None else v
        v = v if isinstance(v, bool) else (
            False if v.lower() == 'false' else True)
        is_open = v

        stamp = self.lock.value(u'stamp')
        if stamp is not None:
            stamp = int(stamp)

        if is_open and stamp == self.lockstamp:
            self.lock.setValue(u'stamp', None)
            self.lock.setValue(u'open', False)

    def showEvent(self, event):
        if self.parent():
            geo = self.parent().viewport().rect()
            self.resize(geo.width(), geo.height())
        self.setFocus(QtCore.Qt.OtherFocusReason)
        self.refresh()

    def hideEvent(self, event):
        if not self.read_only:
            self.save_settings()
        self.unlock()

    def sizeHint(self):
        """Custom size."""
        return QtCore.QSize(460, 460)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = TodoEditorWidget(QtCore.QModelIndex())
    widget.add_item(
        idx=0, text=u'!@#$%^&{Saját tyúkól készítése{;:::hello world!', checked=False)
    widget.add_item(idx=0, text='file://test.com', checked=False)
    widget.show()
    # widget.collect_data()
    app.exec_()
