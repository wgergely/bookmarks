"""Definitions of bookmark, asset, file item views and models.

Each view derives from :class:`.views.ThreadedItemView`, a heavily
customized QListView widget. The views are rendered by :class:`.delegate.ItemDelegate` and
data is served by :class:`.models.ItemModel` instances.

See the item specific submodules for more information:

* :mod:`~bookmarks.items.bookmark_items`
* :mod:`~bookmarks.items.asset_items`
* :mod:`~bookmarks.items.file_items`

To customize the items served by a model take a look at
:meth:`.models.ItemModel.item_generator` and :meth:`.models.ItemModel.init_data` methods.

"""
