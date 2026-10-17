#!/usr/bin/env -S python -P
# encoding=utf-8
# 本文件与标准库 datetime 同名，必须用 -P（已写在 shebang 里）或 `python3 -P datetime.py` 运行：
# 否则脚本所在目录会进入 sys.path[0]，遮蔽标准库 datetime，触发循环导入 ImportError。

from __future__ import  unicode_literals, print_function

import os
import re
import sys

import argparse

from datetime import datetime, timezone, timedelta


def diff_filetime():
    unixtime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    filetime = datetime(1601, 1, 1, tzinfo=timezone.utc)
    difftime = unixtime - filetime
    return difftime


def from_filetime(args):
    difftime = diff_filetime()

    lo = int(args.arng[0])
    hi = int(args.arng[1])
    ft = lo + hi << 32

    s = ft * 1e-7 - difftime.total_seconds()
    t = datetime.utcfromtimestamp(s)
    return t


def from_timestamp(args):
    args.stamp = False
    if args.utc:
        f = datetime.utcfromtimestamp
    else:
        f = datetime.fromtimestamp
    return f(int(args.argn[0]))


def from_timestring(args):
    args.stamp = True
    s = args.argn[0]

    if not s:
        return

    v = sys.version_info
    if v.major >= 3 and v.minor >= 7:
        return datetime.fromisoformat(s)

    if len(s) > 8:
        s = s.split('.')
        t = datetime.strptime(s[0], "%Y-%m-%d %H:%M:%S")
        if len(s) > 1:
            t += timedelta(microseconds=float('.'+s[1])*1e6)
    else:
        t = datetime.strptime(s, "%Y-%m-%d")

    if args.utc:
        return t.replace(tzinfo=timezone.utc)
    else:
        return t

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--utc', action='store_true')

    parser.add_argument('-p', '--print', action='store_true')
    parser.add_argument('-s', '--stamp', action='store_true')

    parser.add_argument('-d', '--diff-filetime', action='store_true')

    parser.add_argument('argn', nargs='*')

    args = parser.parse_args()

    if args.diff_filetime:
        diff = diff_filetime()
        print(diff)
        print(diff.total_seconds(), 'seconds')
        return

    if args.argn:
        argc = len(args.argn)
        if argc == 1:
            if re.search(r'^\d+$', args.argn[0], re.ASCII):
                t = from_timestamp(args)
            else:
                t = from_timestring(args)
                if not t:
                    return 1
        else:
            t = from_filetime(args)
    else:
        if args.utc:
            t = datetime.utcnow()
        else:
            t = datetime.now()

    if not args.stamp:
        args.print = True

    if args.print:
        print(t)

    if args.stamp:
        print(t.timestamp())

    return 0

if __name__ == '__main__':
  sys.exit(main())

