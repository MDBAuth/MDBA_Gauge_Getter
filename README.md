# Gague Getter

<span class="badges">

![Unit%20Tests](https://img.shields.io/badge/Unit%20Tests-100.0%25-brightgreen)
![Execution%20Time](https://img.shields.io/badge/Execution%20Time-0.63s-brightgreen)
![Code%20Coverage](https://img.shields.io/badge/Code%20Coverage-100.0-brightgreen)
![MyPy%20Errors](https://img.shields.io/badge/MyPy%20Errors-5-yellowgreen)
![Pylint%20Rating](https://img.shields.io/badge/Pylint%20Rating-7.8-green)

</span>

## Description
Gague getter provides a unified and simple interface to the following state water portals:


|State|Site|Source|
| --- | --- | --- |
| NSW | realtimedata.waternsw.com.au |CP|
| QLD | water-monitoring.information.qld.gov.au |PUBLISH|
| VIC | data.water.vic.gov.au |AT|

The tool is configured to abstract away the details specific to each state water poral and return a consistent structure. 
By default it will return a daily mean of a flow in Ml/day for a given gauge number, but level and other intervals and aggregations are available


Example of its use can be seen in Gauge_getter_example.ipynb notebook, contact ben.bradshaw@mdba.gov.au for more details.


# Setup / Packaging 

The module has been packaged using `setuptools` -
https://setuptools.readthedocs.io/en/latest/userguide/index.html

To install from source, run `python3 setuptools.py install`

To build a redistributable package (for upload to pip, or a locally managed software repository) use
`python3 setup.py build`. Pip doesn't respect `requirements.txt` so the setup will need to have
install_requires - https://packaging.python.org/discussions/install-requires-vs-requirements/ .


## Installation

- Install dependencies with `pip3 install -r requirements.txt`
- (Optionally) install dev dependencies with `pip3 install -r requirements-dev.txt`
- Run `python3 setup.py install` to install the module

## Development Tools

- To run unit tests, execute 
  `PYTHONPATH="./" python3 -m coverage run --source=mdba_gauge_getter -m pytest`
- To run coverage reports, execute `PYTHONPATH="./" python3 -m coverage report -m`, this
  must be run after pytest has been executed.
- To run pylint (to get a code quality rating), run 
  `pylint --output-format=text mdba_gauge_getter/ tests`
- To run mypy (a type checker) run `mypy mdba_gauge_getter`

These can be wrapped in the `execute-on-change.py` tool in a Linux environment (requires
`pip3 install inotify`).

## CI 

A ci script has been created located at `/ci.py`. It can be run with `PYTHONOPATH="./" python3 ci.py`

The script executes unit tests, pylint 
and mypy, updating README.md with the output. It can be plugged into Azure DevOps Pipelines 
or similar, or run manially prior to git push.


# Unit Tests

Unit tests, with 100% code coverage were used. Code coverage does not mean code is bug-free but 
is a good indicator that code is well tested. There are many benefits of Unit tests:

- You can assert your intentions when writing the code are correctly implemented
- You are forced to logically think through code structures to build testable code
- You can assert future changes do not break existing behaviour

Unit tests have been built with the pytest library, on a Unix operating system to run them
execute `PYTHONPATH="./" pytest-3 --cov=mdba_gauge_getter --cov-report term-missing`.
The reason we set the `PYTHONPATH` environment variable is to force pytest to
load the local directory, rather than any other version that is installed on the computer. 

# CI

The script `ci.py` has been built with the intent of being used in Continuous Integration - it
executes tests and patches this README.txt file. It could be plugged into a CI engine such as
Azure DevOps Pipelines or GitHub Actions - from there it could be explicitly configured to reject
commits which fail some metrics (such as failing unit tests, or reduced code coverage).
