""" Packager script for Bookmarks.

Builds `Bookmarks.exe` and collects the library dependencies
needed to run and Bookmarks as a standalone windows desktop application.

Requirements:

    Visual Studio 2015:     -
    Dependencies.exe:       Used to traverse the dependencies of a given DLL.
    CPython 2.7.x:          Must be built using VS2015 x64.
    Alembic:                DLLs including the *.pyd module.
    OpenImageIO 2.x.x:      DLLs including the *.pyd module.
    Qt 5.x.x:               The version should adhere to the current
                            VFX Reference Platform specs.
    PySide2:                This one is a little tricky as there is not supported
                            combination of Python 2.7 and later versions of Qt5.
                            Best way I found was to build from source or use the
                            Qt shipped with Maya or Houdini.

Configure:                  Source and destination paths.

    PREFIX:                 The root directory for the standalone package files.
                            This is where the installer and the collected
                            package file will be places.
    {PACKAGE}_ROOT:         The install directory of the given dependency.
                            Eg. C:/openexr/install
    {PACKAGE}_LIB:          Paths to core `*.dll`s, to be run agains Dependencies.exe

Note:

    There's no automated build script for building the dependencies at the moment, so
    make sure you're linking against the same includes and libraries as used for
    building the Python, Alembic and OpenImageIO libraries.

"""
import sys
import os
import time
import shutil
import zipfile
from distutils.dir_util import copy_tree


def _find_lib(_ROOT, lib):
    """Recursively search a top level root path for a given library.

    Args:
        root (str): A root apth eg `mypackages/dlls`
        lib (str): A library name, eg. `openimageio.dll`

    Returns:
        str: The library's full file path.

    """
    if os.path.isfile(lib):
        return lib
    for root, _, files in os.walk(_ROOT):
        for f in files:
            if f.lower() == lib.lower():
                print '\x1B[37m\n', 'Found', '\x1B[0m ', '\x1B[32m', root + os.path.sep + f, '\x1B[0m'
                return root + os.path.sep + f
    raise RuntimeError('{} not found'.format(lib))


def path(s):
    """Helper function to find a relative path to a package root. Modify as needed."""
    p = os.path.normpath(
        os.path.dirname(__file__) + os.pardir.join([os.path.sep] * 4) + s)
    if not os.path.isdir(p) and not os.path.isfile(p):
        raise OSError('{} does not exist'.format(p))
    return p

################################################################################
# CONFIGURATION
################################################################################

# General
PREFIX = path('bookmarks-standalone')
VC_ROOT = ur'C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64'
DUMPBIN = VC_ROOT + os.path.sep + ur'dumpbin.exe'
VCPKG_BIN = path('vcpkg/installed/x64-windows/bin')
VC_REDIST = _find_lib(PREFIX, 'VC_redist.x64.exe')

# Package Roots
PYTHON_ROOT = path('Python-2.7.15/install')
ALEMBIC_ROOT = path('alembic-build/install')
QT5_ROOT = path('qt5_13_2_build')
PYSIDE2_ROOT = path('pyside-setup/pyside2_install/py2.7-qt5.13.2-64bit-release')
OPENEXR_ROOT = path('OpenEXR-build/install')
OIIO_ROOT = path('OpenImageIO-build/install')

# Libraries

# Python
LIB_SCANDIR_D = _find_lib(PYTHON_ROOT, '_scandir.pyd')
LIB_SQLITE = _find_lib(PYTHON_ROOT, 'sqlite3.dll')

# Alembic
LIB_ALEMBIC = _find_lib(ALEMBIC_ROOT, 'Alembic.dll')
LIB_ALEMBIC_D = _find_lib(ALEMBIC_ROOT, 'alembic.pyd')

