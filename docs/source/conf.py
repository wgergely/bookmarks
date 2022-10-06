# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

from bookmarks import common
common.initialize(common.StandaloneMode)

from maya import standalone
try:
    standalone.initialize(name='python')
except:
    pass

# -- Project information -----------------------------------------------------

project = 'Bookmarks'
copyright = '2022, Gergely Wootsch'
author = 'Gergely Wootsch'

# The full version, including alpha/beta/rc tags
release = '0.7.1'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.githubpages',
    'autodocsumm',
    'sphinx_markdown_builder',
    'sphinx_carousel.carousel',
    'sphinxcontrib.youtube'
]

napoleon_google_docstring = True
napoleon_use_param = False
napoleon_use_ivar = False

pygments_style = "vs"
pygments_dark_style = "stata-dark"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'
html_theme_options = {
    "light_logo": "icon.png",
    "dark_logo": "icon_bw.png",
    "light_css_variables": {
        "color-brand-primary": "rgba(75, 180, 135, 1)",
        "color-brand-content": "rgba(75, 180, 135, 1)",
        "color-api-name": "rgba(0, 0, 0, 0.9)",
        "color-api-pre-name": "rgba(75, 180, 135, 0.75)",
        "api-font-size": "var(--font-size--normal)",
    },
    "dark_css_variables": {
        "color-brand-primary": "rgba(90, 200, 155, 1)",
        "color-brand-content": "rgba(90, 200, 155, 1)",
        "color-api-name": "rgba(255, 255, 255, 0.9)",

    },
    "navigation_with_keys": True,
}
highlight_language = "python"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

autodoc_default_options = {
    'autosummary': True,
    'member-order': 'groupwise',
    'show-inheritance': True,
    'preserve_defaults': True,
}
autodoc_preserve_defaults = True