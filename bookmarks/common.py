# -*- coding: utf-8 -*-
"""Common core methods and variables used across the project.

The module contains the methods requried to set up the internal environment.
See for instance :func:`.init_components`

File Sequences
--------------

Sequence items are matched using regexes defined in :func:`.get_valid_filename`,
:func:`.get_sequence`, :func:`.is_collapsed`, :func:`.get_sequence_startpath`,
:func:`.get_ranges`.

"""
import collections
import uuid
import functools
import traceback
import inspect
import time
import os
import sys
import re
import hashlib
import weakref
import _scandir

from PySide2 import QtGui, QtCore, QtWidgets

from . import __name__ as module_name

STANDALONE = True  # This must be set to `False` when Bookmarks runs embedded in a DCC.
PRODUCT = module_name.title()
ABOUT_URL = 'https://github.com/wgergely/bookmarks'
BOOKMARK_ROOT_DIR = '.bookmark'

# This is the environment key used to locate the installed libraries
BOOKMARK_ROOT_KEY = f'{module_name.upper()}_ROOT'

DEBUG = False # Print debug messages
TYPECHECK = False # Check types

DEFAULT_BOLD_FONT = 'bmRobotoBold'
DEFAULT_MEDIUM_FONT = 'bmRobotoMedium'

# Templates
PERSISTENT_BOOKMARKS_SOURCE = os.path.abspath(f'{__file__}{os.path.sep}{os.pardir}{os.path.sep}rsc{os.path.sep}templates{os.path.sep}persistent_bookmarks.json')
DEFAULT_ASSET_SOURCE = os.path.abspath(f'{__file__}{os.path.sep}{os.pardir}{os.path.sep}rsc{os.path.sep}templates{os.path.sep}Bookmarks_Default_Job.zip')
DEFAULT_JOB_SOURCE = os.path.abspath(f'{__file__}{os.path.sep}{os.pardir}{os.path.sep}rsc{os.path.sep}templates{os.path.sep}Bookmarks_Default_Asset.zip')

SyncronisedActivePaths = 0
PrivateActivePaths = 1

SESSION_MODE = SyncronisedActivePaths

BookmarkTab = 0
AssetTab = 1
FileTab = 2
FavouriteTab = 3

# Flags
MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000
MarkedAsPersistent = 0b1000000000000

InfoThread = 0
ThumbnailThread = 1

MAXITEMS = 999999

SEQSTART = '{'
SEQEND = '}'
SEQPROXY = '{SEQSTART}0{SEQEND}'.format(
	SEQSTART=SEQSTART,
	SEQEND=SEQEND
)

FAVOURITE_FILE_FORMAT = 'bfav'

# Private caches used to store
SERVERS = []
PERSISTENT_BOOKMARKS = {}
BOOKMARKS = {}
FAVOURITES = {}
FAVOURITES_SET = set()
HASH_DATA = {}
TIMERS = {}

signals = None
font_db = None

FlagsRole = QtCore.Qt.ItemDataRole(QtCore.Qt.UserRole + 4096)
ParentPathRole = QtCore.Qt.ItemDataRole(FlagsRole + 1)
DescriptionRole = QtCore.Qt.ItemDataRole(ParentPathRole + 1)
TodoCountRole = QtCore.Qt.ItemDataRole(DescriptionRole + 1)
AssetCountRole = QtCore.Qt.ItemDataRole(TodoCountRole + 1)
FileDetailsRole = QtCore.Qt.ItemDataRole(AssetCountRole + 1)
SequenceRole = QtCore.Qt.ItemDataRole(FileDetailsRole + 1)
FramesRole = QtCore.Qt.ItemDataRole(SequenceRole + 1)
FileInfoLoaded = QtCore.Qt.ItemDataRole(FramesRole + 1)
ThumbnailLoaded = QtCore.Qt.ItemDataRole(FileInfoLoaded + 1)
StartpathRole = QtCore.Qt.ItemDataRole(ThumbnailLoaded + 1)
EndpathRole = QtCore.Qt.ItemDataRole(StartpathRole + 1)
TypeRole = QtCore.Qt.ItemDataRole(EndpathRole + 1)
EntryRole = QtCore.Qt.ItemDataRole(TypeRole + 1)
IdRole = QtCore.Qt.ItemDataRole(EntryRole + 1)
QueueRole = QtCore.Qt.ItemDataRole(IdRole + 1)
DataTypeRole = QtCore.Qt.ItemDataRole(QueueRole + 1)
SortByNameRole = QtCore.Qt.ItemDataRole(DataTypeRole + 1)
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(SortByNameRole + 1)
SortBySizeRole = QtCore.Qt.ItemDataRole(SortByLastModifiedRole + 1)
SortByTypeRole = QtCore.Qt.ItemDataRole(SortBySizeRole + 1)
ShotgunLinkedRole = QtCore.Qt.ItemDataRole(SortByTypeRole + 1)

FileItem = 1100
SequenceItem = 1200

SORT_WITH_BASENAME = False
DEFAULT_SORT_VALUES = {
	SortByNameRole: 'Name',
	SortBySizeRole: 'Date Modified',
	SortByLastModifiedRole: 'Size',
	SortByTypeRole: 'Type',
}

