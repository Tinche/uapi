from importlib.resources import read_text

swaggerui = read_text(__package__, "swaggerui.html")
redoc = read_text(__package__, "redoc.html")
elements = read_text(__package__, "elements.html")
