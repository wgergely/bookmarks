# -*- coding: utf-8 -*-
"""Module for most image related classes and methods including the
app's.

Thumbnails:
    We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
    Thumbnail operations are multi-threaded.

    See ``ImageCache.oiio_make_thumbnail()`` for the OpenImageIO wrapper for
    generating thubmanails.

All generated thumbnails and ui resources are cached in ``ImageCache``.

"""
import time
import os
import functools
import OpenImageIO
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common


THUMBNAIL_IMAGE_SIZE = 512.0
THUMBNAIL_FORMAT = u'png'
PLACEHOLDER_PATH = u'{}/../rsc/{}/{}.{}'

mutex = QtCore.QMutex()

pixel_ratio = None

oiio_cache = OpenImageIO.ImageCache(shared=True)
oiio_cache.attribute(u'max_memory_MB', 4096.0)
oiio_cache.attribute(u'max_open_files', 0)
oiio_cache.attribute(u'trust_file_extensions', 1)


BufferType = QtCore.Qt.UserRole
PixmapType = BufferType + 1
ImageType = PixmapType + 1
ResourcePixmapType = ImageType + 1
ColorType = ResourcePixmapType + 1

_capture_widget = None
_library_widget = None
_filedialog_widget = None
_viewer_widget = None

accepted_codecs = (u'h.264', u'h264', u'mpeg-4', u'mpeg4')


GuiResource = u'gui'
ThumbnailResource = u'thumbnails'
FormatResource = u'formats'


RESOURCES = {
    GuiResource: [],
    ThumbnailResource: [],
    FormatResource: [],
}


def reset():
    global RESOURCES
    RESOURCES = {
        GuiResource: [],
        ThumbnailResource: [],
        FormatResource: [],
    }
    ImageCache.COLOR_DATA = common.DataDict()
    ImageCache.RESOURCE_DATA = common.DataDict()
    ImageCache.PIXEL_DATA = common.DataDict()
    ImageCache.INTERNAL_DATA = common.DataDict({
        BufferType: common.DataDict(),
        PixmapType: common.DataDict(),
        ImageType: common.DataDict(),
        ResourcePixmapType: common.DataDict(),
        ColorType: common.DataDict(),
    })


def init_resources():
    global RESOURCES
    for _source, k in ((os.path.normpath(os.path.abspath(u'{}/../rsc/{}'.format(__file__, f))), f) for f in (GuiResource, ThumbnailResource, FormatResource)):
        for _entry in _scandir.scandir(_source):
            RESOURCES[k].append(_entry.name.split(u'.')[0])


def get_oiio_extensions():
    """Returns a list of extensions accepted by OpenImageIO.

    """
    v = OpenImageIO.get_string_attribute('extension_list')
    extensions = []
    for e in [f.split(':')[1] for f in v.split(';')]:
        extensions += e.split(',')
    return sorted(extensions)


def get_oiio_namefilters():
    """Gets all accepted formats from the oiio build as a namefilter list.
    Use the return value on the QFileDialog.setNameFilters() method.

    """
    extension_list = OpenImageIO.get_string_attribute('extension_list')
    namefilters = []
    arr = []
    for exts in extension_list.split(u';'):
        exts = exts.split(u':')
        _exts = exts[1].split(u',')
        e = [u'*.{}'.format(f) for f in _exts]
        namefilter = u'{} files ({})'.format(exts[0].upper(), u' '.join(e))
        namefilters.append(namefilter)
        for _e in _exts:
            arr.append(_e)

    allfiles = [u'*.{}'.format(f) for f in arr]
    allfiles = u' '.join(allfiles)
    allfiles = u'All files ({})'.format(allfiles)
    namefilters.insert(0, allfiles)
    return u';;'.join(namefilters)


def check_for_thumbnail_image(source):
    """Utility method for checking for the existance of a `thumbnail.ext` file
    in a source folder.

    Args:
        source (unicode):   Path to folder.

    Returns:
        unicode:    The path to the thumbnail file or `None` if not found.

    """
    # We'll rely on Qt5 to load the image without OpenImageIO so we'll query
    # supportedImageFormats() to get the list of valid image formats.
    for ext in [f.data() for f in QtGui.QImageReader.supportedImageFormats()]:
        file_info = QtCore.QFileInfo(u'{}/thumbnail.{}'.format(source, ext))
        if file_info.exists():
            return file_info.filePath()
    return None