IsSequenceRegex = re.compile(
	r'^(.+?)(\{}.*\{})(.*)$'.format(SEQSTART, SEQEND),
	flags=re.IGNORECASE | re.UNICODE
)
SequenceStartRegex = re.compile(
	r'^(.*)\{}([0-9]+).*\{}(.*)$'.format(SEQSTART, SEQEND),
	flags=re.IGNORECASE | re.UNICODE
)
SequenceEndRegex = re.compile(
	rf'^(.*)\{SEQSTART}.*?([0-9]+)\{SEQEND}(.*)$',
	flags=re.IGNORECASE | re.UNICODE
)
GetSequenceRegex = re.compile(
	r'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{1,})$',
	flags=re.IGNORECASE | re.UNICODE)

PlatformWindows = 0
PlatformMacOS = PlatformWindows + 1
PlatformUnsupported = PlatformMacOS + 1

WindowsPath = 0
MacOSPath = WindowsPath + 1
UnixPath = MacOSPath + 1
SlackPath = UnixPath + 1

PrimaryFontRole = 0
SecondaryFontRole = PrimaryFontRole + 1
MetricsRole = SecondaryFontRole + 1

cursor = QtGui.QCursor()

STYLESHEET = None
SCALE_FACTORS = (0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
UI_SCALE = 1.0
"""The global UI scale value. Depending on context, this should correspond to
any UI scaling set in the host DCC. In standalone mode the app factors in the
current DPI scaling and scales the UI accordingly."""


class Signals(QtCore.QObject):
	logChanged = QtCore.Signal()

	# Top Bar
	updateButtons = QtCore.Signal()
	checkSlackToken = QtCore.Signal()

	# Status Bar
	showStatusTipMessage = QtCore.Signal(str)
	showStatusBarMessage = QtCore.Signal(str)
	clearStatusBarMessage = QtCore.Signal()

	thumbnailUpdated = QtCore.Signal(str)

	# Signal used to update elements after a value is updated in the bookmark database
	databaseValueUpdated = QtCore.Signal(str, str, str, object)

	serversChanged = QtCore.Signal()

	bookmarkAdded = QtCore.Signal(str, str, str)
	bookmarkRemoved = QtCore.Signal(str, str, str)

	favouritesChanged = QtCore.Signal()

	assetAdded = QtCore.Signal(str)
	fileAdded = QtCore.Signal(str)

	toggleFilterButton = QtCore.Signal()
	toggleSequenceButton = QtCore.Signal()
	toggleArchivedButton = QtCore.Signal()
	toggleInlineIcons = QtCore.Signal()
	toggleFavouritesButton = QtCore.Signal()
	toggleMakeThumbnailsButton = QtCore.Signal()

	sessionModeChanged = QtCore.Signal(int)

	tabChanged = QtCore.Signal(int)
	taskViewToggled = QtCore.Signal()

	# Templates
	templatesChanged = QtCore.Signal()
	templateExpanded = QtCore.Signal(str)

	# Shotgun
	entitySelected = QtCore.Signal(dict)
	assetsLinked = QtCore.Signal()
	shotgunEntityDataReady = QtCore.Signal(str, list)

	# General activation signals
	bookmarkActivated = QtCore.Signal(str, str, str)
	assetActivated = QtCore.Signal(str, str, str, str)
	fileActivated = QtCore.Signal(str, str, str, str, str)

	def __init__(self, parent=None):
		super().__init__(parent=parent)
		from . import actions
		self.toggleFilterButton.connect(actions.toggle_filter_editor)
		self.toggleSequenceButton.connect(actions.toggle_sequence)
		self.toggleArchivedButton.connect(actions.toggle_archived_items)
		self.toggleInlineIcons.connect(actions.toggle_inline_icons)
		self.toggleFavouritesButton.connect(actions.toggle_favourite_items)
		self.toggleMakeThumbnailsButton.connect(actions.toggle_make_thumbnails)
		self.databaseValueUpdated.connect(actions.asset_identifier_changed)



def init_environment(skip_pyside2=False):
	"""Add the dependencies to the Python environment.

	The method requires that BOOKMARK_ROOT_KEY is set. The key is usually set
	by the Bookmark installer to point to the install root directory.
	The

	Raises:
		EnvironmentError: When the BOOKMARK_ROOT_KEY is not set.
		RuntimeError: When the BOOKMARK_ROOT_KEY is invalid or a directory missing.

	"""
	if BOOKMARK_ROOT_KEY not in os.environ:
		raise EnvironmentError(f'"{BOOKMARK_ROOT_KEY}" environment variable is not set.')

	v = os.environ[BOOKMARK_ROOT_KEY]

	if not os.path.isdir(v):
		raise RuntimeError(
			f'"{v}" is not a falid folder. Is "{BOOKMARK_ROOT_KEY}" environment variable set?')

	# Add BOOKMARK_ROOT_KEY to the PATH
	v = os.path.normpath(os.path.abspath(v)).strip()
	if v.lower() not in os.environ['PATH'].lower():
		os.environ['PATH'] = v + ';' + os.environ['PATH'].strip(';')

	def _add_path_to_sys(p):
		_v = f'{v}{os.path.sep}{p}'
		if not os.path.isdir(_v):
			raise RuntimeError(f'{_v} does not exist.')

		if _v in sys.path:
			return
		sys.path.insert(0, _v)

	_add_path_to_sys('shared')
	if skip_pyside2:
		return
	_add_path_to_sys('modules')

def init_components(mode):
	"""Initializes the components of the application required to run in
	standalone mode.

	Args:
		mode (bool):    Bookmarks will run in *standalone* mode when `True`.

	"""
	global STANDALONE
	STANDALONE = mode

	_init_resources()
	_init_signals()
	_init_dirs_dir()
	_init_settings()
	_init_ui_scale()
	_init_font_db()
	_init_pixel_ratio()
	_init_session_lock()


def _init_signals():
	global signals
	signals = Signals()


def _init_dirs_dir():
	if not os.path.isdir(temp_path()):
		os.makedirs(os.path.normpath(temp_path()))


def _init_settings():
	"""Initialises the user settings instance.

	The instance will populate the `SERVERS`, `BOOKMARKS` and `FAVOURITES`
	caches for later use.

	"""
	from . import settings

	settings.ACTIVE = collections.OrderedDict()
	for k in settings.ACTIVE_KEYS:
		settings.ACTIVE[k] = None

	settings.instance()


def _init_ui_scale():
	"""Load the current user-set UI scale value.

	"""
	from . import settings

	v = settings.instance().value(
		settings.SettingsSection,
		settings.UIScaleKey
	)

	if v is None:
		v = 1.0
	elif isinstance(v, str):
		if '%' not in v:
			v = 1.0
		else:
			v = v.strip('%')
		try:
			v = float(v) * 0.01
		except:
			return
		if v not in SCALE_FACTORS:
			v = 1.0
	else:
		v = 1.0

	global UI_SCALE
	UI_SCALE = v


def _init_pixel_ratio():
	from . import images

	app = QtWidgets.QApplication.instance()

	if images.pixel_ratio is None and app:
		images.pixel_ratio = app.primaryScreen().devicePixelRatio()
	else:
		images.pixel_ratio = 1.0

	return images.pixel_ratio


def _init_resources():
	from . import images
	images.init_resources()


def _init_session_lock():
	from . import session_lock
	session_lock.prune()
	session_lock.init()


def _init_font_db():
	global font_db
	font_db = FontDatabase()


def get_visible_indexes(widget):
	def index_below(r):
		r.moveTop(r.top() + r.height())
		return widget.indexAt(r.topLeft())

	# Find the first visible index
	r = widget.rect()
	index = widget.indexAt(r.topLeft())
	if not index.isValid():
		return []

	rect = widget.visualRect(index)
	i = 0
	idxs = [index.data(IdRole), ]
	while r.intersects(rect):
		if i >= 999:  # Don't check more than 999 items
			break
		i += 1

		idx = index.data(IdRole)
		idxs.append(idx)

		index = index_below(rect)
		if not index.isValid():
			break
	return set(idxs)


def sort_data(ref, sortrole, sortorder):
	check_type(sortrole, QtCore.Qt.ItemDataRole)
	check_type(sortorder, bool)

	def sort_key(idx):
		# If SORT_WITH_BASENAME is `True` we'll use the base file name for sorting
		v = ref().__getitem__(idx)
		if SORT_WITH_BASENAME and sortrole == SortByNameRole and isinstance(v[sortrole], list):
			return v[sortrole][-1]
		return v[sortrole]

	sorted_idxs = sorted(
		ref().keys(),
		key=sort_key,
		reverse=sortorder
	)

	d = DataDict()
	d.loaded = ref().loaded
	d.data_type = ref().data_type

	for n, idx in enumerate(sorted_idxs):
		if not ref():
			raise RuntimeError('Model mutated during sorting.')
		ref()[idx][IdRole] = n
		d[n] = ref()[idx]
	return d


def get_platform():
	"""Returns the current platform."""
	ptype = QtCore.QSysInfo().productType()
	if ptype.lower() in ('osx', 'macos'):
		return PlatformMacOS
	if 'win' in ptype.lower():
		return PlatformWindows
	return PlatformUnsupported


if get_platform() == PlatformWindows:
	DPI = 72.0
elif get_platform() == PlatformMacOS:
	DPI = 96.0
elif get_platform() == PlatformUnsupported:
	DPI = 72.0


BG = QtGui.QColor(75, 75, 78, 255)
SELECTED_BG = QtGui.QColor(140, 140, 140, 255)
DARK_BG = QtGui.QColor(55, 55, 58, 255)

TEXT = QtGui.QColor(220, 220, 220, 255)
SELECTED_TEXT = QtGui.QColor(250, 250, 250, 255)
DISABLED_TEXT = QtGui.QColor(140, 140, 140, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170, 255)

SEPARATOR = QtGui.QColor(42, 42, 45, 255)
BLUE = QtGui.QColor(107, 135, 165, 255)
RED = QtGui.QColor(219, 114, 114, 255)
GREEN = QtGui.QColor(90, 200, 155, 255)

TRANSPARENT_BLACK = QtGui.QColor(0, 0, 15, 30)
LOG_BG = QtGui.QColor(27, 29, 35, 255)

TRANSPARENT = QtGui.QColor(0, 0, 0, 0)


def SMALL_FONT_SIZE(): return int(psize(11.0))  # 8.5pt@72dbpi


def MEDIUM_FONT_SIZE(): return int(psize(12.0))  # 9pt@72dpi


def LARGE_FONT_SIZE(): return int(psize(16.0))  # 12pt@72dpi


def ROW_HEIGHT(): return int(psize(34.0))


def BOOKMARK_ROW_HEIGHT(): return int(psize(40.0))


def ASSET_ROW_HEIGHT(): return int(psize(64.0))


def ROW_SEPARATOR(): return int(psize(1.0))


def MARGIN(): return int(psize(18.0))


def INDICATOR_WIDTH(): return int(psize(4.0))


def WIDTH(): return int(psize(640.0))


def HEIGHT(): return int(psize(480.0))


def status_bar_message(message):
	def decorator(function):
		def wrapper(*args, **kwargs):
			from . import log
			if DEBUG:
				log.debug(message)
			signals.showStatusBarMessage.emit(message)
			result = function(*args, **kwargs)
			signals.showStatusBarMessage.emit('')
			return result
		return wrapper
	return decorator


def error(func):
	"""Decorator to create a menu set."""
	@functools.wraps(func)
	def func_wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except:
			from . import ui
			from . import log

			info = sys.exc_info()
			if all(info):
				e = ''.join(traceback.format_exception(*info))
			else:
				e = ''

			log.error('Error.')

			# So we can use the method in threads too
			if QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
				try:
					if QtWidgets.QApplication.instance():
						ui.ErrorBox(info[1].__str__(), limit=1).open()
					signals.showStatusBarMessage.emit(
						'An error occured. See log for more details.')
				except:
					pass
			raise
	return func_wrapper


def debug(func):
	"""Decorator to create a menu set."""
	DEBUG_MESSAGE = '{trace}(): Executed in {time} secs.'
	DEBUG_SEPARATOR = ' --> '

	@functools.wraps(func)
	def func_wrapper(*args, **kwargs):
		# If global debugging is turned off, do nothing
		if not DEBUG:
			return func(*args, **kwargs)

		# Otherwise, get the callee, and the executing time and info
		try:
			if DEBUG:
				t = time.time()
			return func(*args, **kwargs)
		finally:
			if args and hasattr(args[0], '__class__'):
				funcname = f'{args[0].__class__}.{func.func_name}'
			else:
				funcname = func.func_name

			if DEBUG:
				trace = []
				for frame in reversed(inspect.stack()):
					if frame[3] == '<module>':
						continue
					mod = inspect.getmodule(frame[0]).__name__
					_funcname = f'{mod}.{frame[3]}'
					trace.append(_funcname)
				trace.append(funcname)

				from . import log
				log.debug(
					DEBUG_MESSAGE.format(
						trace=DEBUG_SEPARATOR.join(trace),
						time=time.time() - t
					)
				)

	return func_wrapper


def psize(n):
	"""Returns a scaled UI value.
	All UI values are assumed to be in `pixels`.

	"""
	return (float(n) * (float(DPI) / 72.0)) * float(UI_SCALE)


def get_hash(key):
	"""Calculates the md5 hash of a str string.

	The resulting hash is used by the `ImageCache`, `local_settings` and
	`BookmarkDB` to associate data with file paths. The generated hashes are
	server agnostic, meaning, if the passed string contains a server's name,
	we'll remove it before hashing.

	Args:
		key (str): A str string to calculate the md5 hash for.

	Returns:
		str: Value of the calculated md5 hexadecimal digest as a `str`.

	"""
	check_type(key, str)

	if key in HASH_DATA:
		return HASH_DATA[key]

	# Path must not contain backslashes
	if '\\' in key:
		key = key.replace('\\', '/')

	# The hash key is server agnostic. We'll check the key against all saved
	# servers and remove it if found in the key.
	s = [f for f in SERVERS if f in key]
	if s:
		s = s[0]
		l = len(s)
		if key[:l] == s:
			key = key[l:]

	key = key.encode('utf-8')
	if key in HASH_DATA:
		return HASH_DATA[key]

	# Otherwise, we calculate, save and return the digest
	HASH_DATA[key] = hashlib.md5(key).hexdigest()
	return HASH_DATA[key]


def get_username():
	"""Returns the name of the currently logged-in user.

	"""
	n = QtCore.QFileInfo(os.path.expanduser('~')).fileName()
	n = re.sub(r'[^a-zA-Z0-9]*', '', n, flags=re.IGNORECASE | re.UNICODE)
	return n


def qlast_modified(n):
	return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def is_collapsed(s):
	"""Check for the presence of the bracket-enclosed sequence markers.

	When Bookmarks is displaying a sequence of files as a single item,
	the item is *collapsed*. Every collapsed item contains a start and an end number
	enclosed in brackets. For instance: ``image_sequence_[001-233].png``

	Args:
		s (str): A file path.

	Returns:
		group 1 (SRE_Match):    All the characters **before** the sequence marker.
		group 2 (SRE_Match):    The sequence marker(eg. ``[01-50]``), as a string.
		group 3 (SRE_Match):    All the characters **after** the sequence marker.

	.. code-block:: python

	   filename = 'job_sh010_animation_[001-299]_wgergely.png'
	   m = is_collapsed(filename)
	   if m:
		   prefix = match.group(1) # 'job_sh010_animation_'
		   sequence_string = match.group(2) # '[001-299]'
		   suffix = match.group(3) # '_wgergely.png'

	Returns:
		``SRE_Match``: If the given name is indeed collpased it returns a ``SRE_Match`` object, otherwise ``None``.

	"""
	check_type(s, str)
	return IsSequenceRegex.search(s)


def proxy_path(v):
	"""Encompasses the logic used to associate preferences with items.

	Sequence items need a generic key to save values as the sequence notation
	might change as files are added/removed to image seuquences. Any `FileItem`
	will use their file path as the key and SequenceItems will use `[0]` in place
	of their frame-range notation.

	Args:
		v (QModelIndex, dict or str): Data dict, index or filepath string.

	Returns:
		str: The key used to store the items information in the local
		preferences and the bookmarks database.

	"""
	if isinstance(v, weakref.ref):
		v = v()[QtCore.Qt.StatusTipRole]
	if isinstance(v, dict):
		v = v[QtCore.Qt.StatusTipRole]
	elif isinstance(v, QtCore.QModelIndex):
		v = v.data(QtCore.Qt.StatusTipRole)
	elif isinstance(v, str):
		pass
	else:
		raise TypeError(
			f'Invalid type, expected one of {weakref.ref}, {QtCore.QModelIndex}, {dict}, got {type(v)}')

	collapsed = is_collapsed(v)
	if collapsed:
		return collapsed.group(1) + SEQPROXY + collapsed.group(3)
	seq = get_sequence(v)
	if seq:
		return seq.group(1) + SEQPROXY + seq.group(3) + '.' + seq.group(4)
	return v


def get_sequence(s):
	"""Check if the given text contains a sequence element.

	Strictly speaking, a sequence is any file that has a valid number element.
	There can only be **one** incrementable element - it will always be the
	number closest to the end.

	The regex will understand sequences with the `v` prefix, eg *v001*, *v002*,
	but works without the prefix as well. Eg. **001**, **002**. In the case of a
	filename like ``job_sh010_animation_v002.c4d`` **002** will be the
	prevailing sequence number, ignoring the number in the extension.

	Likewise, in ``job_sh010_animation_v002.0001.c4d`` the sequence number will
	be **0001**, and not 010 or 002.

	Args:
		s (str): A file path.

	Returns:
		group 1 (SRE_Match):    All the characters **before** the sequence number.
		group 2 (SRE_Match):    The sequence number, as a string.
		group 3 (SRE_Match):    All the characters **after** the sequence number up until the file extensions.
		group 4 (SRE_Match):    The file extension **without** the '.' dot.

	.. code-block:: python

	   s = 'job_sh010_animation_v002_wgergely.c4d'
	   m = get_sequence(s)
	   if m:
		   prefix = match.group(1)
		   sequence_number = match.group(2)
		   suffix = match.group(3)
		   extension = match.group(4)

	Returns:
		``SRE_Match``: ``None`` if the text doesn't contain a number or an ``SRE_Match`` object.

	"""
	check_type(s, str)
	if is_collapsed(s):
		raise RuntimeError(
			'Cannot extract sequence numbers from collapsed items.')
	return GetSequenceRegex.search(s)


def get_sequence_startpath(path):
	"""Checks the given string and if it denotes a seuqence returns the path for
	the first file.

	Args:
		s (str): A collapsed sequence name.

	Returns:
		str: The path to the first file of the sequence.

	"""
	check_type(path, str)

	if not is_collapsed(path):
		return path

	match = SequenceStartRegex.search(path)
	if match:
		path = SequenceStartRegex.sub(r'\1\2\3', path)
	return path


def get_sequence_endpath(path):
	"""Checks the given string and if it denotes a seuqence returns the path for
	the last file.

	Args:
		s (str): A collapsed sequence name.

	Returns:
		str: The path to the last file of the sequence.

	"""
	check_type(path, str)
	if not is_collapsed(path):
		return path

	match = SequenceEndRegex.search(path)
	if match:
		path = SequenceEndRegex.sub(r'\1\2\3', path)
	return path


def get_sequence_paths(index):
	"""Given the index, returns a tuple of filenames referring to the
	individual sequence items.

	Args:
		index (QtCore.QModelIndex): A listview index.

	"""
	path = index.data(QtCore.Qt.StatusTipRole)
	if not is_collapsed(path):
		return path

	sequence_paths = []
	for frame in index.data(FramesRole):
		seq = index.data(SequenceRole)
		seq = seq.group(1) + frame + seq.group(3) + '.' + seq.group(4)
		sequence_paths.append(seq)
	return sequence_paths


def local_user_bookmark():
	"""Return a location on the local system to store temporary files.
	This is used to store thumbnails for starred items and other temporary items.

	Returns:
		tuple: A tuple of path segments.

	"""
	return (
		QtCore.QStandardPaths.writableLocation(
			QtCore.QStandardPaths.GenericDataLocation),
		PRODUCT,
		'temp',
	)


def temp_path():
	"""Path to the folder to store temporary files.

	Returns:
		str: Path to a directory.

	"""
	return '/'.join(local_user_bookmark())


def fit_screen_geometry(widget):
	app = QtWidgets.QApplication.instance()
	for screen in app.screens():
		_geo = screen.availableGeometry()
		if _geo.contains(cursor.pos(screen)):
			widget.setGeometry(_geo)
			return


def center_window(widget):
	widget.adjustSize()
	app = QtWidgets.QApplication.instance()
	for screen in app.screens():
		_geo = screen.availableGeometry()
		r = widget.rect()
		if _geo.contains(cursor.pos(screen)):
			widget.move(_geo.center() + (r.topLeft() - r.center()))
			return


def move_widget_to_available_geo(widget):
	"""Moves the widget inside the available screen geometry, if any of the
	edges fall outside of it.

	"""
	app = QtWidgets.QApplication.instance()
	if widget.window():
		screenID = app.desktop().screenNumber(widget.window())
	else:
		screenID = app.desktop().primaryScreen()

	screen = app.screens()[screenID]
	screen_rect = screen.availableGeometry()

	# Widget's rectangle in the global screen space
	rect = QtCore.QRect()
	topLeft = widget.mapToGlobal(widget.rect().topLeft())
	rect.setTopLeft(topLeft)
	rect.setWidth(widget.rect().width())
	rect.setHeight(widget.rect().height())

	x = rect.x()
	y = rect.y()

	if rect.left() < screen_rect.left():
		x = screen_rect.x()
	if rect.top() < screen_rect.top():
		y = screen_rect.y()
	if rect.right() > screen_rect.right():
		x = screen_rect.right() - rect.width()
	if rect.bottom() > screen_rect.bottom():
		y = screen_rect.bottom() - rect.height()

	widget.move(x, y)


def set_custom_stylesheet(widget):
	"""Set Bookmark's custom stylesheet to the given widget.

	The tokenised stylesheet is stored in the rsc/stylesheet.qss file.
	We'll load and expand the tokens, then store the stylesheet as `STYLESHEET`
	in the module.

	Args:
		widget (QWidget): A widget t apply the stylesheet to.

	Returns:
		str: The stylesheet applied to the widget.

	"""
	global STYLESHEET
	if STYLESHEET:
		widget.setStyleSheet(STYLESHEET)
		return STYLESHEET

	from . import images

	path = os.path.normpath(
		os.path.abspath(
			os.path.join(
				__file__,
				os.pardir,
				'rsc',
				'stylesheet.qss'
			)
		)
	)
	with open(path, 'r', encoding='utf-8') as f:
		f.seek(0)
		qss = f.read()

	try:
		from . import images
		qss = qss.format(
			PRIMARY_FONT=font_db.primary_font(MEDIUM_FONT_SIZE())[0].family(),
			SECONDARY_FONT=font_db.secondary_font(
				SMALL_FONT_SIZE())[0].family(),
			SMALL_FONT_SIZE=int(SMALL_FONT_SIZE()),
			MEDIUM_FONT_SIZE=int(MEDIUM_FONT_SIZE()),
			LARGE_FONT_SIZE=int(LARGE_FONT_SIZE()),
			RADIUS=int(INDICATOR_WIDTH() * 1.5),
			RADIUS_SM=int(INDICATOR_WIDTH()),
			SCROLLBAR_SIZE=int(INDICATOR_WIDTH() * 2),
			SCROLLBAR_MINHEIGHT=int(MARGIN() * 5),
			ROW_SEPARATOR=int(ROW_SEPARATOR()),
			MARGIN=int(MARGIN()),
			INDICATOR_WIDTH=int(INDICATOR_WIDTH()),
			CONTEXT_MENU_HEIGHT=int(MARGIN() * 2),
			CONTEXT_MENU_ICON_PADDING=int(MARGIN()),
			ROW_HEIGHT=int(ROW_HEIGHT()),
			BG=rgb(BG),
			SELECTED_BG=rgb(SELECTED_BG),
			DARK_BG=rgb(DARK_BG),
			TEXT=rgb(TEXT),
			SECONDARY_TEXT=rgb(SECONDARY_TEXT),
			DISABLED_TEXT=rgb(DISABLED_TEXT),
			SELECTED_TEXT=rgb(SELECTED_TEXT),
			GREEN=rgb(GREEN),
			RED=rgb(RED),
			SEPARATOR=rgb(SEPARATOR),
			BLUE=rgb(BLUE),
			TRANSPARENT=rgb(TRANSPARENT),
			TRANSPARENT_BLACK=rgb(TRANSPARENT_BLACK),
			LOG_BG=rgb(LOG_BG),
			BRANCH_CLOSED=images.ImageCache.get_rsc_pixmap(
				'branch_closed', None, None, get_path=True),
			BRANCH_OPEN=images.ImageCache.get_rsc_pixmap(
				'branch_open', None, None, get_path=True),
			CHECKED=images.ImageCache.get_rsc_pixmap(
				'check', None, None, get_path=True),
			UNCHECKED=images.ImageCache.get_rsc_pixmap(
				'close', None, None, get_path=True),
		)
	except KeyError as err:
		from . import log
		msg = 'Looks like there might be an error in the stylesheet file: {}'.format(
			err)
		log.error(msg)
		raise KeyError(msg)

	STYLESHEET = qss
	widget.setStyleSheet(STYLESHEET)
	return STYLESHEET


def rgb(v):
	"""Returns the `rgba(r,g,b,a)` string representation of a QColor.

	Args:
		v (QColor): A color.

	Returns:
		str: The string representation of the color.

	"""
	return 'rgba({})'.format(','.join([str(f) for f in v.getRgb()]))


def draw_aliased_text(painter, font, rect, text, align, color, elide=None):
	"""Allows drawing aliased text using *QPainterPath*.

	This is slow to calculate but ensures the rendered text looks *smooth* (on
	Windows espcially, I noticed a lot of aliasing issues). We're also eliding
	the given text to the width of the given rectangle.

	Args:
		painter (QPainter):         The active painter.
		font (QFont):               The font to use to paint.
		rect (QRect):               The rectangle to fit the text in.
		text (str):             The text to paint.
		align (Qt.AlignmentFlag):   The alignment flags.
		color (QColor):             The color to use.

	Returns:
		int: The width of the drawn text in pixels.

	"""
	from .lists import delegate
	painter.save()

	painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
	painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)

	metrics = QtGui.QFontMetrics(font)

	if elide is None:
		elide = QtCore.Qt.ElideLeft
		if QtCore.Qt.AlignLeft & align:
			elide = QtCore.Qt.ElideRight
		if QtCore.Qt.AlignRight & align:
			elide = QtCore.Qt.ElideLeft
		if QtCore.Qt.AlignHCenter & align:
			elide = QtCore.Qt.ElideMiddle

	text = metrics.elidedText(
		'{}'.format(text),
		elide,
		rect.width() * 1.01)
	width = metrics.horizontalAdvance(text)

	if QtCore.Qt.AlignLeft & align:
		x = rect.left()
	if QtCore.Qt.AlignRight & align:
		x = rect.right() - width
	if QtCore.Qt.AlignHCenter & align:
		x = rect.left() + (rect.width() * 0.5) - (width * 0.5)

	y = rect.center().y() + (metrics.ascent() * 0.5) - (metrics.descent() * 0.5)

	# Making sure text fits the rectangle
	painter.setBrush(color)
	painter.setPen(QtCore.Qt.NoPen)

	path = delegate.get_painter_path(x, y, font, text)
	painter.drawPath(path)

	painter.restore()
	return width


