from . import base
from ... import common, database


class BookmarkItemViewDelegate(base.ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.bookmark_items.BookmarkItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'icon_bw_sm'

    def setEditorData(self, editor, index):
        source_path = index.data(common.ParentPathRole)
        if not source_path:
            return

        # Get the database value
        db = database.get(*source_path[0:3])
        v = db.value(db.source(), 'description', database.AssetTable)

        editor.setText(v)

    def setModelData(self, editor, model, index):
        from ...threads import workers

        text = f'{index.data(common.DescriptionRole)}'
        if text.lower() == editor.text().lower():
            return
        source_path = index.data(common.ParentPathRole)
        if not source_path:
            return

        p = index.data(common.PathRole)
        if common.is_collapsed(p):
            k = common.proxy_path(index)
        else:
            k = p

        # Set the database value
        db = database.get(*source_path[0:3])
        v = editor.text().strip() if editor.text() else ''
        with db.connection():
            db.set_value(k, 'description', common.sanitize_hashtags(v), database.AssetTable)
            bookmark_row_data = db.get_row(db.source(), database.BookmarkTable)

        # Set value to cached data
        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()
        idx = source_index.row()

        data[idx][common.DescriptionRole] = v
        data[idx][common.DescriptionRole] = workers.get_bookmark_description(
            bookmark_row_data
        )
