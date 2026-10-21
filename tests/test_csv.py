import csv
import importlib.util
import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

SPEC = importlib.util.spec_from_file_location('csv_service', Path(__file__).parents[1] / 'bin/user/csv.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class Engine:
    def bind(self, *args):
        pass


def service(path, **options):
    return module.CSV(Engine(), {'CSV': dict(filename=str(path), append_datestamp=False,
                                            mode='overwrite', **options)})


def test_readers_see_complete_records(tmp_path):
    path = tmp_path / 'loop.csv'
    exporter = service(path)
    old = {'dateTime': 1, 'outTemp': 12.0, 'outHumidity': 70}
    exporter.write_data(old)
    previous = path.read_text()
    observed = []
    original_open = io.open
    original_builtin_open = open

    class Writer:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            self.stream.__enter__()
            return self
        def __exit__(self, *args):
            return self.stream.__exit__(*args)
        def write(self, data):
            result = self.stream.write(data)
            self.stream.flush()
            observed.append(path.read_text())
            return result
        def __getattr__(self, name):
            return getattr(self.stream, name)

    def observe_open(file, mode='r', *args, **kwargs):
        stream = original_builtin_open(file, mode, *args, **kwargs)
        return Writer(stream) if 'w' in mode else stream

    def observe_fdopen(fd, *args, **kwargs):
        return Writer(original_open(fd, *args, **kwargs))

    with patch('builtins.open', observe_open), patch.object(module.os, 'fdopen', observe_fdopen):
        exporter.write_data({'dateTime': 2, 'outTemp': 0.0, 'outHumidity': 0})
    assert observed
    assert all(snapshot == previous for snapshot in observed)
    assert list(csv.reader(path.open())) == [['# dateTime', 'outHumidity', 'outTemp'], ['2', '0', '0.0']]


def test_precision_and_fixed_fields(tmp_path):
    path = tmp_path / 'loop.csv'
    exporter = service(path, decimal_places=2, fields=['outTemp', 'outHumidity', 'batteryStatus'])
    exporter.write_data({'dateTime': 1720000000, 'outTemp': 12.3456, 'outHumidity': 0})
    assert list(csv.reader(path.open())) == [
        ['# dateTime', 'outTemp', 'outHumidity', 'batteryStatus'],
        ['1720000000', '12.35', '0', '']]
    exporter.write_data({'dateTime': 1720000001, 'outTemp': -0.25})
    assert list(csv.reader(path.open()))[1] == ['1720000001', '-0.25', '', '']


def test_failed_write_preserves_snapshot(tmp_path):
    path = tmp_path / 'loop.csv'
    exporter = service(path)
    exporter.write_data({'dateTime': 1, 'outTemp': 1.2})
    original = path.read_bytes()
    with patch.object(module.os, 'replace', side_effect=OSError('fixture rename failure')):
        with pytest.raises(OSError):
            exporter.write_data({'dateTime': 2, 'outTemp': 2.3})
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_append_default_and_csv_escaping(tmp_path):
    path = tmp_path / 'records.csv'
    exporter = service(path)
    exporter.mode = 'append'
    exporter.write_data({'dateTime': 1, 'text': 'a,b"c'})
    exporter.write_data({'dateTime': 2, 'text': 'next'})
    assert list(csv.reader(path.open())) == [['# dateTime', 'text'], ['1', 'a,b"c'], ['2', 'next']]
