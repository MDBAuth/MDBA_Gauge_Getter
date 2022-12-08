import json
import datetime
from io import StringIO
from decimal import Decimal
from typing import Dict, Any
import pytest
import logging
import warnings
import requests
import pandas as pd
import bom_water
from mdba_gauge_getter import gauge_getter
from mocks import MockRequestLib, MockCallStateAPI, \
    MockPandasDataFrame, MockGaugePullBOM, MockExtractData, \
    mock_sort_gauges_by_state, mock_tqdm, MOCK_CSV, MockProcessGaugePulls

# pylint: disable=missing-function-docstring,missing-module-docstring
logging.basicConfig()
log = logging.getLogger(__name__[:-3])
log.setLevel(logging.INFO)

REAL_REFERENCES = {
    'requests': gauge_getter.requests,
    'pd': gauge_getter.pd,
    'sort_gauges_by_state': gauge_getter.sort_gauges_by_state,
    'extract_data': gauge_getter.extract_data,
    'gauge_data_uri': gauge_getter.gauge_data_uri,
    'gauge_pull': gauge_getter.gauge_pull,
    'process_gauge_pull': gauge_getter.process_gauge_pull,

}

@pytest.fixture(autouse=True)
def reset():
    '''
    This function 'wraps' all below functions, see
    https://stackoverflow.com/questions/22627659/
    https://realpython.com/primer-on-python-decorators/
    '''
    for k, v in REAL_REFERENCES.items():
        setattr(gauge_getter, k, v)
    gauge_getter.requests = MockRequestLib()
    if hasattr(gauge_getter, 'gauges'): # TODO-DeprecatedContent - Delete this block
        gauge_getter.gauges = None
    if hasattr(gauge_getter, 'lstObservation'): # TODO-DeprecatedContent - Delete this block
        gauge_getter.lstObservation = []
    gauge_getter.tqdm = mock_tqdm # TODO-DeprecatedContent - Delete this line
    yield # This is where the function executes
    # We're now out of the function

def test_init():
    gauge_getter.init()
    assert gauge_getter.gauges is not None


def test_call_state_api():
    start_date = datetime.datetime.strptime('2000-01-31', '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime('2000-02-01', '%Y-%m-%d').date()

    r = gauge_getter.call_state_api('NSW', ['A', 'B', 'C'], start_date, end_date,
                                    'test-data-source', 'F',
                                    'test-interval', 'test-data-type')
    assert isinstance(r['success'], bool) and r['success']
    assert len(gauge_getter.requests.calls) == 1
    req_url = gauge_getter.requests.calls[-1]
    req_url = req_url.split('?', 1)
    

    assert req_url[0] == 'https://realtimedata.waternsw.com.au/cgi/webservice.exe'
    j = json.loads(req_url[1])
    assert j == {
        'params': {
            'site_list': 'A,B,C', 'start_time': '20000131000000', 'varfrom': '100.00',
            'interval': 'test-interval', 'varto': '141.00', 'datasource': 'test-data-source',
            'end_time': '20000201000000', 'data_type': 'test-data-type', 'multiplier': '1'
        },
        'function': 'get_ts_traces', 'version': '2'
    }

    gauge_getter.requests.HTTPError = requests.HTTPError
    gauge_getter.requests.status_code = 400
    with pytest.raises(requests.HTTPError) as e:
        r = gauge_getter.call_state_api('NSW', ['A', 'B', 'C'],
                                        start_date, end_date, 'test-data-source',
                                        'F',
                                        'test-interval', 'test-data-type')
    assert 'failed with HTTP Response code 400' in str(e)

    gauge_getter.requests.status_code = 200
    gauge_getter.requests.response_data = 'Data which is not valid JSON'.encode()
    with pytest.raises(json.decoder.JSONDecodeError) as e:
        r = gauge_getter.call_state_api('NSW', ['A', 'B', 'C'], start_date, end_date,
                                        'test-data-source', 'F',
                                        'test-interval', 'test-data-type')
    assert 'Unable to parse response to request' in str(e)

def test_call_state_api_exceptions():
    start_date = datetime.datetime.strptime('2000-01-31', '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime('2000-02-01', '%Y-%m-%d').date()

    # Ensure critical path completes successfully.
    gauge_getter.call_state_api('NSW', ['A', 'B', 'C'], start_date, end_date,
                                'test-data-source', 'F',
                                'test-interval', 'test-data-type')

    with pytest.raises(TypeError):
        gauge_getter.call_state_api('NSW', ['A', 'B', 'C'], "20210101", end_date,
                                    'test-data-source', 'F',
                                    'test-interval', 'test-data-type')
    with pytest.raises(TypeError):
        gauge_getter.call_state_api('NSW', ['A', 'B', 'C'], start_date, "20210101",
                                    'test-data-source', 'F',
                                    'test-interval', 'test-data-type')


def test_split_into_chunks():
    l = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    r1 = gauge_getter.split_into_chunks(l, 1)
    assert r1 == [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12]]

    r2 = gauge_getter.split_into_chunks(l, 2)
    assert r2 == [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11], [12]]

    r3 = gauge_getter.split_into_chunks(l, 3)
    assert r3 == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11], [12]]

    r4 = gauge_getter.split_into_chunks(l, 4)
    assert r4 == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12]]

    r12 = gauge_getter.split_into_chunks(l, 13)
    assert r12 == [l]

    r13 = gauge_getter.split_into_chunks(l, 14)
    assert r13 == [l]

    r1000 = gauge_getter.split_into_chunks(l, 1000)
    assert r1000 == [l]


