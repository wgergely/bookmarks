"""Definitions of bookmark, asset, file item view and model.

Each view derives from :class:`.view.ThreadedItemView`, a heavily
customized QListView widget. The view are rendered by :class:`.delegate.ItemDelegate` and
data is served by :class:`.model.ItemModel` instances.

See the item specific submodules for more information:

* :mod:`~bookmarks.items.bookmark_items`
* :mod:`~bookmarks.items.asset_items`
* :mod:`~bookmarks.items.file_items`

To customize the items served by a model take a look at
:meth:`.model.ItemModel.item_generator` and :meth:`.model.ItemModel.init_data` methods.

The :mod:`~bookmarks.common` module offers shortcuts for accessing item view and model:

.. code-block:: python
    :linenos:

    from bookmarks import common

    widget = common.widget(common.BookmarkTab)
    model = common.model(common.BookmarkTab)
    source_model = common.source_model(common.BookmarkTab)


"""
