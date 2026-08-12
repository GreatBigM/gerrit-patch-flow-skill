# Change-Id 规则与 gerrit 匹配机制

## Change-Id 格式

- 必须 `I` + 40 位 hex（如 `I110f1e2805a37d6339ddd7f8d96d45ab3d090bf1`）
- 非法值（`Ie2a8800modify20260810`）会被 gerrit 拒绝
- 由 commit-msg hook 自动生成；`git commit --amend -m '...'` 会重生成 → **显式保留原 Change-Id**

## 推送匹配机制（核心认知）

| 情况 | gerrit 行为 |
|------|------------|
| commit hash = 云端已有 revision（open change 当前 patchset） | **跳过**（已知 commit，不生成新 patchset）|
| Change-Id 匹配已有 change，hash 不同 | 更新该 change 为新 patchset |
| Change-Id 全新 | 创建新 change |
| Change-Id 匹配已合入（closed）change | 整个推送被拒（change closed）|

## 关键规则

- `git commit --amend` → 保留 Change-Id → 推送后同 change 新 patchset（不是新 change）
- `git rebase` → 新 commit 新 Change-Id → 推送后**新 change**（不要用于已推送的 commit）
- 推送前逐 commit 检查 message 格式 + Change-Id 合法性

## 保留原 Change-Id 的 amend

```bash
CID=$(git show --format="%B" -s HEAD | grep "^Change-Id:")
git commit --amend -m '...message...'"$CID"
# 或：sed 去掉 Change-Id 行让 hook 重新生成合法值
git log -1 --format='%B' HEAD | sed '/^Change-Id:/d' > /tmp/msg.txt
git commit --amend -F /tmp/msg.txt   # hook 发现无 Change-Id → 生成 I+40hex
```