# Qt5 & PySide2
LIB_QTCORE = _find_lib(QT5_ROOT, 'Qt5Core.dll')
LIB_QTGUI = _find_lib(QT5_ROOT, 'Qt5Gui.dll')
LIB_QTWIDGETS = _find_lib(QT5_ROOT, 'Qt5Widgets.dll')
LIB_EGL = _find_lib(QT5_ROOT, 'libEGL.dll')
LIB_GLES = _find_lib(QT5_ROOT, 'libGLESv2.dll')
LIB_QTCORE_D = _find_lib(PYSIDE2_ROOT, 'QtCore.pyd')
LIB_QTGUI_D = _find_lib(PYSIDE2_ROOT, 'QtGui.pyd')
LIB_QTWIDGETS_D = _find_lib(PYSIDE2_ROOT, 'QtWidgets.pyd')
LIB_SHIBOKEN = _find_lib(PYSIDE2_ROOT, 'shiboken2-python2.7.dll')
LIB_SHIBOKEN_D = _find_lib(PYSIDE2_ROOT, 'shiboken2.pyd')

# ilmbase/openexr
LIB_ILMIMF = _find_lib(OPENEXR_ROOT, 'IlmImf-2_3.dll')
LIB_IEX = _find_lib(OPENEXR_ROOT, 'PyIex.dll')
LIB_IMATH = _find_lib(OPENEXR_ROOT, 'PyImath.dll')
LIB_IEX_D = _find_lib(OPENEXR_ROOT, 'iex.pyd')
LIB_IMATH_D = _find_lib(OPENEXR_ROOT, 'imath.pyd')

# OpenImageIO
LIB_OIIO = _find_lib(OIIO_ROOT, 'OpenImageIO.dll')
LIB_OIIO_D = _find_lib(OIIO_ROOT, 'OpenImageIO.pyd')

################################################################################
# `TOP_LEVEL_LIBS` will have all their dependencies distributed,
# except the libraries defined defined in `SYSTEM_LIBS`.
################################################################################
TOP_LEVEL_LIBS = (
    LIB_SCANDIR_D,
    LIB_SQLITE,
    LIB_ILMIMF,
    LIB_IEX,
    LIB_IEX_D,
    LIB_IMATH,
    LIB_IMATH_D,
    LIB_ALEMBIC,
    LIB_ALEMBIC_D,
    LIB_OIIO,
    LIB_OIIO_D,
    LIB_QTCORE,
    LIB_QTCORE_D,
    LIB_QTGUI,
    LIB_QTGUI_D,
    LIB_QTWIDGETS,
    LIB_QTWIDGETS_D,
    LIB_SHIBOKEN,
    LIB_SHIBOKEN_D,
    LIB_EGL,
    LIB_GLES
)

SYSTEM_LIBS = (
    'ADVAPI32',
    'api-ms',
    'bcrypt',
    # 'concrt140',
    'd3d11',
    'd3d9',
    'dbeng',
    'dbgeng',
    'dwmapi',
    'GDI32',
    'KERNEL',
    'MF',
    'MFPlat',
    'MPR',
    'MSVCP',
    'NETAPI32',
    'ole32',
    'OLEAUT32',
    'OPENGL32',
    'Secur32',
    'SHELL32',
    'SHLWAPI',
    'ucrtbased',
    'USER32',
    'USERENV',
    'UxTheme',
    'VCOMP140',
    # 'VCRUNTIME',
    'VERSION',
    'WINMM',
    'WS2_32',
)
################################################################################


def find_lib(lib):
    """Recursively search the top level root paths for a given library.

    Args:
        lib (str): A library name, eg. `openimageio.dll`

    Returns:
        str: The library's full file path.

    """
    if os.path.isfile(lib):
        return lib

    for _ROOT in (
        PYTHON_ROOT,
        QT5_ROOT,
        PYSIDE2_ROOT,
        OIIO_ROOT,
        OPENEXR_ROOT,
        ALEMBIC_ROOT,
        VCPKG_BIN,
    ):
        for root, _, files in os.walk(_ROOT):
            for f in files:
                if f.lower() == lib.lower():
                    return root + os.path.sep + f
    return None


