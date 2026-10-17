#!/bin/sh
# deploy: git push 之前把仓库里的 datetime.py 同步到 ~/.local/bin/datetime
#
# 由 pre-push hook 触发（hook 本身不入 .git，用软链接指过来）：
#   ln -s ../../tools/deploy.sh .git/hooks/pre-push
# 也可以手动跑：sh tools/deploy.sh
#
# 说明：用 cp 到临时文件再 rename 的方式覆盖目标，保证原子性；
#       不用硬链接 —— git checkout / sed -i / vim 都会静默断链。
#
# 注意：pre-push 以非 0 退出会让 git push 直接中止，所以同步失败会挡住推送，
#       这比“推上去但本地没装上”更容易发现问题。
#
# 局限：只看 HEAD 这一个提交是否改动了 datetime.py。若一次 push 含多个提交、
#       而改动不在最后一个提交上，这里会误判“未改动”而跳过。pre-push 的 stdin
#       会给出 remote_sha..local_sha 范围，需要更严格时可以改成按范围判断。

set -eu

# 日志前缀取 $0 的文件名（busybox 式）：被 hook 调用时显示 hook 名
# （pre-push / post-commit），手动跑时显示 deploy.sh，不会张冠李戴
name="${0##*/}"

rel="datetime.py"
# 默认装到 ~/.local/bin/datetime：用 $HOME 而不是 "~"（引号里 ~ 不展开）。
# 换机器时无需改路径；本机该路径是软链接，会在下面被解析到 config 仓库内的真实文件。
dst_default="${HOME:?未设置 HOME，无法确定安装目录}/.local/bin/datetime"
dst="${DATETIME_INSTALL_DIR:-$dst_default}"

# HEAD 这个提交是否包含 datetime.py（root commit 需要 --root，amend 也能覆盖到）
if ! git diff-tree --root --no-commit-id --name-only -r HEAD 2>/dev/null | grep -qx "$rel"; then
    echo "$name: $rel 未改动，跳过同步" >&2
    exit 0
fi

top="$(git rev-parse --show-toplevel)"
src="$top/$rel"

if [ ! -f "$src" ]; then
    echo "$name: 源文件不存在: $src" >&2
    exit 1
fi

# 目标若是软链接：写入它指向的真实文件，而不是把链接本身替换掉。
# readlink -f 遇到悬空链接返回空串且 rc=1，这时保留原路径，
# 让下面的 mkdir -p + mv 直接在 ~/.local/bin/ 下建出实体文件。
dangling=""
if [ -L "$dst" ]; then
    real="$(readlink -f "$dst" 2>/dev/null || true)"
    if [ -n "$real" ]; then
        # 备用（默认不启用）：软链接解析成功时也想提示的话，取消下一行注释
        # echo "$name: $dst 是软链接，写入其指向的真实文件: $real" >&2
        dst="$real"
    else
        echo "$name: $dst 是悬空链接（指向 $(readlink "$dst" 2>/dev/null)），目标不存在，将用实体文件替换该链接" >&2
        dangling=1
    fi
fi

if [ ! -e "$dst" ] && [ -z "$dangling" ]; then
    echo "$name: $dst 不存在，将新建（必要时自动创建目录）" >&2
fi

dir="$(dirname "$dst")"
mkdir -p "$dir"

tmp="$dir/.datetime.$$"
trap 'rm -f "$tmp"' EXIT
cp "$src" "$tmp"
chmod 755 "$tmp"
mv -f "$tmp" "$dst"
trap - EXIT

echo "$name: synced $src -> $dst" >&2