class FontDatabase(QtGui.QFontDatabase):
	"""Utility class for loading and getting the application's custom fonts.

	"""
	CACHE = {
		PrimaryFontRole: {},
		SecondaryFontRole: {},
		MetricsRole: {},
	}

	def __init__(self, parent=None):
		if not QtWidgets.QApplication.instance():
			raise RuntimeError(
				'FontDatabase must be created after a QApplication was initiated.')

		super().__init__(parent=parent)

		self._metrics = {}
		self.add_custom_fonts()

	def add_custom_fonts(self):
		"""Load the fonts used by Bookmarks to the font database.

		"""
		if DEFAULT_MEDIUM_FONT in self.families():
			return

		p = f'{__file__}/../rsc/fonts'
		p = os.path.normpath(os.path.abspath(p))

		if not os.path.isdir(p):
			raise OSError(f'{p} could not be found')

		for entry in _scandir.scandir(p):
			if not entry.name.endswith('ttf'):
				continue
			idx = self.addApplicationFont(entry.path)
			if idx < 0:
				raise RuntimeError(
					'Failed to add required font to the application')
			family = self.applicationFontFamilies(idx)
			if not family:
				raise RuntimeError(
					'Failed to add required font to the application')

	def primary_font(self, font_size):
		"""The primary font used by the application.

		"""
		if font_size in self.CACHE[PrimaryFontRole]:
			return self.CACHE[PrimaryFontRole][font_size]

		font = self.font(DEFAULT_BOLD_FONT, 'Bold', font_size)
		if font.family() != DEFAULT_BOLD_FONT:
			raise RuntimeError(
				'Failed to add required font to the application')

		font.setPixelSize(font_size)
		metrics = QtGui.QFontMetrics(font)
		self.CACHE[PrimaryFontRole][font_size] = (font, metrics)
		return self.CACHE[PrimaryFontRole][font_size]

	def secondary_font(self, font_size=SMALL_FONT_SIZE()):
		"""The secondary font used by the application.

		"""
		if font_size in self.CACHE[SecondaryFontRole]:
			return self.CACHE[SecondaryFontRole][font_size]

		font = self.font(DEFAULT_MEDIUM_FONT, 'Medium', font_size)
		if font.family() != DEFAULT_MEDIUM_FONT:
			raise RuntimeError(
				'Failed to add required font to the application')

		font.setPixelSize(font_size)
		metrics = QtGui.QFontMetrics(font)
		self.CACHE[SecondaryFontRole][font_size] = (font, metrics)
		return self.CACHE[SecondaryFontRole][font_size]


