# Flag to indicate whether notebook support is available
import os
import warnings

try:
    import ipyleaflet  # NOQA
    NOTEBOOK_SUPPORT = True
except ImportError:
    NOTEBOOK_SUPPORT = False

# Bravado spits out useless warnings by default, this is to silence them
SHOW_WARNINGS = os.getenv("SHOW_WARNINGS_RF", False)

if not SHOW_WARNINGS:
    warnings.simplefilter("ignore")
