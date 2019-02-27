/****************************************************************************
**
** Copyright (C) 2016 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
** This file is part of PySide2.
**
** $QT_BEGIN_LICENSE:LGPL$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** GNU Lesser General Public License Usage
** Alternatively, this file may be used under the terms of the GNU Lesser
** General Public License version 3 as published by the Free Software
** Foundation and appearing in the file LICENSE.LGPL3 included in the
** packaging of this file. Please review the following information to
** ensure the GNU Lesser General Public License version 3 requirements
** will be met: https://www.gnu.org/licenses/lgpl-3.0.html.
**
** GNU General Public License Usage
** Alternatively, this file may be used under the terms of the GNU
** General Public License version 2.0 or (at your option) the GNU General
** Public license version 3 or any later version approved by the KDE Free
** Qt Foundation. The licenses are as published by the Free Software
** Foundation and appearing in the file LICENSE.GPL2 and LICENSE.GPL3
** included in the packaging of this file. Please review the following
** information to ensure the GNU General Public License requirements will
** be met: https://www.gnu.org/licenses/gpl-2.0.html and
** https://www.gnu.org/licenses/gpl-3.0.html.
**
** $QT_END_LICENSE$
**
****************************************************************************/

#undef QT_NO_STL

#undef QT_NO_STL_WCHAR
#define Q_BYTE_ORDER // used to enable QSysInfo.Endian detection on MacOSX

#if defined(__OBJC__) && !defined(__cplusplus)
#  warning "File built in Objective-C mode (.m), but using Qt requires Objective-C++ (.mm)"
#endif

#include <QtCore/qnamespace.h>

QT_BEGIN_NAMESPACE


class QByteArray;
struct QArrayData;
typedef QArrayData QByteArrayData;

class QString;

#ifndef Q_MOC_OUTPUT_REVISION
#define Q_MOC_OUTPUT_REVISION 67
#endif

// The following macros are our "extensions" to C++
// They are used, strictly speaking, only by the moc.


#ifndef QT_NO_META_MACROS
// macro for onaming members
#ifdef METHOD
#undef METHOD
#endif
#ifdef SLOT
#undef SLOT
#endif
#ifdef SIGNAL
#undef SIGNAL
#endif
#endif // QT_NO_META_MACROS

Q_CORE_EXPORT const char *qFlagLocation(const char *method);

#ifndef QT_NO_META_MACROS
#ifndef QT_NO_DEBUG
# define QLOCATION "\0" __FILE__ ":" QT_STRINGIFY(__LINE__)
# ifndef QT_NO_KEYWORDS
#  define METHOD(a)   qFlagLocation("0"#a QLOCATION)
# endif
# define SLOT(a)     qFlagLocation("1"#a QLOCATION)
# define SIGNAL(a)   qFlagLocation("2"#a QLOCATION)
#else
# ifndef QT_NO_KEYWORDS
#  define METHOD(a)   "0"#a
# endif
# define SLOT(a)     "1"#a
# define SIGNAL(a)   "2"#a
#endif

#define QMETHOD_CODE  0                        // member type codes
#define QSLOT_CODE    1
#define QSIGNAL_CODE  2
#endif // QT_NO_META_MACROS

#define Q_ARG(type, data) QArgument<type >(#type, data)
#define Q_RETURN_ARG(type, data) QReturnArgument<type >(#type, data)

class QObject;
class QMetaMethod;
class QMetaEnum;
class QMetaProperty;
class QMetaClassInfo;


class Q_CORE_EXPORT QGenericArgument
{
public:
    inline QGenericArgument(const char *aName = 0, const void *aData = 0)
        : _data(aData), _name(aName) {}
    inline void *data() const { return const_cast<void *>(_data); }
    inline const char *name() const { return _name; }

private:
    const void *_data;
    const char *_name;
};

class Q_CORE_EXPORT QGenericReturnArgument: public QGenericArgument
{
public:
    inline QGenericReturnArgument(const char *aName = 0, void *aData = 0)
        : QGenericArgument(aName, aData)
        {}
};

