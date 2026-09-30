---
name: gerrit-patch-flow
description: Gerrit 端到端流水线 — xml 拉基线 → patch 合入 → 本地修改 → 只推一笔（方案C 保持hash）
version: 1.2.3
category: devops
metadata:
  agent:
    triggers: [拉patch, 打patch, 推patch, gerrit流水线, 只推一笔, 合入change, xml拉代码]
---

# Gerrit 端到端流水线

从零到推一笔的完整链路：**xml 拉基线 → gerrit patch 合入 → 本地修改 → 只推一笔**。
本 skill 是场景流水线（操作顺序）；通用操作细节（commit 格式/amend/具体坑）见下方「高频坑速查」与 `references/`。

## 角色边界（铁律）

- Agent 做：`git add/commit/amend`、cherry-pick/reset、准备推送分支
- **用户做：`repo upload` / `git push origin HEAD:refs/for/...`**——禁止 Agent 未经明确指令推送
- 用户说「repo upload」「推送」「upload」才执行推送

## 四步流水线

### Step 1: xml 拉基线

```bash
# 1.1 从 Jenkins 链接/xml 版本号拿 manifest 名（链接 URL 中 query 参数或 xml 内容里取 manifest 名）
# 1.2 repo init（真相源 = 各项目 project.conf；hm6502 系用 manifest-smart.xml）
repo init -u ssh://<gerrit_host>/manifest -b smart -m <manifest_xml>

# 1.3 对齐基线三步（丢弃本地 commit/修改/产物，100% 回 manifest 锁定 revision）
repo sync -l -d -f                       # 丢本地 commit（输出 discarding N commits）
repo forall -c 'git reset --hard'        # 清 tracked 修改
# 验证：python 解析 manifest revision vs 各仓 HEAD，mismatch=0
```

**⚠️ `git status -sb` 显示 `behind origin/m/smart N` 是设计内的，不是故障**：本流水线就是「基于 manifest 锁定 revision 提交」，
  所以本地分支停在 manifest 锁定值、落后分支 tip 几十笔都属正常（Gerrit 侧 change 的 parent 就是这个锁定 revision）。
   判 base 对不对只看一点：**该 revision 是否仍等于当前 manifest 给这个 project 锁定的值**（不是看 behind 计数）。
  **上传通道验证不留痕**：真推一笔 → Gerrit 上 Abandon → 本地回退到基线（比 `repo upload -n` 更彻底，`-n` 只是 `git push --dry-run`）。

**⚠️ repo start 复活旧分支陷阱**：`repo sync -d` 后直接 `repo start <旧名>` 会检出旧分支（旧 commit 复活）。必须先删旧分支再 start。

### Step 2: gerrit patch 合入

```bash
# 2.1 批量 query 全部 change 的最新 revision + parent（勿用旧会话记录！patchset 天天变）
for c in <change号列表>; do
  ssh -p 29418 <user>@<gerrit_host> gerrit query "change:$c" --format=JSON --current-patch-set
done
# 关键字段：number|status|currentPatchSet.revision|currentPatchSet.parents[0]

# 2.2 判定基线内 change（跳过）：merge-base --is-ancestor <rev> <基线sha> && echo IN_BASE
# 2.3 分析依赖链：parent = 另一 change 的 revision → 父子依赖，先打父
# 2.4 fetch 全部最新 revision（refs/changes/<后2位>/<change>/<ps>）
# 2.5 关键决策：cherry-pick 还是 reset？（见下）
```

### Step 3: 本地修改

```bash
git add <files> && git commit -m '[项目] [Message]<类型> 标题 ...'
# Change-Id 由 commit-msg hook 自动生成（I+40hex 必须合法）
# 追加改动用 git commit --amend --no-edit（保留 Change-Id → 推送后同 change 新 patchset）
```

### Step 4: 只推一笔（方案 C 核心）

**目标**：推送时只更新自己改的那个 change，不把整条链重推、不覆盖云端他人更新。

**原理**：gerrit 按 hash+Change-Id 匹配。链上 commit 的 hash 若 = 云端已有 revision（open change 当前 patchset）→ gerrit 识别为已知，**自动跳过不生成新 patchset**。cherry-pick 会生成新 hash → 整链重推（覆盖他人更新）。

