from . import base


class FavouriteItemViewDelegate(base.ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.favourite_items.FavouriteItemView` items.

    """
    fallback_thumb = 'favourite_item'
