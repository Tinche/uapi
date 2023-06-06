from importlib.resources import files

swaggerui = files(__package__).joinpath("swaggerui.html").read_text()
redoc = files(__package__).joinpath("redoc.html").read_text()
elements = files(__package__).joinpath("elements.html").read_text()
