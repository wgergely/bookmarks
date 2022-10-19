"""The module defines :class:`.ImageCache`, a utility class used to store image and color data and
all other utility methods needed to create, load and store thumbnail images.

Use the high-level :func:`get_thumbnail` to get an item's thumbnail. This relies on the
:class:`ImageCache` to retrieve data and will return an existing thumbnail image or a
suitable placeholder image. See  :func:`get_placeholder_path`.

Note:
    The thumbnail files are stored in the bookmark item cache folder (see
    ``common.bookmark_cache_dir``).

Under the hood, :func:`get_thumbnail` uses :meth:`ImageCache.get_pixmap` and
:meth:`ImageCache.get_image`.

We're using OpenImageIO to generate thumbnails. See :meth:`ImageCache.oiio_make_thumbnail`.
To load an image using OpenImageIO as a QtGui.QImage see :func:`oiio_get_qimage`.

To load gui resources, use :meth:`.ImageCache.rsc_pixmap`.

"""
import functools
import os
import threading
import time

import OpenImageIO
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import log

#: The list of image formats QT is configured to read.
QT_IMAGE_FORMATS = {f.data().decode('utf8')
                    for f in QtGui.QImageReader.supportedImageFormats()}

lock = threading.RLock()

BufferType = QtCore.Qt.UserRole
PixmapType = BufferType + 1
ImageType = PixmapType + 1
IconType = ImageType + 1
ResourcePixmapType = IconType + 1
ColorType = ResourcePixmapType + 1

accepted_codecs = ('h.264', 'h264', 'mpeg-4', 'mpeg4')


def get_cache_size():
    v = common.get_py_obj_size(common.oiio_cache)
    v += common.get_py_obj_size(common.image_resource_data)
    v += common.get_py_obj_size(common.image_cache)
    return v


def init_image_cache():
    """Initialises the OpenImageIO and our own internal image cache.

    """
    common.oiio_cache = OpenImageIO.ImageCache(True)
    common.oiio_cache.attribute('max_memory_MB', 4096.0)
    common.oiio_cache.attribute('max_open_files', 0)
    common.oiio_cache.attribute('trust_file_extensions', 1)
    common.oiio_cache.attribute('forcefloat', 1)

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
    """Initialises the GUI image resources.

    """
    for _source, k in ((common.rsc(f), f) for f in
                       (common.GuiResource, common.ThumbnailResource,
                        common.FormatResource)):
        for _entry in os.scandir(_source):
            common.image_resource_list[k].append(_entry.name.split('.', maxsplit=1)[0])


def init_pixel_ratio():
    """Initialises the pixel ratio value.

    """
    app = QtWidgets.QApplication.instance()
    if not app:
        log.error(
            '`init_pixel_ratio()` was called before a QApplication was created.')

    if app and common.pixel_ratio is None:
        common.pixel_ratio = app.primaryScreen().devicePixelRatio()
    else:
        common.pixel_ratio = 1.0