def _get_lib_dependencies(libpath, l):
    """Find recursively dependencies of `libpath` and append the results to `l`.

    """
    libpath = os.path.basename(libpath)
    _libpath = find_lib(libpath)
    if not _libpath:
        raise RuntimeError('Could not find {}'.format(libpath))
    else:
        libpath = _libpath

    DUMPCMD = '"{}" /dependents {}'.format(DUMPBIN, libpath)
    r = os.popen(DUMPCMD).read()
    r = r.strip().split('\n')
    _dep = [f.strip() for f in r if f.lower().endswith(
        'dll') and not f.lower().startswith('dump')]
    _dep = [f for f in _dep if not f.lower().startswith('file type')]
    _dep = [f for f in _dep if not [
        s for s in SYSTEM_LIBS if s.lower() in f.lower()]]
    l = sorted(list(set(l)))
    if not _dep:
        return l
    l += _dep
    for _libpath in _dep:
        l = _get_lib_dependencies(_libpath, l)
    l = sorted(list(set(l)))
    return l



def get_dependencies():
    """Get all library dependencies based on the set configuration.

    """
    dependencies = []
    for L in TOP_LEVEL_LIBS:
        if L.lower().endswith('dll'):
            dependencies.append(L)
        dependencies = _get_lib_dependencies(L, dependencies)

    LIBS = {}
    for lib in dependencies:
        LIBS[lib] = None
        if os.path.isfile(lib):
            LIBS[lib] = lib
            continue
        for _ROOT in (
            ALEMBIC_ROOT,
            OIIO_ROOT,
            OPENEXR_ROOT,
            VCPKG_BIN,
            QT5_ROOT,
            PYSIDE2_ROOT,
            PYTHON_ROOT,
        ):
            for root, _, files in os.walk(_ROOT):
                for f in files:
                    if f.lower() == lib.lower():
                        LIBS[lib] = root + os.path.sep + f
                        break
            if LIBS[lib]:
                break

    # Pretty print with colors and all
    for k, v in sorted(LIBS.items(), key=lambda x: x[0]):
        if v is None:
            print '\x1B[37m\n', k, '\x1B[0m\n', '\x1B[31mNot Found\x1B[0m'
        else:
            print '\x1B[37m\n', k, '\x1B[0m\n', '\x1B[32m', v, '\x1B[0m'

    if not all(LIBS.values()):
        raise EnvironmentError('Not all dependencies found.\nMissing: {}'.format(
            ','.join([i[0] for i in LIBS.items() if i[1] is None])
        ))

    return LIBS


def make_folders():
    """Create the application's install folder structure.

    """
    if not os.path.isdir(PREFIX):
        os.makedirs(PREFIX)

    root = PREFIX + os.path.sep + u'bookmarks'
    if not os.path.isdir(root):
        os.makedirs(root)
    else:
        n = 0
        shutil.rmtree(root, ignore_errors=True)

        while True:
            try:
                os.makedirs(root)
            except:
                if n > 10:
                    if not os.path.isdir(root):
                        raise OSError('Could not create dir')
                    break
                time.sleep(0.2)
                n += 1


    if not os.path.isdir(root + os.path.sep + u'bin'):
        os.mkdir(root + os.path.sep + u'bin')
    if not os.path.isdir(root + os.path.sep + u'lib'):
        os.mkdir(root + os.path.sep + u'lib')
    if not os.path.isdir(root + os.path.sep + u'lib' + os.path.sep + 'site-packages'):
        os.mkdir(root + os.path.sep + u'lib' + os.path.sep + 'site-packages')
    if not os.path.isdir(root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'PySide2'):
        os.mkdir(root + os.path.sep + u'lib' + os.path.sep +
                 'site-packages' + os.path.sep + 'PySide2')
    if not os.path.isdir(root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'shiboken2'):
        os.mkdir(root + os.path.sep + u'lib' + os.path.sep +
                 'site-packages' + os.path.sep + 'shiboken2')
    if not os.path.isdir(root + os.path.sep + u'platforms'):
        os.mkdir(root + os.path.sep + u'platforms')
    if not os.path.isdir(root + os.path.sep + u'shared'):
        os.mkdir(root + os.path.sep + u'shared')


