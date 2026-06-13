#!/usr/bin/env python
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Python imports
import inspect


class StubOutForTesting:
    """Sample Usage:
    You want os.path.exists() to always return true during testing.

    stubs = StubOutForTesting()
    stubs.set(os.path, 'exists', lambda x: 1)
      ...
    stubs.unset_all()

    The above changes os.path.exists into a lambda that returns 1. Once
    the ... part of the code finishes, the unset_all() looks up the old value
    of os.path.exists and restores it.

    """

    def __init__(self):
        self.cache = []
        self.stubs = []

    def __del__(self):
        self.smart_unset_all()
        self.unset_all()

    def smart_set(self, obj, attr_name, new_attr):
        """Replace obj.attr_name with new_attr. This method is smart and works
         at the module, class, and instance level while preserving proper
         inheritance. It will not stub out C types however unless that has
         been explicitly allowed by the type.

         This method supports the case where attr_name is a staticmethod or a
         classmethod of obj.

         Notes:
        - If obj is an instance, then it is its class that will actually be
          stubbed. Note that the method Set() does not do that: if obj is
          an instance, it (and not its class) will be stubbed.
        - The stubbing is using the builtin getattr and setattr. So, the
          __get__ and __set__ will be called when stubbing (TODO: A better
          idea would probably be to manipulate obj.__dict__ instead of
          getattr() and setattr()).

         Raises AttributeError if the attribute cannot be found.
        """
        if inspect.ismodule(obj) or (not inspect.isclass(obj) and attr_name in obj.__dict__):
            orig_obj = obj
            orig_attr = getattr(obj, attr_name)

        else:
            if not inspect.isclass(obj):
                mro = list(inspect.getmro(obj.__class__))
            else:
                mro = list(inspect.getmro(obj))

            mro.reverse()

            orig_attr = None

            for cls in mro:
                try:
                    orig_obj = cls
                    orig_attr = getattr(obj, attr_name)
                except AttributeError:
                    continue

        if orig_attr is None:
            raise AttributeError("Attribute not found.")

        # Calling getattr() on a staticmethod transforms it to a 'normal'
        # function. We need to ensure that we put it back as a staticmethod.
        old_attribute = obj.__dict__.get(attr_name)
        if old_attribute is not None and isinstance(old_attribute, staticmethod):
            orig_attr = staticmethod(orig_attr)

        # Record whether orig_obj actually defined the attribute itself. When
        # it only inherited it (the attribute lives on a base class), setattr
        # below creates a *new* shadowing entry in orig_obj.__dict__ that was
        # not there before. smart_unset_all() must delete that shadow rather
        # than leave it behind, otherwise it would not truly restore the
        # original definition.
        had_own_attr = attr_name in orig_obj.__dict__

        self.stubs.append((orig_obj, attr_name, orig_attr, had_own_attr))
        setattr(orig_obj, attr_name, new_attr)

    def smart_unset_all(self):
        """Reverses all the SmartSet() calls, restoring things to their
        original definition. It's okay to call smart_unset_all() repeatedly, as
        later calls have no effect if no SmartSet() calls have been made.

        """
        self.stubs.reverse()

        for orig_obj, attr_name, orig_attr, had_own_attr in self.stubs:
            if had_own_attr:
                setattr(orig_obj, attr_name, orig_attr)
            else:
                # The attribute was inherited; remove the shadow we created so
                # the inherited value is exposed again, as it was originally.
                try:
                    delattr(orig_obj, attr_name)
                except AttributeError:  # pragma: no cover - defensive fallback
                    setattr(orig_obj, attr_name, orig_attr)

        self.stubs = []

    def set(self, parent, child_name, new_child):
        """Replace child_name's old definition with new_child, in the context
        of the given parent.  The parent could be a module when the child is a
        function at module scope.  Or the parent could be a class when a class'
        method is being replaced.  The named child is set to new_child, while
        the prior definition is saved away for later, when unset_all() is
        called.

        This method supports the case where child_name is a staticmethod or a
        classmethod of parent.
        """
        old_child = getattr(parent, child_name)

        old_attribute = parent.__dict__.get(child_name)
        if old_attribute is not None:
            if isinstance(old_attribute, staticmethod):
                old_child = staticmethod(old_child)
            elif isinstance(old_attribute, classmethod):
                old_child = classmethod(old_child.__func__)

        self.cache.append((parent, old_child, child_name))
        setattr(parent, child_name, new_child)

    def unset_all(self):
        """Reverses all the set() calls, restoring things to their original
        definition. It's okay to call unset_all() repeatedly, as later calls
        have no effect if no set() calls have been made.

        """
        # Undo calls to set() in reverse order, in case set() was called on the
        # same arguments repeatedly (want the original call to be last one
        # undone)
        self.cache.reverse()

        for parent, old_child, child_name in self.cache:
            setattr(parent, child_name, old_child)
        self.cache = []

    SmartSet = smart_set
    SmartUnsetAll = smart_unset_all
    Set = set
    UnsetAll = unset_all


stubout = StubOutForTesting
