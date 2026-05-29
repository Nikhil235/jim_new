# Graphify Setup Guide for JIM Trading System

## Quick Start

Graphify is a knowledge graph tool that maps your codebase structure, detects relationships, and finds architectural patterns. It requires an LLM API key for semantic inference (optional but recommended for better results).

## Installation ✅ COMPLETE

Graphify is now installed via `uv`:
- **Version**: 0.8.24
- **Location**: `C:\Users\amita\.local\bin\graphify`
- **Status**: ✅ Ready to use

## Step 1: Configure PATH (Do This First)

The graphify executable is at `C:\Users\amita\.local\bin`. Add it to your PATH:

### Option A: Temporary (Current PowerShell Session Only)
```powershell
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
graphify --version
# Output: graphify 0.8.24
```

### Option B: Permanent (Recommended)

**Via PowerShell Profile** (for all future sessions):
```powershell
# Open your PowerShell profile
notepad $PROFILE

# Add this line at the end:
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"

# Save and reload PowerShell
```

**Via System Environment Variables** (GUI):
1. Press `Win + X` → "System" 
2. "Advanced system settings" → "Environment Variables"
3. Click "New" under User variables:
   - **Name**: `PATH`
   - **Value**: `C:\Users\amita\.local\bin`
4. Click OK, then restart PowerShell

**Verify**:
```powershell
graphify --version
# Should output: graphify 0.8.24
```

---

## Step 2: Configure LLM API Key (REQUIRED for Graphify to Work)

**Important**: Graphify requires an LLM API key to function. Without it, you'll get:
```
error: no LLM API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY...
```

**Three Options**:

### ✅ Option A: Google Gemini (FREE - Recommended)
```powershell
# Create .env file in project root
$env:GOOGLE_API_KEY = "your-gemini-api-key"

# Or add to .env file
echo 'GOOGLE_API_KEY=your-key' > .env
```

### Option B: OpenAI (Claude/GPT)
```powershell
$env:ANTHROPIC_API_KEY = "your-claude-api-key"
# OR
$env:OPENAI_API_KEY = "your-openai-api-key"
```

### Option C: Other Providers
```powershell
# Kimi
$env:MOONSHOT_API_KEY = "your-kimi-key"

# DeepSeek
$env:DEEPSEEK_API_KEY = "your-deepseek-key"
```

**To get a free API key**:
- **Google Gemini**: Visit https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/keys

---

## Step 3: Enable Pre-commit Hook

The hook will auto-update your knowledge graph before each commit.

```powershell
# 1. Configure git to use .githooks
git config core.hooksPath .githooks

# 2. Verify it's set
git config core.hooksPath
# Output: .githooks

# 3. Test it
git add .
git commit -m "test: verify graphify hook"
```

**Expected output**:
```
[graphify-hook] Checking for Python file changes...
[graphify-hook] Found X Python file(s) changed
[graphify-hook] Updating knowledge graph...
[graphify-hook] Knowledge graph updated ✓
```

---

## Step 4: Test Graphify on Your Project

```powershell
# Set PATH and navigate to project
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
cd e:\PRO\JIMxNik\jim_new

# Option 1: Quick update (AST-only, no LLM needed)
graphify . --update --no-viz

# Option 2: Full analysis (with LLM inference - requires API key)
graphify . --force

# View the report
type graphify-out/GRAPH_REPORT.md | Select-Object -First 50
```

**Without API key**:
- ✅ AST extraction (functions, classes, imports)
- ❌ Semantic inference (relationships between distant concepts)
- ❌ Community clustering (grouping related code)

**With API key**:
- ✅ Everything above PLUS:
- ✅ Semantic inference (what code modules conceptually relate to)
- ✅ Community clustering (automatic grouping of related features)
- ✅ Better query results

---

## Step 5: Use Graphify Commands

Once installed and configured:

