# Publish codex-mem to GitHub

## Prerequisites

- A GitHub repo: `<YOUR_ORG_OR_USER>/codex-mem`
- A PAT with repo write permission

## 1) Create repo (choose one)

### Option A: Web UI
Create `https://github.com/new` with name `codex-mem` under org/user `<YOUR_ORG_OR_USER>`.

### Option B: API (with PAT)

```bash
export GH_AUTH_TOKEN='<AUTH_CREDENTIAL>'
curl -sS -X POST https://api.github.com/user/repos \
  -H "Authorization: Bearer ${GH_AUTH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -d '{"name":"codex-mem","private":false}'
```

## 2) Push current local branch

```bash
cd /ABS/PATH/codex-mem
git remote set-url origin https://github.com/<YOUR_ORG_OR_USER>/codex-mem.git
# recommended: use PAT once then store by credential helper
git push -u origin codex/init
```

## 3) If HTTPS prompts fail, use PAT in URL once

```bash
cd /ABS/PATH/codex-mem
git push -u https://<GITHUB_USERNAME>:<AUTH_CREDENTIAL>@github.com/<YOUR_ORG_OR_USER>/codex-mem.git codex/init
```

## 4) Open PR (optional)

```bash
# if main exists and you want PR from codex/init
# https://github.com/<YOUR_ORG_OR_USER>/codex-mem/compare/main...codex/init
```
