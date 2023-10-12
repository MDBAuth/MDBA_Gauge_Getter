import os
import json
import logging
import datetime
from decimal import Decimal
from typing import Tuple, List, Dict, TypeVar, Set, Optional, Any
import requests
import pandas as pd
import bom_water


logging.basicConfig()
log = logging.getLogger(__name__[:-3])
log.setLevel(logging.INFO)

T = TypeVar('T') 

gauge_data_uri = os.path.join(os.path.dirname(os.path.abspath(__file__)), \
                              'data/bom_gauge_data.csv')
gauges: pd.core.frame.DataFrame = None

STATE_URLS = {
    'NSW': 'realtimedata.waternsw.com.au',
    'QLD': 'water-monitoring.information.qld.gov.au',
    'VIC': 'data.water.vic.gov.au'
}


STATE_LEVEL_VarFrom = {
    'NSW' : Decimal('100.00'),
    'VIC' : Decimal('100.00'),
    'QLD' : Decimal('100.00')
}

STATE_LEVEL_VarTo = {
    'NSW': Decimal('100.00'),
    'VIC' : Decimal('100.00'),
    'QLD' : Decimal('100.00')
}

STATE_FLOW_VarFrom = {
    'NSW': Decimal('100.00'),
    'VIC' : Decimal('100.00'),
    'QLD' : Decimal('100.00')
}

STATE_FLOW_VarTo = {
    'NSW': Decimal('141.00'),
    'VIC' : Decimal('141.00'),
    'QLD' : Decimal('141.00')
}

STATE_LAKELEVEL_VarFrom = {
    'NSW' : Decimal('130.00'),
    'VIC' : Decimal('130.00'),
    'QLD' : Decimal('130.00')
}

STATE_LAKELEVEL_VarTo = {
    'NSW': Decimal('130.00'),
    'VIC' : Decimal('130.00'),
    'QLD' : Decimal('130.00')
}

STATE_STORAGEVOLUME_VarFrom = {
    'NSW' : Decimal('130.00'),
    'VIC' : Decimal('136.00'),
    'QLD' : Decimal('136.00')
}

STATE_STORAGEVOLUME_VarTo = {
    'NSW': Decimal('136.00'),
    'VIC' : Decimal('136.00'),
    'QLD' : Decimal('136.00')
}

STATE_PRECIP_VarFrom = {
    'NSW' : Decimal('10.00'),
    'VIC' : Decimal('10.00'),
    'QLD' : Decimal('10.00')
}

STATE_PRECIP_VarTo = {
    'NSW' : Decimal('10.00'),
    'VIC' : Decimal('10.00'),
    'QLD' : Decimal('10.00')
}

STATE_DO_VarFrom = {
    'NSW' : Decimal('2351.00'),
    'VIC' : Decimal('2351.00'),
    'QLD' : Decimal('2351.00')
}

STATE_DO_VarTo = {
    'NSW' : Decimal('2351.00'),
    'VIC' : Decimal('2351.00'),
    'QLD' : Decimal('2351.00')
}

STATE_WATERTEMP_VarFrom = {
    'NSW' : Decimal('2080.00'),
    'VIC' : Decimal('2080.00'),
    'QLD' : Decimal('2080.00')
}

STATE_WATERTEMP_VarTo = {
    'NSW' : Decimal('2080.00'),
    'VIC' : Decimal('2080.00'),
    'QLD' : Decimal('2080.00')
}

MAX_SITES_PER_REQUEST = {
    'NSW': 5,
    'VIC': 5,
    'QLD': 5,
    'SA' : 5 
}

BARRAGE_GAUGES ={"A4261002"}


def init() -> None:
    '''
    Loads gauges from disk. This will dynamically trigger when other libraries require
    gague data.
    '''
    global gauges
    gauges = pd.read_csv(gauge_data_uri, skiprows=1, skipfooter=1,
                         names=['gauge_name', 'gauge_number',
                                'gauge_owner', 'lat', 'long'], engine='python')
    gauges['State'] = gauges['gauge_owner'].apply(lambda x: x.strip().split(' ', 1)[0])
    gauges = gauges.drop(['lat', 'long', 'gauge_owner'], axis=1)