def get_thumbnail(server, job, root, source, size=common.thumbnail_size,
                  fallback_thumb='placeholder',
                  get_path=False):
    """Get the thumbnail of a list item.

    When an item is missing a bespoke cached thumbnail file, we will try to load
    a fallback image instead. For files, this will be an image associated with
    the file-format, or for asset and bookmark items, we will look in
    bookmark's, then the job's root folder to see if we can find a
    `thumbnail.png` file. When all lookup fails we'll return the provided
    `fallback_thumb`.

    See also :func:`get_cached_thumbnail_path()` for a lower level method used
    to find a cached image file.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        source (str): Full file path of source item.
        size (int): The size of the thumbnail image in pixels.
        fallback_thumb(str): A fallback thumbnail image.
        get_path (bool): Returns a path instead of a QPixmap if set to `True`.

    Returns:
        tuple:                   `(QPixmap, QColor)`, or `(None, None)`.
        str:                 Path to the thumbnail file when `get_path=True`.


    """
    if not all((server, job, root, source)):
        if get_path:
            return None
        return (None, None)

    def _get(server, job, root, source, proxy):
        path = get_cached_thumbnail_path(
            server, job, root, source, proxy=proxy)
        with lock:
            pixmap = ImageCache.get_pixmap(path, size)
        if not pixmap or pixmap.isNull():
            return (path, None, None)
        with lock:
            color = ImageCache.get_color(path)
        if not color:
            return (path, pixmap, None)
        return (path, pixmap, color)

    size = int(round(size * common.pixel_ratio))

    args = (server, job, root)

    # In the simplest of all cases, the source has a bespoke thumbnail saved we
    # can return outright.

    thumbnail_path, pixmap, color = _get(server, job, root, source, False)
    if pixmap and not pixmap.isNull() and get_path:
        return thumbnail_path
    if pixmap and not pixmap.isNull():
        return (pixmap, color)

    # If this item is an un-collapsed sequence item, the sequence
    # might have a thumbnail instead.
    thumbnail_path, pixmap, color = _get(server, job, root, source, True)
    if pixmap and not pixmap.isNull() and get_path:
        return thumbnail_path
    if pixmap and not pixmap.isNull():
        return (pixmap, color)

    # If the item refers to a folder, e.g. an asset or a bookmark item,  we'll
    # check for a 'thumbnail.{ext}' file in the folder's root and if this fails,
    # we will check the job folder. If both fails will we proceed to load a
    # placeholder thumbnail.
    if common.is_dir(source):
        _hash = common.get_hash(source)

        n = 3
        while n >= 1:
            thumb_path = f'{"/".join(args[0:n])}/thumbnail.{common.thumbnail_format}'
            pixmap = ImageCache.get_pixmap(
                thumb_path,
                size,
                hash=_hash
            )
            if pixmap and get_path:
                return thumb_path
            if pixmap:
                with lock:
                    color = ImageCache.get_color(
                        thumb_path,
                        hash=_hash,
                    )
                return pixmap, color
            n -= 1

    # Let's load a placeholder if there's no generated thumbnail or
    # thumbnail file present in the source's root.
    thumb_path = get_placeholder_path(source, fallback_thumb)
    pixmap = ImageCache.get_pixmap(thumb_path, size)
    if pixmap and not pixmap.isNull() and get_path:
        return thumb_path

    if pixmap and not pixmap.isNull():
        return pixmap, None

    # In theory, we will never get here as get_placeholder_path should always
    # return a valid pixmap
    if get_path:
        return None
    return (None, None)


def wait_for_lock(source, timeout=1.0):
    """Waits for a maximum amount of time when a lock file is present.

    Args:
        source (str): A file path.
        timeout (float): The maximum amount of time to wait in seconds.

    """
    t = 0.0
    while os.path.isfile(f'{source}.lock'):
        if t > timeout:
            break
        time.sleep(0.1)
        t += 0.1


@functools.lru_cache(maxsize=4194304)
def get_oiio_extensions():
    """Returns a list of extensions accepted by OpenImageIO.

    """
    v = OpenImageIO.get_string_attribute('extension_list')
    extensions = []
    for e in [f.split(':')[1] for f in v.split(';')]:
        extensions += e.split(',')
    return sorted(extensions)


@functools.lru_cache(maxsize=4194304)
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


