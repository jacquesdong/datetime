#!/usr/bin/env -S python -P
# encoding=utf-8
# 本文件与标准库 datetime 同名，必须用 -P（已写在 shebang 里）或 `python3 -P datetime.py` 运行：
# 否则脚本所在目录会进入 sys.path[0]，遮蔽标准库 datetime，触发循环导入 ImportError。


import re
import sys

import argparse

from datetime import datetime, timezone, timedelta


# datetime 能表示的年份是 1..9999，对应 epoch 秒的上界
MAX_EPOCH_SECONDS = 253402300799          # 9999-12-31 23:59:59 UTC
# 必须从小到大判断：第一个放得下的单位就是答案
UNITS = (('s', 1), ('ms', 10 ** 3), ('us', 10 ** 6), ('ns', 10 ** 9))


def guess_unit(value):
    """按数量级推断时间戳单位，返回 (unit, scale)。

    s   <= 2.5e11（12 位及以内）
    ms  <= 2.5e14（15 位及以内）
    us  <= 2.5e17（18 位及以内）
    ns  其余，直到 2.5e20
    超过上界说明不是这四种单位，报错。
    """
    v = abs(value)
    for unit, scale in UNITS:
        if v <= MAX_EPOCH_SECONDS * scale:
            return unit, scale
    raise ValueError('时间戳超出 datetime 可表示范围: %d' % value)


def from_timestamp(args):
    value = int(args.argn[0])
    unit, scale = guess_unit(value)

    # 整数运算保证大数不丢精度：秒部分给 fromtimestamp，
    # 不足 1 秒的部分折算成微秒（datetime 的最小分辨率）后补上
    whole, frac = divmod(abs(value), scale)
    micros = frac * 1000000 // scale
    sign = -1 if value < 0 else 1

    if args.utc:
        f = datetime.utcfromtimestamp
    else:
        f = datetime.fromtimestamp
    t = f(sign * whole)
    if micros:
        t += timedelta(microseconds=sign * micros)
    return t


def from_timestring(args):
    s = ' '.join(args.argn)

    return datetime.fromisoformat(s)


def main():
    parser = argparse.ArgumentParser()

    # argparse 判断“负数字”用的是实例上的私有正则（3.12 在 __init__ 里就地编译，
    # 所以改模块级变量无效，必须改实例），且只匹配 -\d+、不认识 _，
    # 于是 -1_000 会被当成未知选项。放宽它，让带 _ 的负数也能当位置参数。
    parser._negative_number_matcher = re.compile(r'^-\d+(?:_\d+)*$|^-\d*\.\d+$')

    parser.add_argument('-u', '--utc', action='store_true')

    parser.add_argument('-s', '--stamp', action='store_true',
                        help='无参数时输出 epoch 秒（而不是日期时间）')

    parser.add_argument('argn', nargs='*')

    args = parser.parse_args()

    if args.argn:
        if not all(args.argn):
            parser.error('参数不能为空')

        if len(args.argn) == 1:
            # 数字里允许用 _ 分组（如 1_792_189_920），规则同 Python 整数字面量：
            # _ 只能出现在两个数字之间；int() 本身也接受这种写法
            if re.search(r'^-?\d+(?:_\d+)*$', args.argn[0], re.ASCII):
                t = from_timestamp(args)
                print(t)
            else:
                t = from_timestring(args)
                print(t.timestamp())
        else:
            t = from_timestring(args)
            print(t.timestamp())
    else:
        if args.utc:
            t = datetime.utcnow()
        else:
            t = datetime.now()

        if args.stamp:
            print(t.timestamp())
        else:
            print(t)


if __name__ == '__main__':
  sys.exit(main())
