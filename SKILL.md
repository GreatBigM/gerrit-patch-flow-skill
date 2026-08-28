---
name: gerrit-patch-flow
description: Gerrit 端到端流水线 — xml 拉基线 → patch 合入 → 本地修改 → 只推一笔（方案C 保持hash）
version: 1.2.1
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

## 支持文件

- `references/` — 详细参考（方案 C 全流程、Change-Id 规则）
- `scripts/` — 辅助脚本
- `CHANGELOG.md` — 版本历史
