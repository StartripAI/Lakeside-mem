# Installation

## Requirements

- Python 3.10+
- SQLite with FTS5 support
- Optional: Codex CLI for MCP registration

## Clone

```bash
git clone https://github.com/<YOUR_ORG_OR_USER>/lakeside-mem.git
cd lakeside-mem
```

## Initialize Local Memory Store

```bash
bash Scripts/lakeside_mem.sh init --project demo
```

## Optional: Start Local Web Viewer

```bash
bash Scripts/lakeside_mem.sh web --project-default demo --host 127.0.0.1 --port 37777
```

Open:
- `http://127.0.0.1:37777/`

## Optional: Register MCP in Codex

```bash
codex mcp add lakeside-mem -- python3 /ABS/PATH/lakeside-mem/Scripts/codex_mem_mcp.py --root /ABS/PATH/lakeside-mem --project-default demo
```

## Verify

```bash
python3 Scripts/codex_mem_smoketest.py --root .
```

## Optional: Launch Ops Toolkit Commands

```bash
bash Scripts/lakeside_mem.sh load-demo-data --reset
bash Scripts/lakeside_mem.sh make-gifs
bash Scripts/lakeside_mem.sh validate-assets --check-readme --strict
bash Scripts/lakeside_mem.sh social-pack --version v0.3.0
```

Expected output includes:
- `"ok": true`
- non-zero search results
- verified MCP tools
- verified web endpoints
