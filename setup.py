import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='mdba_gauge_getter',
    version='0.1',
    author='Murray Darling Basin Authority',
    author_email='TODO@mdba.gov.au',  # Be aware this email will get spammed
    description='Facilitates waterflow gauge data ingest from several endpoints. Dependency to several other projects.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/TODO',
    project_urls={
        'Bug Tracker': 'https://github.com/TODO/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    packages=['mdba_gauge_getter',],
    package_data={'': ['data/*.csv']},
    python_requires='>=3.6',
)

