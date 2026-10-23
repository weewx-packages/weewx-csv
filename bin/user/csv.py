# Copyright 2015-2021 Matthew Wall
# Modified 2026-10-22: atomic snapshots, fixed fields and decimal formatting.
# Modified 2026-10-23: datestamp before the file extension, empty field for None.
# Distributed under the terms of the GNU Public License (GPLv3)

import csv as csvlib
import os
import stat
import tempfile
import os.path
import time

import weewx
import weewx.engine
import weeutil.weeutil

VERSION = "0.12.0"

try:
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)
    def loginf(msg):
        log.info(msg)
    def logerr(msg):
        log.error(msg)

except ImportError:
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'csv: %s' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

class CSV(weewx.engine.StdService):
    def __init__(self, engine, config_dict):
        super(CSV, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)
        d = config_dict.get('CSV', {})
        # location of the output file
        self.filename = d.get('filename', '/var/tmp/data.csv')
        # optionally emit a header line as the first line of the file
        self.emit_header = weeutil.weeutil.to_bool(d.get('header', True))
        # mode can be append or overwrite
        self.mode = d.get('mode', 'append')
        # optionally append a datestamp to the filename
        self.append_datestamp = weeutil.weeutil.to_bool(d.get('append_datestamp', True))
        # format for the filename datestamp
        self.datestamp_format = d.get('datestamp_format', '%Y-%m')
        # format for the per-record timestamp
        self.timestamp_format = d.get('timestamp_format')
        self.decimal_places = d.get('decimal_places')
        if self.decimal_places is not None:
            self.decimal_places = int(self.decimal_places)
            if not 0 <= self.decimal_places <= 15:
                raise ValueError('decimal_places must be between 0 and 15')
        self.fields = weeutil.weeutil.option_as_list(d.get('fields'))
        # bind to either loop or archive events
        self.binding = d.get('binding', 'loop')
        if self.binding == 'loop':
            self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop)
        else:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.handle_new_archive)

    def handle_new_loop(self, event):
        self.write_data(event.packet)

    def handle_new_archive(self, event):
        self.write_data(event.record)

    def write_data(self, data):
        flag = "a" if self.mode == 'append' else "w"
        filename = self.filename
        if self.append_datestamp:
            basename, ext = os.path.splitext(filename)
            tstr = time.strftime(self.datestamp_format,
                                 time.gmtime(data['dateTime']))
            filename = "%s-%s%s" % (basename, tstr, ext)
        header = self.emit_header and (not os.path.exists(filename) or flag == "w")
        if flag == 'a':
            with open(filename, flag, newline='') as stream:
                self.write_record(stream, data, header)
            return
        directory = os.path.dirname(os.path.abspath(filename))
        fd, temporary = tempfile.mkstemp(prefix='.weewx-csv-', dir=directory)
        try:
            try:
                mode = stat.S_IMODE(os.stat(filename).st_mode)
            except FileNotFoundError:
                mode = 0o644
            with os.fdopen(fd, 'w', newline='') as stream:
                os.fchmod(stream.fileno(), mode)
                self.write_record(stream, data, header)
            # Readers must never observe a truncated header or half a packet.
            os.replace(temporary, filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def write_record(self, stream, record, header):
        """Write one CSV record, with its matching header when requested.

        Args:
            stream (typing.IO[str]): Open text output stream.
            record (dict): WeeWX loop packet or archive record.
            header (bool): Whether to write the column names first.
        """
        writer = csvlib.writer(stream, lineterminator='\n')
        if header:
            keys = self.sort_keys(record)
            writer.writerow(['# ' + keys[0]] + keys[1:])
        writer.writerow(self.sort_data(record))

    def sort_keys(self, record):
        fields = ['dateTime']
        for k in self.fields if self.fields is not None else sorted(record):
            if k != 'dateTime':
                fields.append(k)
        return fields

    def sort_data(self, record):
        tstr = str(record['dateTime'])
        if self.timestamp_format is not None:
            tstr = time.strftime(self.timestamp_format,
                                 time.gmtime(record['dateTime']))
        fields = [tstr]
        for k in self.sort_keys(record)[1:]:
            value = record.get(k)
            if value is None:
                value = ''
            if self.decimal_places is not None and isinstance(value, float):
                fields.append(format(value, '.%df' % self.decimal_places))
            else:
                fields.append(str(value))
        return fields
