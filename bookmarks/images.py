# -*- coding: utf-8 -*-
"""Module for most image related classes and methods including the
app's.

We're relying on ``OpenImageIO`` to generate image and movie thumbnails.
All generated thumbnails and UI resources are cached by ``ImageCache`` into ``image_cache``.

"""
import functools
import os
import time

import OpenImageIO
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import log

QT_IMAGE_FORMATS = {f.data().decode('utf8')
                    for f in QtGui.QImageReader.supportedImageFormats()}

mutex = QtCore.QMutex()

BufferType = QtCore.Qt.UserRole
PixmapType = BufferType + 1
ImageType = PixmapType + 1
IconType = ImageType + 1
ResourcePixmapType = IconType + 1
ColorType = ResourcePixmapType + 1

accepted_codecs = ('h.264', 'h264', 'mpeg-4', 'mpeg4')


def init_imagecache():
    common.oiio_cache = OpenImageIO.ImageCache(shared=True)
    common.oiio_cache.attribute('max_memory_MB', 4096.0)
    common.oiio_cache.attribute('max_open_files', 0)
    common.oiio_cache.attribute('trust_file_extensions', 1)

    common.image_resource_list = {
        common.GuiResource: [],
        common.ThumbnailResource: [],
        common.FormatResource: [],
    }
    common.image_resource_data = {}
    common.image_cache = {
        BufferType: {},
        PixmapType: {},
        ImageType: {},
        IconType: {},
        ResourcePixmapType: {},
        ColorType: {},
    }


def init_resources():
    for _source, k in ((common.get_rsc(f), f) for f in
                       (common.GuiResource, common.ThumbnailResource, common.FormatResource)):
        for _entry in os.scandir(_source):
            common.image_resource_list[k].append(_entry.name.split('.', maxsplit=1)[0])


def init_pixel_ratio():
    app = QtWidgets.QApplication.instance()
    if not app:
        log.error(
            '`init_pixel_ratio()` was called before a QApplication was created.')

    if app and common.pixel_ratio is None:
        common.pixel_ratio = app.primaryScreen().devicePixelRatio()
    else:
        common.pixel_ratio = 1.0


def wait_for_lock(source):
    t = 0.0
    while os.path.isfile(source + '.lock'):
        if t > 1.0:
            break
        time.sleep(0.1)
        t += 0.1


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
    for exts in extension_list.split(';'):
        exts = exts.split(':')
        _exts = exts[1].split(',')
        e = ['*.{}'.format(f) for f in _exts]
        namefilter = '{} files ({})'.format(exts[0].upper(), ' '.join(e))
        namefilters.append(namefilter)
        for _e in _exts:
            arr.append(_e)

    allfiles = ['*.{}'.format(f) for f in arr]
    allfiles = ' '.join(allfiles)
    allfiles = 'All files ({})'.format(allfiles)
    namefilters.insert(0, allfiles)
    return ';;'.join(namefilters)


def check_for_thumbnail_image(source):
    """Utility method for checking for the existance of a `thumbnail.ext` file
    in a source folder.

    Args:
        source (str):   Path to folder.

    Returns:
        str:    The path to the thumbnail file or `None` if not found.

    """
    # We'll rely on Qt5 to load the image without OpenImageIO so we'll query
    # supportedImageFormats() to get the list of valid image formats.
    for ext in QT_IMAGE_FORMATS:
        file_info = QtCore.QFileInfo(f'{source}/thumbnail.{ext}')
        if file_info.exists():
            return file_info.filePath()
    return None