def test_extract_data():
    wrapper = {
        'error_num': 0,
        'return': {
            'traces':  [
                {
                    'site': 'site1',
                    'trace': [
                        {'q': 901, 't': '20210101010101', 'v': 'trace1_v'},
                        {'q': 902, 't': '20220202010101', 'v': 'trace2_v'},
                        {'q': 903, 't': '20230303010101', 'v': 'trace3_v'},
                        {'q': 1001, 't': '20230303010101', 'v': 'trace3_v'},
                    ]
                }
            ]
        }
    }
    ret = gauge_getter.extract_data('test-state', wrapper)
    assert ret == [
        ['test-state', 'site1', 'WATER', datetime.date(2021, 1, 1), 'trace1_v', 901],
        ['test-state', 'site1', 'WATER', datetime.date(2022, 2, 2), 'trace2_v', 902],
        ['test-state', 'site1', 'WATER', datetime.date(2023, 3, 3), 'trace3_v', 903]
    ]

def test_gauge_pull():
    m = MockProcessGaugePulls()
    b = MockGaugePullBOM()
    gauge_getter.pd = MockPandasDataFrame()

    gauge_getter.extract_data = MockExtractData().extract_data
    gauge_getter.sort_gauges_by_state = mock_sort_gauges_by_state
    gauge_getter.process_gauge_pull = m.process_gauge_pull
    start = datetime.datetime.strptime('2000-01-31', '%Y-%m-%d').date()
    end = datetime.datetime.strptime('2000-02-01', '%Y-%m-%d').date()

    gauge_getter.gauge_pull([
        '1', '3', # NSW
        '2', '3', '4', # QLD
        '4', '5', # VIC
        '6', # SA
        '10', '15' # Rest did not appear in the calls variable
        ], start, end)

    calls = m.calls
    calls.append(b.calls)
    
    log.warning(f'{calls[0]}\n{calls[1]}\n{calls[2]}\n{calls[3]}')
    warnings.warn(UserWarning(f'\n#Calls: {len(calls)}\n{calls[0]}\n{calls[1]}\n{calls[2]}\n{calls[3]}'))
    assert(len(calls)) == 4
    assert calls[0] == (['1', '3'], 'NSW', 'CP', start, end, 'F', 'day', 'mean')
    assert calls[1] == (['4', '5'], 'VIC', 'PUBLISH', start, end, 'F', 'day', 'mean')
    assert calls[2] == (['2', '3', '4'], 'QLD', 'AT', start, end, 'F', 'day', 'mean')
    assert calls[3] == []

    calls = gauge_getter.pd.calls
    assert len(calls) == 2
    warnings.warn(UserWarning(f'\n#Calls: {len(calls)}\n{calls[0]}\n{calls[1]}'))
    assert len(calls[1]) == 2
    data, columns = calls[1]
    assert columns == ['DATASOURCEID', 'SITEID', 'SUBJECTID', 'DATETIME', 'VALUE', 'QUALITYCODE']
    assert len(data) == 3
    assert data[0] == (
        ['1', '3'], 'NSW', 'CP', start, end, 'F', 'day', 'mean'
    )
    assert data[1] == (
        ['4', '5'], 'VIC', 'PUBLISH', start, end, 'F', 'day', 'mean'
    )
    assert data[2] == (
        ['2', '3', '4'], 'QLD', 'AT', start, end, 'F', 'day', 'mean'
    )


def test_gauge_pull_bom():
    b = MockGaugePullBOM()
    gauge_getter.pd = MockPandasDataFrame()
    gauge_getter.gauge_pull_bom = b.gauge_pull_bom
    gauge_getter.sort_gauges_by_state = mock_sort_gauges_by_state
    start = datetime.datetime.strptime('2000-01-31', '%Y-%m-%d').date()
    end = datetime.datetime.strptime('2000-02-01', '%Y-%m-%d').date()

    gauge_getter.gauge_pull([
        '6', # SA
        '10', '15' # Rest 
        ], start, end)

    calls = b.calls
    warnings.warn(UserWarning(f'\n#Calls: {len(calls)}\n{calls}'))
    assert(len(calls)) == 1
    data = calls[0][0]
    assert data == ['6']
    b = MockGaugePullBOM()