def get_thumbnail(server, job, root, source, size=THUMBNAIL_IMAGE_SIZE, fallback_thumb=u'placeholder', get_path=False):
    """Loads a thumbnail for a given item.

    When an item is missing a bespoke cached thumbnail file, we will try to load
    a fallback image instead. For files, this will be an image associated with
    the file-format, or for asset and bookmark items, we will look in
    bookmark's, then the job's root folder to see if we can find a
    `thumbnail.png` file. When all lookup fails we'll return the provided
    `fallback_thumb`.

    See also :func:`get_cached_thumbnail_path()` for a lower level method used
    to find a cached image file.

    Args:
        server (unicode):        A server name.
        job (unicode):           A job name.
        root (unicode):          A root folder name.
        source (unicode):        Full file path of source item.
        size (int):              The size of the thumbnail image in pixels.
        fallback_thumb(unicode): A fallback thumbnail image.
        get_path (bool):         Returns a path instead of a QPixmap if set to `True`.

    Returns:
        tuple:                   QPixmap and QColor, or (`None`, `None)`.
        unicode:                 Path to the thumbnail file when `get_path` is `True`.


    """
    if not all((server, job, root, source)):
        if get_path:
            return None
        return (None, None)

    def get(server, job, root, source, proxy):
        thumbnail_path = get_cached_thumbnail_path(
            server, job, root, source, proxy=proxy)

        pixmap = ImageCache.get_pixmap(thumbnail_path, size)
        if not pixmap or pixmap.isNull():
            return (thumbnail_path, None, None)

        color = ImageCache.get_color(thumbnail_path)
        if not color:
            return (thumbnail_path, pixmap, None)

        return (thumbnail_path, pixmap, color)

    # if isinstance(size, (long, float)):
    #     size = int(round(size))
    size = int(round(size * pixel_ratio))

    args = (server, job, root)

    # In the simplest of all cases, the source has a bespoke thumbnail saved we
    # can return outright.
    thumbnail_path, pixmap, color = get(server, job, root, source, False)
    if pixmap and not pixmap.isNull() and get_path:
        return thumbnail_path
    if pixmap and not pixmap.isNull():
        return (pixmap, color)

    # If this item is an un-collapsed sequence item, the sequence
    # might have a thumbnail instead.
    thumbnail_path, pixmap, color = get(server, job, root, source, True)
    if pixmap and not pixmap.isNull() and get_path:
        return thumbnail_path
    if pixmap and not pixmap.isNull():
        return (pixmap, color)

    # If the item refers to a folder, eg. an asset or a bookmark item,  we'll
    # check for a 'thumbnail.{ext}' file in the folder's root and if this fails,
    # we will check the job folder. If both fails will we proceed to load a
    # placeholder thumbnail.
    if QtCore.QFileInfo(source).isDir():
        _hash = common.get_hash(source)

        thumb_path = check_for_thumbnail_image(u'/'.join(args[0:3]))
        if not thumb_path:
            thumb_path = check_for_thumbnail_image(u'/'.join(args[0:2]))

        if thumb_path:
            pixmap = ImageCache.get_pixmap(
                thumb_path,
                size,
                hash=_hash
            )
            if pixmap and get_path:
                return thumb_path
            if pixmap:
                color = ImageCache.get_color(thumb_path)
                return pixmap, color

    # Let's load a placeholder if there's no generated thumbnail or
    # tumbnail file present in the source's root.
    thumb_path = get_placeholder_path(source, fallback=fallback_thumb)
    pixmap = ImageCache.get_pixmap(thumb_path, size)
    if pixmap and not pixmap.isNull() and get_path:
        return thumb_path

    if pixmap:
        if not pixmap.isNull():
            return pixmap, None

    # In theory we will never get here as get_placeholder_path will always
    # return a valid pixmap
    if get_path:
        return None
    return (None, None)


