# CHANGELOG

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
