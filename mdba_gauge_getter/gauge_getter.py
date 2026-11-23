import os
import json
import logging
import datetime
from decimal import Decimal
from typing import Tuple, List, Dict, TypeVar, Set, Optional, Any
import requests
import pandas as pd
from urllib.parse import quote


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
SA_DATASETS = {

    "A4250010": {
        "F": "Discharge.Master--Daily Read--ML/day",
        "L": "Water Level.Master--Daily Read"
    },
    "A4260501": {

        "L": "Water Level.Master--Daily Read"
    },
    "A4260506": {

        "L": "Water Level.Master--Daily Read"
    },
    "A4260508": {

        "L": "Water Level.Master--Daily Read"
    },

    "A4260633": {
        "L": "Tide Height.Best Available--Continuous"
    },

    "A4261002": {
        "F": "Discharge.Total barrage flow"
    },
    "A4260505": {
    "F": "Discharge.Master--Daily Read--ML/day"
    },
    "A4260507": {
    "F": "Discharge.Master--Daily Read--ML/day"
    },
    "A4260509": {
    "F": "Discharge.Master--Daily Read--ML/day"
    },
    "A4260524": {
        "L": "Lake Level.Master--Daily Read"
    },
    "A4261001": {
        "F": "Discharge.Master--Daily Calculation--ML/day"
    },

}


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
def gauge_pull_sa(
    gauge_numbers: List[str],
    start_time_user: datetime.date,
    end_time_user: datetime.date,
    var: str = 'F',
    interval: str = 'day',
    data_type: str = 'mean'
) -> pd.DataFrame:

    extracted_gauge = []

    for gauge in gauge_numbers:

        if gauge not in SA_DATASETS:
            raise ValueError(
                f"No SA dataset configured for gauge {gauge}"
            )

        if var not in SA_DATASETS[gauge]:
            raise ValueError(
                f"No SA dataset configured for gauge {gauge} var {var}"
            )

        dataset = (
            SA_DATASETS[gauge][var]
            + "@"
            + gauge
        )

        dataset = quote(dataset)

        if var == "F":
            unit_id = 241

        elif var == "L":
            unit_id = 82

        else:
            raise ValueError(
                f"Unsupported SA variable {var}"
            )

        url = (
            "https://water.data.sa.gov.au/Export/DataSet"
            f"?DataSet={dataset}"
            "&Calendar=CALENDARYEAR"
            f"&StartTime={start_time_user:%Y-%m-%d}"
            f"&EndTime={end_time_user:%Y-%m-%d}"
            "&DateRange=Custom"
            f"&UnitID={unit_id}"
            "&Conversion=Instantaneous"
            "&IntervalPoints=PointsAsRecorded"
            "&ApprovalLevels=False"
            "&Qualifiers=False"
            "&Step=1"
            "&ExportFormat=csv"
            "&Compressed=false"
            "&RoundData=True"
            "&GradeCodes=True"
            "&InterpolationTypes=False"
            "&Timezone=9.5"
        )

        df = pd.read_csv(
            url,
            skiprows=3
        )

        df = df.iloc[1:].reset_index(drop=True)

        df.columns = [
            "Timestamp",
            "Value",
            "Grade Code"
        ]

        for _, row in df.iterrows():

            objRow = [
                "SA",
                gauge,
                "WATER",
                pd.to_datetime(row["Timestamp"]),
                float(row["Value"]),
                row["Grade Code"]
            ]

            extracted_gauge.append(objRow)

    return extracted_gauge


def gauge_pull(gauge_numbers: List[str], start_time_user: datetime.date, end_time_user: datetime.date,
               var: str = 'F', interval: str = 'day', data_type: str = 'mean', data_source: str = 'state') -> pd.DataFrame:
    '''
    Given a list of gauge numbers, sorts the list into state groups, and queries relevant
    HTTP endpoints for data, returning as a Pandas dataframe object.

    `data_source` is retained for backwards compatibility. Data is always fetched from the
    state portals; the BOM data source was removed and `data_source='BOM'` raises ValueError.
    '''

    if isinstance(gauge_numbers, str):
        gauge_numbers = [gauge_numbers]

    if str(data_source).lower() == 'bom':
        raise ValueError("The 'BOM' data_source is no longer supported. "
                         "Data is fetched from the state water portals only.")

    gauges_by_state = sort_gauges_by_state(gauge_numbers)

    data: List[List[Any]] = []

    if gauges_by_state['SA']:
        data += gauge_pull_sa(
            gauges_by_state['SA'],
            start_time_user,
            end_time_user,
            var,
            interval,
            data_type
        )

    nsw = process_gauge_pull(gauges_by_state['NSW'], 'NSW', 'CP', start_time_user,
                             end_time_user, var, interval, data_type)
    if not len(nsw) and len(gauges_by_state['NSW']) > 0:
        log.warning('No NSW data returned')
    data += nsw

    vic = process_gauge_pull(gauges_by_state['VIC'], 'VIC', 'PUBLISH', start_time_user,
                             end_time_user, var, interval, data_type)
    if not len(vic) and len(gauges_by_state['VIC']) > 0:
        log.warning('No VIC data returned')
    data += vic

    qld = process_gauge_pull(gauges_by_state['QLD'], 'QLD', 'AT', start_time_user,
                             end_time_user, var, interval, data_type)
    if not len(qld) and len(gauges_by_state['QLD']) > 0:
        log.warning('No QLD data returned')
    data += qld

    barrage_gauges = list(set(gauges_by_state['rest']) & BARRAGE_GAUGES)
    if barrage_gauges:
        data += gauge_pull_aq(barrage_gauges, start_time_user,
                              end_time_user, var, interval, data_type)

    cols = ['DATASOURCEID', 'SITEID', 'SUBJECTID', 'DATETIME', 'VALUE', 'QUALITYCODE']
    return pd.DataFrame(data=data, columns=cols)
