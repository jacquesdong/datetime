#!/usr/bin/env -S python -P
# encoding=utf-8
# 本文件与标准库 datetime 同名，以 datetime.py 运行时必须用 -P（已写在 shebang 里）
# 或 `python3 -P datetime.py` 运行：
# 否则脚本所在目录会进入 sys.path[0]，遮蔽标准库 datetime，触发循环导入 ImportError。

import argparse
import re
import sys
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# datetime 能表示的年份是 1..9999，对应 epoch 秒的上界
MAX_EPOCH_SECONDS = 253402300799          # 9999-12-31 23:59:59 UTC
# 必须从小到大判断：第一个放得下的单位就是答案
UNITS: tuple[tuple[str, int], ...] = (('s', 1), ('ms', 10 ** 3), ('us', 10 ** 6), ('ns', 10 ** 9))

# 判断单个参数是不是一个整数时间戳。数字里允许用 _ 分组（如 1_792_189_920），
# 规则同 Python 整数字面量：_ 只能出现在两个数字之间；int() 本身也接受这种写法
NUMBER_RE = re.compile(r'-?\d+(?:_\d+)*', re.ASCII)


def guess_unit(value: int) -> tuple[str, int]:
    """按数量级推断时间戳单位，返回 (unit, scale)。

    s   <= 2.5e11（12 位及以内）
    ms  <= 2.5e14（15 位及以内）
    us  <= 2.5e17（18 位及以内）
    ns  其余，直到 2.5e20
    超过上界说明不是这四种单位，报错。

    >>> guess_unit(0)
    ('s', 1)
    >>> guess_unit(1792189920)            # 10 位：秒
    ('s', 1)
    >>> guess_unit(1792189920160)         # 13 位：毫秒
    ('ms', 1000)
    >>> guess_unit(1792189920160073)      # 16 位：微秒
    ('us', 1000000)
    >>> guess_unit(1792189920160073024)   # 19 位：纳秒
    ('ns', 1000000000)
    >>> guess_unit(-1792189920160073024)  # 负数按绝对值判断
    ('ns', 1000000000)
    """
    v = abs(value)
    for unit, scale in UNITS:
        if v <= MAX_EPOCH_SECONDS * scale:
            return unit, scale
    raise ValueError(f'时间戳超出 datetime 可表示范围: {value}')


def parse_tz(s: str) -> tzinfo:
    """时区名（UTC / Asia/Shanghai）或偏移（+08:00 / -0530）-> tzinfo

    不是合法时区时抛 ValueError（调用方据此回退或报错）。ZoneInfo 对坏 key 只抛
    三类：ZoneInfoNotFoundError（库里没有）、ValueError（key 格式非法）、
    OSError（tzdata 文件不可读等），所以只catch这三类，其余 Bug 照样往外抛。

    >>> parse_tz('UTC') is timezone.utc
    True
    >>> parse_tz('z') is timezone.utc               # 大小写不敏感
    True
    >>> parse_tz('+08:00') == timezone(timedelta(hours=8))
    True
    >>> parse_tz('-0530') == timezone(timedelta(hours=-5, minutes=-30))
    True
    >>> str(parse_tz('Asia/Shanghai'))              # IANA 名，依赖系统 tzdata
    'Asia/Shanghai'
    >>> parse_tz('Mars/Olympus')
    Traceback (most recent call last):
    ValueError: 无法识别时区 'Mars/Olympus'
    """
    if s.upper() in ('UTC', 'GMT', 'Z'):
        return UTC

    m = re.fullmatch(r'([+-])(\d{1,2}):?(\d{2})?', s)
    if m:
        sign, hh, mm = m.groups()
        delta = timedelta(hours=int(hh), minutes=int(mm or 0))
        return timezone(-delta if sign == '-' else delta)
    try:
        return ZoneInfo(s)              # 依赖系统 /usr/share/zoneinfo
    except (ZoneInfoNotFoundError, ValueError, OSError) as e:
        # 只 catch ZoneInfo 对坏 key 实际抛的三类；其余异常是 bug，原样抛出。
        # from e 把原因挂到 __cause__ 上，traceback 里能看到原始异常链，
        # 消息里就不用再把 e 的文本抄一遍。
        raise ValueError(f'无法识别时区 {s!r}') from e


