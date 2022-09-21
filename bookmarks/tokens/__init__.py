"""``Tokens`` are properties associated with bookmark items and hold some generic file
and folder definitions of asset items.

This information can be used, for instance, to suggest default save locations
for scenes and caches, or to set format filters based on file types.
This is useful when browsing files as we might want to exclude image files inside a
``scenes`` folder, or vice-versa, we might only want to show cache files when browsing a
``cache`` folder, but not images.

The values stored in tokens config also allow generating custom file names based on
the values set in the bookmark item database. See :meth:`.TokenConfig.expand_tokens`.

The token values are stored in the bookmark item's database using the 'tokens' column.
Values can be set programmatically using either the :mod:`bookmarks.tokens.tokens`
interface or the ui elements defined in :mod:`bookmarks.tokens.tokens_editor`. These
editor widgets are embedded in the standard bookmark item editor widget.

"""