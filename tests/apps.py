from uapi.base import App


def make_generic_subapp() -> App:
    app = App()

    @app.get("/subapp")
    def subapp() -> str:
        return "subapp"

    return app