def copy_libs(libs):
    """Copy all the dependencies to the install directory."""
    root = PREFIX + os.path.sep + u'bookmarks'

    for k in libs:
        dest = root + os.path.sep + 'bin' + \
            os.path.sep + os.path.basename(libs[k])
        shutil.copy2(
            libs[k], dest)
        print libs[k], '>', dest

    pzip = os.path.dirname(__file__) + os.path.sep + 'python27.zip'
    if not os.path.isfile(pzip):
        raise RuntimeError('Python27.zip is missing')

    with zipfile.ZipFile(pzip, 'r') as zip:
        zip.extractall(path=root + os.path.sep + 'lib')
        print pzip, '>', root + os.path.sep + 'lib'

    for k in (
        LIB_ALEMBIC_D,
        LIB_IEX_D,
        LIB_IMATH_D,
    ):
        shutil.copy2(
            k,
            root + os.path.sep + 'lib' + os.path.sep + 'site-packages' + os.path.sep + os.path.basename(k))

    # PySide2
    shutil.copy2(
        LIB_QTCORE_D,
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'PySide2' + os.path.sep + os.path.basename(LIB_QTCORE_D))
    shutil.copy2(
        LIB_QTGUI_D,
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'PySide2' + os.path.sep + os.path.basename(LIB_QTGUI_D))
    shutil.copy2(
        LIB_QTWIDGETS_D,
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'PySide2' + os.path.sep + os.path.basename(LIB_QTWIDGETS_D))

    pyside_root = PYSIDE2_ROOT + os.path.sep + 'lib' + \
        os.path.sep + 'site-packages' + os.path.sep + 'PySide2'
    shutil.copy2(
        pyside_root + os.path.sep + '__init__.py',
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'PySide2' + os.path.sep + '__init__.py')

    # Shiboken
    shiboken_root = PYSIDE2_ROOT + os.path.sep + 'lib' + \
        os.path.sep + 'site-packages' + os.path.sep + 'shiboken2'
    shutil.copy2(
        shiboken_root + os.path.sep + 'shiboken2.pyd',
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'shiboken2' + os.path.sep + 'shiboken2.pyd')
    shutil.copy2(
        shiboken_root + os.path.sep + '__init__.py',
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' + os.path.sep + 'shiboken2' + os.path.sep + '__init__.py')
    copy_tree(
        shiboken_root + os.path.sep + 'files.dir',
        root + os.path.sep + u'lib' + os.path.sep + 'site-packages' +
        os.path.sep + 'shiboken2' + os.path.sep + 'files.dir'
    )

    # Qt5 platform
    shutil.copy2(
        QT5_ROOT + os.path.sep + 'plugins' + os.path.sep +
        'platforms' + os.path.sep + 'qwindows.dll',
        root + os.path.sep + u'platforms' + os.path.sep + 'qwindows.dll')

    shutil.copy2(
        LIB_OIIO_D,
        root + os.path.sep + 'shared' + os.path.sep + os.path.basename(LIB_OIIO_D))

    shutil.copy2(
        LIB_SCANDIR_D,
        root + os.path.sep + 'shared' + os.path.sep + os.path.basename(LIB_SCANDIR_D))



def build_bin():
    """Build the Bookmarks executable."""
    bindir = os.path.normpath(
        __file__ + os.path.sep + '..' + os.path.sep + 'bin')
    os.chdir(bindir)
    os.system(bindir + os.path.sep + 'make-bin.bat')
    if not os.path.isfile(bindir + os.path.sep + 'bookmarks.exe'):
        raise RuntimeError('bookmarks.exe not found')
    if not os.path.isfile(bindir + os.path.sep + 'bookmarks_d.exe'):
        raise RuntimeError('bookmarks_d.exe not found')
    shutil.copy2(
        bindir + os.path.sep + 'bookmarks.exe',
        PREFIX + os.path.sep + u'bookmarks' + os.path.sep + 'bookmarks.exe')
    shutil.copy2(
        bindir + os.path.sep + 'bookmarks_d.exe',
        PREFIX + os.path.sep + u'bookmarks' + os.path.sep + 'bookmarks_d.exe')
    shutil.move(
        PREFIX + os.path.sep + u'bookmarks' +
        os.path.sep + 'bin' + os.path.sep + 'python27.dll',
        PREFIX + os.path.sep + u'bookmarks' + os.path.sep + 'python27.dll',
    )
    os.remove(bindir + os.path.sep + 'bookmarks.exe')
    os.remove(bindir + os.path.sep + 'bookmarks_d.exe')


def install_python_modules():
    """Install python dependencies.

    Installed Modules:
        bookmarks:      The core python Bookmarks module.
        numpy:          Pre-prepared numpy distribution, see `numpy.zip`
        psutil:         Pre-prepared psutil distribution, see `psutil.zip`
        SlackClient:    Downloaded using pip.


    """
    root = PREFIX + os.path.sep + u'bookmarks'
    pzip = os.path.dirname(__file__) + os.path.sep + 'numpy.zip'
    if not os.path.isfile(pzip):
        raise RuntimeError('numpy.zip is missing')
    with zipfile.ZipFile(pzip, 'r') as zip:
        zip.extractall(path=root + os.path.sep +
                       'shared' + os.path.sep + 'numpy')
        print pzip, '>', root + os.path.sep + 'shared'

    pzip = os.path.dirname(__file__) + os.path.sep + 'psutil.zip'
    if not os.path.isfile(pzip):
        raise RuntimeError('psutil.zip is missing')
    with zipfile.ZipFile(pzip, 'r') as zip:
        zip.extractall(path=root + os.path.sep + 'shared')
        print pzip, '>', root + os.path.sep + 'shared'

    source = os.path.normpath(__file__ + os.path.sep + '..' + os.path.sep +
                              '..' + os.path.sep + '..' + os.path.sep + 'bookmarks')
    if not os.path.isdir(source):
        raise RuntimeError('bookmarks is missing.')
    copy_tree(
        source,
        PREFIX + os.path.sep + u'bookmarks' +
        os.path.sep + 'shared' + os.path.sep + 'bookmarks'
    )

    target = PREFIX + os.path.sep + u'bookmarks' + os.path.sep + 'shared'
    cmd = ur'pip install --target="{}" --compile --no-cache-dir SlackClient'.format(
        target)
    os.system(cmd)
    cmd = ur'pip install --target="{}" --compile --no-cache-dir git+git://github.com/shotgunsoftware/python-api.git'.format(
        target)
    os.system(cmd)

    p = root + os.path.sep + 'shared'
    for f in os.listdir(p):
        if 'dist-info' in f:
            shutil.rmtree(p + os.path.sep + f)


def inno_create_installer():
    """Package the install directory into a distributable installer file.

    See `installer.iss` for the windows installer definition.
    The installer script takes care of deploying Bookmarks and it will set
    automatically the BOOKMARKS_ROOT environment variable to point to the
    install root.

    """
    INNO_COMPILER = ur'C:\Program Files (x86)\Inno Setup 6\iscc.exe'
    if not os.path.isfile(INNO_COMPILER):
        raise ValueError('Could not find Inno Setup')

    p = os.path.dirname(__file__)
    os.chdir(p)
    cmd = u'"{}" .\\installer.iss'.format(INNO_COMPILER)
    os.system(cmd)

    import bookmarks
    import subprocess
    path = PREFIX + os.path.sep + 'Bookmarks_setup_{}.exe'.format(bookmarks.__version__)
    subprocess.Popen('"' + path + '"')


def verify_configuration():
    def _verify(l):
        if os.path.isfile(l):
            return
        if os.path.isdir(l):
            return
        sys.stderr.write('"{}" does not exist.\n'.format(l))
        return

    for k, v in globals().items():
        if k.endswith('_ROOT'):
            _verify(v)
        if k.startswith('LIB_'):
            _verify(v)

    _verify(VC_ROOT)
    _verify(VC_REDIST)
    _verify(DUMPBIN)
    _verify(PREFIX)

    sys.stdout.write('Configuration is valid')

if __name__ == '__main__':
    verify_configuration()
    make_folders()
    libs = get_dependencies()
    copy_libs(libs)
    build_bin()
    install_python_modules()
    inno_create_installer()