template <class T>
class QArgument: public QGenericArgument
{
public:
    inline QArgument(const char *aName, const T &aData)
        : QGenericArgument(aName, static_cast<const void *>(&aData))
        {}
};
template <class T>
class QArgument<T &>: public QGenericArgument
{
public:
    inline QArgument(const char *aName, T &aData)
        : QGenericArgument(aName, static_cast<const void *>(&aData))
        {}
};


template <typename T>
class QReturnArgument: public QGenericReturnArgument
{
public:
    inline QReturnArgument(const char *aName, T &aData)
        : QGenericReturnArgument(aName, static_cast<void *>(&aData))
        {}
};

struct Q_CORE_EXPORT QMetaObject
{
    class Connection;
    const char *className() const;
    const QMetaObject *superClass() const;

    QObject *cast(QObject *obj) const;
    const QObject *cast(const QObject *obj) const;

#ifndef QT_NO_TRANSLATION
    QString tr(const char *s, const char *c, int n = -1) const;
#endif // QT_NO_TRANSLATION

    int methodOffset() const;
    int enumeratorOffset() const;
    int propertyOffset() const;
    int classInfoOffset() const;

    int constructorCount() const;
    int methodCount() const;
    int enumeratorCount() const;
    int propertyCount() const;
    int classInfoCount() const;

    int indexOfConstructor(const char *constructor) const;
    int indexOfMethod(const char *method) const;
    int indexOfSignal(const char *signal) const;
    int indexOfSlot(const char *slot) const;
    int indexOfEnumerator(const char *name) const;
    int indexOfProperty(const char *name) const;
    int indexOfClassInfo(const char *name) const;

    QMetaMethod constructor(int index) const;
    QMetaMethod method(int index) const;
    QMetaEnum enumerator(int index) const;
    QMetaProperty property(int index) const;
    QMetaClassInfo classInfo(int index) const;
    QMetaProperty userProperty() const;

    static bool checkConnectArgs(const char *signal, const char *method);
    static bool checkConnectArgs(const QMetaMethod &signal,
                                 const QMetaMethod &method);
    static QByteArray normalizedSignature(const char *method);
    static QByteArray normalizedType(const char *type);

    // internal index-based connect
    static Connection connect(const QObject *sender, int signal_index,
                        const QObject *receiver, int method_index,
                        int type = 0, int *types = 0);
    // internal index-based disconnect
    static bool disconnect(const QObject *sender, int signal_index,
                           const QObject *receiver, int method_index);
    static bool disconnectOne(const QObject *sender, int signal_index,
                              const QObject *receiver, int method_index);
    // internal slot-name based connect
    static void connectSlotsByName(QObject *o);

    // internal index-based signal activation
    static void activate(QObject *sender, int signal_index, void **argv);
    static void activate(QObject *sender, const QMetaObject *, int local_signal_index, void **argv);
    static void activate(QObject *sender, int signal_offset, int local_signal_index, void **argv);

    static bool invokeMethod(QObject *obj, const char *member,
                             Qt::ConnectionType,
                             QGenericReturnArgument ret,
                             QGenericArgument val0 = QGenericArgument(0),
                             QGenericArgument val1 = QGenericArgument(),
                             QGenericArgument val2 = QGenericArgument(),
                             QGenericArgument val3 = QGenericArgument(),
                             QGenericArgument val4 = QGenericArgument(),
                             QGenericArgument val5 = QGenericArgument(),
                             QGenericArgument val6 = QGenericArgument(),
                             QGenericArgument val7 = QGenericArgument(),
                             QGenericArgument val8 = QGenericArgument(),
                             QGenericArgument val9 = QGenericArgument());

