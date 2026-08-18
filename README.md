# gerrit-patch-flow

Gerrit 端到端流水线 skill — **xml 拉基线 → gerrit patch 合入 → 本地修改 → 只推一笔**。

解决核心痛点：cherry-pick 打 patch 后 `repo upload` 会整链重推、覆盖云端他人更新的问题。方案 C（fetch+reset 保持 hash 一致）是社区标准解法。

## 安装

### 方式 1：一键脚本（推荐）

```bash
curl -fsSL https://gitee.com/GreatBigM/gerrit-patch-flow-skill/raw/main/install.sh | bash
```

等价于手动复制，不经过安全扫描。重复执行 = 升级（自动备份旧版到 `.bak.<时间戳>`）。

### 方式 2：手动复制

```bash
git clone --depth 1 https://gitee.com/GreatBigM/gerrit-patch-flow-skill.git /tmp/gpp-skill
cp -r /tmp/gpp-skill/references /tmp/gpp-skill/scripts /tmp/gpp-skill/SKILL.md /tmp/gpp-skill/CHANGELOG.md ~/.hermes/skills/gerrit-patch-flow/   # Hermes
cp -r /tmp/gpp-skill/references /tmp/gpp-skill/scripts /tmp/gpp-skill/SKILL.md /tmp/gpp-skill/CHANGELOG.md ~/.zcode/skills/gerrit-patch-flow/   # ZCode
```

### 方式 3：GitHub 镜像（海外备选）

```bash
curl -fsSL https://raw.githubusercontent.com/GreatBigM/gerrit-patch-flow-skill/main/install.sh | bash
```

## 依赖

| 依赖 | 必需 | 说明 |
|------|------|------|
| repo + git | ✓ | repo 工作区管理 |
| gerrit ssh 访问 | ✓ | `ssh -p 29418 <user>@<gerrit_host>`（免密配置）|

## 使用

对 AI 说"拉 patch / 打 patch / 只推一笔"，或加载本 skill 按四步流程执行：

1. **xml 拉基线**：repo init + 对齐三步（sync -l -d -f + reset --hard）
2. **gerrit patch 合入**：批量 query 最新 revision → fetch → 依赖序 reset/cherry-pick
3. **本地修改**：commit + Change-Id（hook 生成）
4. **只推一笔**：方案 C（保持 hash 一致）→ push 只更新目标 change

## 内容

- `SKILL.md` — 四步流水线 + 验证清单 + 坑速查
- `references/keep-hash-aligned.md` — 方案 C 完整流程（2026-08-12 实证）
- `references/change-id-rules.md` — Change-Id 规则与 gerrit 匹配机制
- `scripts/gerrit_query.py` — 批量查 change 最新 revision/parent
- `scripts/verify_chain.py` — 本地链与云端对齐验证
- `CHANGELOG.md` — 版本历史

## 相关

- 通用 gerrit 操作细节（commit 格式/amend/坑）已内嵌本 skill「高频坑速查」与 `references/`——本 skill 自包含，不依赖外部技能
