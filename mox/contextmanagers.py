class Create:
    def __init__(self):
        from .mox import Mox

        self.m = Mox()

    def __call__(self, class_to_mock, attrs=None):
        # Re-register in case a previous test's teardown cleared the registry;
        # mox.expect relies on this shared Mox being globally tracked.
        type(self.m).track(self.m)
        return self.m.create_mock(class_to_mock, attrs)

    def any(self, description=None):
        type(self.m).track(self.m)
        return self.m.create_mock_anything(description=description)


create = Create()


class Stubout:
    def __init__(self, *stub, _class=False):
        import mox

        self.stubs = [stub] if stub else []
        self._class = _class
        self.m = mox.Mox()

    def __enter__(self):
        stub_objs = []
        if self._class:
            method = getattr(self.m, "stubout_class")
        else:
            method = getattr(self.m, "stubout")

        for stub_args in self.stubs:
            if len(stub_args) >= 3:
                obj, attr_name, *use_mock_anything = stub_args
            elif len(stub_args) == 2:
                if isinstance(stub_args[0], str):
                    obj = stub_args[0]
                    attr_name = None
                    use_mock_anything = stub_args[1]
                else:
                    obj, attr_name, *use_mock_anything = stub_args
            else:
                obj = stub_args[0]
                attr_name = None
                use_mock_anything = False
            kwargs = {} if self._class else {"use_mock_anything": bool(use_mock_anything)}

            stub_obj = method(obj=obj, attr_name=attr_name, **kwargs)
            stub_objs.append(stub_obj)

        if len(stub_objs) == 1:
            return stub_objs[0]
        return stub_objs

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.m.replay_all()

    @classmethod
    def many(cls, *stubs):
        cm = cls()
        cm.stubs = stubs
        return cm

    @classmethod
    def klass(cls, *stub):
        cm = cls(*stub, _class=True)
        return cm


stubout = Stubout


class Expect:
    def __init__(self, *stub, mox_obj=None):
        self.stubs = [*stub] if stub else []
        self.mox_obj = mox_obj

    def __enter__(self):
        import mox

        mox.reset(*self.stubs)
        if self.mox_obj:
            self.mox_obj.reset_all()

        if len(self.stubs) == 1:
            return self.stubs[0]
        return self.stubs

    def __exit__(self, exc_type, exc_value, exc_tb):
        import mox

        try:
            if not self.mox_obj and not self.stubs:
                mox.Mox.global_replay()
                return

            if self.mox_obj:
                self.mox_obj.replay_all()
            if self.stubs:
                mox.replay(*self.stubs)
        finally:
            # `mox.expect` is a module-level singleton; calling it (e.g.
            # `with mox.expect(stub):`) sets these on the shared instance. Reset
            # them so a later bare `with mox.expect:` is not poisoned by leftover
            # stubs - which would skip the global replay.
            self.stubs = []
            self.mox_obj = None

    def __call__(self, *stubs):
        self.stubs = stubs
        return self

    @classmethod
    def from_mox(cls, mox_obj):
        cm = cls(mox_obj=mox_obj)
        return cm


expect = Expect()