def get_thumbnail(server, job, root, source, size=common.thumbnail_size, fallback_thumb='placeholder',
                  get_path=False):
    """Get the thumbnail of a given item.

    When an item is missing a bespoke cached thumbnail file, we will try to load
    a fallback image instead. For files, this will be an image associated with
    the file-format, or for asset and bookmark items, we will look in
    bookmark's, then the job's root folder to see if we can find a
    `thumbnail.png` file. When all lookup fails we'll return the provided
    `fallback_thumb`.

    See also :func:`get_cached_thumbnail_path()` for a lower level method used
    to find a cached image file.

    Args:
        server (str):        A server name.
        job (str):           A job name.
        root (str):          A root folder name.
        source (str):        Full file path of source item.
        size (int):              The size of the thumbnail image in pixels.
        fallback_thumb(str): A fallback thumbnail image.
        get_path (bool):         Returns a path instead of a QPixmap if set to `True`.

    Returns:
        tuple:                   `(QPixmap, QColor)`, or `(None, None)`.
        str:                 Path to the thumbnail file when `get_path=True`.


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

    size = int(round(size * common.pixel_ratio))

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

        thumb_path = check_for_thumbnail_image('/'.join(args[0:3]))
        if not thumb_path:
            thumb_path = check_for_thumbnail_image('/'.join(args[0:2]))

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
    # thumbnail file present in the source's root.
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
            s = 'Failed to remove existing thumbnail file.'
            raise RuntimeError(s)

    res = ImageCache.oiio_make_thumbnail(
        image,
        thumbnail_path,
        common.thumbnail_size
    )
    if not res:
        raise RuntimeError('Failed to make thumbnail.')

    ImageCache.flush(thumbnail_path)


def get_cached_thumbnail_path(server, job, root, source, proxy=False):
    """Returns the path to a cached thumbnail file.

    When `proxy` is set to `True` or the source file is a sequence, we will use
    the sequence's first item as our thumbnail source.

    Args:
        server (str):       The `server` segment of the file path.
        job (str):          The `job` segment of the file path.
        root (str):         The `root` segment of the file path.
        source (str):       The full file path.

    Returns:
        str:                The resolved thumbnail path.

    """
    for arg in (server, job, root, source):
        common.check_type(arg, str)

    if proxy or common.is_collapsed(source):
        source = common.proxy_path(source)
    name = common.get_hash(source) + '.' + common.thumbnail_format
    return server + '/' + job + '/' + root + '/' + common.bookmark_cache_dir + '/' + name


def get_placeholder_path(file_path, fallback='placeholder'):
    """Returns an image path used to represent an item.

    In absence of a custom user-set thumbnail, we'll try and find one based on
    the file's format extension.

    Args:
        file_path (str): Path to a file or folder.

    Returns:
        str: Path to the placeholder image.

    """
    common.check_type(file_path, str)

    def path(r, n):
        return common.get_rsc(f'{r}/{n}.{common.thumbnail_format}')

    file_info = QtCore.QFileInfo(file_path)
    suffix = file_info.suffix().lower()

    if suffix in common.image_resource_list[common.FormatResource]:
        path = path(common.FormatResource, suffix)
        return os.path.normpath(path)

    if fallback in common.image_resource_list[common.FormatResource]:
        path = path(common.FormatResource, fallback)
    elif fallback in common.image_resource_list[common.ThumbnailResource]:
        path = path(common.ThumbnailResource, fallback)
    elif fallback in common.image_resource_list[common.GuiResource]:
        path = path(common.GuiResource, fallback)
    else:
        path = path(common.GuiResource, 'placeholder')

    return os.path.normpath(path)


def invalidate(func):
    @functools.wraps(func)
    def func_wrapper(source, **kwargs):
        result = func(source, **kwargs)
        common.oiio_cache.invalidate(source, force=True)
        return result

    return func_wrapper


@invalidate
def oiio_get_buf(source, hash=None, force=False):
    """Check and load a source image with OpenImageIO's format reader.

    Args:
        source (str):       Path to an OpenImageIO compatible image file.
        hash (str):         Specify the hash manually, otherwise will be generated.
        force (bool):       When `true`, forces the buffer to be re-cached.

    Returns:
        ImageBuf: An `ImageBuf` instance or `None` if the file is invalid.

    """
    common.check_type(source, str)

    if hash is None:
        hash = common.get_hash(source)

    if not force and ImageCache.contains(hash, BufferType):
        return ImageCache.value(hash, BufferType)

    # We use the extension to initiate an ImageInput with a format
    # which in turn is used to check the source's validity
    if '.' not in source:
        return None
    ext = source.split('.').pop().lower()
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


def oiio_get_qimage(source, buf=None, force=True):
    """Load the pixel data using OpenImageIO and return it as a
    `RGBA8888` / `RGB888` QImage.

    Args:
        source (str):                 Path to an OpenImageIO readable image.
        buf (OpenImageIO.ImageBuf):     When buf is valid ImageBuf instance it will be used
                                        as the source instead of `source`. Defaults to `None`.

    Returns:
        QImage: An QImage instance or `None` if the image/source is invalid.

    """
    if buf is None:
        buf = oiio_get_buf(source, force=force)
        if buf is None:
            return None

    spec = buf.spec()
    if not int(spec.nchannels):
        return None
    if int(spec.nchannels) < 3:
        b = OpenImageIO.ImageBufAlgo.channels(
            buf,
            (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]),
            ('R', 'G', 'B')
        )
    elif int(spec.nchannels) > 4:
        if spec.channelindex('A') > -1:
            b = OpenImageIO.ImageBufAlgo.channels(
                buf, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
        else:
            b = OpenImageIO.ImageBufAlgo.channels(
                buf, ('R', 'G', 'B'), ('R', 'G', 'B'))

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
    image.setDevicePixelRatio(common.pixel_ratio)

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

    All cached images are stored in ``common.image_cache`` using a image
    cache type value.

    Loading image resources is done by `ImageCache.get_image()` and
    `ImageCache.get_pixmap()`. These methods automatically save data in the
    cache for later retrieval. The actual hashing and saving is done under the
    hood by `ImageCache.value()` and `ImageCache.setValue()` methods.

    GUI resources should be loaded with ``ImageCache.get_rsc_pixmap()``.

    """

    @classmethod
    def contains(cls, hash, cache_type):
        """Checks if the given hash exists in the database."""
        return hash in common.image_cache[cache_type]

    @classmethod
    def value(cls, hash, cache_type, size=None):
        """Get a value from the ImageCache.

        Args:
            hash (str): A hash value generated by `common.get_hash`

        """

        if not cls.contains(hash, cache_type):
            return None
        if size is not None:
            if size not in common.image_cache[cache_type][hash]:
                return None
            return common.image_cache[cache_type][hash][size]
        return common.image_cache[cache_type][hash]

    @classmethod
    def setValue(cls, hash, value, cache_type, size=None):
        """Sets a value in the ImageCache using `hash` and the `cache_type`.

        If force is `True`, we will flush the sizes stored in the cache before
        setting the new value. This only applies to Image- and PixmapTypes.

        """
        if not cls.contains(hash, cache_type):
            common.image_cache[cache_type][hash] = {}

        if cache_type == BufferType:
            common.check_type(value, OpenImageIO.ImageBuf)

            common.image_cache[BufferType][hash] = value
            return common.image_cache[BufferType][hash]

        elif cache_type == ImageType:
            common.check_type(value, QtGui.QImage)

            if size is None:
                raise ValueError('size cannot be `None`')

            if not isinstance(size, int):
                size = int(size)

            common.image_cache[cache_type][hash][size] = value
            return common.image_cache[cache_type][hash][size]

        elif cache_type in (PixmapType, ResourcePixmapType):
            common.check_type(value, QtGui.QPixmap)

            if not isinstance(size, int):
                size = int(size)

            common.image_cache[cache_type][hash][size] = value
            return common.image_cache[cache_type][hash][size]

        elif cache_type == ColorType:
            common.check_type(value, QtGui.QColor)

            common.image_cache[ColorType][hash] = value
            return common.image_cache[ColorType][hash]

        raise TypeError('`cache_type` is invalid.')

    @classmethod
    def flush(cls, source):
        """Flushes all values associated with a given source from the image cache.

        """
        hash = common.get_hash(source)
        for k in common.image_cache:
            if hash in common.image_cache[k]:
                del common.image_cache[k][hash]

    @classmethod
    def get_pixmap(cls, source, size, hash=None, force=False, oiio=False):
        """Loads, resizes `source` as a QPixmap and stores it for later use.

        When size is '-1' the full image will be loaded without resizing.

        The resource will be stored as a QPixmap instance in
        `common.image_cache[PixmapType][hash]`. The hash value is generated using
        `source`'s value but this can be overwritten by explicitly setting
        `hash`.

        Note:
            It is not possible to call this method outside the main gui thread.
            Use `get_image` instead. This method is backed by `get_image()`
            anyway.

        Args:
            source (str):   Path to an OpenImageIO compliant image file.
            size (int):     The size of the requested image.
            hash (str):     Use this hash key instead of a source's hash value to store the data.
            force (bool):   Force reload the pixmap.

        Returns:
            QPixmap: The loaded and resized QPixmap, or `None`.

        """
        if not QtGui.QGuiApplication.instance():
            raise RuntimeError(
                'Cannot create QPixmaps without a gui application.')

        common.check_type(source, str)

        app = QtWidgets.QApplication.instance()
        if app and app.thread() != QtCore.QThread.currentThread():
            s = 'Pixmaps can only be initiated in the main gui thread.'
            raise RuntimeError(s)

        if isinstance(size, float):
            size = int(round(size))

        if size == -1:
            buf = oiio_get_buf(source)
            spec = buf.spec()
            size = max((spec.width, spec.height))

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
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        if pixmap.isNull():
            return None
        cls.setValue(hash, pixmap, PixmapType, size=size)
        return pixmap

    @classmethod
    def get_color(cls, source, force=False):
        common.check_type(source, str)

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
    def make_color(cls, source, hash=None):
        """Calculate the average color of a source image."""
        locker = QtCore.QMutexLocker(mutex)
        wait_for_lock(source)

        buf = oiio_get_buf(source)
        if not buf:
            return None

        if hash is None:
            hash = common.get_hash(source)

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

        cls.setValue(hash, color, ColorType)

        return color

    @classmethod
    def get_image(cls, source, size, hash=None, force=False, oiio=False):
        """Loads, resizes `source` as a QImage and stores it for later use.

        When size is '-1' the full image will be loaded without resizing.

        The resource will be stored as QImage instance at
        `common.image_cache[ImageType][hash]`. The hash value is generated by default
        using `source`'s value but this can be overwritten by explicitly
        setting `hash`.

        Args:
            source (str):       Path to an OpenImageIO compliant image file.
            size (int):         The size of the requested image.
            hash (str):         Use this hash key instead source to store the data.
            force (bool):       Force reloads the image from the source.
            oiio (bool):        Use OpenImageIO to load the image data.

        Returns:
            QImage: The loaded and resized QImage, or `None` if loading fails.

        """
        common.check_type(source, str)

        if isinstance(size, float):
            size = int(round(size))

        if size == -1:
            buf = oiio_get_buf(source)
            spec = buf.spec()
            size = max((spec.width, spec.height))

        if hash is None:
            hash = common.get_hash(source)

        # Check the cache and return the previously stored value
        if not force and cls.contains(hash, ImageType):
            data = cls.value(hash, ImageType, size=size)
            if data:
                return data

        # If not yet stored, load and save the data
        if size != -1:
            buf = oiio_get_buf(source, hash=hash, force=force)
        if not buf:
            return None

        if oiio:
            image = oiio_get_qimage(source)
        else:
            image = QtGui.QImage(source)
            image.setDevicePixelRatio(common.pixel_ratio)

        if image.isNull():
            return None

        # Let's resize, but only if the source is bigger than the requested size
        # spec = buf.spec()
        # msize = max((spec.width, spec.height))

        # if size != -1 and size < msize:
        if size != -1:
            image = cls.resize_image(image, size)
        if image.isNull():
            return None

        # ...and store
        cls.setValue(hash, image, ImageType, size=size)

        # The loaded pixel values are cached by OpenImageIO automatically.
        # By invalidating the buf, we can ditch the cached data.
        common.oiio_cache.invalidate(source, force=True)
        common.oiio_cache.invalidate(buf.name, force=True)

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
        common.check_type(size, (int, float))
        common.check_type(image, QtGui.QImage)

        w = image.width()
        h = image.height()
        factor = float(size) / max(w, h)
        w *= factor
        h *= factor
        return image.smoothScaled(round(w), round(h))

    @classmethod
    def get_rsc_pixmap(cls, name, color, size, opacity=1.0, resource=common.GuiResource, get_path=False):
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
        common.check_type(name, str)
        common.check_type(color, (QtGui.QColor, None))

        source = common.get_rsc(f'{resource}/{name}.{common.thumbnail_format}')

        if get_path:
            file_info = QtCore.QFileInfo(source)
            return file_info.absoluteFilePath()

        _color = color.name() if isinstance(color, QtGui.QColor) else 'null'
        k = 'rsc:' + name + ':' + str(int(size)) + ':' + _color

        if k in common.image_resource_data:
            return common.image_resource_data[k]

        image = QtGui.QImage()
        image.setDevicePixelRatio(common.pixel_ratio)
        image.load(source)
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

        image = cls.resize_image(image, size * common.pixel_ratio)
        image.setDevicePixelRatio(common.pixel_ratio)

        # Setting transparency
        if opacity < 1.0:
            _image = QtGui.QImage(image)
            _image.setDevicePixelRatio(common.pixel_ratio)
            _image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter()
            painter.begin(_image)
            painter.setOpacity(opacity)
            painter.drawImage(0, 0, image)
            painter.end()
            image = _image

        # Finally, we'll convert the image to a pixmap
        pixmap = QtGui.QPixmap()
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.convertFromImage(image, flags=QtCore.Qt.ColorOnly)
        common.image_resource_data[k] = pixmap
        return common.image_resource_data[k]

    @classmethod
    def oiio_make_thumbnail(cls, source, destination, size, nthreads=3):
        """Converts `source` to an sRGB image fitting the bounds of `size`.

        Args:
            source (str): Source image's file path.
            destination (str): Destination of the converted image.
            size (int): The bounds to fit the converted image (in pixels).
            nthreads (int): Number of threads to use. Defaults to 4.

        Returns:
            bool: True if successfully converted the image.

        """
        log.debug('Converting {}...'.format(source), cls)

        def get_scaled_spec(source_spec):
            w = source_spec.width
            h = source_spec.height
            factor = float(size) / max(float(w), float(h))
            w *= factor
            h *= factor

            s = OpenImageIO.ImageSpec(int(w), int(h), 4, OpenImageIO.UINT8)
            s.channelnames = ('R', 'G', 'B', 'A')
            s.alpha_channel = 3
            s.attribute('oiio:ColorSpace', 'sRGB')
            s.attribute('oiio:Gamma', '0.454545')
            return s

        def shuffle_channels(buf, source_spec):
            if int(source_spec.nchannels) < 3:
                buf = OpenImageIO.ImageBufAlgo.channels(
                    buf,
                    (source_spec.channelnames[0], source_spec.channelnames[0],
                     source_spec.channelnames[0]),
                    ('R', 'G', 'B')
                )
            elif int(source_spec.nchannels) > 4:
                if source_spec.channelindex('A') > -1:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
                else:
                    buf = OpenImageIO.ImageBufAlgo.channels(
                        buf, ('R', 'G', 'B'), ('R', 'G', 'B'))
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
            colorspace = source_spec.get_string_attribute('oiio:ColorSpace')

            if source_spec.get_string_attribute('oiio:Movie') == 1:
                return
            try:
                if colorspace != 'sRGB':
                    buf = OpenImageIO.ImageBufAlgo.colorconvert(
                        buf, colorspace, 'sRGB')
            except:
                log.error('Could not convert the color profile')
            return buf

        buf = oiio_get_buf(source)
        if not buf:
            return False
        source_spec = buf.spec()
        if source_spec.get_int_attribute('oiio:Movie') == 1:
            codec_name = source_spec.get_string_attribute('ffmpeg:codec_name')
            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            if codec_name:
                if not [f for f in accepted_codecs if f.lower() in codec_name.lower()]:
                    log.debug(
                        'Unsupported movie format: {}'.format(codec_name))
                    common.oiio_cache.invalidate(source, force=True)
                    return False

        destination_spec = get_scaled_spec(source_spec)
        buf = shuffle_channels(buf, source_spec)
        buf = flatten(buf, source_spec)
        # buf = colorconvert(buf, source_spec)
        buf = resize(buf, source_spec)

        # if buf.nchannels > 3:
        # background_buf = OpenImageIO.ImageBuf(destination_spec)
        # OpenImageIO.ImageBufAlgo.checker(
        #     background_buf,
        #     12, 12, 1,
        #     (0.3, 0.3, 0.3),
        #     (0.2, 0.2, 0.2)
        # )
        # buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)

        spec = buf.spec()
        buf.set_write_format(OpenImageIO.UINT8)

        # The libpng seems to fussy about corrupted and invalid ICC profiles and
        # OpenImageIO seems to interpret warning about these as errors that
        # bring python down. Removing the ICC profile seems to fix the issue.
        spec.erase_attribute('.*icc||ccp.*', casesensitive=True)

        # On some dpx images I'm getting "GammaCorrectedinf"
        if spec.get_string_attribute('oiio:ColorSpace') == 'GammaCorrectedinf':
            spec['oiio:ColorSpace'] = 'sRGB'
            spec['oiio:Gamma'] = '0.454545'

        # Initiating a new spec with the modified spec
        _buf = OpenImageIO.ImageBuf(spec)
        _buf.copy_pixels(buf)
        _buf.set_write_format(OpenImageIO.UINT8)

        if not QtCore.QFileInfo(QtCore.QFileInfo(destination).path()).isWritable():
            common.oiio_cache.invalidate(source, force=True)
            common.oiio_cache.invalidate(destination, force=True)
            log.error('Destination path is not writable')
            return False

        # Create a lock file before writing
        with open(destination + '.lock', 'w', encoding='utf8') as _f:
            pass

        success = _buf.write(destination, dtype=OpenImageIO.UINT8)
        os.remove(destination + '.lock')

        if not success:
            s = '{}\n{}'.format(
                buf.geterror(),
                OpenImageIO.geterror())
            log.error(s)

            if not QtCore.QFile(destination).remove():
                log.error('Cleanup failed.')

            common.oiio_cache.invalidate(source, force=True)
            common.oiio_cache.invalidate(destination, force=True)
            return False

        common.oiio_cache.invalidate(source, force=True)
        common.oiio_cache.invalidate(destination, force=True)
        return True
