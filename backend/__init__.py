try:
    import starlette.routing
    # Monkeypatch Starlette Router to handle older FastAPI versions that pass on_startup/on_shutdown
    original_init = starlette.routing.Router.__init__
    def patched_init(self, *args, **kwargs):
        kwargs.pop('on_startup', None)
        kwargs.pop('on_shutdown', None)
        original_init(self, *args, **kwargs)
        self.on_startup = []
        self.on_shutdown = []
    starlette.routing.Router.__init__ = patched_init

    from .handler import ConfigHandler
    from .app import create_app
    __all__ = ["ConfigHandler", "create_app"]
except ImportError:
    __all__ = []