def get_states_for_gauge(gauge_number: str) -> Set[str]:
    '''
    Given a gauge number, returns a set of states which that gauge may belong to.
    '''

    # TODO-Review There's possibly a bug here - some gauges, such as 422204A (CULGOA @ WHYENBAH)
    # Return two results in different states, that may create integrity issues and
    # should be investigated. It is caused by the data within bom_gauge_data.csv. not application
    # logic.
    if not hasattr(gauges, "empty") or gauges.empty:
        init()
    matching = list(gauges[gauges['gauge_number'] == gauge_number]['State'])
    if len(matching) > 1:
        log.warning(f'Gauge {gauge_number} has {len(matching)} state results: {matching}')
    return set(matching)


def sort_gauges_by_state(gauge_numbers: List[str]) -> Dict[str, List[str]]:
    '''
    Splits the listed gauges into state-based lists.
    '''
    states: Dict[str, List[str]] = {
        'NSW': [],
        'QLD': [],
        'VIC': [],
        'SA': [],
        'rest': [],
    }

    for gauge in gauge_numbers:
        gauge_states = get_states_for_gauge(gauge)
        if gauge_states:
            for gauge_state in gauge_states:
                if gauge_state not in states:
                    gauge_state = 'rest'
                if gauge in states[gauge_state]:
                    continue
                states[gauge_state].append(gauge)
        else:
            states['rest'].append(gauge)
    return states


def call_state_api(state: str, indicative_sites: List[str], start_time: datetime.date,
                   end_time: datetime.date, data_source: str, var: str,
                   interval: str, data_type: str) -> Dict[str, Any]:
    '''
    Sends a web request with a destination based on `state` of the gauge.

    Returns a JSON dict object containing web responses, and will fail if the server returns
    either a non HTTP-200 error code, or invalid JSON
    '''
    if not isinstance(start_time, datetime.date):
        raise TypeError('start_time must be a datetime.date object, but got type '
                        f'{type(start_time)} (value: \'{start_time}\')')
    if not isinstance(end_time, datetime.date):
        raise TypeError('end_time must be a datetime.date object, but got type '
                        f'{type(end_time)} (value: \'{end_time}\')')
    
    url = STATE_URLS[state]

    if (var=="L"):
        var_from = STATE_LEVEL_VarFrom[state]
        var_to = STATE_LEVEL_VarTo[state]

    elif (var=="F"):
        var_from = STATE_FLOW_VarFrom[state]
        var_to = STATE_FLOW_VarTo[state]

    elif (var=="LL"):
        var_from = STATE_LAKELEVEL_VarFrom[state]
        var_to = STATE_LAKELEVEL_VarTo[state]

    elif (var=="SV"):
        var_from = STATE_STORAGEVOLUME_VarFrom[state]
        var_to = STATE_STORAGEVOLUME_VarTo[state]

    elif (var=="P"):
        var_from = STATE_PRECIP_VarFrom[state]
        var_to = STATE_PRECIP_VarTo[state]

    elif (var=="DO"):
        var_from = STATE_DO_VarFrom[state]
        var_to = STATE_DO_VarTo[state]

    elif (var=="WT"):
        var_from = STATE_WATERTEMP_VarFrom[state]
        var_to = STATE_WATERTEMP_VarTo[state]

    else:
        raise AttributeError("The input 'var' takes 'L', 'F', 'LL', 'SV', 'P', 'DO', 'WT' only.") # TODO: Implement a more accurate exception handling

    sites = ','.join(indicative_sites)
    data = {
        'params': {
            'site_list': sites,
            'start_time': start_time.strftime('%Y%m%d') + '000000',
            'varfrom': f'{var_from:.2f}',
            'interval': str(interval),
            'varto': f'{var_to:.2f}', 
            'datasource': str(data_source),
            'end_time': end_time.strftime('%Y%m%d') + '000000',
            'data_type': str(data_type),
            'multiplier':'1'
        },
        'function':'get_ts_traces',
        'version':'2'
    }
    if((state == "NSW") & (var=="L")): #nsw L is strange about 100.00
        data = {
            'params': {
                'site_list': sites,
                'start_time': start_time.strftime('%Y%m%d') + '000000',
                'varfrom': "100",
                'interval': str(interval),
                'varto': "100", 
                'datasource': str(data_source),
                'end_time': end_time.strftime('%Y%m%d') + '000000',
                'data_type': str(data_type),
                'multiplier':'1'
            },
            'function':'get_ts_traces',
            'version':'2'
        }    

    json_data = json.dumps(data, separators=(',', ':'))

 
    req_url = f'https://{url}/cgi/webservice.exe?{json_data}'

    if state =="QLD": # replace when QLD upgrades
        req_url = f'https://{url}/cgi/webservice.pl?{json_data}'

    req_url = req_url.replace(' ', '%20')
    
    # TODO-idiosyncratic the use of JSON in the query string seems werid, this should be a HTTP POST
    # but requires endpoints to support it..
    log.debug(f'Sending request to URL \'{req_url}\'')
    r = requests.get(req_url)
    if not r.status_code == 200: 
        raise requests.HTTPError(f'Request to \'{url}\' failed with HTTP Response code '
                                 f'{r.status_code} and HTTP Response:\n{r.content}')
    try:
        return json.loads(r.content)
    except json.decoder.JSONDecodeError:
        raise json.decoder.JSONDecodeError(
            f'Unable to parse response to request to \'{url}\'. The server returned invalid JSON '
            f' data. Got HTTP Response code {r.status_code} and HTTP Response:\n{r.content}',
            r.content.decode(), 0)