@common.error
@common.debug
def create_thumbnail_from_image(server, job, root, source, image, proxy=False):
    """Creates a thumbnail from a given image file and saves it as the source
    file's thumbnail image.

    The ``server``, ``job``, ``root``, ``source`` arguments refer to a file we
    want to create a new thumbnail for. The ``image`` argument should be a path to
    an image file that will be converted using :func:`oiio_make_thumbnail()` to a
    thumbnail image and saved to our image cache and disk to represent ``source``.

    Args:
         server (str): `server` path segment.
         job (str): `job` path segment.
         root (str): `root` path segment.
         source (str): The full file path.
         image (str): Path to an image file to use as a thumbnail for ``source``.
         proxy (bool, optional): Specify if the source is an image sequence and if
                the proxy path should be used to save the thumbnail instead.

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


@functools.lru_cache(maxsize=4194304)
def get_cached_thumbnail_path(server, job, root, source, proxy=False):
    """Returns the path to a cached thumbnail file.

    When `proxy` is set to `True` or the source file is a sequence, we will use
    the sequence's first item as our thumbnail source.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        source (str): The full file path.

    Returns:
        str:                The resolved thumbnail path.

    """
    for arg in (server, job, root, source):
        common.check_type(arg, str)

    if proxy or common.is_collapsed(source):
        source = common.proxy_path(source)
    name = common.get_hash(source) + '.' + common.thumbnail_format
    return f'{server}/{job}/{root}/{common.bookmark_cache_dir}/thumbnails/{name}'


@functools.lru_cache(maxsize=4194304)
def get_placeholder_path(file_path, fallback):
    """Returns an image path used to represent an item.

    In absence of a custom user, or generated thumbnail, we'll try and find one based on
    the file's format extension.

    Args:
        file_path (str): Path to a file or folder.
        fallback (str): An image to use if no suitable placeholder is found.

    Returns:
        str: Path to the placeholder image.

    """
    common.check_type(file_path, str)

    def _path(r, n):
        return common.rsc(f'{r}/{n}.{common.thumbnail_format}')

    file_info = QtCore.QFileInfo(file_path)
    suffix = file_info.suffix().lower()

    if suffix in common.image_resource_list[common.FormatResource]:
        path = _path(common.FormatResource, suffix)
        return os.path.normpath(path)

    if fallback in common.image_resource_list[common.FormatResource]:
        path = _path(common.FormatResource, fallback)
    elif fallback in common.image_resource_list[common.ThumbnailResource]:
        path = _path(common.ThumbnailResource, fallback)
    elif fallback in common.image_resource_list[common.GuiResource]:
        path = _path(common.GuiResource, fallback)
    else:
        path = _path(common.GuiResource, 'placeholder')

    return os.path.normpath(path)


def oiio_get_buf(source, hash=None, force=False, subimage=0):
    """Checks and loads a source image with OpenImageIO's format reader.


    Args:
        source (str): Path to an OpenImageIO compatible image file.
        hash (str): Specify the hash manually, otherwise will be generated.
        force (bool): When `true`, forces the buffer to be re-cached.

    Returns:
        ImageBuf: An `ImageBuf` instance or `None` if the image cannot be read.

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
    ext = source.split('.')[-1].lower()
    if ext not in get_oiio_extensions():
        return None
    i = OpenImageIO.ImageInput.create(ext)
    if not i or not i.valid_file(source):
        i.close()
        return None

    # If all went well, we can initiate an ImageBuf
    config = OpenImageIO.ImageSpec()
    config.format = OpenImageIO.TypeDesc(OpenImageIO.FLOAT)

    buf = OpenImageIO.ImageBuf()
    buf.reset(source, subimage, 0, config=config)
    if buf.has_error:
        log.error(buf.geterror())
        return None

    ImageCache.setValue(hash, buf, BufferType)
    return buf


