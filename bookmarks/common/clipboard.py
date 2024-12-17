"""Internal clipboard data.

"""
__all__ = [
    'BookmarkPropertyClipboard',
    'AssetPropertyClipboard',
    'ThumbnailClipboard',
    'AssetLinksClipboard',
    'get_clipboard',
    'clear_clipboard',
    'set_clipboard',
]

from . import core

BookmarkPropertyClipboard = core.idx(start=0, reset=True)
AssetPropertyClipboard = core.idx()
ThumbnailClipboard = core.idx()
AssetLinksClipboard = core.idx()

CLIPBOARD = {
    BookmarkPropertyClipboard: {},
    AssetPropertyClipboard: {},
    ThumbnailClipboard: {},
    AssetLinksClipboard: [],
}


def get_clipboard(clipboard_type):
    if clipboard_type not in CLIPBOARD:
        raise ValueError(f'Unknown clipboard type: {clipboard_type}')
    return CLIPBOARD[clipboard_type]


def clear_clipboard(clipboard_type):
    if clipboard_type not in CLIPBOARD:
        raise ValueError(f'Unknown clipboard type: {clipboard_type}')
    CLIPBOARD[clipboard_type].clear()


def set_clipboard(clipboard_type, data):
    if clipboard_type not in CLIPBOARD:
        raise ValueError(f'Unknown clipboard type: {clipboard_type}')
    CLIPBOARD[clipboard_type] = data