```bash
# 4.1 验证云端主线线性：全部 revision 都是链尾 revision 的祖先
for rev in <全部revision>; do
  git merge-base --is-ancestor $rev <链尾rev> && echo YES || echo NO
done
# 全 YES = 线性，reset 一步到位；出现 NO = 有分叉 change，单独处理

# 4.2 reset 到链尾 revision（保持 hash 与云端完全一致，替代 cherry-pick！）
git reset --hard <链尾revision>
# 验证：全部 revision 都是 HEAD 祖先（merge-base --is-ancestor → 全 YES）

# 4.3 挂在旧 ps 上的 change（云端主链已前进但该 change 未跟随）→ rebase 到新主线
git cherry-pick <该change云端最新revision>
git log -1 --format='%b' HEAD | grep Change-Id   # 验证 Change-Id 仍是原 change 的（=推送更新而非新建）

# 4.4 推送（用户执行）——只更新目标 change，其余链上 commit 云端已识别跳过
cd <repo_root>/<subrepo> && repo upload --yes .
# 或：git push origin HEAD:refs/for/m/smart
```

## 验证清单

- [ ] 对齐后 mismatch=0（Step 1）
- [ ] 全部 change revision fetch 为最新 patchset（Step 2）
- [ ] 链上 commit hash = 云端 revision（`git merge-base --is-ancestor` 全 YES）
- [ ] 无冲突残留（`grep -rn "<<<<<<<" <目录>` 空）
- [ ] 推送前 commit message 格式逐 commit 检查
- [ ] 工作区干净（`git status --porcelain` 无 tracked 改动）

## 高频坑速查

| 坑 | 现象 | 解法 |
|----|------|------|
| cherry-pick 丢 hash | push 整链重推、覆盖云端他人更新 | fetch+reset 保持 hash 一致（方案 C）|
| patchset 号过期 | 打了旧版白干 | query currentPatchSet.number 再拼 ref |
| 宏缺括号 | `if (in_interrupt)` 恒真 | grep 宏名确认全部带 `()` |
| 遍历 kfree 错对象 | list 循环 free 新分配对象 | 审查 kfree 对象 = 遍历变量 |
| 批量漏打 | 中间冲突后静默跳过后续 change | 逐个核对 commit 数 + 特征 grep |
| repo upload 推整链 | 分支选择编辑器弹窗/旧分支默认选中 | `repo upload --br=<分支名>` 显式指定 |
| repo upload 报 `urlopen error ... Connection timed out` | `[FAILED] <proj> (<review_url>/: <urlopen error [Errno 110]>)`，SSH 却明明能通 | review URL 的 HTTP `ssh_info` 是 Python urllib 发的，**只认 `http_proxy`、不读 ~/.ssh/config**。内网必须借道：`proxyon` 后上传；或 `REPO_HOST_PORT_INFO="<host> 29418" repo upload -y .` 直接跳过该探测（勿用 `REPO_IGNORE_SSH_INFO=1`，会把推送退回 http） |

6. **入口全景（源码实证，`<repo_root>/.repo/repo/git_config.py` 的 `ReviewUrl()`）**：review URL 判定只有四个分支，按顺序
   `REVIEW_CACHE` → **`REPO_HOST_PORT_INFO` env** → review URL 的 scheme 为 `sso:`/`ssh:`（直接采信，**零探测**）→ `REPO_IGNORE_SSH_INFO`（退回 http，**禁用**）→ 兜底才 `GET <review>/ssh_info`。
   哑客户端（无 http_proxy、无内网通路）只有前两条可用：`http_proxy=<跳板> repo upload .` 或 `REPO_HOST_PORT_INFO="<host> <port>" repo upload .`。
   ⚠️ **不要试图用 local_manifests 把 manifest 的 `review` 改成 `ssh://`**（看似能“根治”掉这次探测）——
   repo 明确拒绝：`fatal: remote origin already exists with different attributes`（实证），且该文件一放进去
   **所有 repo 子命令全部报错**（`repo manifest` / `repo sync` 一起挂，不只是 upload）。改 review URL 只能改团队 manifest，非本机可控。
