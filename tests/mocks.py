import json
import requests
import pandas as pd

# pylint: disable=missing-function-docstring,missing-module-docstring,too-few-public-methods
# pylint: disable=missing-class-docstring,unused-argument

MOCK_CSV = '''
site name,gauge number,owner,lat,lon
Gauge1.0,"1",WA  - Gauge1.0,-1.111,1.111
Gauge2.0,"2",NSW - Gauge2.0,-2.222,2.222
Gauge3.0,3,NSW - Gauge3.0,-3.333,3.333
Gauge3.1,3,QLD - Gauge3.1,-3.111,3.111
Gauge4.0,4,QLD - Gauge4.0,-4.444,4.444
Gauge4.1,4,QLD - Gauge4.1,-4.111,4.111
Gauge5,SomeRandomString,QLD - Used to force the col datatype to string,-5.555,5.555
random data (This line is stripped in init())
'''.strip()


class MockRequestLib:
    def __init__(self):
        self.status_code = 200
        self.response_data = json.dumps({'success': True}).encode()
        self.calls = []

    def get(self, url) -> requests.Response:
        self.calls.append(url)
        ret = requests.Response()
        ret.status_code = self.status_code
        ret._content = self.response_data
        return ret


class MockCallStateAPI:
    def __init__(self):
        self.calls = []

    def call_state_api(self, state, indicative_sites, start_time, end_time, data_source,
                       var, interval, data_type):
        self.calls.append([state, indicative_sites, start_time, end_time, data_source,
                           var, interval, data_type])
        return {'success': True}

class MockProcessGaugePulls:
    def __init__(self):
        self.calls = []

    def process_gauge_pull(self, *args):
        self.calls.append(args)
        return [args]

class MockPandaDataFrame:
    def __init__(self):
        self.columns = None
        self.calls = []

    def DataFrame(self, data, columns):
        self.calls.append([data, columns])
        return [data, columns]


class MockGaugePull:
    def __init__(self):
        self.calls = []

    def gauge_pull(self, *args):
        self.calls.append(args)
        return pd.DataFrame()


class MockExtractData:
    def __init__(self):
        self.calls = []

    def extract_data(self, state, data):
        self.calls.append([state, data])
        return [[state, data]]


def mock_sort_gauges_by_state(states):
    return {
        'NSW': ['1', '5', '9'], #  NSW
        'QLD': ['2', '6', '10'], # QLD
        'VIC': ['3', '7', '11'], # VIC
        'rest': ['4', '8', '12'] # Rest
    }

def mock_tqdm(l, desc, position, leave, bar_format):
    return l

