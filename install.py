# installer for csv service
# Copyright 2015-2021 Matthew Wall
# Modified 2026-10-22: release the independent continuation.
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller

def loader():
    return CSVInstaller()

class CSVInstaller(ExtensionInstaller):
    def __init__(self):
        super(CSVInstaller, self).__init__(
            version="0.12.1",
            name='csv',
            description='Emit loop or archive data in CSV format.',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            process_services='user.csv.CSV',
            config={
                'CSV': {
                    'filename': '/var/tmp/data.csv'}},
            files=[('bin/user', ['bin/user/csv.py'])]
            )