def split_tz(argn: list[str]) -> tuple[list[str], tzinfo | None]:
    """最后一个参数像时区就摘出来，返回 (剩余参数, tzinfo 或 None)。

    这样 "日期 时间 时区" 和 "时间戳 时区" 都能写；最后一个参数不是合法
    时区时原样返回，交给 fromisoformat 去报错。

    >>> split_tz(['2026-10-17', '06:32:00', 'UTC'])
    (['2026-10-17', '06:32:00'], datetime.timezone.utc)
    >>> split_tz(['2026-10-17', '06:32:00'])           # 末尾不是时区
    (['2026-10-17', '06:32:00'], None)
    >>> split_tz(['2026-10-17', '06:32:00', 'extra'])  # 'extra' 不是时区
    (['2026-10-17', '06:32:00', 'extra'], None)
    >>> split_tz(['UTC'])                              # 只有一个参数时不拆
    (['UTC'], None)
    """
    if len(argn) > 1:
        try:
            return argn[:-1], parse_tz(argn[-1])
        except ValueError:
            pass
    return argn, None


def from_timestamp(value: int, tz: tzinfo | None = None) -> datetime:
    """epoch 时间戳（自动识别 s/ms/us/ns）-> datetime

    整数运算保证大数不丢精度：秒部分交给 fromtimestamp，不足 1 秒的部分折算成
    微秒（datetime 的最小分辨率）后补上。指定时区输出带偏移的 aware 时间，否则
    按本地时区输出墙钟时间（依赖 TZ 环境变量，所以示例都显式传时区）。

    >>> from_timestamp(0, parse_tz('UTC'))
    datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
    >>> from_timestamp(1792189920, parse_tz('UTC'))
    datetime.datetime(2026, 10, 16, 22, 32, tzinfo=datetime.timezone.utc)
    >>> from_timestamp(1792189920160, parse_tz('UTC'))         # 毫秒
    datetime.datetime(2026, 10, 16, 22, 32, 0, 160000, tzinfo=datetime.timezone.utc)
    >>> from_timestamp(1792189920160073, parse_tz('UTC'))      # 微秒
    datetime.datetime(2026, 10, 16, 22, 32, 0, 160073, tzinfo=datetime.timezone.utc)
    >>> from_timestamp(1792189920160073024, parse_tz('UTC'))   # 纳秒
    datetime.datetime(2026, 10, 16, 22, 32, 0, 160073, tzinfo=datetime.timezone.utc)
    >>> from_timestamp(-1792189920, parse_tz('UTC'))           # 1970 之前
    datetime.datetime(1913, 3, 18, 1, 28, tzinfo=datetime.timezone.utc)

    guess_unit 只按数量级判断，没算时区偏移，所以极端值仍可能越界，这里转成
    ValueError 交给调用方报错（不让它冒成 traceback）：

    >>> from_timestamp(253402300799, parse_tz('+14:00'))       # UTC 上界 + 正偏移
    Traceback (most recent call last):
    ValueError: 时间戳 253402300799 换算到 UTC+14:00 后超出 datetime 可表示范围（年份需在 1..9999）
    """
    _unit, scale = guess_unit(value)

    whole, frac = divmod(abs(value), scale)
    micros = frac * 1000000 // scale
    sign = -1 if value < 0 else 1

    try:
        # 指定时区输出带偏移的 aware 时间；否则按本地时区输出墙钟时间
        t = datetime.fromtimestamp(sign * whole, tz) if tz else datetime.fromtimestamp(sign * whole)
        if micros:
            t += timedelta(microseconds=sign * micros)
    except (OverflowError, ValueError) as e:
        # 时区偏移会把结果推出 1..9999 年：同一数值在 UTC 合法、在 +14:00 就可能越界
        # （负偏移方向则是下界先越）；微秒补偿也可能把 0001-01-01 顶到前一年。
        tzname = str(tz) if tz is not None else '本地时区'
        raise ValueError(f'时间戳 {value} 换算到 {tzname} 后超出 '
                         f'datetime 可表示范围（年份需在 1..9999）') from e
    return t


