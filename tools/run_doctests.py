#!/usr/bin/env python3
"""跑 datetime.py 里的 doctest。

为什么不能用 `pytest --doctest-modules datetime.py`：本文件与标准库 datetime 同名，
pytest 导入它时拿到的是 sys.modules 里已经加载的标准库 datetime（要么报
"import file mismatch"，要么静默收集 0 个），永远抓不到本文件的示例。

这里用 importlib 以**别的模块名**加载文件，既避开同名冲突，也不需要 -P
（本脚本在 tools/ 下，sys.path[0] 是 tools/，仓库根目录不在搜索路径里）。

用法：
    python3 tools/run_doctests.py [-v]
"""
import doctest
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'datetime.py'
# 模块名不能叫 datetime：加载时文件里的 `from datetime import ...` 会解析到
# 它自己，造成循环导入（同脚本必须用 -P 的原因）
MODULE_NAME = 'dt_cli'


def load():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load()
    verbose = '-v' in sys.argv
    result = doctest.testmod(module, verbose=verbose)
    print(f'{result.attempted - result.failed}/{result.attempted} 个 doctest 通过')
    return 1 if result.failed else 0


if __name__ == '__main__':
    sys.exit(main())
