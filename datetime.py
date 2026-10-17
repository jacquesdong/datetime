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


# FILETIME 是 Windows 系统里表示时间的格式（注册表、GetFileTime、AD、EventLog、SQL Server、NTFS 时间戳都用它），特点是：
#
# 用 64 位无符号整数，拆成两个 32 位 DWORD：低 32 位 dwLowDateTime + 高 32 位 dwHighDateTime
# 起点是 1601-01-01 00:00:00 UTC（不是 Unix 的 1970）
# 单位是 100 纳秒（1e-7 秒），也叫 tick
def from_filetime(args):
    difftime = diff_filetime()

    # dwLowDateTime
    lo = int(args.argn[0])
    # dwHighDateTime
    hi = int(args.argn[1])

    # + 优先级高于 <<，括号必须写，否则算成 (lo + hi) << 32
    ft = lo + (hi << 32)

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

