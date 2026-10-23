# CSV output

Write LOOP packets or archive records from WeeWX to a comma-separated-value
file. Unlike a Cheetah report, it can write every LOOP packet, not just
archive data. It writes a local file only and does not convert units: values
are written in the units of the packet or record.

Independent continuation of
[matthewwall/weewx-csv](https://github.com/matthewwall/weewx-csv), starting
from upstream commit `34a9a52e5fedb47af216c281084f03a833fd75e6`.

## Requirements

- Write permission for the WeeWX user in the destination directory. In
  overwrite mode the service creates a temporary file in that directory.
- No Python package beyond WeeWX.

## Installation

Install `csv` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/csv.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

The installer registers `user.csv.CSV` in `process_services` and adds:

```ini
[CSV]
    filename = /var/tmp/data.csv
```

With the other defaults, this appends every LOOP packet to a monthly file
such as `/var/tmp/data-2026-10.csv`.

## Configuration

This example replaces a single snapshot of two observations on every archive
record:

```ini
[CSV]
    filename = /var/tmp/weather.csv
    binding = archive
    mode = overwrite
    append_datestamp = False
    fields = outTemp, outHumidity
```

| Option | Default | Meaning |
| --- | --- | --- |
| `filename` | `/var/tmp/data.csv` | Path of the output file. |
| `binding` | `loop` | `loop` writes on every LOOP packet. Any other value, for example `archive`, writes on archive records. |
| `mode` | `append` | `append` adds a line per event. Any other value, for example `overwrite`, replaces the file on every event. |
| `append_datestamp` | `True` | Insert a UTC datestamp into the file name, so `/var/tmp/data.csv` becomes `/var/tmp/data-2026-10.csv`. A name without an extension gets it at the end. |
| `datestamp_format` | `%Y-%m` | `strftime` format of that datestamp. `%Y-%m-%d` starts a new file each day. |
| `header` | `True` | Write a header line with the column names, prefixed by `# `. |
| `timestamp_format` | none | `strftime` format for `dateTime`, in UTC. Without it, `dateTime` is the Unix epoch. |
| `fields` | all observations | Ordered list of observations to write. `dateTime` is always the first column. |
| `decimal_places` | none | Fractional digits for floating-point values, from 0 to 15. Integers and `dateTime` are unchanged. |

In overwrite mode the file holds one line, after the header if `header` is
on. The new file
replaces the old one by an atomic rename, so readers never see a partial file
and a failed write leaves the previous file intact. The file keeps its
permission bits; a new file gets mode `0644`.

In append mode the header is written only when the file does not exist yet.

Without `fields`, the columns are `dateTime` followed by the observations of
the packet sorted by name. LOOP packets can contain different
observations on each event, so the columns can shift between lines. Set
`fields` for fixed columns, or use `binding = archive` for consolidated
archive records. A configured field missing from the packet is written empty,
and so is an observation without a value.
Values containing commas, quotes or line breaks are quoted.

## Development

Run `python -m pytest -q tests` in an environment with WeeWX and pytest
installed.

## License

Copyright 2015-2021 Matthew Wall.
Distributed under the terms of the [GNU GPLv3](license).
