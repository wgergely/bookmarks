"""Defines the base model used to display bookmark, asset and files items.

The model loads and reset data via the :meth:`ItemModel.init_data()` and
:meth:`ItemModel.reset_data()` methods.

The model itself does not store data, but all retrieved data is cached independently to
:attr:`bookmarks.common.item_data`. The interface for getting and
setting data can be found in the :mod:`bookmarks.common.data`. However, the model is
responsible for populating the data cache. See :meth:`.ItemModel.item_generator()`.

The model exposes different datasets to the view using the :meth:`ItemModel.task` and
:meth:`ItemModel.data_type` switches. This is because file items are stored as sequence
and individual items simultaneously and because the file model also keeps separate data
for each task folder it encounters.

The currently exposed data can be retrieved by :meth:`.ItemModel.model_data()`. To
change/set the data set emit the :attr:`.ItemModel.taskFolderChanged` and
:attr:`.ItemModel.dataTypeChanged` signals with their appropriate arguments.

Worth keeping in mind that Bookmarks loads data in two passes. The model is responsible
for discovering items, but will not populate all item the data, and instead uses helper
threads to offload work. The model's associated threads are defined by overriding
:attr:`.ItemModel.queues`.

Each base model is nested inside a QSortFilterProxy used for filtering **only**. Sorting
is implemented separately to run directly over the source data.

"""