def test_bom_params():
    bm = bom_water.BomWater()
    
    r1 = gauge_getter.bom_params('F', 'hour', 'mean')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_HourlyMean 

    r1 = gauge_getter.bom_params('F', 'day', 'min')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_DailyMin 
 
    r1 = gauge_getter.bom_params('F', 'day', 'average')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_DailyMean 
  
    r1 = gauge_getter.bom_params('F', 'day', 'max')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_DailyMax 

    r1 = gauge_getter.bom_params('F', 'month', 'avg')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_MonthlyMean 
        
    r1 = gauge_getter.bom_params('F', 'year', 'av')
    assert r1[0] == bm.properties.Water_Course_Discharge
    assert r1[1] == bm.procedures.Pat4_C_B_1_YearlyMean     


    r1 = gauge_getter.bom_params('L', 'hour', 'average')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_HourlyMean 

    r1 = gauge_getter.bom_params('L', 'day', 'min')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_DailyMin 
 
    r1 = gauge_getter.bom_params('L', 'day', 'mean')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_DailyMean 
  
    r1 = gauge_getter.bom_params('L', 'day', 'max')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_DailyMax 

    r1 = gauge_getter.bom_params('L', 'month', 'avg')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_MonthlyMean 
        
    r1 = gauge_getter.bom_params('L', 'year', 'av')
    assert r1[0] == bm.properties.Water_Course_Level
    assert r1[1] == bm.procedures.Pat3_C_B_1_YearlyMean 
        

    r1 = gauge_getter.bom_params('SL', 'hour', 'average')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_HourlyMean 

    r1 = gauge_getter.bom_params('SL', 'day', 'min')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_DailyMin 
 
    r1 = gauge_getter.bom_params('SL', 'day', 'mean')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_DailyMean 
  
    r1 = gauge_getter.bom_params('SL', 'day', 'max')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_DailyMax 

    r1 = gauge_getter.bom_params('SL', 'month', 'avg')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_MonthlyMean 
        
    r1 = gauge_getter.bom_params('SL', 'year', 'av')
    assert r1[0] == bm.properties.Storage_Level
    assert r1[1] == bm.procedures.Pat7_C_B_1_YearlyMean 
        

    r1 = gauge_getter.bom_params('SV', 'hour', 'average')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_HourlyMean 

    r1 = gauge_getter.bom_params('SV', 'day', 'min')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_DailyMin 
 
    r1 = gauge_getter.bom_params('SV', 'day', 'mean')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_DailyMean 
  
    r1 = gauge_getter.bom_params('SV', 'day', 'max')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_DailyMax 

    r1 = gauge_getter.bom_params('SV', 'month', 'avg')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_MonthlyMean 
        
    r1 = gauge_getter.bom_params('SV', 'year', 'av')
    assert r1[0] == bm.properties.Storage_Volume
    assert r1[1] == bm.procedures.Pat6_C_B_1_YearlyMean 


def test_process_gauge_pull():
    mock_call_state_api = MockCallStateAPI()
    mock_extract_data = MockExtractData()
    gauge_getter.call_state_api = mock_call_state_api.call_state_api
    gauge_getter.extract_data = mock_extract_data.extract_data
    start = datetime.datetime.strptime('2000-01-31', '%Y-%m-%d').date()
    end = datetime.datetime.strptime('2000-02-01', '%Y-%m-%d').date()
    var = 'F'

    gauge_getter.process_gauge_pull(['1', '6', '11'], 'NSW', 'CP', start, end,
                                     'F','day', 'mean')
    assert len(mock_call_state_api.calls[0])  == len([['NSW', ['1','6','11'], start, end, 'CP', var, 'day', 'mean']][0])                             
    assert mock_call_state_api.calls == [
        ['NSW', ['1','6','11'], start, end, 'CP', var, 'day', 'mean']]
        #['NSW', ['5'], start, end, 'CP', var, 'day', 'mean'],
        #['NSW', ['9'], start, end, 'CP', var, 'day', 'mean']
    #]
    assert mock_extract_data.calls == [
        ['NSW', {'success': True}]]


def test_states_for_gauge():
    gauge_getter.gauge_data_uri = StringIO(MOCK_CSV)
    assert gauge_getter.get_states_for_gauge('1') == set(['NSW'])
    assert gauge_getter.get_states_for_gauge('2') == set(['QLD'])
    assert gauge_getter.get_states_for_gauge('3') == set(['NSW', 'QLD'])
    assert gauge_getter.get_states_for_gauge('4') == set(['QLD', 'VIC'])
    assert gauge_getter.get_states_for_gauge('5') == set(['VIC'])
    assert gauge_getter.get_states_for_gauge('6') == set(['SA'])

def dict_matches(d1: Dict[str, Any], d2: Dict[str, Any]):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in d1_keys if d1[o] != d2[o]}
    return not modified and not removed and not added

def test_sort_gauges_by_state():
    gauge_getter.gauge_data_uri = StringIO(MOCK_CSV)
    print(gauge_getter.gauge_data_uri)
    gauge_getter.init()
    ret = gauge_getter.sort_gauges_by_state(['1', '2', '3', '4', '5', '6', '10'])
    expect = {'NSW': ['1', '3'], 'QLD': ['2', '3', '4'], 'VIC': ['4', '5'], 'SA': ['6'], 'rest': ['10']}
    if not dict_matches(ret, expect):
        raise Exception(f'Dict \'{ret}\' does not match dict \'{expect}\'')


if __name__ == '__main__':
    import pudb
    pudb.set_trace()
    test_state_sorter()