class DataDict(dict):
	"""Subclassed dict type for weakref compatibility."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._loaded = False
		self._refresh_needed = False
		self._data_type = None

	@property
	def loaded(self):
		return self._loaded

	@loaded.setter
	def loaded(self, v):
		self._loaded = v

	@property
	def refresh_needed(self):
		return self._refresh_needed

	@refresh_needed.setter
	def refresh_needed(self, v):
		self._refresh_needed = v

	@property
	def data_type(self):
		return self._data_type

	@data_type.setter
	def data_type(self, v):
		self._data_type = v


class Timer(QtCore.QTimer):
	"""A custom QTimer.

	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		TIMERS[repr(self)] = self

	def setObjectName(self, v):
		v = '{}_{}'.format(v, uuid.uuid1().hex)
		super().setObjectName(v)


def get_path_to_executable(key):
	"""Returns the path to an executable.

	Args:
		key (str):  The setting key to look up (one of setings.FFMpegKey, or
					settings.RVKey) or `None` if not found.

	Returns:
		str:        The path to the executable.

	"""
	from . import settings

	# Only FFMpeg and RV are implemented at the moment
	if key == settings.FFMpegKey:
		name = 'ffmpeg'
	elif key == settings.RVKey:
		name = 'rv'
	else:
		raise ValueError('Unsupported key value.')

	# First let's check if we have set explictily a path to an executable
	v = settings.instance().value(settings.SettingsSection, key)
	if isinstance(v, str) and QtCore.QFileInfo(v).exists():
		return QtCore.QFileInfo(v).filePath()

	# Otheriwse, let's check the environment
	if get_platform() == PlatformWindows:
		paths = os.environ['PATH'].split(';')
		paths = {os.path.normpath(f).rstrip('\\') for f in paths if os.path.isdir(f)}

		for path in paths:
			for entry in _scandir.scandir(path):
				if entry.name.lower().startswith(name):
					return QtCore.QFileInfo(entry.path).filePath()

	# If the envinronment lookup fails too, we'll return nothing
	return None