7. 两种可用解法的取舍：`http_proxy=<跳板>` 是多走一条 HTTP 腿（依赖跳板侧能判 DIRECT + 远端解析），作用域限该进程；
   `REPO_HOST_PORT_INFO` 只替换一个本机常量、网络行为零改变（推送照旧走 ssh_config），代价是硬编码 host/port
   （Gerrit 换 ssh 端口需同步改；改错时在推送阶段报错，不会静默走错）。两者都**依赖跳板在线**——
   ssh 推送本身经 ProxyCommand 借道，跳板是硬前提。日常推荐的封装（**通用透传**，把 `repo` 换成 `repo-vpn`；两个 env 都给：`REPO_HOST_PORT_INFO` 跳过探测、
   `http_proxy` 覆盖其他可能的 HTTP 腿；单进程作用域，不挂全局）：
   `repo-vpn() { REPO_HOST_PORT_INFO="<host> <port>" http_proxy="$LAN_PROXY" https_proxy="$LAN_PROXY" repo "$@"; }`
   ⇒ 参数**原样透传**，`repo-vpn sync` / `repo-vpn upload -y .` 都可用。⚠ **勿设 `all_proxy`**：
   urllib 不支持 socks 代理，会把 http 请求一起带崩（`all_proxy` 是 curl 一族的入口，别塞给 repo）。
   ⚠ 借道只是临时状态时（如内网服务器即将迁入同一局域网），**只做这种“一行函数、与借道配置同块、可整段删”的最小封装**，
   不要写启动脚本或挂全局 `http_proxy`——界线是负债大小，不是时间长短；迁移后改回原生 `repo upload` 并删掉该行。
8. **只有 `repo upload` 需要这层封装**：全树只有 `project.py` 的 `UploadForReview` 调用 `ReviewUrl()`（HTTP 探测只活在这里）；
   `repo init` / `repo sync` 只碰 **fetch URL**（manifest 仓、各工程 remote、launcher 自拉工具均为 `ssh://`）
   ⇒ 天然走 ssh_config 的 ProxyCommand，**无需任何环境变量**（实测不带代理变量 ls-remote 均通）。
   例外：URL 写成 `https://…` 或走 `--smart-sync`/manifest server 这类 HTTP 入口时才需要代理。
9. Gerrit 上工程名以 manifest 的 `name` 为准（如 `m/smart/test/ostest`）；`git ls-remote ssh://<host>:29418/<name>` 报
   `project not found` 是路径写错、不是链路故障。

## 上传前置检查（本机=Ubuntu 哑客户端）

1. `ssh -p 29418 <user>@<gerrit> gerrit query --format=JSON change:<Change-Id>` → rowCount=0 说明该笔**还没上去**（正常）
2. SSH 能通 ≠ upload 能通：urllib 的 HTTP 探测不走 ssh_config（见上表）
3. 想先验证不真推：`repo upload -n -y --br=<分支> .`（dry-run，实测不落 change）
4. 不动环境变量也能通（推荐，符合「默认直连 + 按域名显式送」）：
   `REPO_HOST_PORT_INFO="<gerrit_host> 29418" repo upload -y .` —— 跳过 ssh_info 探测，推送仍走 ssh_config 的 ProxyCommand。
5. 复现/验证这个探测<b>必须用独立进程</b>：`urllib.request` 的全局 opener 会被首次调用缓存（`ProxyHandler` 在 build 时快照代理），
   同进程内先无代理跑一次再 export http_proxy，第二次仍走旧的 no-proxy opener ⇒ 会得到「配了代理也不通」的假结论。
   正确姿势：`env http_proxy=<proxy> python3 -c "import urllib.request; ..."`，一次进程一个配置。

## 支持文件

- `references/change-id-rules.md` — Change-Id 规则与 gerrit 匹配机制
- `references/keep-hash-aligned.md` — 方案 C：保持 hash 一致（2026-08-12 实证）
- `scripts/gerrit_query.py` — Gerrit change 批量查询（最新 revision + parent + status）
- `scripts/verify_chain.py` — 校验本地链与云端 revision 对齐（方案 C 校验）
- `CHANGELOG.md` — 版本历史
