obstats
=======

Provide basic downloads statistics to OBS via a REST API.  To do that
this script downloads the apache log files, convert it into a format
fast to scan (using a BerkeleyDB container), analyze the result and
store the data in a Redis store.

The information is always available via a REST API implemented with
the microframework Flask, that query the data in the Redis store.


Installation
============

Install dependencies:

  pip install -r requirements.txt

Configure the URL where are stored the OBS logs files:

  vi obstat.cfg

Create the BerkeleyDB containers:

  ./log2db.sh 2014-01-01

Store the information in Redis:

  ./analyze.sh 2014-01-01

This last scripts takes care of not duplicating the information,
analyzing twice the same file, so for example, a new call to the
analyze script will skip the files already in the database.

Setup the REST API:

  python api.py


API
===

We publish two different metrics, the number of simple hits and the
number of visits (different IPs) in an object.  Each metric can be
queried for five different objects: packages, architecture,
repository, project and time.

The URL pattern for hist is:

   /hits/<unit>/<date>/[[[[<project>]/<repository>]/<arch>]/<package>]

and for visits is:

   /visits/<unit>/<date>/[[[[<project>]/<repository>]/<arch>]/<package>]

The <unit> slot is can be 'day', 'week' or 'month'.  Depending of this
slot, <date> can have a different format:

| unit  | date format | example                                                  |
|-------|-------------|----------------------------------------------------------|
| day   | YYYYMMDD    | 20140215 -- Single day 2014/02/15                        |
| week  | YYYYWW      | 201401 -- First week of 2014 (2013/12/30 to 2014/02/5)   |
| month | YYYYMM      | 201401 -- First month of 2014 (2014/01/01 to 2014/01/31) |

Example of valid requests:

  /hits/day/20140215/home:tiwai:pa-fix-13.1/standard/x86_64/pulseaudio-module-lirc-4.0.git.270.g9490a-6.1.x86_64.rpm
  /hits/day/20140215/home:tiwai:pa-fix-13.1/standard/x86_64
  /visits/week/201403/home:oprudkyi
  /visits/month/201402/openSUSE:13.1/standard/x86_64
