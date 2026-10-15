# 方案 C：保持 hash 一致（2026-08-12 实证）

## 问题场景

本地 cherry-pick 打了一串 change（A,B,C）再加新 commit D，`repo upload` 会把 A,B,C,D **全部** push，gerrit 按 Change-Id 把每个都更新为新 patchset——**若 B 在云端已被别人更新（新 patchset），本地旧版 B 的 push 会覆盖别人的新版**。

## 根因

cherry-pick 生成**新 commit hash**（与云端原 revision 不同）→ gerrit 视为新内容 → 整链重推。这是 gerrit 设计特性（hash=身份），无开关可跳过。

## 解法（社区标准，官方文档 + SO/DeepWiki/知乎一致）

**打 patch 用 fetch + reset（不 cherry-pick）**，保持本地链 hash 与云端 revision 一致：

```bash
# 打 patch 正确姿势
git fetch origin refs/changes/<后2位>/<change>/<ps>
git reset --hard <revision>        # 直接落在云端 revision 上，hash 不变
# 新改动 D 用正常 commit 追加
```

push 时链上 commit 的 hash 若 = 云端已有 revision（open change 的当前 patchset），gerrit 识别为**已知 commit 自动跳过**，只产生真正新 commit（D）的 change。一次对齐长期干净。

## 完整执行流程（24 change 重打实证）

```bash
# ① 批量 query 全部 change 的最新 revision + parent
for c in <change号列表>; do
  ssh -p 29418 <user>@<gerrit_host> gerrit query "change:$c" --format=JSON --current-patch-set \
    | jq -r '"\(.number)|ps\(.currentPatchSet.number)|\(.currentPatchSet.revision)|parent=\(.currentPatchSet.parents[0])"'
done

# ② fetch 全部最新 revision（refs/changes/<后2位>/<change>/<ps>）

# ③ 验证云端主线线性（关键前提！）
for rev in <全部revision>; do
  git merge-base --is-ancestor $rev <链尾revision> && echo "$rev YES" || echo "$rev NO"
done
# 全部 YES = 云端链线性，reset 一步到位；NO = 有分叉（如 213307 挂旧 ps4），单独处理

# ④ reset 到链尾 revision
git reset --hard <链尾revision>
# 验证：for rev in <全部>; do merge-base --is-ancestor $rev HEAD && echo -n . || echo -n X; done

# ⑤ 挂在旧 ps 上的 change → cherry-pick 其内容 rebase 到新主线
git cherry-pick <该change云端最新revision>
git log -1 --format='%b' HEAD | grep Change-Id   # Change-Id 仍是原 change = 推送更新而非新建
```

## 判别信号

- 本地链 commit hash ≠ 云端 revision（cherry-pick 过）→ 推整链必然重推全部
- 云端某 change 被他人更新：`gerrit query change:<N> --format=JSON --current-patch-set` 对比本地 commit 内容
- cherry-pick 输出 "Auto-merging <某文件>" → 基线与云端树有差异，检查基准

## 备选（单次）

`git push origin <sha>:refs/for/<branch>` 只推指定 commit（repo upload 粒度是整个 HEAD 链，git push 可指定 sha；前提 parent 已在云端）。