def extract_data(state: str, data) -> List[List[Any]]:
    """
    Collects 
    """
    
    # log.info(f'data keys {data.keys()}')
    # log.info(f'data is {data}')
    extracted = []
    if '_return' in data.keys():
        
        data['return'] = data['_return']
        del data['_return']
    try:
        for sample in data['return']['traces']:
            for obs in sample['trace']:
                # TODO-Detail - put detail re the purpose of obs['q'] - I don't know what/why this
                # logic exists, it's obviously to sanitise data but unclear on what/why
                # TODO-idiosyncratic: was < 999 prior to refactor, this means that 998 is the max
                # accepted number, this would presumably be 999, but I can't say for sure
                if int(obs['q']) >= 999:
                    continue
                obsdate = datetime.datetime.strptime(str(obs['t']), '%Y%m%d%H%M%S').date()
                objRow = [state, sample['site'], 'WATER', obsdate, obs['v'], obs['q']]
                extracted.append(objRow)

    except KeyError:
        log.error('No valid data contained in response, skipping')

    return extracted


def split_into_chunks(input_list: List[T], maxlen: int) -> List[List[T]]:
    '''
    Splits a list into many lists of maximum `maxlen` length. Let input_list = [1,2,3,4].
    When:

    - `maxlen=1` => `[[1],[2],[3],[4]]`
    - `maxlen=2` => `[[1, 2],[3, 4]]`
    - `maxlen=3` => `[[1, 2, 3], [4]]`
    - `maxlen=4` => `[[1, 2, 3, 4]]`
    - `maxlen=5` => `[[1, 2, 3, 4]]`
    '''

    assert(maxlen) > 0
    l = []
    for i in range(0, len(input_list), maxlen):
        l.append(input_list[i:i + maxlen])
    return l


def process_gauge_pull(sitelist: List[str], callstate: str, call_data_source: str,
                       start_time_user: datetime.date, end_time_user: datetime.date,
                       var: str, interval: str,
                       data_type: str) -> List[List[Any]]:
    '''
    Intermediate function which splits many gauge_pull records into separate web requests
    and provides user feedback on progress
    '''

    max_sites_per_request = MAX_SITES_PER_REQUEST[callstate]
    site_chunks = split_into_chunks(sitelist, max_sites_per_request)
    response_data: List[List[str]] = []
    for index, s in enumerate(site_chunks):
        log.info(f'{callstate} - Request {index+1} of {len(site_chunks)}')
        ret = call_state_api(callstate, s, start_time_user, end_time_user,
                             call_data_source, var, interval, data_type)

        response_data += extract_data(callstate, ret)

    return response_data