def oiio_get_qimage(source, buf=None, force=True):
    """Load the pixel data using OpenImageIO and return it as a
    `RGBA8888` / `RGB888` QImage.

    Args:
        source (str): Path to an OpenImageIO readable image.
        buf (OpenImageIO.ImageBuf): When buf is valid ImageBuf instance it will be used
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

    You shouldn't have to use the :meth:`value` and :meth:`setValue` methods. Instead,
    use the :meth:`get_image` and :meth:`get_pixmap` - they're high-level functions, that
    will automatically cache and convert resources.

    The stored data is associated with a `type` and `hash` (see
    :func:`~bookmarks.common.core.get_hash`) and `size`. This means a single source image can have
    multiple QPixmap and QImage cache entries as various sizes are requested and cached.

    .. code-block:: python
        :linenos:

        common.image_cache[cache_type][hash][size] = pixmap

    To remove a resource from the cache use the :meth:`flush` method.

    """

    @classmethod
    def flush(cls, source):
        """Flushes all values associated with a given source from the image cache.

        Args:
            source (str): A file path.

        """
        hash = common.get_hash(source)

        for k in common.image_cache:
            if hash in common.image_cache[k]:
                del common.image_cache[k][hash]

    @classmethod
    def get_image(cls, source, size, hash=None, force=False, oiio=False):
        """Loads, resizes `source` as a QImage and stores it for later use.

        When size is '-1' the full image will be loaded without resizing.

        The resource will be stored as QImage instance at
        `common.image_cache[ImageType][hash]`. The hash value is generated by default
        using `source`'s value but this can be overwritten by explicitly
        setting `hash`.

        Args:
            source (str): Path to an OpenImageIO compliant image file.
            size (int): The size of the requested image.
            hash (str): Use this hash key instead source to store the data.
            force (bool): Force reloads the image from source.
            oiio (bool): Use OpenImageIO to load the image data.

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
        # wait_for_lock(source)
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
        return image

    @classmethod
    def get_pixmap(cls, source, size, hash=None, force=False, oiio=False):
        """Loads, resizes `source` as a QPixmap and stores it for later use.

        When size is '-1' the full image will be loaded without resizing.

        The resource will be stored as a QPixmap instance and saved to
        :attr:`common.image_cache[PixmapType][hash]`. The hash value is generated using
        ``source`` but this can be overwritten by explicitly setting ``hash``.

        Note:
            It is not possible to call this method outside the main gui thread.
            Use :meth:`get_image` instead. This method is backed by :meth:`get_image`
            anyway.

        Args:
            source (str): Path to an image file.
            size (int): The size of the requested image.
            hash (str): Use this hash key instead of a source's hash value to store the data.
            force (bool): Force reloads the pixmap.
            oiio (bool): Use OpenImageIO to load the image, instead of Qt.

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
            if not buf:
                return None
            spec = buf.spec()
            size = max((spec.width, spec.height))

        # Check the cache and return the previously stored value if exists
        if hash is None:
            hash = common.get_hash(source)
        contains = cls.contains(hash, PixmapType)
        if not force and contains:
            data = cls.value(hash, PixmapType, size=size)
            if data:
                return data

        # We'll load a cache a QImage to use as the basis for the QPixmap. This
        # is because of how the thread affinity of QPixmaps don't permit use
        # outside the main gui thread
        image = cls.get_image(source, size, hash=hash, force=force, oiio=oiio)
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
    def contains(cls, _hash, cache_type):
        """Checks if the given hash exists in the database."""
        return _hash in common.image_cache[cache_type]

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
                raise ValueError('Invalid size value.')

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
    def get_color(cls, source, hash=None, force=False):
        """Gets a cached QColor associated with the given source.

        Args:
            source (str): A file path.
            force (bool): Force value recache.
            hash (str): Hash value override.

        """
        common.check_type(source, str)

        # Check the cache and return the previously stored value if exists
        if hash is None:
            hash = common.get_hash(source)

        if not cls.contains(hash, ColorType):
            return cls.make_color(source, hash=hash)
        elif cls.contains(hash, ColorType) and not force:
            return cls.value(hash, ColorType)
        elif cls.contains(hash, ColorType) and force:
            return cls.make_color(source, hash=hash)
        return None

    @classmethod
    def make_color(cls, source, hash=None):
        """Calculate the average color of a source image.

        Args:
            source (str): Path to an image file.
            hash (str, optional): Has value to use instead of source image's hash.

        Returns:
            QtGui.QImage: The average color of the source image.

        """
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
    def rsc_pixmap(cls, name, color, size, opacity=1.0, resource=common.GuiResource,
                   get_path=False, oiio=False):
        """Loads an image resource and returns it as a resized (and recolored) QPixmap.

        Args:
            name (str): Name of the resource without the extension.
            color (QColor or None): The color of the icon.
            size (int or None): The size of pixmap.
            opacity (float): Sets the opacity of the returned pixmap.
            resource (str): Optional resource type. Default: common.GuiResource.
            get_path (bool): Returns a path when True.

        Returns:
            A QPixmap of the requested resource, or a str path if ``get_path`` is True.
            None if the resource could not be found.

        """
        common.check_type(name, str)
        common.check_type(color, (None, QtGui.QColor))
        common.check_type(size, (None, float, int))
        common.check_type(opacity, float)

        source = common.rsc(f'{resource}/{name}.{common.thumbnail_format}')

        if get_path:
            file_info = QtCore.QFileInfo(source)
            return file_info.absoluteFilePath()

        size = size if isinstance(size, (float, int)) else -1
        _color = color.name() if isinstance(color, QtGui.QColor) else 'null'
        k = 'rsc:' + name + ':' + str(int(size)) + ':' + _color

        if k in common.image_resource_data:
            return common.image_resource_data[k]

        image = cls.get_image(source, size, oiio=oiio)
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
    def oiio_make_thumbnail(cls, source, destination, size, nthreads=2):
        """Converts the `source` image to an sRGB image fitting the bounds of
        `size` and saves it to `destination`.

        If size is `-1`, the image won't be resized.

        Args:
            source (str): Source image's file path.
            destination (str): Destination of the converted image.
            size (int): The bounds to fit the converted image (in pixels).
            nthreads (int): Number of threads to use. Defaults to 4.

        Returns:
            bool: True if successfully converted the image, False otherwise.

        """
        _lock_path = f'{destination}.lock'
        if os.path.isfile(_lock_path):
            return

        log.debug(f'Converting {source}...', cls)
        open(_lock_path, 'a', encoding='utf8')

        def _get_scaled_spec(source_spec):
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

        def _shuffle_channels(buf, source_spec):
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

        def _resize(buf, destination_spec):
            return OpenImageIO.ImageBufAlgo.resample(
                buf, roi=destination_spec.roi, interpolate=True, nthreads=nthreads)

        def _flatten(buf, source_spec):
            if source_spec.get_int_attribute('deep', defaultval=-1) != 1:
                return buf
            if source_spec.deep:
                buf = OpenImageIO.ImageBufAlgo.flatten(buf, nthreads=nthreads)
            return buf

        def _colorconvert(buf, source_spec):
            if source_spec.get_int_attribute('oiio:Movie') == 1:
                return buf
            colorspace = source_spec.get_string_attribute('oiio:ColorSpace')
            try:
                if colorspace == 'linear':
                    buf = OpenImageIO.ImageBufAlgo._colorconvert(
                        buf, colorspace, 'sRGB')
            except:
                log.error('Could not convert the color profile')
            return buf

        def _checker(buf, source_spec, destination_spec):
            if source_spec.get_int_attribute('oiio:Movie', defaultval=-1) == 1:
                return buf
            if buf.nchannels <= 3:
                return buf
            background_buf = OpenImageIO.ImageBuf(destination_spec)
            OpenImageIO.ImageBufAlgo._checker(
                background_buf,
                12, 12, 1,
                (0.3, 0.3, 0.3),
                (0.2, 0.2, 0.2)
            )
            buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)
            return buf

        buf = oiio_get_buf(source)
        if not buf:
            common.oiio_cache.invalidate(source, force=True)
            os.remove(_lock_path)
            return False

        source_spec = buf.spec()

        # The LibPNG seems to be fussy about corrupted and invalid ICC profiles
        # and OpenImageIO seems to interpret warning about these as errors that
        # causes the interpreter to crash. Removing the ICC profile seems to fix
        # the issue. Also, OpenImageIO seems to have a bug when trying to
        # explicitly erase the attribute. The workaround seems to be to set the
        # attribute value prior to deleting it.
        source_spec['ICCProfile'] = 0
        source_spec.erase_attribute('ICCProfile')

        if source_spec.get_int_attribute('oiio:Movie', defaultval=-1) == 1:
            # Load the middle frame of the video
            buf = oiio_get_buf(source, subimage=int(buf.nsubimages / 2))

            is_gif = source_spec.get_int_attribute('gif:LoopCount', defaultval=-1) >= 0

            # I'm having issues working with very short movie files - that contain only a couple of frames,
            # so, let's ignore those (gifs are fine)
            if not is_gif and source_spec.get_int_attribute('oiio:subimages',
                                                            defaultval=-1) <= 2:
                common.oiio_cache.invalidate(source, force=True)
                os.remove(_lock_path)
                return False

            # [BUG] Not all codec formats are supported by ffmpeg. There does
            # not seem to be (?) error handling and an unsupported codec will
            # crash ffmpeg and the rest of the app.
            codec_name = source_spec.get_string_attribute('ffmpeg:codec_name')
            if not is_gif and codec_name:
                if not [f for f in accepted_codecs if f.lower() in codec_name.lower()]:
                    log.debug(f'Unsupported movie format: {codec_name}')
                    common.oiio_cache.invalidate(source, force=True)
                    os.remove(_lock_path)
                    return False

        destination_spec = _get_scaled_spec(source_spec)
        if size != -1:
            buf = _resize(buf, destination_spec)
        buf = _shuffle_channels(buf, source_spec)
        buf = _flatten(buf, source_spec)
        buf = _colorconvert(buf, source_spec)
        # buf = _checker(buf, source_spec, destination_spec)

        spec = buf.spec()
        buf.set_write_format(OpenImageIO.UINT8)

        # On some dpx images I'm getting "GammaCorrectedinf"
        if 'gammacorrectedinf' in spec.get_string_attribute('oiio:ColorSpace').lower():
            spec['oiio:ColorSpace'] = 'sRGB'
            spec['oiio:Gamma'] = '0.454545'

        # Create a lock file before writing
        success = buf.write(destination, dtype=OpenImageIO.UINT8)
        os.remove(_lock_path)

        if not success:
            log.error(f'{buf.geterror()}\n{OpenImageIO.geterror()}')

            if not QtCore.QFile(destination).remove():
                log.error('Cleanup failed.')

            common.oiio_cache.invalidate(source, force=True)
            return False

        common.oiio_cache.invalidate(source, force=True)
        return True
