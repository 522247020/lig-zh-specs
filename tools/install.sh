#!/bin/sh
# 把本仓库的 spec 安装到 lig 的用户目录，并检查 lig 是否已安装。
#
#   ./tools/install.sh           # 软链接（推荐：git pull 后自动生效）
#   ./tools/install.sh --copy    # 复制一份
#   ./tools/install.sh --force   # 覆盖已有文件，不做备份
#   ./tools/install.sh --install-lig   # 发现没有 lig 时直接装（不询问）
#
# 目标目录: ${XDG_CONFIG_HOME:-$HOME/.config}/lig/specs
set -eu

LIG_REPO=https://github.com/KevenGoncalves/lig
LIG_INSTALL_URL=https://github.com/KevenGoncalves/lig/releases/latest/download/install.sh
LIG_MIN=1.4.0

src=$(cd "$(dirname "$0")/../specs" && pwd)
dst="${XDG_CONFIG_HOME:-$HOME/.config}/lig/specs"
mode=link
force=0
auto_lig=0

for arg in "$@"; do
    case $arg in
        --copy) mode=copy ;;
        --link) mode=link ;;
        --force) force=1 ;;
        --install-lig) auto_lig=1 ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "未知参数: $arg" >&2; exit 1 ;;
    esac
done

install_methods() {
    cat <<EOF
lig 是一个 IDE 风格的终端补全工具，本仓库的 spec 需要它才能生效：
  仓库: $LIG_REPO
  安装: $LIG_REPO#install

安装方式（选一个）：
  Linux / macOS:  curl -fsSL $LIG_INSTALL_URL | sh
  Homebrew:       brew install kevengoncalves/tap/lig
  Fedora / RHEL:  sudo dnf copr enable kevengoncalves/lig && sudo dnf install lig
  Debian / Ubuntu: 见仓库 README 的 APT 段（添加 keyring 与 apt 源）
  Nix:            home-manager 的 programs.lig 模块
  从源码:         cargo install --path .（Rust 1.85+）
安装完成后运行 \`lig install\` 启用 shell 集成，并用 \`lig doctor\` 检查。
EOF
}

ensure_lig() {
    if command -v lig >/dev/null 2>&1; then
        version=$(lig --version 2>/dev/null | head -n 1)
        echo "✓ 已找到 lig: ${version:-lig}"
        case $version in
            "lig 1."[0-3].*) echo "  注意: 本仓库在 lig $LIG_MIN 上验证；旧版本可能有字段不被识别" ;;
        esac
        return 0
    fi

    echo "✗ 没有找到 lig 命令" >&2
    echo >&2
    install_methods >&2

    answer=
    if [ "$auto_lig" -eq 1 ] && command -v curl >/dev/null 2>&1; then
        answer=y
    elif [ -t 0 ]; then
        printf '\n现在用官方脚本安装 lig 吗？[y/N] '
        read -r answer || answer=
    else
        echo >&2
        echo "非交互环境：跳过 lig 安装，只安装 spec。装好 lig 后再跑一次 ./tools/install.sh 或 lig doctor。" >&2
        return 0
    fi

    case $answer in
        y|Y|yes|YES)
            command -v curl >/dev/null 2>&1 || { echo "✗ 需要 curl 才能自动安装，请手动安装 lig" >&2; return 0; }
            echo "→ 执行官方安装脚本 …"
            if curl -fsSL "$LIG_INSTALL_URL" | sh; then
                hash -r 2>/dev/null || true
                if command -v lig >/dev/null 2>&1; then
                    echo "✓ lig 已安装: $(lig --version 2>/dev/null | head -n 1)"
                    echo "  如果 shell 提示找不到命令，重开终端或把安装目录加进 PATH"
                else
                    echo "✗ 安装脚本结束但没找到 lig，可能需要重开 shell 或手动调整 PATH" >&2
                fi
            else
                echo "✗ 自动安装失败，请按上面的方式手动安装 lig" >&2
            fi
            ;;
        *)
            echo "跳过安装 lig，继续安装 spec"
            ;;
    esac
}

ensure_lig

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