def fixdate(timestamp):
    date = timestamp.to_pydatetime()
    date = date.date()
    #datetime.astimzone('Australia/Sydney',date) #date.tz_localize('Australia/Sydney')   #datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
    return date

def bom_params(var, interval, data_type):
    bm = bom_water.BomWater()
    if var == "F":
        prop = bm.properties.Water_Course_Discharge
        if (interval.lower() in ['hour', 'h']):
            procedure = bm.procedures.Pat4_C_B_1_HourlyMean
        elif (interval.lower() in ['day', 'd']):
            if (data_type in ['min', 'minimum']):
                procedure = bm.procedures.Pat4_C_B_1_DailyMin
            elif (data_type in ['mean', 'avg', 'average', 'av', 'a']):
                procedure = bm.procedures.Pat4_C_B_1_DailyMean
            elif (data_type in ['max', 'maximum']):
                procedure = bm.procedures.Pat4_C_B_1_DailyMax        
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat4_C_B_1_MonthlyMean
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat4_C_B_1_YearlyMean
    elif var == "L":
        prop = bm.properties.Water_Course_Level
        if (interval.lower() in ['hour', 'h']):
            procedure = bm.procedures.Pat3_C_B_1_HourlyMean
        elif (interval.lower() in ['day', 'd']):
            if (data_type in ['min', 'minimum']):
                procedure = bm.procedures.Pat3_C_B_1_DailyMin
            elif (data_type in ['mean', 'avg', 'average', 'av', 'a']):
                procedure = bm.procedures.Pat3_C_B_1_DailyMean
            elif (data_type in ['max', 'maximum']):
                procedure = bm.procedures.Pat3_C_B_1_DailyMax        
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat3_C_B_1_MonthlyMean
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat3_C_B_1_YearlyMean
    elif var in ["LL", "SL"]:
        prop = bm.properties.Storage_Level
        if (interval.lower() in ['hour', 'h']):
            procedure = bm.procedures.Pat7_C_B_1_HourlyMean
        elif (interval.lower() in ['day', 'd']):
            if (data_type in ['min', 'minimum']):
                procedure = bm.procedures.Pat7_C_B_1_DailyMin
            elif (data_type in ['mean', 'avg', 'average', 'av', 'a']):
                procedure = bm.procedures.Pat7_C_B_1_DailyMean
            elif (data_type in ['max', 'maximum']):
                procedure = bm.procedures.Pat7_C_B_1_DailyMax        
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat7_C_B_1_MonthlyMean
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat7_C_B_1_YearlyMean
    elif var == "SV":
        prop = bm.properties.Storage_Volume
        if (interval.lower() in ['hour', 'h']):
            procedure = bm.procedures.Pat6_C_B_1_HourlyMean
        elif (interval.lower() in ['day', 'd']):
            if (data_type in ['min', 'minimum']):
                procedure = bm.procedures.Pat6_C_B_1_DailyMin
            elif (data_type in ['mean', 'avg', 'average', 'av', 'a']):
                procedure = bm.procedures.Pat6_C_B_1_DailyMean
            elif (data_type in ['max', 'maximum']):
                procedure = bm.procedures.Pat6_C_B_1_DailyMax        
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat6_C_B_1_MonthlyMean
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat6_C_B_1_YearlyMean

    elif var == "WT":
        prop = bm.properties.Water_Temperature
        if (interval.lower() in ['hour', 'h']):
            raise NotImplementedError('Hourly data not available for Water Temp')
        elif (interval.lower() in ['day', 'd']):
            if (data_type in ['min', 'minimum']):
                procedure = bm.procedures.Pat1_C_B_1_DailyMin
            elif (data_type in ['mean', 'avg', 'average', 'av', 'a']):
                procedure = bm.procedures.Pat1_C_B_1_DailyMean
            elif (data_type in ['max', 'maximum']):
                procedure = bm.procedures.Pat1_C_B_1_DailyMax
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat1_C_B_1_MonthlyMean
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat1_C_B_1_YearlyMean

    elif var == "P":
        prop = bm.properties.Rainfall
        if (interval.lower() in ['hour', 'h']):
            raise NotImplementedError('Hourly data not available for Precipitation')
        elif (interval.lower() in ['day', 'd']):
            procedure = bm.procedures.Pat2_C_B_1_DailyTot09
        elif (interval.lower() in ['month', 'm']):
            procedure = bm.procedures.Pat2_C_B_1_MonthlyTot24
        elif (interval.lower() in ['year', 'y']):
            procedure = bm.procedures.Pat2_C_B_1_YearlyTot24

    elif var == "DO":
            raise AttributeError("Var 'DO' not available on the BoM API")

    return prop, procedure

