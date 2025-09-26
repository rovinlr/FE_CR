"""Odoo module bootstrap for the Costa Rican electronic invoicing addon."""

from __future__ import annotations

import os
import sys


def _ensure_fe_cr_on_path() -> None:
    """Ensure the sibling ``fe_cr`` package is importable.

    The Python helpers used by the addon live in a top-level ``fe_cr``
    directory within the repository so that they can be re-used outside of
    Odoo (for instance in unit tests).  When the addon is installed inside an
    Odoo environment the module path only contains the ``l10n_cr_edi``
    directory, which means the sibling package would not be discoverable by
    default.  Adding the shared repository root to ``sys.path`` makes the
    package available without requiring a separate pip installation, avoiding
    spurious external dependency errors during module installation.
    """

    module_dir = os.path.dirname(__file__)
    addons_root = os.path.normpath(os.path.join(module_dir, os.pardir))
    package_dir = os.path.join(addons_root, "fe_cr")

    if os.path.isdir(package_dir) and addons_root not in sys.path:
        sys.path.insert(0, addons_root)


_ensure_fe_cr_on_path()

from . import models

__all__ = ["models"]
