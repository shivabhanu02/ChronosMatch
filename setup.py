
from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension("src.matching_engine", ["src/matching_engine.pyx"])
]

setup(
    name="chronosmatch",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
)
