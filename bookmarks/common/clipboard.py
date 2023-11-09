"""Internal clipboard data.

"""
from . import core


BookmarkPropertyClipboard = core.idx(start=0, reset=True)
AssetPropertyClipboard = core.idx()
ThumbnailClipboard = core.idx()


CLIPBOARD = {
    BookmarkPropertyClipboard: {},
    AssetPropertyClipboard: {},
    ThumbnailClipboard: {},
}
