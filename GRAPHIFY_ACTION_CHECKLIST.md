# Graphify Setup - Final Action Checklist

## ✅ What's Done

- [x] Graphify installed (version 0.8.24)
- [x] Pre-commit hook created (`.githooks/pre-commit-graphify`)
- [x] Manual scripts created (`Update-Graphify.ps1`, `update-graphify.sh`)
- [x] GitHub Actions CI/CD integration (`.github/workflows/ci.yml`)
- [x] Documentation created (3 guides)
- [x] Git configured for graphify (`.gitignore` updated)

---

## 📋 Your To-Do List (Next 15 minutes)

### Step 1: Make PATH Permanent (5 min)

Choose **ONE** option:

#### Option A: PowerShell Profile (Recommended for daily use)
```powershell
# Open PowerShell profile
notepad $PROFILE

# Add this line at the end:
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"

# Save and restart PowerShell
```

#### Option B: System Environment Variables (One-time, all apps)
1. Press `Win + X` → Click "System"
2. → "Advanced system settings"
3. → "Environment Variables"
4. Under "User variables", click "New":
   - **Name**: `PATH`
   - **Value**: `C:\Users\amita\.local\bin`
5. Click OK, restart PowerShell

#### Option C: Test in current session only
```powershell
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
graphify --version
# Output: graphify 0.8.24
```

### Step 2: Enable Pre-commit Hook (2 min)

```powershell
# Enable git hooks directory
git config core.hooksPath .githooks

# Verify
git config core.hooksPath
# Output: .githooks
```

### Step 3: Test the Integration (3 min)

```powershell
# Add some changes
git add .

# Commit - hook will run automatically
git commit -m "test: verify graphify integration"

# You should see:
# [graphify-hook] Checking for Python file changes...
# [graphify-hook] Found X Python file(s) changed
# [graphify-hook] Updating knowledge graph...
# [graphify-hook] Knowledge graph updated ✓
```

### Step 4: (Optional) Set API Key (5 min)

For better semantic inference, set an LLM API key:

```powershell
# Option 1: Google Gemini (Free)
[Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-key-here", "User")

# Option 2: OpenAI
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key-here", "User")

# Option 3: Anthropic Claude
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key-here", "User")

# Get API keys from:
# - Google: https://aistudio.google.com/app/apikey
# - OpenAI: https://platform.openai.com/api-keys
# - Anthropic: https://console.anthropic.com/keys

# Restart PowerShell for env vars to take effect
```

---

## 🧪 Test Graphify After Setup

```powershell
# Make sure PATH is set
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"

# Navigate to project
cd e:\PRO\JIMxNik\jim_new

# Option 1: Quick update (AST-only, no API key needed)
graphify . --update --no-viz

# Option 2: Full update with inference (requires API key)
graphify . --force

# Option 3: Use the script
.\scripts\Update-Graphify.ps1
```

---

## 📖 Documentation Created

| File | Purpose |
|------|---------|
| `GRAPHIFY_INSTALLATION.md` | **← START HERE** Complete setup guide with all options |
| `GRAPHIFY_SETUP.md` | Detailed steps with CI/CD details |
| `GRAPHIFY_QUICK_START.md` | Quick reference for common commands |
| `.github/workflows/ci.yml` | GitHub Actions auto-update |
| `.githooks/pre-commit-graphify` | Auto-update on commit |
| `scripts/Update-Graphify.ps1` | Manual update for Windows |
| `scripts/update-graphify.sh` | Manual update for Linux/Mac |

---

## ✨ After Setup - How to Use

### Auto-Update (Happens Automatically)
```powershell
# Local: Every commit
git add .
git commit -m "feature: add new code"
# → Graph updates automatically

# Remote: Every push
git push origin main
# → GitHub Actions updates graph on CI/CD
```

### Manual Update
```powershell
# Quick update (fast)
.\scripts\Update-Graphify.ps1 -Quick

# Full rebuild
.\scripts\Update-Graphify.ps1 -Force

# Or via CLI
graphify . --update
```

### Query the Graph
```powershell
# Understand architecture
graphify query "how does ensemble prediction work?"

# Find relationships
graphify path "run_lstm" "ensemble_stacking"

# Explain concept
graphify explain "feature engineering"

# View report
type graphify-out/GRAPH_REPORT.md
```

---

## ✅ Verification Checklist

Run this to verify everything is set up:

```powershell
# 1. PATH is correct
graphify --version
# Output: graphify 0.8.24

# 2. Hook is enabled
git config core.hooksPath
# Output: .githooks

# 3. Can run graphify
cd e:\PRO\JIMxNik\jim_new
graphify . --update --no-viz
# Output: Building graph...

# 4. Graph exists
ls graphify-out/graph.json
# Output: File size in MB
```

---

## 🚨 Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| `graphify: command not found` | Add PATH: `$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"` |
| Hook not running | Check: `git config core.hooksPath` → Should be `.githooks` |
| Graph update fails | Use quick: `graphify . --update --no-viz` |
| LLM error | Set API key (see Step 4 above) or use `--no-viz` |

---

## 🎯 Summary

**Graphify is now:**
- ✅ Installed
- ✅ Configured for auto-update (pre-commit + CI/CD)
- ✅ Ready to use

**Your next steps:**
1. **Make PATH permanent** (5 min) - Pick Option A, B, or C
2. **Enable hook** (2 min) - `git config core.hooksPath .githooks`
3. **Test it** (3 min) - Make a commit
4. **Start using** - Queries, paths, explanations

**Documentation:**
- Read `GRAPHIFY_INSTALLATION.md` first
- Then `GRAPHIFY_QUICK_START.md` for commands

---

**Setup Time**: ~15 minutes
**Status**: ✅ Ready for next steps
**Last Updated**: May 29, 2026
