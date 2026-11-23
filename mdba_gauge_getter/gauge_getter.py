import os
import io
import re
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
SA_PORTAL = 'https://water.data.sa.gov.au'
SA_TIMEOUT = 60
SA_GAUGE_RE = re.compile(r'^A\d{6,7}$')  # SA gauge ids, e.g. A4260501

# For each `var`, the AQUARIUS parameter names to look for (in priority order), the
# unit id to ask the portal to convert to (None = leave as stored), and the pandas
# resample code for each `interval`.
SA_VAR_PARAMS = {
    'F':  {'params': ['Discharge'], 'unit_id': 241},                                  # ML/day
    'L':  {'params': ['Water Level', 'Tide Height'], 'unit_id': None},
    'LL': {'params': ['Lake Level', 'Water Level'], 'unit_id': None},
    'SV': {'params': ['Total Storage'], 'unit_id': None},                      # Total Lake/Storage Volume
}
SA_RESAMPLE = {'hour': 'h', 'day': 'D', 'month': 'MS', 'year': 'YS'}

_sa_session: Optional[requests.Session] = None
_sa_params: Optional[pd.DataFrame] = None
_sa_datasets: Dict[str, pd.DataFrame] = {}   # cache: param_id -> dataset list


def _sa_get_session() -> requests.Session:
    global _sa_session
    if _sa_session is None:
        _sa_session = requests.Session()
    return _sa_session


def sa_fetch_params() -> pd.DataFrame:
    '''Parameters (Discharge, Water Level, ...) the SA portal offers, with their ids.'''
    global _sa_params
    if _sa_params is None:
        r = _sa_get_session().post(f'{SA_PORTAL}/Data/List/', timeout=SA_TIMEOUT)
        r.raise_for_status()
        rows = re.findall(r'<option[^>]*value="(\d+)"[^>]*data-code="([^"]*)"[^>]*>([^<]*)<', r.text)
        rows += [(i, c, d) for c, i, d in
                 re.findall(r'<option[^>]*data-code="([^"]*)"[^>]*value="(\d+)"[^>]*>([^<]*)<', r.text)]
        _sa_params = pd.DataFrame(rows, columns=['param_id', 'param_name', 'param_desc']).drop_duplicates()
    return _sa_params


def sa_fetch_datasets(param_id: str) -> pd.DataFrame:
    '''Every dataset (time series) on the SA portal for one parameter. Cached per session.'''
    if param_id in _sa_datasets:
        return _sa_datasets[param_id]
    results: List[Dict[str, Any]] = []
    page = 1
    while True:
        query = {'page': page, 'pageSize': 5000, 'parameters[0]': param_id}
        r = _sa_get_session().post(f'{SA_PORTAL}/Data/Data_List', data=query, timeout=SA_TIMEOUT)
        r.raise_for_status()
        body = r.json()
        results += body['Data']
        if not body['Data'] or len(results) >= body['Total']:
            break
        page += 1
    df = pd.DataFrame(results, columns=['LocationIdentifier', 'DatasetIdentifier'] if not results else None)
    _sa_datasets[param_id] = df
    return df


def _sa_rank(dataset_id: str, interval: str) -> int:
    '''Lower is better. Prefer curated series; match "Daily" series to daily requests.'''
    label = dataset_id.split('@')[0].lower()
    score = 10
    if 'master' in label:
        score -= 3
    if 'best available' in label or 'total' in label:
        score -= 2
    if interval in ('day', 'month', 'year') and 'daily' in label:
        score -= 2
    if interval == 'hour' and 'continuous' in label:
        score -= 2
    if 'ml/day' in label:
        score -= 1
    if any(w in label for w in ('raw', 'telemetry', 'unverified', 'provisional')):
        score += 3
    return score


def sa_find_dataset(gauge: str, var: str, interval: str = 'day') -> str:
    '''
    Finds the best dataset id (`Param.Label@Gauge`) for a gauge and var by asking the portal
    what the gauge has, rather than relying on a hand-maintained table. `SA_DATASETS` entries
    still act as explicit overrides.
    '''
    override = SA_DATASETS.get(gauge, {}).get(var)
    if override:
        return f'{override}@{gauge}'
    if var not in SA_VAR_PARAMS:
        raise ValueError(f"Unsupported SA variable '{var}'. Use one of {sorted(SA_VAR_PARAMS)}")
    params = sa_fetch_params()
    for wanted in SA_VAR_PARAMS[var]['params']:
        match = params[params['param_name'].str.lower() == wanted.lower()]
        if match.empty:
            match = params[params['param_desc'].str.lower().str.contains(wanted.lower(), na=False)]
        for pid in match['param_id']:
            ds = sa_fetch_datasets(str(pid))
            ds = ds[ds['LocationIdentifier'] == gauge]
            if not ds.empty:
                return sorted(ds['DatasetIdentifier'], key=lambda d: (_sa_rank(d, interval), d))[0]
    raise ValueError(f"SA gauge {gauge} has no '{var}' dataset on {SA_PORTAL}")


