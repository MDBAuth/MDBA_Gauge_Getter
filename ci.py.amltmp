#!/usr/bin/python
import os
import json
from typing import Dict
from subprocess import Popen, PIPE

APPLICATION_NAME = 'mdba_gauge_getter'

BADGE_URL = 'https://img.shields.io/badge/'

PYTEST_TIME_COLOR_MAP = {
    4: 'red',
    3: 'orange',
    2: 'yellowgreen',
    1: 'brightgreen',
}

PYTEST_PERCENT_COLOR_MAP = {
    100: 'brightgreen',
    90: 'yellowgreen',
    80: 'orange',
    70: 'red',
}

COVERAGE_PERCENT_COLOR_MAP = {
    100: 'brightgreen',
    95: 'yellowgreen',
    90: 'orange',
    80: 'red',
}

MYPY_COLOR_MAP = {
    0: 'brightgreen',
    10: 'yellowgreen',
    15: 'orange',
    20: 'red',
}

PYLINT_COLOR_MAP = {
    9: 'brightgreen',
    7.5: 'green',
    6: 'orange',
    5: 'red',
}


def parse_pytest_output(pytest_out: str) -> Dict[str, float]:
    print(pytest_out)
    results_raw = pytest_out.strip().split('\n')[-1].split('===== ')[1].split(' ======')[0]
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
    }
    for keyword in 'passed', 'skipped', 'failed':
        keyword = ' ' + keyword
        if keyword in results_raw:
            val = int(results_raw.split(keyword, 1)[0].strip().rsplit(' ', 1)[-1])
            results[keyword.strip()] = val
    time_raw = results_raw.split(' in ', 1)[1].strip()
    time_value, time_measurement = time_raw.split(" ", 1)
    time_value = float(time_value)
    if time_measurement == "seconds":
        pass
    elif time_measurement == "minutes":
        time_value = time_value * 60
    else:
        time_value = time_value * 3600
    results['time'] = time_value
    return results


def get_color_from_map(value: float, color_map: Dict[float, str], bigger_is_better: bool):
    if bigger_is_better:
        rating_val = min(color_map.keys())
    else:
        rating_val = max(color_map.keys())
    for k, v in color_map.items():
        if bigger_is_better and value >= k:
            rating_val = max(rating_val, k)
        elif not bigger_is_better and value <= k:
            rating_val = min(rating_val, k)
    return color_map[rating_val]


def get_pytest_data():
    results = parse_pytest_output(pytest.communicate()[0].decode())
    exec_time = results['time']
    percent = 0
    if results['passed'] > 0:
        percent = (results['passed'] / (results['failed'] + results['passed'])) * 100

    percent_color = get_color_from_map(percent, PYTEST_PERCENT_COLOR_MAP, True)
    exec_time_color = get_color_from_map(exec_time, PYTEST_TIME_COLOR_MAP, False)
    return [
        {'name': 'Unit Tests', 'value': f'{percent}%', 'color': percent_color},
        {'name': 'Execution Time', 'value': f'{exec_time}s', 'color': exec_time_color},
    ]


def get_coverage_data():
    # Coverage has to run after pytest has finished
    coverage = Popen(['python3', '-m', 'coverage', 'json',
                      '-o', '.coverage.json'], stdout=PIPE)
    coverage.wait()
    with open(".coverage.json", "r") as fhandle:
        out = json.loads(fhandle.read())
    percent = out["totals"]["percent_covered"]
    color = get_color_from_map(percent, COVERAGE_PERCENT_COLOR_MAP, True)
    return [
        {'name': 'Code Coverage', 'value': percent, 'color': color}
    ]

def get_mypy_data():
    errors = int(mypy.communicate()[0].decode().split(" errors ", 1)[0].rsplit(" ", 1)[-1])
    color = get_color_from_map(errors, MYPY_COLOR_MAP, False)
    return [
        {'name': 'MyPy Errors', 'value': errors, 'color': color}
    ]


def get_pylint_data():
    rating = float(pylint.communicate()[0].decode().split(" rated at ")[1].split("/")[0])
    color = get_color_from_map(rating, PYLINT_COLOR_MAP, True)
    return [
        {'name': 'Pylint Rating', 'value': rating, 'color': color}
    ]


def generate_badge_data(badges):
    extra_html = '\n\n<span class="badges">\n\n'
    for b in badges:
        badge_line = f'![{b["name"]}]({BADGE_URL}{b["name"]}-{b["value"]}-{b["color"]})\n'
        extra_html += badge_line.replace('%', '%25').replace(" ", "%20")
    extra_html += '\n</span>\n\n'
    return extra_html


def write_badge_data(badge_html):
    with open('README.md') as fhandle:
        readme = fhandle.read()
    readme = readme.split('<span class="badges">', 1)
    readme[0] = readme[0].rstrip()
    readme[1] = readme[1].split('</span>', 1)[1].lstrip()
    try:
        with open('README.md.temp', 'w') as fhandle:
            fhandle.write(readme[0])
            fhandle.write(badge_html)
            fhandle.write(readme[1])
        os.rename('README.md', 'README.md.old')
        os.rename('README.md.temp', 'README.md')
        os.remove('README.md.old')
    finally:
        if os.path.exists('README.md.old'):
            os.rename('README.md.olod', 'README.md')
        if os.path.exists('README.md.temp'):
            os.remove('README.md.temp')


if __name__ == "__main__":
    pytest = Popen(['python3', '-m', 'coverage', 'run',
                    '--source', APPLICATION_NAME, '-m', 'pytest'], stdout=PIPE)
    pylint = Popen(['pylint', '--output-format', 'text', APPLICATION_NAME, 'tests'], stdout=PIPE)
    mypy = Popen(['mypy', APPLICATION_NAME], stdout=PIPE)

    badges = (
        get_pytest_data() +
        get_coverage_data() +
        get_mypy_data() +
        get_pylint_data()
    )

    html = generate_badge_data(badges)
    write_badge_data(html)
    print("CI Script Complete")
