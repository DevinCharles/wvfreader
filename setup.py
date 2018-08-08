import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wvf_reader",
    version="0.1.1",
    author="Devin Prescott",
    author_email="devincprescott@gmail.com",
    description="A package for working with Yokogowa oscilloscope files (WDF, WVF).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/wvf_reader",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL License",
        "Operating System :: OS Independent",
    ),
)