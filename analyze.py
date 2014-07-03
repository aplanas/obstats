#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import datetime
import md5
import os.path
import urllib

import bsddb3
import redis

import dblist


def day_key(date_):
    """Name of the daily key. Return YYYYMMDD string."""
    return '%04d%02d%02d-day' % (date_.year, date_.month, date_.day)


def week_key(date_):
    """Name the weekly key. Return YYYYWW string."""

    # Group the date at the end of the week, so some dates can appears
    # in a different year. For example, 31/12/2012 will appear as a
    # 201301, the first week of 2013.

    delta = datetime.timedelta(days=6-date_.weekday())
    week_date = date_ + delta
    return '%04d%02d-week' % (week_date.year, week_date.isocalendar()[1])


def month_key(date_):
    """Name of the monthly key. Return YYYYMM string."""
    return '%04d%02d-month' % (date_.year, date_.month)


def is_package(path):
    return any(path.endswith(extension) for extension in ('.rpm', '.deb'))


def path_info(path):
    """Take a path and detect the project, repository, arch and package
    from it.

    """
    project, repository, arch, package = '', '', '', ''

    path = os.path.normpath(urllib.unquote(path))
    path_ = (p for p in path.split('/') if p)

    assert path_.next() == 'repositories', 'Path do not starts with /repositories/'

    for p in path_:
        project += p
        if not p.endswith(':'):
            break

    repository = path_.next()

    arch = path_.next()
    if arch == 'rpm':
        arch = path_.next()

    package = path_.next()

    assert package.endswith('.rpm') or package.endswith('.deb'), ('Error parsing the path', path)

    return (project, repository, arch, package)


def analyze(dbenv, dbname, day):
    """Read every line and analyze the data."""

    rdb = redis.Redis()

    # Check if the file is in the Redis database
    if rdb.sismember('processed_logs', dbname):
        print 'File %s was stored in the database.'
        return

    rdb.sadd('processed_logs', dbname)

    # Open lines databases
    lines = dblist.open(None, os.path.join(dbenv, dbname), flags=bsddb3.db.DB_RDONLY)
    lines_path = dblist.open(None, os.path.join(dbenv, dbname+'_paths'), flags=bsddb3.db.DB_RDONLY)
    # lines_uuid = dblist.open(None, os.path.join(dbenv, dbname+'_uuids'), flags=bsddb3.db.DB_RDONLY)

    # Read the bots file
    bots = set(l.strip() for l in open('bots.txt'))

    # Recover the path information
    paths = {md5.new(path).digest(): path for path in lines_path}

    for line in lines:
        # A line is a tuple with this schema:
        #   ip, hour, minute, second, md5_path, status, size,
        #   referrer, user_agent, md5_uuid, medium, version, arch
        (ip, _, _, _, path_md5, status, _, _, user_agent, _, _, _, _) = line

        if user_agent in bots or status == 404:
            continue

        path = paths[path_md5]

        if not path.startswith('/repositories/') or not is_package(path):
            # print 'Ignoring', path, status
            continue

        project, repository, arch, package = path_info(path)

        # Hits
        for time_key in (day_key(day), week_key(day), month_key(day)):
            rdb.incr(('hits', time_key, project, repository, arch, package))
            rdb.incr(('hits', time_key, project, repository, arch))
            rdb.incr(('hits', time_key, project, repository))
            rdb.incr(('hits', time_key, project))
            rdb.incr(('hits', time_key))

        # Visits
        for time_key in (day_key(day), week_key(day), month_key(day)):
            rdb.sadd(('visit', time_key, project, repository, arch, package), ip)
            rdb.sadd(('visit', time_key, project, repository, arch), ip)
            rdb.sadd(('visit', time_key, project, repository), ip)
            rdb.sadd(('visit', time_key, project), ip)
            rdb.sadd(('visit', time_key), ip)

    lines.close()
    lines_path.close()
    # lines_uuid.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze a single bdb log file into bdb')
    parser.add_argument('--dbenv', default='dbenv', help='Database environment')
    parser.add_argument('--db', help='Name of the database to read the information')

    args = parser.parse_args()

    year, month, day = (int(x) for x in (args.db[:4], args.db[4:6], args.db[6:]))
    day = datetime.datetime(year=year, month=month, day=day)

    # dbenv = bsddb3.db.DBEnv()
    # dbenv.open(args.dbenv,
    #            bsddb3.db.DB_INIT_MPOOL
    #            | bsddb3.db.DB_CREATE)

    analyze(args.dbenv, args.db, day)

    # dbenv.close()
