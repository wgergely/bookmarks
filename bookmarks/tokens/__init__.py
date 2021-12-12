"""``Tokens`` are properties associated with a bookmark item that permits defining
descriptions and roles of project files and folders.

This information can be used, for instance, to suggest a default save locations
for scenes and caches, or to exclude/include format types when browsing files. The
rational is that we might not want to see image files in a ``scenes`` folder,
or vice-versa, we might only want to see cache files when browsing a ``cache``
folder. These associations can be defined in the bookmarks item's properties, using
either the :mod:`bookmarks.tokens.tokens` interface or the ui elements defined in
:mod:`bookmarks.tokens.tokens_editor`.

The values stored in tokens config also allow generating custom file names based on
the values set in the bookmark item database. See
:meth:`.TokenConfig.expand_tokens`.

"""