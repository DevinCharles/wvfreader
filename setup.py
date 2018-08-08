from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="wvfreader",
    version="0.1.3",
    author="Devin Prescott",
    author_email="devincprescott@gmail.com",
    description="A package for working with Yokogowa oscilloscope files (WDF, WVF).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/wvfreader",
    #packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    py_modules=["wvfreader"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ),
    install_requires=['numpy'],
    keywords='Yokogowa Oscilloscope WVF WDF',
)