def from_timestring(argn: list[str], tz: tzinfo | None = None) -> datetime:
    """ISO 8601 日期/日期时间 -> datetime；指定时区则挂上 tzinfo

    >>> from_timestring(['2026-10-17'])
    datetime.datetime(2026, 10, 17, 0, 0)
    >>> from_timestring(['2026-10-17', '06:32:00', 'UTC'])[0]
    Traceback (most recent call last):
    ValueError: Invalid isoformat string: '2026-10-17 06:32:00 UTC'
    >>> from_timestring(['2026-10-17', '06:32:00.160073'], parse_tz('UTC'))
    datetime.datetime(2026, 10, 17, 6, 32, 0, 160073, tzinfo=datetime.timezone.utc)
    >>> from_timestring(['2026-10-17', '06:32:00'], parse_tz('UTC')).timestamp()
    1792218720.0
    >>> from_timestring(['2026-10-17'], parse_tz('UTC')).timestamp()
    1792195200.0
    """
    t = datetime.fromisoformat(' '.join(argn))
    return t if tz is None else t.replace(tzinfo=tz)


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。

    >>> build_parser().parse_args([]).argn
    []
    >>> build_parser().parse_args(['1792189920', 'UTC']).argn
    ['1792189920', 'UTC']
    >>> build_parser().parse_args(['-s']).stamp
    True
    """
    parser = argparse.ArgumentParser(
        description='时间戳 / 日期时间互转：给数字还日期时间，给日期时间还 epoch 秒')

    # argparse 判断“负数字”用的是实例上的私有正则（3.12 在 __init__ 里就地编译，
    # 改模块级变量无效，必须改实例），原版只认 -\d+。这里用 VERBOSE 模式把三类
    # “长得像选项”的参数逐条注释放行：
    #   带 _ 分组的负时间戳、负小数（argparse 原本支持）、负 UTC 偏移
    parser._negative_number_matcher = re.compile(r"""  # type: ignore[attr-defined]
          ^-\d+(?:_\d+)*$      # 负整数，允许 _ 分组：-1_792_189_920
        | ^-\d*\.\d+$          # 负小数：-1.5、-.5
        | ^-\d{1,2}:?\d{2}$    # 负 UTC 偏移：-05:30 / -0530 / -8:00
    """, re.VERBOSE)

    parser.add_argument('-s', '--stamp', action='store_true',
                        help='输出 epoch 秒')
    parser.add_argument('argn', nargs='*',
                        help='时间戳（自动识别 s/ms/us/ns，可用 _ 分组）；'
                             '或 "日期 [时间] [时区]"；'
                             '或只给一个时区（显示该时区的当前时间）。'
                             '时区写法：UTC / Asia/Shanghai / +08:00 / -0530')

    return parser


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    # 输出什么表示：默认按输入类型决定（数字->日期时间，日期时间->epoch 秒），
    # -s 则一律输出 epoch 秒
    stamp = args.stamp

    if args.argn:
        if not all(args.argn):
            parser.error('参数不能为空')

        # 只给一个参数且它是时区 -> 显示该时区的当前时间
        if len(args.argn) == 1:
            try:
                tz: tzinfo | None = parse_tz(args.argn[0])
            except ValueError:
                pass
            else:
                t = datetime.now(tz)
                print(t.timestamp() if stamp else t)
                return 0

        rest, tz = split_tz(args.argn)

        if len(rest) == 1 and NUMBER_RE.fullmatch(rest[0]):
            t = from_timestamp(int(rest[0]), tz)  # 给数字还日期时间
        else:
            t = from_timestring(rest, tz)         # 给日期时间还 epoch 秒
            stamp = True
    else:
        t = datetime.now()

    print(t.timestamp() if stamp else t)
    return 0


if __name__ == '__main__':
    sys.exit(main())
