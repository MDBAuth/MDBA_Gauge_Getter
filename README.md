# MDBA Gauge Getter

<span class="badges">

![Unit%20Tests](https://img.shields.io/badge/Unit%20Tests-100.0%25-brightgreen)
![Execution%20Time](https://img.shields.io/badge/Execution%20Time-0.63s-brightgreen)
![Code%20Coverage](https://img.shields.io/badge/Code%20Coverage-100.0-brightgreen)
![MyPy%20Errors](https://img.shields.io/badge/MyPy%20Errors-5-yellowgreen)
![Pylint%20Rating](https://img.shields.io/badge/Pylint%20Rating-7.8-green)
[![CI](https://github.com/agile-analytics-au/MDBA_Gauge_Getter/actions/workflows/tox-tests.yml/badge.svg)]()
[![PyPI](https://img.shields.io/pypi/v/mdba-gauge-getter)](https://pypi.org/project/mdba-gauge-getter/)
[![DOI](https://zenodo.org/badge/431267159.svg)](https://zenodo.org/badge/latestdoi/431267159)
</span>

## Description
MDBA Gauge Getter provides a unified and simple interface to collect surface water data from the following state water portals:

|State|Site|Source|
| --- | --- | --- |
| NSW | realtimedata.waternsw.com.au |CP|
| QLD | water-monitoring.information.qld.gov.au |PUBLISH|
| VIC | data.water.vic.gov.au |AT|
| SA  | bom.gov.au/waterdata/ | BOM Water Data Online|

The tool is configured to abstract away the details specific to each state water portal and return a consistent structure. By default it will return a daily mean of a flow in ML/day for a given gauge number, but storage level, storage volume, other intervals and aggregations are available.


Example of its use can be seen in Gauge_getter_example.ipynb notebook, contact ben.bradshaw@mdba.gov.au for more details.

## Local Installation via git

- Clone the repo in your local folder: for example, inside `~./users/john.doe` git clone `https://github.com/MDBAuth/MDBA_Gauge_Getter.git` which will create a git tracked project repository inside `~./users/john.doe/mdba_gauge_getter`.
- Create a virtual environment: for example, `conda create --name gauge_getter_env`.
- Activate the virtual environment: `conda activate gauge_getter_env`.
- Go inside the project folder i.e., `cd ~./users/john.doe/mdba_gauge_getter`.
- Check `git status` and `git branch`.
- Install dependencies with `pip3 install -r requirements.txt`
- (Optionally) install dev dependencies with `pip3 install -r requirements-dev.txt`
- Run `python3 setup.py install` to install the module

## Quick Start

- Install via pip with the command: `pip install mdba-gauge-getter`
- After installation, import the package with the command: `import mdba_gauge_getter.gauge_getter as gg`
- Import datetime for converting your intervals into python datetime object: `import datetime as dt`

## Usage

There are several options to call Gauge Getter which are as follows:
- `gauge_numbers` denotes the gauge(s) for which the parameters such as flow, lake/storage level, storage volume etc. will be obtained. It takes a list of strings (gauge numbers) as input.
- `start_time_user` denotes the start time of the userdefined interval. It takes a datetime python object as input.
- `end_time_user` denotes the end time of the userdefined interval. It takes a datetime python object as input.
- `data_source` denotes which state the gauge(s) belong(s) to which API to fetch the data from. Please note that SA does not currently have an API to obtain the data from; hence, the data is fetched from the BOM API. Different *data_source* options are:
    - <STATE> i.e., 'NSW', 'VIC', 'QLD', 'SA'/'BOM'
    - 'BOM'
- `var` denotes the parameter to retreieve such as flow, lake/storage level, storage volume etc. It takes a string indicating the parameter type as input. Different string notation for different *var* options are:
    - 'F' for flow (default).
    - 'L' for water level used for flow calculation.
    - 'LL'/'SL' for lake/storage level.
    - 'SV' for storage volume. Please note that this is exclusively a BOM API parameter. Please specify the data source as 'BOM' if you would like to retrieve this parameter. 
- `interval` indicates the duration the parameter data are collected for aggregation. Different *interval* options are:
    - 'day'. Alternate options for BOM API call is: 'd'.
    - 'hour'. Alternate options for BOM API call is: 'h'.
    - 'month'. Alternate options for BOM API call is: 'm'.
    - 'year'. Alternate options for BOM API call is: 'y'.
- `data_type` inidcates the aggregation method. Different *data_type* options are:
    - 'mean' (default). Alternate options for BOM API call are: 'avg', 'average', 'av' and 'a'.
    - 'min'. Alternate options for BOM API call is: 'minimum'. Only available when obtaining *daily* interval data.
    - 'max'. Alternate options for BOM API call is: 'maximum'. Only available when obtaining *daily* interval data.

## Support 
For issues relating to the script, a tutorial, or feedback please contact Ben Bradshaw (ben.bradshaw@mdba.gov.au) or Ahsanul Habib (ahsanul.habib@mdba.gov.au). 

For data issues please see the corresponding state water portals.
