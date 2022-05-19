# MDBA Gague Getter

<span class="badges">

![Unit%20Tests](https://img.shields.io/badge/Unit%20Tests-100.0%25-brightgreen)
![Execution%20Time](https://img.shields.io/badge/Execution%20Time-0.63s-brightgreen)
![Code%20Coverage](https://img.shields.io/badge/Code%20Coverage-100.0-brightgreen)
![MyPy%20Errors](https://img.shields.io/badge/MyPy%20Errors-5-yellowgreen)
![Pylint%20Rating](https://img.shields.io/badge/Pylint%20Rating-7.8-green)
[![CI](https://github.com/agile-analytics-au/MDBA_Gauge_Getter/actions/workflows/tox-tests.yml/badge.svg)]()
[![PyPI](https://img.shields.io/pypi/v/mdba-gauge-getter)](https://pypi.org/project/mdba-gauge-getter/)

</span>

## Description
MDBA Gague Getter provides a unified and simple interface to collect surface water data from the following state water portals:


|State|Site|Source|
| --- | --- | --- |
| NSW | realtimedata.waternsw.com.au |CP|
| QLD | water-monitoring.information.qld.gov.au |PUBLISH|
| VIC | data.water.vic.gov.au |AT|

The tool is configured to abstract away the details specific to each state water portal and return a consistent structure. 
By default it will return a daily mean of a flow in ML/day for a given gauge number, but level and other intervals and aggregations are available


Example of its use can be seen in Gauge_getter_example.ipynb notebook, contact ben.bradshaw@mdba.gov.au for more details.

## Installation

- Install dependencies with `pip3 install -r requirements.txt`
- (Optionally) install dev dependencies with `pip3 install -r requirements-dev.txt`
- Run `python3 setup.py install` to install the module

## Support 
For issues relating to the script, a tutorial, or feedback please contact Ben Bradshaw ben.bradshaw@mdba.gov.au
For data issues please see the corresponding state water portals