```powershell
# Query the graph
graphify query "how does ensemble prediction work?"

# Find relationships
graphify path "run_lstm" "ensemble_stacking"

# Explain a concept
graphify explain "feature engineering"

# Update graph after code changes
graphify . --update

# Full rebuild with clustering
graphify . --force --wiki
```

---

## Using the Manual Update Scripts

### Windows PowerShell
```powershell
# Quick update
.\scripts\Update-Graphify.ps1

# Force rebuild
.\scripts\Update-Graphify.ps1 -Force

# Quick (AST-only)
.\scripts\Update-Graphify.ps1 -Quick
```

### Linux/Mac Bash
```bash
# Quick update
./scripts/update-graphify.sh

# Force rebuild
./scripts/update-graphify.sh --force
```

---

## How It Works

### Local Development (Pre-commit Hook)
1. You make code changes
2. Run `git commit`
3. Hook automatically runs `graphify . --update`
4. Graph updates with your changes
5. Changes auto-staged and commit proceeds

### CI/CD Pipeline (GitHub Actions)
1. Push to main/develop
2. GitHub Actions triggers `graphify-update` job
3. Full graph rebuild with `--force`
4. Updates committed back to branch
5. Tests run with fresh graph

### Manual Updates
Use `Update-Graphify.ps1` or `update-graphify.sh` anytime

---

## Configuration Files

| File | Purpose |
|------|---------|
| `graphify-out/graph.json` | Core graph (track in git) |
| `graphify-out/GRAPH_REPORT.md` | Human-readable report (track in git) |
| `graphify-out/manifest.json` | File metadata (track in git) |
| `graphify-out/cache/` | Ignored in git (rebuild fast) |
| `.githooks/pre-commit-graphify` | Auto-update hook |
| `scripts/Update-Graphify.ps1` | Manual update script |

---

## Troubleshooting

### "graphify: command not found"
```powershell
# Solution 1: Add to PATH temporarily
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"

# Solution 2: Update PowerShell profile permanently
notepad $PROFILE
# Add: $env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
```

### "no LLM API key found"
```powershell
# Option 1: Set API key
$env:GOOGLE_API_KEY = "your-gemini-key"

# Option 2: Use AST-only (no LLM)
graphify . --update --no-viz

# Option 3: Add to .env file
echo 'GOOGLE_API_KEY=your-key' > .env
```

### Graph update is slow
```powershell
# Use quick AST-only update (no inference)
graphify . --update

# Or skip inference entirely
graphify . --update --no-viz
```

### Hook not running
```powershell
# Check hook is enabled
git config core.hooksPath
# Should output: .githooks

# Force enable
git config core.hooksPath .githooks

# Check hook file exists
ls .githooks\pre-commit-graphify
```

### Skip hook for a commit
```powershell
git commit --no-verify -m "quick commit, skip graph update"
```

---

## Verification Checklist

- [x] Graphify installed (`graphify --version` works)
- [ ] PATH configured (can run `graphify` from anywhere)
- [ ] LLM API key set (optional but recommended)
- [ ] Pre-commit hook enabled (`git config core.hooksPath` = `.githooks`)
- [ ] Tested with `git commit`

---

## Next Steps

1. **Add to PATH** permanently (Step 1 Option B)
2. **Set API key** if you have one (Step 2)
3. **Test the hook** (Step 3)
4. **Run initial graph** (Step 4)
5. **Read GRAPH_REPORT.md** to understand architecture

---

## Quick Commands Reference

```powershell
# Setup
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
git config core.hooksPath .githooks

# Update graph
graphify . --update
graphify . --force

# Query
graphify query "ensemble voting"
graphify path "feature_engineering" "ensemble"

# Manual update
.\scripts\Update-Graphify.ps1
```

---

## Questions?

See:
- `graphify --help` — Full CLI reference
- `graphify-out/GRAPH_REPORT.md` — Architecture overview
- `GRAPHIFY_QUICK_START.md` — Quick reference

---

**Status**: ✅ Graphify installed and ready
**Next Action**: Add to PATH permanently
**Last Updated**: May 29, 2026
