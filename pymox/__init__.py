"""``import pymox`` alias for the ``mox`` package.

The distribution is published on PyPI as ``pymox`` while the import package has
always been ``mox``. That mismatch trips people up (``pip install pymox`` then
``import pymox`` used to fail), so this thin alias makes ``import pymox`` resolve
to the exact same module object as ``import mox`` - ``pymox is mox`` - and
submodules such as ``pymox.testing.pytest_mox`` resolve to the ``mox`` ones too.
"""

# Python imports
import sys

# Internal imports
import mox

# Make `pymox` *be* `mox` so there is a single set of classes, a single global
# Mox registry, and a single copy of the pytest plugin (no duplicate fixtures).
sys.modules[__name__] = mox
