from . import base


class FileItemViewDelegate(base.ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.file_items.FileItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'file_item'
