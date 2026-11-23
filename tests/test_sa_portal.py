import datetime
import json
import pytest
from mdba_gauge_getter import gauge_getter as gg

PARAMS_HTML = ('<select><option value="1" data-code="Discharge">Discharge</option>'
               '<option value="2" data-code="Water Level">Water Level</option>'
               '<option value="3" data-code="Lake Level">Lake Level</option></select>')

DATASETS = {
    '1': [{'LocationIdentifier': 'A1', 'DatasetIdentifier': 'Discharge.Telemetry@A1'},
          {'LocationIdentifier': 'A1', 'DatasetIdentifier': 'Discharge.Master--Daily Read--ML/day@A1'}],
    '2': [{'LocationIdentifier': 'A2', 'DatasetIdentifier': 'Water Level.Best Available--Continuous@A2'}],
    '3': [],
}

CSV = ('Export,x\nDataset,y\nTimeZone,9.5\n'
       'Timestamp (UTC+09:30),Value,Grade Code\n'
       '2024-01-01 00:00:00,1.0,A\n2024-01-01 12:00:00,3.0,A\n2024-01-02 00:00:00,5.0,A\n')


class Resp:
    def __init__(self, text='', body=None):
        self.text, self._body = text, body
    def raise_for_status(self): pass
    def json(self): return self._body


class FakeSession:
    def __init__(self):
        self.exports = []
    def post(self, url, data=None, timeout=None):
        if url.endswith('/Data/List/'):
            return Resp(PARAMS_HTML)
        pid = str(data['parameters[0]'])
        return Resp(body={'Total': len(DATASETS[pid]), 'Data': DATASETS[pid]})
    def get(self, url, params=None, timeout=None):
        self.exports.append(params)
        return Resp(CSV)


@pytest.fixture(autouse=True)
def fake_portal(monkeypatch):
    s = FakeSession()
    monkeypatch.setattr(gg, '_sa_session', s)
    monkeypatch.setattr(gg, '_sa_params', None)
    monkeypatch.setattr(gg, '_sa_datasets', {})
    return s


def test_prefers_daily_master_dataset():
    assert gg.sa_find_dataset('A1', 'F', 'day') == 'Discharge.Master--Daily Read--ML/day@A1'


def test_discovers_gauge_not_in_override_table():
    assert gg.sa_find_dataset('A2', 'L') == 'Water Level.Best Available--Continuous@A2'


def test_missing_dataset_raises():
    with pytest.raises(ValueError):
        gg.sa_find_dataset('A9', 'F')


def test_pull_aggregates_daily_mean(fake_portal):
    rows = gg.gauge_pull_sa(['A1'], datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 'F')
    assert [(r[3], r[4]) for r in rows] == [(datetime.date(2024, 1, 1), 2.0),
                                            (datetime.date(2024, 1, 2), 5.0)]
    assert fake_portal.exports[0]['UnitID'] == 241


def test_pull_max_and_level_has_no_unit_conversion(fake_portal):
    rows = gg.gauge_pull_sa(['A2'], datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 'L', 'day', 'max')
    assert rows[0][4] == 3.0
    assert 'UnitID' not in fake_portal.exports[0]


def test_bad_args():
    with pytest.raises(ValueError):
        gg.gauge_pull_sa(['A1'], datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 'ZZ')


def test_skips_gauges_without_dataset(fake_portal):
    rows = gg.gauge_pull_sa(['A9', 'A1'], datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 'F')
    assert {r[1] for r in rows} == {'A1'}


def test_all_gauges_missing_raises():
    with pytest.raises(ValueError):
        gg.gauge_pull_sa(['A9'], datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 'F')
