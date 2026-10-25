# datetime 的开发入口。用法：just --list
# 安装 just：https://github.com/casey/just（cargo install just / brew install just）

# 裸 `just` 等于 `just check`
default: check

# 为什么 run 里必须带 -P：本文件与标准库 datetime 同名，不加 -P 会把仓库目录塞进
# sys.path[0]，`from datetime import ...` 会导入到脚本自己，直接循环导入报错。
# （与 datetime.py shebang 里带 -P 是同一个原因。）

# 跑脚本，参数原样透传，如 just run 1792189920 UTC / just run 2026-10-17 06:32:00
run *argv:
    python3 -P datetime.py {{argv}}

# 三项检查全跑
check: lint test typecheck

# ruff：代码风格 / 未使用导入 / pyupgrade 等
lint:
    uv run ruff check .

# doctest：30 个示例，走 tools/run_doctests.py（pytest 收集不到，原因见该文件注释）
test:
    python3 tools/run_doctests.py

# mypy：类型检查（经 tools/typecheck.sh 绕开同名自导入）
typecheck:
    sh tools/typecheck.sh

# 手动同步到 ~/.local/bin/datetime，等价于 pre-push hook 自动做的事
deploy:
    sh tools/deploy.sh
