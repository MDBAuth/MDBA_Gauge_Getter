#!/usr/bin/python3
import os
import time
import inotify.adapters

execute_commands = [
    'PYTHONPATH="./" pytest-3 --cov=mdba_gauge_getter --cov-report term-missing',
    # 'pylint --output-format=text gauge_getter/ tests',
    'mypy mdba_gauge_getter',
]

def _main():
    no_execute_until = -1
    i = inotify.adapters.InotifyTree('./')

    for event in i.event_gen(yield_nones=False):
        if no_execute_until > time.time():
            continue
        (_, type_names, path, filename) = event
        if not filename:  # Directory ops
            continue
        for i in ['IN_CLOSE_NOWRITE', 'IN_MODIFY', 'IN_OPEN',
                  'IN_ACCESS', 'IN_ISDIR']:
            if i in type_names:
                type_names.remove(i)
        if not type_names:
            continue
        if not filename.endswith(".py"):
            continue
        for execute_command in execute_commands:
            os.system(execute_command)
            no_execute_until = time.time() + 0.25


if __name__ == '__main__':
    for execute_command in execute_commands:
        os.system(execute_command)
    _main()
