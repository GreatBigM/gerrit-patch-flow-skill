# Changelog
## 1.2.4 (2026-10-14)

### Fixed（install.sh 两处 + 发布闸门，与 qwiki-skill 同款）

- **`--target hermes,claude`（空格形式）从未生效**：解析只认 `--target=`，空格形式把值吞成空串后落进"非交互 = 装全部"分支——而 README / 用法行 / 脚本头部**三处文档全写的空格形式**。现两种形式都支持，且 `--target` 缺参数时直接报错退出（不再静默装全部）。
- **备份落在 skills 扫描根之内**：旧版备份写成 `<skills>/<name>.bak.<时间戳>`，而 agent 按「含 SKILL.md 的目录」发现技能、不看目录名 ⇒ 备份被当成**第二个同名技能**加载（重名歧义下静默跳过其一）。现备份落 `<tool 根>/skills-backup/`（扫描根之外），README 与脚本尾注同步。
- **挂上 pre-push 闸门（脱敏 + CHANGELOG 同步）**：`scripts/publish-check.py`（扫项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径，自带 `--self-test`）+ `scripts/hooks/pre-push`；启用一次 `git config core.hooksPath scripts/hooks`。理由与脱敏规则同源：**靠人记必然回潮**，检查要做成"推送时自动拦"而不是"记得手动跑"。CHANGELOG 闸门名单 = SKILL.md / install.sh / scripts/ / references/。
- **脱敏：正文里的项目代号与示例内网 IP 换占位符**——`scripts/publish-check.py` 挂上后首扫命中，逐条判定（另 4 处『凭据赋值』为误报：都是串口提示符 `Password:` 字面量与说明，无真实密钥）后替换：正文 / references 里的项目代号 → `<项目A>`（多处依次 A/B/C/D），模板示例里的内网 IP → 文档保留段 `192.0.2.x`。这些标识已随历史提交公开过，本次只保证**往后的版本不再含**；历史不回改——force push 也收不回（已 clone/fork/缓存的副本），脱敏的真实收益是往后不再泄漏。
- 版本 1.2.3 → 1.2.4

# CHANGELOG

## v1.2.3 (2026-09-30)

### Added（回灌本机 Hermes 副本的 09-30 实测）

- **review URL 判定四分支源码实证**（`<repo_root>/.repo/repo/git_config.py` 的 `ReviewUrl()`）：`REVIEW_CACHE` → `REPO_HOST_PORT_INFO` env → review URL scheme 为 `sso:`/`ssh:`（直接采信、**零探测**）→ `REPO_IGNORE_SSH_INFO`（退回 http，**禁用**）→ 兜底才 `GET <review>/ssh_info`；只有 `project.py` 的 `UploadForReview` 调用它 ⇒ **只有 `repo upload` 需要这层封装**，`repo init`/`repo sync` 只碰 fetch URL（天然走 ssh_config 的 ProxyCommand）
- **推荐封装 `repo-vpn`**（一行函数、通用透传：`REPO_HOST_PORT_INFO` 跳探测 + `http_proxy` 覆盖其它 HTTP 腿）：参数原样透传，`repo-vpn sync` / `repo-vpn upload -y .` 均可用；⚠ **勿设 `all_proxy`**（urllib 不支持 socks，会把 http 请求一起带崩）；借道属临时状态时只做这种可整段删的最小封装
- **「`git status -sb` 显示 behind origin/<分支> N」是设计内的**（本流水线基于 manifest 锁定 revision 提交），判 base 对不对只看「该 revision 是否等于 manifest 当前锁定值」；**上传通道验证不留痕**：真推一笔 → Gerrit Abandon → 本地回退（比 `repo upload -n` 更彻底）
- **反例**：`local_manifests` 把 manifest 的 `review` 改成 `ssh://` 求「根治探测」→ repo 明确拒绝（`fatal: remote origin already exists with different attributes`），且该文件在时**所有 repo 子命令一起挂**（`repo manifest`/`repo sync` 都报错），只能改团队 manifest
- 复现该探测**必须独立进程**：`urllib.request` 的全局 opener 首次调用即快照代理，同进程内改 env 无效（会得到「配了代理也不通」的假结论）→ 用 `env http_proxy=<proxy> python3 -c ...`
- 版本 1.2.2 → 1.2.3

## v1.2.2 (2026-09-29)

### Added

- 高频坑速查新增一条：`repo upload` 报 `urlopen error ... Connection timed out` —— review URL 的 HTTP `ssh_info` 探测由 Python urllib 发出，只认 `http_proxy`、不读 `~/.ssh/config`；内网（Ubuntu 哑客户端）必须借道，解 = `proxyon` 或 `REPO_HOST_PORT_INFO="<host> 29418"`（勿用 `REPO_IGNORE_SSH_INFO=1`）
- 新增「上传前置检查」小节：Change-Id 是否已在云端（rowCount 判据）、SSH 通 ≠ upload 通、`repo upload -n -y` dry-run 可先验不落 change
- 版本 1.2.1 → 1.2.2

## v1.2.0 (2026-08-18)

### Fixed（自包含化）

- **去除死链引用**：`gerrit-workflow` / `references/jenkins-link-parsing.md`（不存在的技能/文件）→ 高频坑速查自包含、Jenkins 链接解析内嵌说明、README 相关段改为自包含声明
- 版本 1.1.0 → 1.2.0

## v1.1.0 (2026-08-18)

- **ZCode 安装目标**：install.sh 支持 ZCode（探测 `~/.zcode` → 安装到 `~/.zcode/skills/gerrit-patch-flow`），README 补手动复制 ZCode 路径，发布页一键命令即可装到 ZCode

## v1.0.0 (2026-08-12)

- 初版：Gerrit 端到端流水线（xml 拉基线 → patch 合入 → 本地修改 → 只推一笔）
- 方案 C：fetch+reset 保持 hash 一致（替代 cherry-pick），解决整链重推/覆盖云端他人更新
- 云端链线性验证方法（merge-base --is-ancestor 全 YES 前提）
- 分叉 change rebase 处理（挂旧 ps 的 change → cherry-pick 到新主线，Change-Id 不变）
- Change-Id 规则卡（I+40hex、匹配机制表、amend 保留原 ID）
- 辅助脚本：gerrit_query.py（批量查 revision/parent）、verify_chain.py（链对齐验证）
- 来源：2026-08-10~12 多轮实证（17→24 change 重打、213266 ps2→ps5、213307 rebase）

## 1.2.1 (2026-08-28)

### Added

- install.sh 新增 pi 安装目标（探测 `~/.pi/agent` → 安装到 `~/.pi/agent/skills/<skill>`，pi 自动发现）
- 版本 1.2.0 → 1.2.1
