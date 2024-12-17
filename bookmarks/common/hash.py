import functools
import hashlib

from .. import common


@functools.lru_cache(maxsize=4194304)
def get_hash(key):
    """Calculates the md5 hash of a string.

    Generates unique hashes for file paths. These
    hashes are used by the `ImageCache`, `user_settings` and `BookmarkDB` to
    associate data with the file items. Generated hashes are server agnostic,
    meaning, if the passed string contains a known server's name, it is removed
    before hashing.

    Args:
        key (str): A key string to calculate a md5 hash for.

    Returns:
        str: MD5 hexadecimal digest of the key.

    """
    # Path mustn't contain backslashes
    if '\\' in key:
        key = key.replace('\\', '/')

    for s in common.servers:
        if s not in key:
            continue

        l = len(s)
        if key[:l] == s:
            key = key[l:]
            key = key.lstrip('/')
            break

    # Otherwise, we calculate, save, and return the digest
    return hashlib.md5(key.encode('utf8')).hexdigest()
