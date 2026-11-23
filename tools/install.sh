#!/bin/sh
# 把本仓库的 spec 安装到 lig 的用户目录。
#
#   ./tools/install.sh           # 软链接（推荐：git pull 后自动生效）
#   ./tools/install.sh --copy    # 复制一份
#   ./tools/install.sh --force   # 覆盖已有文件，不做备份
#
# 目标目录: ${XDG_CONFIG_HOME:-$HOME/.config}/lig/specs
set -eu

src=$(cd "$(dirname "$0")/../specs" && pwd)
dst="${XDG_CONFIG_HOME:-$HOME/.config}/lig/specs"
mode=link
force=0

for arg in "$@"; do
    case $arg in
        --copy) mode=copy ;;
        --link) mode=link ;;
        --force) force=1 ;;
        -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "未知参数: $arg" >&2; exit 1 ;;
    esac
done

command -v lig >/dev/null 2>&1 || echo "提示: PATH 里没有 lig，装完可能需要先安装 lig 才能生效" >&2

mkdir -p "$dst"

stamp=$(date +%Y%m%d-%H%M%S)
count=0
for file in "$src"/*.toml "$src"/*.json; do
    [ -e "$file" ] || continue
    name=$(basename "$file")
    target="$dst/$name"
    if [ -e "$target" ] || [ -L "$target" ]; then
        if [ -L "$target" ]; then
            # 旧软链：直接替换
            :
        elif [ "$force" -eq 0 ]; then
            cp -p "$target" "$target.bak.$stamp"
            echo "备份 $name -> $(basename "$target").bak.$stamp"
        fi
        rm -f "$target"
    fi
    if [ "$mode" = copy ]; then
        cp -p "$file" "$target"
    else
        ln -s "$file" "$target"
    fi
    count=$((count + 1))
done

echo "已安装 $count 个 spec 到 $dst（模式: $mode）"
echo "新开一个终端标签页即可看到中文描述；用 lig doctor 检查集成状态。"
