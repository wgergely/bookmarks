"""Definitions of the core bookmark, asset, file item list widgets and their
respective models.

Each list item widget derives from :class:`.views.ThreadedBaseWidget`, a heavily
customized QListView widget. The views are rendered by :class:`.delegate.BaseDelegate` and
data is served by :class:`.models.BaseModel` instances.


Hint
----

To customize which items are read and how they're displayed, take a look at
:meth:`.models.BaseModel.item_generator` and :meth:`.models.BaseModel.init_data`
methods and their implementation in the item models.

"""