def gauge_pull_bom(gauge_numbers: List[str], start_time_user: datetime.date, end_time_user: datetime.date,
               var: str = 'F', interval: str = 'day', data_type: str = 'mean') -> pd.DataFrame:
    '''
    Given a list of gauge numbers, breaks the list into individual gauges, and uses BomWater to get data, 
    returning as a Pandas dataframe object in a gauge getter format.
    '''
    bm = bom_water.BomWater()
    
    prop, procedure = bom_params(var, interval, data_type)
    
    t_begin = start_time_user.strftime("%Y-%m-%dT%H:%M:%S%z")
    t_end = end_time_user.strftime("%Y-%m-%dT%H:%M:%S%z")

    # t_begin = "1800-01-01T00:00:00+10"
    # t_end = "2030-12-31T00:00:00+10"
    collect=[]
    for gauge in gauge_numbers:
        response = bm.request(bm.actions.GetObservation, gauge, prop, procedure, t_begin, t_end)
        # response_json = bm.xml_to_json(response.text)  
        ts = bm.parse_get_data(response)
        if ts.empty:
            ts = pd.DataFrame(columns=["DATASOURCEID","SITEID",	"SUBJECTID", "DATETIME", "VALUE", "QUALITYCODE"])
            collect.append(ts)
        else:
            # move to format DATASOURCEID	SITEID	SUBJECTID	DATETIME	VALUE	QUALITYCODE
            ts["DATASOURCEID"] = "BOM"
            ts["SITEID"] = gauge
            ts["SUBJECTID"] = "WATER"
            ts["DATETIME"] = ts.index.to_pydatetime()
            ts["DATETIME"] = pd.to_datetime(ts["DATETIME"])
            ts["DATETIME"] = ts["DATETIME"].apply(fixdate)
            if var.lower() == "f":
                ts["VALUE"] = 86.4*ts["Value[cumec]"] # Converting it from Cumec to ML/day
            elif var.lower() in ['l', 'll', 'sl']:
                ts["VALUE"] = ts["Value[m]"]
            elif var.lower() == 'sv':
                ts["VALUE"] = ts["Value[Ml]"]
            elif var.lower() == 'wt':
                ts["VALUE"] = ts["Value[°C]"]
            elif var.lower() == 'p':
                ts["VALUE"] = ts["Value[mm]"]
            ts["QUALITYCODE"] = ts["Quality"]
            ts.reset_index(drop=True, inplace=True)
            collect.append(ts[["DATASOURCEID","SITEID",	"SUBJECTID", "DATETIME", "VALUE", "QUALITYCODE"]])
            log.info(f'BOM Data DF: {collect}')

    output = pd.concat(collect)
    # log.info(f'BOM Data DF: {output}')
    output = output.values.tolist()
    # log.info(f'BOM Data Dict: {output}')
    return output

