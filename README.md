# lig-zh-specs

[lig](https://github.com/KevenGoncalves/lig) 的**中文描述 spec 集合**：让终端补全弹窗里的子命令、参数说明显示成中文。

lig 是一个 IDE 风格的终端补全工具，弹窗里的说明文字来自它的 spec 文件（Fig 格式，TOML/JSON）。lig 自带几百个命令的 spec，但描述都是英文。本仓库把这些 spec 的 `description` 翻译成中文，并对几个常用命令补上了更细的枚举值和中文提示。

> 非官方项目，与 lig 作者无关。只在 lig 1.4.0 上验证过。

## 效果

```
$ lig complete "pacman -"
-Syu      同步数据库并升级全部软件包
-Syyu     强制刷新数据库后升级全部
-Rns      删除包、配置文件和依赖
-Qdtq     列出无人依赖的孤儿包
-Ss       在仓库中按关键字搜索
--color   彩色化输出的时机
...

$ lig complete "ping -M "
do     自己做 PMTU 发现
dont   不做 PMTU 发现
want   希望做 PMTU 发现
probe  用探测方式判断 MTU

$ lig complete "tmux split-window -"
-h  水平拆分
-v  垂直拆分
-c  起始目录
...
```

## 覆盖的命令

| 文件 | 命令 | 规模 | 说明 |
|---|---|---|---|
| `ls.toml` | GNU coreutils `ls` | 55 选项 | 按 Linux 的 GNU 参数重写（内置版是 BSD/macOS 的） |
| `eza.toml` | `eza` | 66 选项 | 覆盖 0.23.x 全部参数 |
| `find.toml` | GNU `find` | 74 项 | 含测试/动作，以及 `!`、`(`、`)`、`-a`、`-o` 快捷项 |
| `grep.toml` | GNU `grep` | 47 选项 | 含 `--color`、`--binary-files`、`--exclude-dir` 等枚举值 |
| `awk.toml` | GNU `awk` (gawk) | 34 选项 | 可选参数区分了“紧跟”与 `=` 两种写法 |
| `ping.toml` | iputils `ping` | 38 选项 | 含 `-M`/`-T`/`-N` 的取值说明 |
| `ail-cli.toml` | AppImageLauncher CLI | 3 子命令 | `integrate` / `unintegrate` / `would-integrate` |
| `pacman.toml` | `pacman` | 71 选项 | `-S/-Q/-R/-U/-F/-T/-D` 的选项全部纳入，描述带操作前缀 |
| `yay.toml` | `yay` | 158 选项 | 含 AUR 专属操作 `-Y/-B/-G/-P/-W` |
| `tmux.json` | `tmux` | 85 子命令 / 312 选项 | 由 lig 内置 spec 全量翻译（399 条描述） |
| `curl.json` | `curl` | 225 选项 | 由 lig 内置 spec 全量翻译（226 条描述） |

合计约 700 条中文描述。`tmux`/`curl` 是整体翻译，其余是手写（参数取自本机 `--help`）。

## 安装

```bash
git clone https://github.com/522247020/lig-zh-specs.git
cd lig-zh-specs
./tools/install.sh            # 默认建软链接，git pull 后自动生效
# 或
./tools/install.sh --copy     # 复制一份到 ~/.config/lig/specs
```

装完**新开一个终端标签页**。检查：

```bash
lig specs list | grep -E 'pacman|yay|tmux'   # 应显示 user
lig complete "pacman -S -"                   # 应输出中文说明
```

只想要其中几个，直接复制对应文件即可：

```bash
cp specs/pacman.toml ~/.config/lig/specs/
```

⚠️ **用户 spec 会整体替换 lig 内置 spec**。装了本仓库的 `pacman.toml` 后，`pacman` 的补全只来自这个文件；想让 lig 重新读内置版，删掉文件后执行 `lig specs new pacman`。

卸载：删掉 `~/.config/lig/specs/` 里对应文件。`lig uninstall` 只清 shell 集成，不动这些 spec。

## 已知限制（lig 1.4.0 实测）

这些是 lig 本身的解析行为，spec 层面绕不过，写在这里免得当成 bug 提：

1. **组合短参数只记住最后一个字母**。`src/engine.rs` 的 `match_option()` 对 `-Rns` 只把 `-s` 记为已用，`-R`/`-n` 仍会出现在候选里。
   缓解：把常用组合（`-Syu`、`-Rns`、`-Qdtq` …）做成独立条目，弹窗里会显示成一行并整组插入。
2. **以 `-` 开头的子命令进不去**。`pactest -S -` 不会进入 `-S` 的子层，所以 `pacman`/`yay` 的操作被扁平化成选项，描述用 `S：`、`Q：`、`S/R/U：` 前缀区分适用操作。副作用：`pacman -S -` 也会列出 Q/R 的选项。
3. **选项按短名去重**。同一个短名定义两次只保留第一条，所以同字母多义（`-c` = clean/changelog/cascade）合并成一条，长名（`--changelog` …）单独保留，`--cha` 仍能正确补出并插入 `--changelog`。
4. **`=` 后面的值不补全**。`awk --dump-variables=/etc/ho` 没有候选，空格形式（`find . -newer /etc/ho`）正常。
5. **选项参数的 `isCommand` 不生效**。`find . -exec ` 不会补命令名（位置参数的 `isCommand` 才有效，如 `sudo `）。
6. **没有 pacman/yay 的包名 generator**。`pacman -S ` / `yay -S ` 返回空——lig 没有内置该数据源；可用 `pacman -Qq` 自建 `generators.script`（本仓库暂未收录，欢迎 PR）。
7. 改完 spec 后，**已打开的 tab 可能仍用旧数据**，新开 tab 或 `lig specs clear-cache` 后复查。

## 参与贡献

1. 从内置 spec 起步（会覆盖同名文件，注意先备份自己想保留的改动）：

   ```bash
   lig specs new <命令>        # 生成 ~/.config/lig/specs/<命令>.json
   ```

2. **只改 `description`**。`name`、`args`、`suggestions`、`generators`、`requiresSeparator`、`isRepeatable` 等结构字段不要动，除非是在修正错误并在 PR 里说明。
3. 风格约定：
   - 短句、名词短语，**不加句号**；尽量 ≤ 18 字，最长不超过 30 字。
   - 技术名词保留英文：AUR、repo、PKGBUILD、URL、HTTP、TLS、stdin、glob 等。
   - 操作相关的选项加前缀，例如 `S：清理缓存`、`S/R/U：跳过依赖检查`、`Q：查看更新日志`。
   - 枚举值写成表，让每个取值都有说明：

     ```toml
     args = { name = "时机", suggestions = [
       { name = "always", description = "始终着色" },
       { name = "auto", description = "仅在输出到终端时着色" },
       { name = "never", description = "关闭颜色" },
     ] }
     ```
4. 验证（不需要改动你自己的 lig 配置，脚本会在临时目录里跑 `lig specs check`）：

   ```bash
   python3 tools/verify.py                    # 中文覆盖率 + 描述长度 + lig specs check
   python3 tools/verify.py --upstream         # tmux/curl：与内置 spec 比对结构（原文以外的字段必须一致）
   python3 tools/verify.py --coverage pacman  # 与 pacman 各 --help 比对，缺失应为 0
   ```

5. 常用术语表：session=会话、window=窗口、pane=窗格、client=客户端、server=服务端、detach=分离、attach=接入、binding=绑定、target=目标、header=请求头、proxy=代理、redirect=重定向。

提交时请附上 `tools/verify.py` 的输出，以及截图或 `lig complete "<命令>"` 的结果。

## 目录结构

```
specs/             lig spec 文件（TOML 或 JSON，文件名即命令名）
tools/install.sh   安装到 ~/.config/lig/specs（软链或复制，自动备份）
tools/verify.py    校验：中文覆盖率、描述长度、lig specs check、结构比对、选项覆盖度
```

## 许可

本项目以 MIT 许可发布，见 [LICENSE](LICENSE)。

`tmux.json`、`curl.json` 的描述翻译自 [withfig/autocomplete](https://github.com/withfig/autocomplete)（MIT），lig 内置 spec 由该项目转换而来，版权归 Hercules Labs Inc. 及贡献者。