@common.error
@common.debug
def load_thumbnail_from_image(server, job, root, source, image, proxy=False):
    """Loads an image from a given image path and cache to to `ImageCache` to be
    associated with `source`.

    """
    thumbnail_path = get_cached_thumbnail_path(
        server, job, root, source, proxy=proxy)
    if QtCore.QFileInfo(thumbnail_path).exists():
        if not QtCore.QFile(thumbnail_path).remove():
            s = u'Failed to remove existing thumbnail file.'
            raise RuntimeError(s)

    res = ImageCache.oiio_make_thumbnail(
        image,
        thumbnail_path,
        THUMBNAIL_IMAGE_SIZE
    )
    if not res:
        raise RuntimeError(u'Failed to make thumbnail.')

    ImageCache.flush(thumbnail_path)


def get_cached_thumbnail_path(server, job, root, source, proxy=False):
    """Returns the path to a cached thumbnail file.

    When `proxy` is set to `True` or the source file is a sequence, we will use
    the sequence's first item as our thumbnail source.

    Args:
        server (unicode):       The `server` segment of the file path.
        job (unicode):          The `job` segment of the file path.
        root (unicode):         The `root` segment of the file path.
        source (unicode):       The full file path.

    Returns:
        unicode:                The resolved thumbnail path.

    """
    for arg in (server, job, root, source):
        if not isinstance(arg, unicode):
            raise TypeError(
                'Invalid type. Expected {}, got {}'.format(unicode, type(arg)))

    if proxy or common.is_collapsed(source):
        source = common.proxy_path(source)
    name = common.get_hash(source) + u'.' + THUMBNAIL_FORMAT
    return server + u'/' + job + u'/' + root + u'/' + common.BOOKMARK_ROOT_DIR + u'/' + name


def get_placeholder_path(file_path, fallback=u'placeholder'):
    """Returns an image path used to represent an item.

    In absense of a custom user-set thumbnail, we'll try and find one based on
    the file's format extension.

    Args:
        file_path (unicode): Path to a file or folder.

    Returns:
        unicode: Path to the placehoder image.

    """
    if not isinstance(file_path, unicode):
        raise TypeError(
            u'Invalid type. Expected {}, got {}'.format(unicode, type(file_path)))

    def path(r, n):
        return PLACEHOLDER_PATH.format(
            __file__, r, n, THUMBNAIL_FORMAT
        )

    file_info = QtCore.QFileInfo(file_path)
    suffix = file_info.suffix().lower()

    if suffix in RESOURCES[FormatResource]:
        path = path(FormatResource, suffix)
    else:
        if fallback in RESOURCES[FormatResource]:
            path = path(FormatResource, fallback)
        elif fallback in RESOURCES[ThumbnailResource]:
            path = path(ThumbnailResource, fallback)
        elif fallback in RESOURCES[GuiResource]:
            path = path(GuiResource, fallback)
        else:
            path = path(GuiResource, u'placeholder')

    return os.path.normpath(os.path.abspath(path)).replace(u'\\', u'/')


def invalidate(func):
    @functools.wraps(func)
    def func_wrapper(source, **kwargs):
        result = func(source, **kwargs)
        oiio_cache.invalidate(source, force=True)
        return result
    return func_wrapper


@invalidate
def oiio_get_buf(source, hash=None, force=False):
    """Check and load a source image with OpenImageIO's format reader.

    Args:
        source (unicode):   Path to an OpenImageIO compatible image file.
        hash (str):         Defaults to `None`.
        force (bool):       When true, forces the buffer to be re-cached.

    Returns:
        ImageBuf: An `ImageBuf` instance or `None` if the file is invalid.

    """
    if not isinstance(source, unicode):
        raise TypeError(
            u'Expected {}, got {}'.format(unicode, type(source)))
    if hash is None:
        hash = common.get_hash(source)

    if not force and ImageCache.contains(hash, BufferType):
        return ImageCache.value(hash, BufferType)

    # We use the extension to initiate an ImageInput with a format
    # which in turn is used to check the source's validity
    if u'.' not in source:
        return None
    ext = source.split(u'.').pop().lower()
    i = OpenImageIO.ImageInput.create(ext)
    if not i:
        return None
    if not i.valid_file(source):
        i.close()
        return None

    # If all went well, we can initiate an ImageBuf
    i.close()
    buf = OpenImageIO.ImageBuf()
    buf.reset(source, 0, 0)
    if buf.has_error:
        return None

    ImageCache.setValue(hash, buf, BufferType)
    return buf


