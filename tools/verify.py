#!/usr/bin/env python3
"""校验本仓库里的 lig spec。

用法:
  python3 tools/verify.py                        # 中文覆盖率 / 描述长度 / lig specs check
  python3 tools/verify.py --upstream             # 额外: 与 lig 内置 spec 做结构比对 (tmux, curl)
  python3 tools/verify.py --coverage pacman yay  # 额外: 与 --help 的选项覆盖度比对

退出码 0 表示全部通过。需要 lig 在 PATH 里 (1.4.0 测试过)。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
SPECS = REPO / "specs"
CJK = re.compile(r"[\u4e00-\u9fff]")
MAX_COLS = 60  # 约 30 个汉字（汉字按 2 列计）

# 哪些 spec 是从内置 spec 翻译来的(需要 --upstream 做结构比对)
FROM_BUILTIN = {"tmux": "tmux.json", "curl": "curl.json"}

# 哪些命令需要额外抓取各操作的 --help 才能算覆盖度
OP_RECIPES = {
    "pacman": [[], ["-S"], ["-Q"], ["-R"], ["-U"], ["-F"], ["-T"], ["-D"]],
    "yay": [[], ["-S"], ["-Q"], ["-R"], ["-U"], ["-F"], ["-T"], ["-D"], ["-Y"], ["-B"], ["-G"], ["-P"], ["-W"]],
}


def load(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    return tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)


def walk(obj, path="", out=None):
    """收集 (路径, description) 对。"""
    out = out if out is not None else []
    if isinstance(obj, dict):
        if isinstance(obj.get("description"), str):
            out.append((path or obj.get("name", "?"), obj["description"]))
        for key, value in obj.items():
            if key != "description":
                walk(value, f"{path}/{key}" if path else key, out)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            walk(value, f"{path}[{i}]", out)
    return out


def strip_descriptions(obj):
    if isinstance(obj, dict):
        return {k: strip_descriptions(v) for k, v in obj.items() if k != "description"}
    if isinstance(obj, list):
        return [strip_descriptions(v) for v in obj]
    return obj


def option_names(obj):
    names = set()
    for opt in obj.get("options") or []:
        n = opt["name"]
        names.update(n if isinstance(n, list) else [n])
    for sub in obj.get("subcommands") or []:
        names |= option_names(sub)
    return names


def display_width(text: str) -> int:
    """终端显示宽度：汉字/全角按 2 列，其余按 1 列。"""
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def check_descriptions() -> list[str]:
    errors = []
    print(f"{'文件':<16} {'描述':>5} {'无中文':>6} {'超宽':>5} {'最宽':>5}")
    for path in sorted(SPECS.iterdir()):
        if path.suffix not in (".toml", ".json"):
            continue
        spec = load(path)
        descs = [d for _, d in walk(spec)]
        no_cjk = [p for p, d in walk(spec) if not CJK.search(d)]
        too_long = [(p, d) for p, d in walk(spec) if display_width(d) > MAX_COLS]
        widest = max((display_width(d) for d in descs), default=0)
        print(f"{path.name:<16} {len(descs):>5} {len(no_cjk):>6} {len(too_long):>5} {widest:>5}")
        for p in no_cjk:
            errors.append(f"{path.name}: 描述里没有中文 -> {p}")
        for p, d in too_long:
            errors.append(f"{path.name}: 描述超过 {MAX_COLS} 列 -> {p}: {d}")
    return errors


LIG_REPO = "https://github.com/KevenGoncalves/lig"
LIG_INSTALL = (
    "安装: https://github.com/KevenGoncalves/lig#install （"
    "Linux/macOS: curl -fsSL https://github.com/KevenGoncalves/lig/releases/latest/download/install.sh | sh）"
)


def missing_lig() -> None:
    print("未找到 lig 命令，跳过需要 lig 的检查。")
    print(f"  lig 仓库: {LIG_REPO}")
    print(f"  {LIG_INSTALL}")


def lig_specs_check() -> list[str]:
    if not shutil.which("lig"):
        missing_lig()
        return []
    with tempfile.TemporaryDirectory() as tmp:
        cfg = pathlib.Path(tmp)
        target = cfg / "lig" / "specs"
        target.mkdir(parents=True)
        for path in SPECS.iterdir():
            if path.suffix in (".toml", ".json"):
                shutil.copy2(path, target / path.name)
        env = {**os.environ, "XDG_CONFIG_HOME": tmp}
        proc = subprocess.run(["lig", "specs", "check"], capture_output=True, text=True, env=env)
    errors = []
    for line in proc.stdout.splitlines():
        print("  " + line)
        if line.strip() and not line.rstrip().endswith(": ok"):
            errors.append(f"lig specs check: {line}")
    if proc.returncode:
        errors.append(f"lig specs check 退出码 {proc.returncode}")
    return errors


def compare_upstream() -> list[str]:
    """tmux / curl：与 lig 内置 spec 比对结构（忽略 description）。"""
    if not shutil.which("lig"):
        missing_lig()
        return []
    errors = []
    for cmd, filename in FROM_BUILTIN.items():
        path = SPECS / filename
        if not path.exists():
            continue
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "XDG_CONFIG_HOME": tmp}
            subprocess.run(["lig", "specs", "new", cmd], capture_output=True, text=True, env=env)
            builtin = pathlib.Path(tmp) / "lig" / "specs" / f"{cmd}.json"
            if not builtin.exists():
                errors.append(f"{cmd}: 无法从 lig 内置 spec 生成对照文件")
                continue
            mine = load(path)
            theirs = json.loads(builtin.read_text(encoding="utf-8"))
            if strip_descriptions(mine) == strip_descriptions(theirs):
                print(f"  {filename}: 结构与内置一致（仅描述不同）")
            else:
                errors.append(f"{filename}: 结构与内置 spec 不一致")
    return errors


def coverage(cmds: list[str]) -> list[str]:
    errors = []
    for cmd in cmds:
        spec_path = SPECS / f"{cmd}.toml"
        if not spec_path.exists():
            spec_path = SPECS / f"{cmd}.json"
        if not spec_path.exists():
            errors.append(f"{cmd}: 仓库里没有对应 spec")
            continue
        names = option_names(load(spec_path))
        found, text = set(), ""
        for op in OP_RECIPES.get(cmd, [[]]):
            proc = subprocess.run([cmd, *op, "--help"], capture_output=True, text=True, errors="replace")
            out = proc.stdout + proc.stderr
            text += out
            for line in out.splitlines():
                m = re.match(r"^\s{1,6}(-{1,2}\S.*?)\s{2,}\S", line)
                if m:
                    found.update(re.findall(r"(?<![\w-])-{1,2}[A-Za-z0-9?][\w-]*", m.group(1)))
            for group in re.findall(r"\{([^}]*)\}", out):
                found.update(re.findall(r"(?<![\w-])-{1,2}[A-Za-z0-9?][\w-]*", group))
        missing = sorted(found - names)
        print(f"  {cmd}: spec {len(names)} 个名字 / 帮助识别 {len(found)} 个 / 缺失 {len(missing)}")
        if missing:
            print("    缺失: " + " ".join(missing))
            errors.append(f"{cmd}: 缺失 {len(missing)} 个帮助里的选项")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 lig 中文 spec")
    parser.add_argument("--upstream", action="store_true", help="与 lig 内置 spec 比对结构")
    parser.add_argument("--coverage", nargs="*", metavar="CMD", help="与 --help 比对选项覆盖度")
    args = parser.parse_args()

    errors = []
    print("== 描述检查 ==")
    errors += check_descriptions()

    print("\n== lig specs check ==")
    errors += lig_specs_check()

    if args.upstream:
        print("\n== 与内置 spec 结构比对 ==")
        errors += compare_upstream()

    if args.coverage:
        print("\n== 覆盖度 ==")
        errors += coverage(args.coverage or list(OP_RECIPES))

    print()
    if errors:
        print(f"✗ {len(errors)} 个问题:")
        for err in errors:
            print("  - " + err)
        return 1
    print("✓ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
