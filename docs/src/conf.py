# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

print('\n\n#####################################################################\n\n')
# To make the documentation we have to import bookmarks and initialize Maya
from bookmarks import common
common.initialize(common.StandaloneMode)

try:
    from maya import standalone
    standalone.initialize(name='python')
except:
    pass
print('\n\n#####################################################################\n\n')


# -- Project information -----------------------------------------------------

project = 'Bookmarks'
copyright = '2023 Gergely Wootsch'
author = 'Gergely Wootsch'

# The full version, including alpha/beta/rc tags
release = '0.8.6'

html_baseurl = 'https://bookmarks-vfx.com'
html_extra_path = [
    'robots.txt',
    'google287f295c58adf6d0.html'
]
html_context = {
    "display_github": True,
    "github_user": "wgergely",
    "github_repo": "bookmarks",
    "github_version": "main",
    "conf_py_path": "/docs/source",
}

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
    'sphinx_sitemap',
    'sphinx_markdown_builder',
    'sphinx_design',
    'sphinxcontrib.youtube',
    'sphinx_licenseinfo'
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
        "color-highlight-on-target": "rgba(0,0,0,0)",
        "api-font-size": "var(--font-size--normal)",
    },
    "dark_css_variables": {
        "color-brand-primary": "rgba(90, 200, 155, 1)",
        "color-brand-content": "rgba(90, 200, 155, 1)",
        "color-highlight-on-target": "rgba(0,0,0,0)",
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