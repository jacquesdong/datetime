#!/bin/sh
# 一次跑完三项检查：ruff / doctest / mypy
#
# 也挂在 .git/hooks/pre-commit 上（hook 本身不入 .git，用软链接指过来）：
#   ln -s ../../tools/check.sh .git/hooks/pre-commit
# 也可以手动跑：sh tools/check.sh
#
# 注意：被 hook 调用时 $0 是 .git/hooks/pre-commit 这个链接路径，不能用
# `dirname $0/..` 推仓库根（会得到 .git/），所以用 git rev-parse --show-toplevel。
#
# doctest 没有走 `pytest --doctest-modules`，原因见 tools/run_doctests.py 的说明：
# 本文件与标准库 datetime 同名，pytest 导入时拿到的是标准库模块，抓不到本文件的示例。
set -e

repo="$(git rev-parse --show-toplevel)"
cd "$repo"

echo '=== ruff check ==='
uv run ruff check .

echo '=== doctest ==='
python3 tools/run_doctests.py

echo '=== mypy ==='
sh tools/typecheck.sh

echo
echo '全部通过'