def oiio_get_qimage(path, buf=None, force=True):
    """Load the pixel data using OpenImageIO and return it as a
    `RGBA8888` / `RGB888` QImage.

    Args:
        path (unicode):                 Path to an OpenImageIO readable image.
        buf (OpenImageIO.ImageBuf):     When buf is valid ImageBuf instance it will be used
                                        as the source instead of `path`. Defaults to `None`.

    Returns:
        QImage: An QImage instance or `None` if the image/path is invalid.

    """
    if buf is None:
        buf = oiio_get_buf(path, force=force)
        oiio_cache.invalidate(path, force=True)
        if buf is None:
            return None

    # Cache this would require some serious legwork
    # Return the cached version if exists
    # hash = common.get_hash(buf.name)
    # if not force and hash in ImageCache.PIXEL_DATA:
    #     return ImageCache.PIXEL_DATA[hash]

    spec = buf.spec()
    if not int(spec.nchannels):
        return None
    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            buf,
            (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]),
            (u'R', u'G', u'B')
        )
    elif int(spec.nchannels) > 4:
        if spec.channelindex(u'A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B', u'A'), (u'R', u'G', u'B', u'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                b, (u'R', u'G', u'B'), (u'R', u'G', u'B'))

    np_arr = buf.get_pixels(OpenImageIO.UINT8)
    # np_arr = (np_arr / (1.0 / 255.0)).astype(np.uint8)

    if np_arr.shape[2] == 1:
        _format = QtGui.QImage.Format_Grayscale8
    if np_arr.shape[2] == 2:
        _format = QtGui.QImage.Format_Invalid
    elif np_arr.shape[2] == 3:
        _format = QtGui.QImage.Format_RGB888
    elif np_arr.shape[2] == 4:
        _format = QtGui.QImage.Format_RGBA8888
    elif np_arr.shape[2] > 4:
        _format = QtGui.QImage.Format_Invalid

    image = QtGui.QImage(
        np_arr,
        spec.width,
        spec.height,
        spec.width * spec.nchannels,  # scanlines
        _format
    )

    # The loaded pixel values are cached by OpenImageIO automatically.
    # By invalidating the buf, we can ditch the cached data.
    oiio_cache.invalidate(path, force=True)
    oiio_cache.invalidate(buf.name, force=True)

    # As soon as the numpy array is garbage collected, the data for QImage becomes
    # unusable and Qt5 crashes. This could possibly be a bug, I would expect,
    # the data to be copied automatically, but by making a copy
    # the numpy array can safely be GC'd
    return image.copy()


class ImageCache(QtCore.QObject):
    """Utility class for storing, and accessing image data.

    The stored data is associated with a `type` and `hash` value.  The hash
    values are generated by `common.get_hash` based on input file paths and are
    used to associate multiple image cached image sizes with a source image.

    All cached images are stored in ``ImageCache.INTERNAL_DATA`` using a image
    cache type value.

    Loading image resources is done by `ImageCache.get_image()` and
    `ImageCache.get_pixmap()`. These methods automatically save data in the
    cache for later retrieval. The actual hashing and saving is done under the
    hood by `ImageCache.value()` and `ImageCache.setValue()` methods.

    GUI resources should be loaded with ``ImageCache.get_rsc_pixmap()``.

    """
    COLOR_DATA = common.DataDict()
    RESOURCE_DATA = common.DataDict()
    PIXEL_DATA = common.DataDict()
    INTERNAL_DATA = common.DataDict({
        BufferType: common.DataDict(),
        PixmapType: common.DataDict(),
        ImageType: common.DataDict(),
        ResourcePixmapType: common.DataDict(),
        ColorType: common.DataDict(),
    })

    @classmethod
    def contains(cls, hash, cache_type):
        """Checks if the given hash exists in the database."""
        return hash in cls.INTERNAL_DATA[cache_type]

    @classmethod
    def value(cls, hash, cache_type, size=None):
        """Get a value from the ImageCache.

        Args:
            hash (str): A hash value generated by `common.get_hash`

        """

        if not cls.contains(hash, cache_type):
            return None
        if size is not None:
            if size not in cls.INTERNAL_DATA[cache_type][hash]:
                return None
            return cls.INTERNAL_DATA[cache_type][hash][size]
        return cls.INTERNAL_DATA[cache_type][hash]

    @classmethod
    def setValue(cls, hash, value, cache_type, size=None):
        """Sets a value in the ImageCache using `hash` and the `cache_type`.

        If force is `True`, we will flush the sizes stored in the cache before
        setting the new value. This only applies to Image- and PixmapTypes.

        """
        if not cls.contains(hash, cache_type):
            cls.INTERNAL_DATA[cache_type][hash] = common.DataDict()

        if cache_type == BufferType:
            if not isinstance(value, OpenImageIO.ImageBuf):
                raise TypeError(
                    u'Invalid type. Expected <type \'ImageBuf\'>, got {}'.format(type(value)))

            cls.INTERNAL_DATA[BufferType][hash] = value
            return cls.INTERNAL_DATA[BufferType][hash]

        elif cache_type == ImageType:
            if not isinstance(value, QtGui.QImage):
                raise TypeError(
                    u'Invalid type. Expected {}, got {}'.format(QtGui.QImage, type(value)))
            if size is None:
                raise ValueError(u'Invalid size')

            if not isinstance(size, int):
                size = int(size)

            cls.INTERNAL_DATA[cache_type][hash][size] = value
            return cls.INTERNAL_DATA[cache_type][hash][size]

        elif cache_type == PixmapType or cache_type == ResourcePixmapType:
            if not isinstance(value, QtGui.QPixmap):
                raise TypeError(
                    u'Invalid type. Expected <type \'QPixmap\'>, got {}'.format(type(value)))

            if not isinstance(size, int):
                size = int(size)

            cls.INTERNAL_DATA[cache_type][hash][size] = value
            return cls.INTERNAL_DATA[cache_type][hash][size]

        elif cache_type == ColorType:
            if not isinstance(value, QtGui.QColor):
                raise TypeError(
                    u'Invalid type. Expected <type \'QColor\'>, got {}'.format(type(value)))

            cls.INTERNAL_DATA[ColorType][hash] = value
            return cls.INTERNAL_DATA[ColorType][hash]
        else:
            raise TypeError('Invalid cache type.')

    @classmethod
    def flush(cls, source):
        """Flushes all values associated with a given source from the image cache.

        """
        hash = common.get_hash(source)
        for k in cls.INTERNAL_DATA:
            if hash in cls.INTERNAL_DATA[k]:
                del cls.INTERNAL_DATA[k][hash]

    @classmethod
    def get_pixmap(cls, source, size, hash=None, force=False):
        """Loads, resizes `source` as a QPixmap and stores it for later use.

        The resource will be stored as a QPixmap instance in
        `INTERNAL_DATA[PixmapType][hash]`. The hash value is generated using
        `source`'s value but this can be overwritten by explicitly setting
        `hash`.

        Note:
            It is not possible to call this method outside the main gui thread.
            Use `get_image` instead. This method is backed by `get_image()`
            anyway.

        Args:
            source (unicode):   Path to an OpenImageIO compliant image file.
            size (int):         The size of the requested image.
            hash (str):         Use this hash key instead of a source's hash value to store the data.

        Returns:
            QPixmap: The loaded and resized QPixmap, or `None`.

        """
        if not QtGui.QGuiApplication.instance():
            raise RuntimeError(
                u'Cannot create QPixmaps without a gui application.')

        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected {}, got {}'.format(
                unicode, type(source)))

        app = QtWidgets.QApplication.instance()
        if app and app.thread() != QtCore.QThread.currentThread():
            s = u'Pixmaps can only be initiated in the main gui thread.'
            raise RuntimeError(s)

        if isinstance(size, (float, long)):
            size = int(round(size))

        # Check the cache and return the previously stored value if exists
        hash = common.get_hash(source)
        contains = cls.contains(hash, PixmapType)
        if not force and contains:
            data = cls.value(hash, PixmapType, size=size)
            if data:
                return data

        # We'll load a cache a QImage to use as the basis for the qpixmap. This
        # is because of how the thread affinity of QPixmaps don't permit use
        # outside the main gui thread
        image = cls.get_image(source, size, hash=hash, force=force)
        if not image:
            return None

        pixmap = QtGui.QPixmap()
        pixmap.setDevicePixelRatio(pixel_ratio)
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        if pixmap.isNull():
            return None
        cls.setValue(hash, pixmap, PixmapType, size=size)
        return pixmap

    @classmethod
    def get_color(cls, source, force=False):
        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected {}, got {}.'.format(unicode, type(source)))

        # Check the cache and return the previously stored value if exists
        _hash = common.get_hash(source)

        if not cls.contains(_hash, ColorType):
            return cls.make_color(source)
        elif cls.contains(_hash, ColorType) and not force:
            return cls.value(_hash, ColorType)
        elif cls.contains(_hash, ColorType) and force:
            return cls.make_color(source)
        return None

    @classmethod
    def make_color(cls, source):
        """Calculate the average color of a source image."""
        locker = QtCore.QMutexLocker(mutex)

        buf = oiio_get_buf(source)
        if not buf:
            return None

        _hash = common.get_hash(source)

        stats = OpenImageIO.ImageBufAlgo.computePixelStats(buf)
        if not stats:
            return None
        if stats.avg and len(stats.avg) > 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[1] * 255),
                int(stats.avg[2] * 255),
                a=240
                # a=int(stats.avg[3] * 255)
            )
        elif stats.avg and len(stats.avg) == 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[1] * 255),
                int(stats.avg[2] * 255),
            )
        elif stats.avg and len(stats.avg) < 3:
            color = QtGui.QColor(
                int(stats.avg[0] * 255),
                int(stats.avg[0] * 255),
                int(stats.avg[0] * 255),
            )
        else:
            return None

        cls.setValue(_hash, color, ColorType)
        return color

    @classmethod
    def get_image(cls, source, size, hash=None, force=False):
        """Loads, resizes `source` as a QImage and stores it for later use.

        The resource will be stored as QImage instance at
        `INTERNAL_DATA[ImageType][hash]`. The hash value is generated by default
        using `source`'s value but this can be overwritten by explicitly
        setting `hash`.

        Args:
            source (unicode):   Path to an OpenImageIO compliant image file.
            size (int):         The size of the requested image.
            hash (str):         Use this hash key instead source to store the data.

        Returns:
            QImage: The loaded and resized QImage, or `None` if loading fails.

        """
        locker = QtCore.QMutexLocker(mutex)

        # The thumbnail might be being written by a thread worker
        t = 0.0
        while os.path.isfile(source + '.lock'):
            if t > 1.0:
                break
            time.sleep(0.1)
            t += 0.1

        if not isinstance(source, unicode):
            raise TypeError(u'Invalid type. Expected {}, got {}.'.format(
                unicode, type(source)))

        if isinstance(size, (float, long)):
            size = int(round(size))

        if hash is None:
            hash = common.get_hash(source)

        # Check the cache and return the previously stored value
        if not force and cls.contains(hash, ImageType):
            data = cls.value(hash, ImageType, size=size)
            if data:
                return data

        # If not yet stored, load and save the data
        buf = oiio_get_buf(source, hash=hash, force=force)
        if not buf:
            return None

        image = QtGui.QImage(source)
        image.setDevicePixelRatio(pixel_ratio)
        if image.isNull():
            return None

        # Let's resize...
        image = cls.resize_image(image, size)
        if image.isNull():
            return None

        # ...and store
        cls.setValue(hash, image, ImageType, size=size)
        return image

    @staticmethod
    def resize_image(image, size):
        """Returns a scaled copy of the image that fits in size.

        Args:
            image (QImage): The image to rescale.
            size (int): The size of the square to fit.

        Returns:
            QImage: The resized copy of the original image.

        """
        if not isinstance(size, (int, float)):
            raise TypeError(u'Invalid size.')
        if not isinstance(image, QtGui.QImage):
            raise TypeError(
                u'Expected a <type \'QtGui.QImage\'>, got {}.'.format(type(image)))

        w = image.width()
        h = image.height()
        factor = float(size) / max(w, h)
        w *= factor
        h *= factor
        return image.smoothScaled(round(w), round(h))

    @classmethod
    def get_rsc_pixmap(cls, name, color, size, opacity=1.0, resource=GuiResource, get_path=False):
        """Loads an image resource and returns it as a sized (and recolored) QPixmap.

        Args:
            name (str):         Name of the resource without the extension.
            color (QColor):     The colour of the icon.
            size (int):         The size of pixmap.
            opacity (float):    Sets the opacity of the returned pixmap.
            get_path (bool):    Returns the path to the image instead of a pixmap.

        Returns:
            QPixmap: The loaded image.

        """
        source = u'{}/../rsc/{}/{}.png'.format(__file__, resource, name)
        file_info = QtCore.QFileInfo(source)

        if get_path:
            return file_info.absoluteFilePath()

        if not file_info.exists():
            return QtGui.QPixmap()

        k = u'rsc:{name}:{size}:{color}'.format(
            name=name,
            size=int(size),
            color=u'null' if not color else color.name()
        )

        if k in cls.RESOURCE_DATA:
            return cls.RESOURCE_DATA[k]

        image = QtGui.QImage()
        image.setDevicePixelRatio(pixel_ratio)
        image.load(file_info.filePath())
        if image.isNull():
            return QtGui.QPixmap()

        # Do a re-color pass on the source image
        if color is not None:
            painter = QtGui.QPainter()
            painter.begin(image)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(image.rect())
            painter.end()

        image = cls.resize_image(image, size * pixel_ratio)
        image.setDevicePixelRatio(pixel_ratio)

        # Setting transparency
        if opacity < 1.0:
            _image = QtGui.QImage(image)
            _image.setDevicePixelRatio(pixel_ratio)
            _image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(_image)
            painter.setOpacity(opacity)
            painter.drawImage(0, 0, image)
            painter.end()
            image = _image

        # Finally, we'll convert the image to a pixmap
        pixmap = QtGui.QPixmap()
        pixmap.setDevicePixelRatio(pixel_ratio)
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        cls.RESOURCE_DATA[k] = pixmap
        return cls.RESOURCE_DATA[k]

    @classmethod
    def oiio_make_thumbnail(cls, source, destination, size, nthreads=3):
        """Converts `source` to an sRGB image fitting the bounds of `size`.

        Args:
            source (unicode): Source image's file path.
            destination (unicode): Destination of the converted image.
            size (int): The bounds to fit the converted image (in pixels).
            nthreads (int): Number of threads to use. Defaults to 4.

        Returns:
            bool: True if successfully converted the image.

        """
        log.debug(u'Converting {}...'.format(source), cls)

        def get_scaled_spec(source_spec):
            w = source_spec.width
            h = source_spec.height
            factor = float(size) / max(float(w), float(h))
            w *= factor
            h *= factor

            s = OpenImageIO.ImageSpec(int(w), int(h), 4, OpenImageIO.UINT8)
            s.channelnames = (u'R', u'G', u'B', u'A')
            s.alpha_channel = 3
            s.attribute(u'oiio:ColorSpace', u'sRGB')
            s.attribute(u'oiio:Gamma', u'0.454545')
            return s

        def shuffle_channels(buf, source_spec):
            if int(source_spec.nchannels) < 3:
                buf = OpenImageIO.ImageBufAlgo.channels(
                    buf,
                    (source_spec.channelnames[0], source_spec.channelnames[0],
                     source_spec.channelnames[0]),
                    (u'R', u'G', u'B')
                )
            elif int(source_spec.nchannels) > 4:
                if source_spec.channelindex(u'A') > -1:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, (u'R', u'G', u'B', u'A'), (u'R', u'G', u'B', u'A'))
                else:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, (u'R', u'G', u'B'), (u'R', u'G', u'B'))
            return buf

        def resize(buf, source_spec):
            buf = OpenImageIO.ImageBufAlgo.resample(
                buf, roi=destination_spec.roi, interpolate=True, nthreads=nthreads)
            return buf

        def flatten(buf, source_spec):
            if source_spec.deep:
                buf = OpenImageIO.ImageBufAlgo.flatten(buf, nthreads=nthreads)
            return buf

        def colorconvert(buf, source_spec):
            colorspace = source_spec.get_string_attribute(u'oiio:ColorSpace')

            if source_spec.get_string_attribute(u'oiio:Movie') == 1:
                return
            try:
                if colorspace != u'sRGB':
                    buf = OpenImageIO.ImageBufAlgo.colorconvert(
                        buf, colorspace, u'sRGB')
            except:
                log.error(u'Could not convert the color profile')
            return buf

        buf = oiio_get_buf(source)
        if not buf:
            return False
        source_spec = buf.spec()
        if source_spec.get_int_attribute(u'oiio:Movie') == 1:
            codec_name = source_spec.get_string_attribute(u'ffmpeg:codec_name')
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            if codec_name:
                if not [f for f in accepted_codecs if f.lower() in codec_name.lower()]:
                    log.debug(
                        u'Unsupported movie format: {}'.format(codec_name))
                    oiio_cache.invalidate(source, force=True)
                    return False

        destination_spec = get_scaled_spec(source_spec)
        buf = shuffle_channels(buf, source_spec)
        buf = flatten(buf, source_spec)
        # buf = colorconvert(buf, source_spec)
        buf = resize(buf, source_spec)

        if buf.nchannels > 3:
            background_buf = OpenImageIO.ImageBuf(destination_spec)
            OpenImageIO.ImageBufAlgo.checker(
                background_buf,
                12, 12, 1,
                (0.3, 0.3, 0.3),
                (0.2, 0.2, 0.2)
            )
            buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)

        spec = buf.spec()
        buf.set_write_format(OpenImageIO.UINT8)

        # There seems to be a problem with the ICC profile exported from Adobe
        # applications and the PNG library. The sRGB profile seems to be out of
        # date and pnglib crashes when encounters an invalid profile. Removing
        # the ICC profile seems to fix the issue.
        _spec = OpenImageIO.ImageSpec()
        _spec.from_xml(spec.to_xml())  # this doesn't copy the extra attributes
        for i in spec.extra_attribs:
            # There's a strange bug I'm seeing with OIIO where python hits a
            # buffer overrun, integer value is bigger than sys.maxsize, or
            # something like that.
            try:
                if i.name.lower() == u'iccprofile':
                    continue
                _spec[i.name] = i.value
            except:
                continue
        spec = _spec

        # On some dpx images I'm getting "GammaCorrectedinf"
        if spec.get_string_attribute(u'oiio:ColorSpace') == u'GammaCorrectedinf':
            spec[u'oiio:ColorSpace'] = u'sRGB'
            spec[u'oiio:Gamma'] = u'0.454545'

        # Initiating a new spec with the modified spec
        _buf = OpenImageIO.ImageBuf(spec)
        _buf.copy_pixels(buf)
        _buf.set_write_format(OpenImageIO.UINT8)

        if not QtCore.QFileInfo(QtCore.QFileInfo(destination).path()).isWritable():
            oiio_cache.invalidate(source, force=True)
            oiio_cache.invalidate(destination, force=True)
            log.error(u'Destination path is not writable')
            return False

        # Create a lock file before writing
        open(destination + '.lock', 'w').close()
        success = _buf.write(destination, dtype=OpenImageIO.UINT8)
        os.remove(destination + '.lock')

        if not success:
            s = u'{}\n{}'.format(
                buf.geterror(),
                OpenImageIO.geterror())
            log.error(s)

            if not QtCore.QFile(destination).remove():
                log.error(u'Cleanup failed.')

            oiio_cache.invalidate(source, force=True)
            oiio_cache.invalidate(destination, force=True)
            return False

        oiio_cache.invalidate(source, force=True)
        oiio_cache.invalidate(destination, force=True)
        return True
