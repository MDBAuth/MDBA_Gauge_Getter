import setuptools

import sys

sys.path[0:0] = ['mdba_gauge_getter']

from version import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mdba_gauge_getter",
    version=__version__,
    author="Murray Darling Basin Authority",
    author_email="TODO@mdba.gov.au",  # Be aware this email will get spammed
    description="Facilitates waterflow gauge data ingest from several endpoints. Dependency to several other projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TODO",
    project_urls={
        "Bug Tracker": "https://github.com/TODO/issues",
    },
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Pytest',
    ],
    packages=[
        "mdba_gauge_getter",
    ],
    install_requires=[
        "pandas",
        "requests",
        "bomwater",
    ],
    package_data={"": ["data/*.csv"]},
    python_requires=">=3.6",
)
