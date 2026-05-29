

# Graphify Quick Reference

## One-Time Setup (5 minutes)

```powershell
# 1. Install (choose one method)
# Option A: Via uv (recommended)
uv tool install graphifyy

# Option B: Via pip
pip install graphifyy

# Verify: graphify --version

# 2. Enable pre-commit hook
git config core.hooksPath .githooks

# 3. Test it
git add .
git commit -m "test: verify graphify"
```

**Expected output**: `[graphify-hook] Knowledge graph updated ✓`

---

## Common Commands

### Manual Graph Update

**Windows PowerShell**:
```powershell
# Quick update
.\scripts\Update-Graphify.ps1

# Force rebuild
.\scripts\Update-Graphify.ps1 -Force
```

**Linux/Mac Bash**:
```bash
# Quick update
./scripts/update-graphify.sh

# Force rebuild
./scripts/update-graphify.sh --force
```

### Query the Graph

```bash
# "How does X work?"
graphify query "ensemble prediction voting"

# "What calls X?"
graphify path "run_lstm" "run_ensemble"

# "Explain X"
graphify explain "feature_engineering"
```

---

## What Gets Auto-Updated?

✅ **Local commits** (via pre-commit hook)
- Runs on every `git commit`
- Only updates if Python files changed
- Takes <5 seconds
- Auto-stages `graphify-out/` changes

✅ **Remote (CI/CD)** (via GitHub Actions)
- Runs on push to main/develop
- Runs on pull requests
- Full update with inference
- Commits back to branch

---

## File Locations

| File | Purpose | Track in Git |
|------|---------|--------------|
| `graphify-out/graph.json` | Core graph data | ✅ Yes |
| `graphify-out/GRAPH_REPORT.md` | Human-readable report | ✅ Yes |
| `graphify-out/manifest.json` | Metadata & hashes | ✅ Yes |
| `graphify-out/cache/` | AST cache | ❌ No (ignored) |
| `.githooks/pre-commit-graphify` | Hook script | ✅ Yes |
| `scripts/Update-Graphify.ps1` | Manual update script | ✅ Yes |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Hook not running | `git config core.hooksPath` should return `.githooks` |
| `graphify: command not found` | `pip install graphify` |
| Graph update slow | Run `.\scripts\Update-Graphify.ps1 -Quick` (AST-only) |
| Graph is stale | Run with `--force` flag to rebuild |
| Skip hook for this commit | `git commit --no-verify -m "message"` |

---

## Tips

- 📖 Read `graphify-out/GRAPH_REPORT.md` for architecture overview
- 🔍 Use `graphify query` before refactoring large modules
- 📍 Use `graphify path A B` to understand dependencies
- 💾 Always commit the updated graph (helps team)
- ⚡ Local hook uses AST-only (fast), CI uses full update (comprehensive)

---

**Setup Guide**: See `GRAPHIFY_SETUP.md` for detailed instructions