def gauge_pull_aq(gauge_numbers: List[str], start_time_user: datetime.date, end_time_user: datetime.date,
               var: str = 'F', interval: str = 'day', data_type: str = 'mean') -> pd.DataFrame:

    log.info(f'AQ gaugepull')
    extracted_gauge=[]
    for gauge in  gauge_numbers:
        head ="https://water.data.sa.gov.au/Export/BulkExportJson?"
        times ="DateRange=Custom&StartTime=" +start_time_user.strftime('%Y-%m-%d') +"&EndTime="+end_time_user.strftime('%Y-%m-%d') +"&TimeZone=9.5"
        dataset = "&Datasets[0].DatasetName=Discharge.Total%20barrage%20flow%40"+gauge
        format = "&ExportFormat=json"
        code = "&Datasets[0].Calculation=Instantaneous&Datasets[0].UnitId=241"

        url = head+ times + dataset + format +code
        log.info(url)

        x = requests.get(url)

        data = x.json()

        extracted = []
        for row in data['Rows']:
            obsdate = datetime.datetime.strptime(str(row['Timestamp']), '%Y-%m-%dT%H:%M:%S%z').date()
            objRow = ["SA", data["Datasets"][0]["LocationIdentifier"], 'WATER', obsdate, row["Points"][0]["Value"], data["Datasets"][0]["Unit"]]
            extracted.append(objRow)
        extracted_gauge.extend(extracted)
    return extracted_gauge

def gauge_pull(gauge_numbers: List[str], start_time_user: datetime.date, end_time_user: datetime.date,
               var: str = 'F', interval: str = 'day', data_type: str = 'mean', data_source: str = 'state') -> pd.DataFrame:
    '''
    Given a list of gauge numbers, sorts the list into state groups, and queries relevant
    HTTP endpoints for data, returning as a Pandas dataframe object.
    '''

    if isinstance(gauge_numbers, str):
        gauge_numbers=[gauge_numbers]

    gauges_by_state = sort_gauges_by_state(gauge_numbers)
    

    if data_source.lower() == 'bom':
        gauges_by_state = {'NSW': [], 'QLD': [], 'VIC': [], 'SA': [], 'rest': [],'BOM': gauge_numbers}
    elif gauges_by_state['SA']:
        gauges_by_state['BOM'] = gauges_by_state['SA']

    # log.info(f'Gauges by state is: {gauges_by_state}')
    data: List[List[List[Any]]] = []
    nsw = process_gauge_pull(gauges_by_state['NSW'], 'NSW', 'CP', start_time_user,
                               end_time_user, var, interval, data_type)
    if not len(nsw) and len(gauges_by_state['NSW']) > 0:
        log.warn(f'Data not available from NSW API, querying BOM...')
        gauges_by_state['BOM'] = gauges_by_state['NSW']
        nsw += gauge_pull_bom(gauges_by_state['BOM'], start_time_user, 
                               end_time_user, var, interval, data_type)   
    data += nsw

    vic = process_gauge_pull(gauges_by_state['VIC'], 'VIC', 'PUBLISH', start_time_user,
                               end_time_user, var, interval, data_type)
    if not len(vic) and len(gauges_by_state['VIC']) > 0:
        log.warn(f'Data not available from VIC API, querying BOM...')
        gauges_by_state['BOM'] = gauges_by_state['VIC']
        vic += gauge_pull_bom(gauges_by_state['BOM'], start_time_user, 
                               end_time_user, var, interval, data_type)   
    data += vic

    qld = process_gauge_pull(gauges_by_state['QLD'], 'QLD', 'AT', start_time_user,
                               end_time_user, var, interval, data_type)
    if not len(qld) and len(gauges_by_state['QLD']) > 0:
        log.warn(f'Data not available from QLD API, querying BOM...')
        gauges_by_state['BOM'] = gauges_by_state['QLD']
        qld += gauge_pull_bom(gauges_by_state['BOM'], start_time_user, 
                               end_time_user, var, interval, data_type)   
    data += qld
    # log.info(f'State data:{data}')
    if 'BOM' in gauges_by_state:                          
        data += gauge_pull_bom(gauges_by_state['BOM'], start_time_user, 
                               end_time_user, var, interval, data_type)   
        # log.info(f'BOM data:{data}')
    barrage_gauges=list(set(gauges_by_state["rest"]) & BARRAGE_GAUGES)
    if barrage_gauges:
        data += gauge_pull_aq(barrage_gauges, start_time_user, 
                               end_time_user, var, interval, data_type)
   
    cols = ['DATASOURCEID', 'SITEID', 'SUBJECTID', 'DATETIME', 'VALUE', 'QUALITYCODE']
    flow_data_frame = pd.DataFrame(data=data, columns=cols)

    return flow_data_frame
