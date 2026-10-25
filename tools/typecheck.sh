#!/bin/sh
# 对 datetime.py 跑 mypy。
#
# 为什么不能直接 `mypy datetime.py`：本文件与标准库 datetime 同名，mypy 把正在检查的
# 文件注册为模块 "datetime"，于是文件里的 `from datetime import ...` 解析到它自己，
# 报 "Module datetime has no attribute datetime"（类型全丢）。
#
# 解法：复制一份、换个模块名，放到一个不含 datetime.py 的临时目录里检查。文件内容
# 逐字节相同，所以报错行号与源码一一对应，只有文件名前缀不同。
#
# 仓库根用 git rev-parse --show-toplevel 取：被 hook 调用时 $0 是
# .git/hooks/ 下的软链接路径，`dirname $0/..` 会推到 .git/ 去。
set -e

repo="$(git rev-parse --show-toplevel)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cp "$repo/datetime.py" "$tmp/dt_cli.py"
cd "$tmp"

exec uv run --project "$repo" mypy \
    --config-file "$repo/pyproject.toml" \
    --cache-dir "$repo/.mypy_cache" \
    dt_cli.py
