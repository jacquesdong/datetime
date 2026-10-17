#!/bin/sh
# 一次跑完三项检查：ruff / doctest / mypy
#
#   sh tools/check.sh
#
# doctest 没有走 `pytest --doctest-modules`，原因见 tools/run_doctests.py 的说明：
# 本文件与标准库 datetime 同名，pytest 导入时拿到的是标准库模块，抓不到本文件的示例。
set -e

repo="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo"

echo '=== ruff check ==='
uv run ruff check .

echo '=== doctest ==='
python3 tools/run_doctests.py

echo '=== mypy ==='
sh tools/typecheck.sh

echo
echo '全部通过'
