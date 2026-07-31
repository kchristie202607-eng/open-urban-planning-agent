# 提交操作手册（SUBMIT_GUIDE）

本手册把 `repo_root_drafts/` 的内容落地到 GitHub 仓库 `kchristie202607-eng/open-urban-planning-agent`，
并完成 Codex 开源基金申请提交。**所有命令需在具有仓库写入权限的本地环境中由维护者执行；本 Agent 不代为推送。**

## 前置条件

- 本地已 `git clone` 该仓库，且 `git remote -v` 指向正确。
- 已安装 Git 并能向 GitHub 推送（已配置 SSH 或 PAT）。
- 已将 `SECURITY.md` 与 `CODE_OF_CONDUCT.md` 中的 `maintainer@example.com` 替换为真实联系邮箱。

## 步骤 1 — 复制仓库根文件

```bash
# 在仓库根目录执行（假设本包位于 ../OUPAP_Codex_Fund_Application）
cp -r OUPAP_Codex_Fund_Application/repo_root_drafts/.  ./

# 确认点文件已复制（.gitignore / .github 为隐藏项）
ls -a | grep -E '^\.(gitignore|github)$'
```

## 步骤 2 — 确认无私有内容被跟踪

```bash
git add -A -n        # 先 dry-run，确认无 data/ output/ project_state/ backups/ 出现
git status
```

若 `git status` 中出现私有目录，检查 `.gitignore` 是否生效，必要时 `git rm --cached -r <dir>`。

## 步骤 3 — 提交并推送

```bash
git add -A
git commit -m "chore: add open-source governance, CI, and templates (Apache-2.0)"
git push origin main
```

## 步骤 4 — 开启 CI

- 进入仓库 **Settings → Actions → General**，确认 "Allow all actions"。
- 推送后到 **Actions** 标签确认 `ci.yml` 跑绿（隐私护栏通过）。

## 步骤 5 — （可选）同步申请包元文件

将 `WORK_LOG.md`、`TASKS.md`、`CHANGELOG.md`、`docs/fund-readiness.md` 复制进仓库根或保留在 `OUPAP_Codex_Fund_Application/` 子目录（维护者决定）。

## 步骤 6 — 提交基金申请

1. 打开 **Codex for Open Source** 申请入口。
2. 填写仓库 URL：`https://github.com/kchristie202607-eng/open-urban-planning-agent`
3. 引用 `FUND_APPLICATION/codex_application.md` 作为申请正文，`technical_overview.md` 作为技术说明。
4. 在 `WORK_LOG.md` 记录提交确认编号与日期。

## 合规红线（全程遵守）

- ❌ 不提交任何客户数据、规划项目、GIS 文件、卫星影像、私有知识库或凭证。
- ✅ 仅使用合成 / 公开信息与项目文档。
- ✅ CI 隐私护栏会在出现私有路径时失败，作为最后一道闸。