def delete_timers():
	for k in list(TIMERS):
		try:
			TIMERS[k].isActive()
		except:
			# The C++ object is probably already deleted
			del TIMERS[k]
			continue

		# Check thread affinity
		if TIMERS[k].thread() != QtCore.QThread.currentThread():
			continue
		TIMERS[k].stop()
		TIMERS[k].deleteLater()
		del TIMERS[k]


def quit():
	"""Closes and deletes all cached data and ui elements.

	"""
	import gc

	from .lists import alembic_preview
	from .lists import thumb_capture
	from .lists import thumb_library
	from .lists import thumb_picker
	from .property_editor import asset_editor
	from .property_editor import bookmark_editor
	from .property_editor import file_editor
	from .property_editor import preference_editor

	from . import standalone
	from . import settings
	from . import main
	from . import database
	from . import images
	from . import ui
	from . import actions
	from .threads import threads
	from .lists import delegate

	delete_timers()
	threads.quit()

	if STANDALONE and standalone.instance():
		standalone._instance.hide()

	if main._instance:
		main._instance.hide()

		for widget in (
			main._instance.bookmarkswidget,
			main._instance.assetswidget,
			main._instance.fileswidget,
			main._instance.favouriteswidget,
			main._instance.taskswidget
		):
			if not widget:
				continue

			widget.removeEventFilter(widget)
			widget.removeEventFilter(main._instance)
			if hasattr(widget.model(), 'sourceModel'):
				widget.model().sourceModel().deleteLater()
				widget.model().setSourceModel(None)
			widget.model().deleteLater()
			widget.setModel(None)

			for child in widget.children():
				child.deleteLater()

			widget.deleteLater()

		for widget in (main._instance.topbar, main._instance.stackedwidget, main._instance.statusbar):
			if not widget:
				continue

			for child in widget.children():
				child.deleteLater()
			widget.deleteLater()

		main._instance._initialized = False

	global SERVERS
	SERVERS = []
	global BOOKMARKS
	BOOKMARKS = {}
	global FAVOURITES
	FAVOURITES = {}
	global FAVOURITES_SET
	FAVOURITES_SET = set()
	global HASH_DATA
	HASH_DATA = {}

	global font_db
	try:
		font_db.deleteLater()
	except:
		pass
	font_db = None

	# Signas teardown
	global signals
	for k, v in Signals.__dict__.items():
		if not isinstance(v, QtCore.Signal):
			continue
		if not hasattr(signals, k):
			continue
		signal = getattr(signals, k)
		try:
			signal.disconnect()
		except RuntimeError as e:
			pass

	try:
		signals.deleteLater()
	except:
		pass
	signals = None

	database.close()
	images.reset()
	settings.delete()
	ui.reset()
	delegate.reset()

	alembic_preview.close()
	thumb_capture.close()
	thumb_library.close()
	thumb_picker.close()
	asset_editor.close()
	bookmark_editor.close()
	file_editor.close()
	preference_editor.close()

	if main._instance:
		main._instance.deleteLater()
		main._instance = None
	if STANDALONE and standalone._instance:
		standalone._instance.deleteLater()
		standalone._instance = None

	# delete_module_import_cache()

	# Force garbage collection
	gc.collect()


class InvalidTypeError(TypeError):
	""" Raised when an invalid object type is encountered.

	Args:
		value (object): An object of invalid type.
		valid_type (type): The valid type.

	"""

	def __init__(self, value, valid_type):
		super().__init__(
			f'Invalid type. Expected {valid_type}, got {value}'
		)


def check_type(value, valid_type):
	"""Verify the type of an object.

	Args:
		value (object): An object of invalid type.
		valid_type (type or tuple): The valid type.

	"""
	if not TYPECHECK:
		return

	try:
		it = iter(valid_type)
		for _type in it:
			if not isinstance(value, _type):
				raise InvalidTypeError(value, _type)
	except:
		if not isinstance(value, valid_type):
			raise InvalidTypeError(value, valid_type)