    static inline bool invokeMethod(QObject *obj, const char *member,
                             QGenericReturnArgument ret,
                             QGenericArgument val0 = QGenericArgument(0),
                             QGenericArgument val1 = QGenericArgument(),
                             QGenericArgument val2 = QGenericArgument(),
                             QGenericArgument val3 = QGenericArgument(),
                             QGenericArgument val4 = QGenericArgument(),
                             QGenericArgument val5 = QGenericArgument(),
                             QGenericArgument val6 = QGenericArgument(),
                             QGenericArgument val7 = QGenericArgument(),
                             QGenericArgument val8 = QGenericArgument(),
                             QGenericArgument val9 = QGenericArgument())
    {
        return invokeMethod(obj, member, Qt::AutoConnection, ret, val0, val1, val2, val3,
                val4, val5, val6, val7, val8, val9);
    }

    static inline bool invokeMethod(QObject *obj, const char *member,
                             Qt::ConnectionType type,
                             QGenericArgument val0 = QGenericArgument(0),
                             QGenericArgument val1 = QGenericArgument(),
                             QGenericArgument val2 = QGenericArgument(),
                             QGenericArgument val3 = QGenericArgument(),
                             QGenericArgument val4 = QGenericArgument(),
                             QGenericArgument val5 = QGenericArgument(),
                             QGenericArgument val6 = QGenericArgument(),
                             QGenericArgument val7 = QGenericArgument(),
                             QGenericArgument val8 = QGenericArgument(),
                             QGenericArgument val9 = QGenericArgument())
    {
        return invokeMethod(obj, member, type, QGenericReturnArgument(), val0, val1, val2,
                                 val3, val4, val5, val6, val7, val8, val9);
    }

    static inline bool invokeMethod(QObject *obj, const char *member,
                             QGenericArgument val0 = QGenericArgument(0),
                             QGenericArgument val1 = QGenericArgument(),
                             QGenericArgument val2 = QGenericArgument(),
                             QGenericArgument val3 = QGenericArgument(),
                             QGenericArgument val4 = QGenericArgument(),
                             QGenericArgument val5 = QGenericArgument(),
                             QGenericArgument val6 = QGenericArgument(),
                             QGenericArgument val7 = QGenericArgument(),
                             QGenericArgument val8 = QGenericArgument(),
                             QGenericArgument val9 = QGenericArgument())
    {
        return invokeMethod(obj, member, Qt::AutoConnection, QGenericReturnArgument(), val0,
                val1, val2, val3, val4, val5, val6, val7, val8, val9);
    }

    QObject *newInstance(QGenericArgument val0 = QGenericArgument(0),
                         QGenericArgument val1 = QGenericArgument(),
                         QGenericArgument val2 = QGenericArgument(),
                         QGenericArgument val3 = QGenericArgument(),
                         QGenericArgument val4 = QGenericArgument(),
                         QGenericArgument val5 = QGenericArgument(),
                         QGenericArgument val6 = QGenericArgument(),
                         QGenericArgument val7 = QGenericArgument(),
                         QGenericArgument val8 = QGenericArgument(),
                         QGenericArgument val9 = QGenericArgument()) const;

    enum Call {
        InvokeMetaMethod,
        ReadProperty,
        WriteProperty,
        ResetProperty,
        QueryPropertyDesignable,
        QueryPropertyScriptable,
        QueryPropertyStored,
        QueryPropertyEditable,
        QueryPropertyUser,
        CreateInstance,
        IndexOfMethod,
        RegisterPropertyMetaType,
        RegisterMethodArgumentMetaType
    };

    int static_metacall(Call, int, void **) const;
    static int metacall(QObject *, Call, int, void **);

    struct { // private data
        const QMetaObject *superdata;
        const QByteArrayData *stringdata;
        const uint *data;
        typedef void (*StaticMetacallFunction)(QObject *, QMetaObject::Call, int, void **);
        StaticMetacallFunction static_metacall;
        const QMetaObject * const *relatedMetaObjects;
        void *extradata; //reserved for future use
    } d;
};