def _sa_parse_csv(text: str) -> pd.DataFrame:
    '''Parses an AQUARIUS CSV export, locating the header row instead of assuming its position.'''
    lines = text.splitlines()
    header = next((i for i, l in enumerate(lines) if l.startswith('Timestamp')), None)
    if header is None:
        raise ValueError(f'Unexpected SA portal response (no Timestamp header): {text[:200]!r}')
    df = pd.read_csv(io.StringIO('\n'.join(lines[header:])))
    df = df.iloc[:, :3]
    df.columns = ['Timestamp', 'Value', 'Grade Code'][:df.shape[1]]
    if 'Grade Code' not in df:
        df['Grade Code'] = None
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    return df.dropna(subset=['Timestamp', 'Value'])


def gauge_pull_sa(gauge_numbers: List[str], start_time_user: datetime.date,
                  end_time_user: datetime.date, var: str = 'F', interval: str = 'day',
                  data_type: str = 'mean') -> List[List[Any]]:
    '''
    Pulls any SA gauge from water.data.sa.gov.au. The dataset is discovered from the portal
    for each gauge, and the result is aggregated to `interval` with `data_type`.
    Returns rows of [state, gauge, 'WATER', date, value, quality].
    '''
    if var not in SA_VAR_PARAMS:
        raise ValueError(f"Unsupported SA variable '{var}'. Use one of {sorted(SA_VAR_PARAMS)}")
    if interval not in SA_RESAMPLE:
        raise ValueError(f"Unsupported interval '{interval}'")
    if data_type not in ('mean', 'min', 'max'):
        raise ValueError(f"Unsupported data_type '{data_type}'")

    rows: List[List[Any]] = []
    skipped: List[str] = []
    for gauge in gauge_numbers:
        try:
            dataset = sa_find_dataset(gauge, var, interval)
        except ValueError as err:
            if 'has no' not in str(err):
                raise
            log.warning(f'Skipping {gauge}: {err}')
            skipped.append(gauge)
            continue
        query = {
            'DataSet': dataset, 'Calendar': 'CALENDARYEAR', 'DateRange': 'Custom',
            'StartTime': f'{start_time_user:%Y-%m-%d}', 'EndTime': f'{end_time_user:%Y-%m-%d}',
            'Conversion': 'Instantaneous', 'IntervalPoints': 'PointsAsRecorded',
            'ApprovalLevels': 'False', 'Qualifiers': 'False', 'Step': '1',
            'ExportFormat': 'csv', 'Compressed': 'false', 'RoundData': 'True',
            'GradeCodes': 'True', 'InterpolationTypes': 'False', 'Timezone': '9.5',
        }
        unit_id = SA_VAR_PARAMS[var]['unit_id']
        if unit_id:
            query['UnitID'] = unit_id
        r = _sa_get_session().get(f'{SA_PORTAL}/Export/DataSet', params=query, timeout=SA_TIMEOUT)
        r.raise_for_status()
        df = _sa_parse_csv(r.text)
        if df.empty:
            log.warning(f'No SA data returned for {gauge} ({dataset})')
            continue
        grade = df['Grade Code'].iloc[-1]
        agg = df.set_index('Timestamp')['Value'].resample(SA_RESAMPLE[interval]).agg(data_type).dropna()
        for ts, val in agg.items():
            rows.append(['SA', gauge, 'WATER', ts.date(), float(val), grade])
    if skipped and len(skipped) == len(gauge_numbers):
        raise ValueError(f"None of the SA gauges {skipped} have a '{var}' dataset on {SA_PORTAL}")
    return rows


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

    # Gauges missing from the CSV (e.g. the barrages) but with an SA-style id go to the SA portal
    extra_sa = [g for g in gauges_by_state['rest'] if SA_GAUGE_RE.match(str(g))]
    if extra_sa:
        data += gauge_pull_sa(extra_sa, start_time_user, end_time_user, var, interval, data_type)

    cols = ['DATASOURCEID', 'SITEID', 'SUBJECTID', 'DATETIME', 'VALUE', 'QUALITYCODE']
    return pd.DataFrame(data=data, columns=cols)
