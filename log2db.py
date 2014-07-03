#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import datetime
import md5
import re
import sys

# import bsddb3

import dblist


# Different parts of a log line
LINE_PARTS = [
    r'(?P<ip>\S+)',                                   # host %h
    r'\S+',                                           # indent %l (unused)
    r'\S+',                                           # user %u
    r'\[(?P<date>.+)\]',                              # time %t
    r'"(?:GET|HEAD) (?P<path>[^ ]+)[^"]*"',           # request "%r"
    r'(?P<status>\d+)',                               # status %>s
    r'(?P<size>\S+)',                                 # size %b (careful, can be '-')
    r'"(?P<referrer>[^"]*)"',                         # referer "%{Referer}i"
    r'"(?P<user_agent>(?:[^\\"]|\\.)*)"',             # user agent "%{User-agent}i"
    r'.*?(?P<uuid>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})?',  # UUID
    r'"(?P<medium>[^"]*)"',
]
LINE = re.compile(r'\s+'.join(LINE_PARTS)+r'\s*$')

# Some Zypper requests have a distribution signature
ZYPPER_VER = re.compile(r'.*openSUSE-(?P<version>[^-]+)-(?P<arch>.+)')

# The path have multiple alternatives
PATH_VER = [
    re.compile(r'/update/(?P<version>[^/]+)/rpm/(?P<arch>[^/]+)/.*'),
    re.compile(r'/distribution/(?P<version>[^/]+)/repo/[^/]+/suse/(?P<arch>[^/]+)/.*'),
    re.compile(r'/(?P<version>factory)(?:-snapshot)?/repo/[^/]+/suse/(?P<arch>[^/]+)/.*'),
]


def parse_ver_arch(hit):
    m = ZYPPER_VER.match(hit['user_agent'])
    if m:
        info = m.groupdict()
        return info['version'], info['arch']

    for pattern in PATH_VER:
        m = pattern.match(hit['path'])
        if m:
            info = m.groupdict()
            return info['version'], info['arch']

    return None, None


def parse_hit(line):
    """Parse a single log line using the pattern RE."""
    m = LINE.match(line)
    if m:
        hit = m.groupdict()
    else:
        return None

    # Fix the date using the timezone information
    if hit['date']:
        offset = int(hit['date'][-5:])
        delta = datetime.timedelta(hours=offset/100)
        hit['date'] = datetime.datetime.strptime(hit['date'][:-6], '%d/%b/%Y:%H:%M:%S')
        hit['date'] -= delta

    try:
        hit['status'] = int(hit['status'])
    except:
        return None

    # Sometines we do not have size
    try:
        hit['size'] = int(hit['size'])
    except:
        hit['size'] = 0

    # Sometines we do not have a referrer
    if hit['referrer'] == '-':
        hit['referrer'] = None

    # Sometines we do not have a meidum
    if hit['medium'] == '-':
        hit['medium'] = None

    hit['version'], hit['arch'] = parse_ver_arch(hit)

    # Always return the hit if is a real hit
    if hit['status'] == 200 or hit['status'] == 302:
        return hit

    # ... but None if is not from a user
    if not hit['uuid']:
        return None

    return hit


_KEY_COUNT = {}


def get_key(hit):
    """Use the time entry to create a key."""
    # Key format YYYYMMDDHHMMSSCCCCCC, where CCCCCC is some external counter
    key = '{:04}{:02}{:02}{:02}{:02}{:02}'.format(
        hit['date'].year,
        hit['date'].month,
        hit['date'].day,
        hit['date'].hour,
        hit['date'].minute,
        hit['date'].second,
    )
    counter = _KEY_COUNT.get(key, 0) + 1
    _KEY_COUNT[key] = counter
    return '{}{:06}'.format(key, counter)


def import_file(dbenv, dbname, infile):
    """Import a log file line by line into a bdb."""
    lines = dblist.open(None, dbname)
    lines_paths = dblist.open(None, dbname + '_paths')
    lines_uuids = dblist.open(None, dbname + '_uuids')

    paths_md5 = set()
    uuids_md5 = set()

    for line in infile:
        try:
            hit = parse_hit(line)
        except Exception as e:
            hit = None
            print >>sys.stderr, 'Error parsing:', line
            print >>sys.stderr, e

        if hit:
            path_md5 = md5.new(hit['path']).digest() if hit['path'] else None
            uuid_md5 = md5.new(hit['uuid']).digest() if hit['uuid'] else None
            item = (hit['ip'],
                    hit['date'].hour, hit['date'].minute, hit['date'].second,
                    path_md5,
                    hit['status'],
                    hit['size'],
                    hit['referrer'],
                    hit['user_agent'],
                    uuid_md5,
                    hit['medium'],
                    hit['version'],
                    hit['arch'])

            lines.append(item)

            if path_md5 and path_md5 not in paths_md5:
                paths_md5.add(path_md5)
                lines_paths.append(hit['path'])

            if uuid_md5 and uuid_md5 not in uuids_md5:
                uuids_md5.add(uuid_md5)
                lines_uuids.append(hit['uuid'])

    lines.close()
    lines_paths.close()
    lines_uuids.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Store log file into bdb')
    parser.add_argument('--dbenv', default='dbenv', help='Database environment')
    parser.add_argument('--db', help='Name of the database')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin, help='Logfile used to read the information')

    args = parser.parse_args()

    # dbenv = bsddb3.db.DBEnv()
    # dbenv.open(args.dbenv,
    #            bsddb3.db.DB_INIT_MPOOL
    #            | bsddb3.db.DB_CREATE)

    import_file(args.dbenv, args.db, args.infile)

    # dbenv.close()