class Q_CORE_EXPORT QMetaObject::Connection {
    void *d_ptr; //QObjectPrivate::Connection*
    explicit Connection(void *data) : d_ptr(data) {  }
    friend class QObject;
    friend class QObjectPrivate;
    friend struct QMetaObject;
public:
    ~Connection();
    Connection();
    Connection(const Connection &other);
    Connection &operator=(const Connection &other);
#ifdef Q_QDOC
    operator bool() const;
#else
    typedef void *Connection::*RestrictedBool;
    operator RestrictedBool() const { return d_ptr ? &Connection::d_ptr : 0; }
#endif

#ifdef Q_COMPILER_RVALUE_REFS
    inline Connection(Connection &&o) : d_ptr(o.d_ptr) { o.d_ptr = 0; }
    inline Connection &operator=(Connection &&other)
    { qSwap(d_ptr, other.d_ptr); return *this; }
#endif
};

inline const QMetaObject *QMetaObject::superClass() const
{ return d.superdata; }

namespace QtPrivate {
    /* Trait that tells is a the Object has a Q_OBJECT macro */
    template <typename Object> struct HasQ_OBJECT_Macro {
        template <typename T>
        static char test(int (T::*)(QMetaObject::Call, int, void **));
        static int test(int (Object::*)(QMetaObject::Call, int, void **));
        enum { Value =  sizeof(test(&Object::qt_metacall)) == sizeof(int) };
    };
}

QT_END_NAMESPACE

// This Q_QDOC definition is only a convenience, since the shiboken parser is
// happier with the simplified constructions. XXX remove this for Qt 5.7.
#define Q_QDOC

#if 0
  #define Q_OS_X11
#elif 0
  #define Q_OS_MAC
#elif 1
  #include "pysidewtypes.h"
  #define Q_OS_WIN
#endif

// There are symbols in Qt that exist in Debug but
// not in release
#define QT_NO_DEBUG

#include <QtCore/QtCore>
#if 0 || 1 || 0
  // Workaround to parse the QApplication header
  #define Q_INTERNAL_QAPP_SRC
  #undef Q_QDOC
#endif
#if 1
#  include <QtGui/QtGui>
#endif
#if 1
#  include <QtWidgets/QtWidgets>
#endif
#ifndef Q_QDOC
// Make sure that Q_QDOC is defined for as much modules as possible.
// This creates more wrappers without extra work.
// Will disappear when we have a really good parser!
#  define Q_QDOC
#endif

#include "qpytextobject.h"  // PySide class

#if 0
#  if 
#    include <QtX11Extras/QX11Info>
#  endif
#elif 0
#  include <QtGui/qmacstyle_mac.h>
#endif

// QT_WIDGETS_LIB must be defined to QSqlRelationalDelegate become visible.
// It also changes code generation in pysideqtesttouch.h
#define QT_WIDGETS_LIB
#undef Q_DECLARE_INTERFACE

#if 1
#  include "pysideqtesttouch.h"
#endif

#ifndef QT_NO_OPENGL
#  include <C:/Program Files (x86)/Windows Kits/10/Include/10.0.16299.0/um/GL/gl.h>
#endif // QT_NO_OPENGL

// Here are now all configured modules appended:
#include "QtCore/QtCore"
#include "QtGui/QtGui"
#include "QtWidgets/QtWidgets"
#include "QtPrintSupport/QtPrintSupport"
#include "QtSql/QtSql"
#include "QtNetwork/QtNetwork"
#include "QtTest/QtTest"
#include "QtConcurrent/QtConcurrent"
#include "QtWinExtras/QtWinExtras"
#include "QtXml/QtXml"
#include "QtXmlPatterns/QtXmlPatterns"
#include "QtHelp/QtHelp"
#include "QtMultimedia/QtMultimedia"
#include "QtMultimediaWidgets/QtMultimediaWidgets"
#include "QtOpenGL/QtOpenGL"
#include "QtQml/QtQml"
#include "QtQuick/QtQuick"
#include "QtQuickWidgets/QtQuickWidgets"
#include "QtSvg/QtSvg"
#include "QtUiTools/QtUiTools"
#include "QtWebChannel/QtWebChannel"
#include "QtWebEngineWidgets/QtWebEngineWidgets"
#include "QtWebSockets/QtWebSockets"
