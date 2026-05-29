# Graphify Integration Guide

This document explains how to use the automated graphify knowledge graph integration in the JIM trading system.

## What is Graphify?

Graphify is a code analysis tool that:
- Maps code structure (functions, classes, imports, dependencies)
- Detects relationships between modules
- Identifies code communities (clusters of related functionality)
- Enables smart semantic search across the codebase

**Benefits for JIM**:
- Fast architecture understanding (10-20x faster than grep/manual search)
- Impact analysis before refactoring
- Dead code detection
- Developer onboarding
- Automatic documentation

## Setup (One-time)

### 1. Install Graphify

Graphify is a knowledge graph tool developed by Andrej Karpathy. It builds persistent code graphs with community detection.

**Recommended: Use `uv` (fastest)**

```powershell
# Via uv (recommended - fastest)
uv tool install graphifyy

# Verify installation
graphify --version
graphify --help
```

**Alternative: Via pip**

```bash
# If uv is not available, use pip
pip install graphifyy

# Verify
graphify --version
```

**Troubleshooting**:
- If `graphify` command not found, try `python -m graphify` instead
- On Windows, you may need to restart PowerShell after installation
- Ensure Python 3.11+ is available

### 2. Enable Pre-commit Hook (Local Development)

The pre-commit hook automatically updates the graph before each commit.

```bash
# Enable git hooks directory
git config core.hooksPath .githooks

# Make hook executable (Linux/Mac)
chmod +x .githooks/pre-commit-graphify

# Verify it's working
git hooks --list
```

**Note for Windows users**: Git on Windows automatically executes hooks in `.githooks/` if you've set the config above.

### 3. Verify Setup

Make a small code change and try committing:

```bash
git add .
git commit -m "test: verify graphify hook"
```

You should see output like:
```
[graphify-hook] Checking for Python file changes...
[graphify-hook] Found X Python file(s) changed
[graphify-hook] Updating knowledge graph...
[graphify-hook] Knowledge graph updated ✓
```

## Usage

### Automatic Updates

The graph auto-updates in two ways:

#### 1. **Local (Before Every Commit)**
The pre-commit hook triggers automatically:
- Runs on Python file changes only
- Uses AST-only update (fast, <5 seconds)
- No API cost
- Updates graphify-out/ and stages it

#### 2. **CI/CD (After Every Push)**
GitHub Actions triggers on push/PR:
- Runs full `graphify update .` with `--force` flag
- Commits updated graph back to repository
- Available for all team members to use

**Commit message**: `docs: auto-update knowledge graph [skip ci]`

### Manual Updates

If you need to manually update the graph:

#### On Windows (PowerShell):
```powershell
# Full update
.\scripts\Update-Graphify.ps1

# Force full rebuild
.\scripts\Update-Graphify.ps1 -Force

# Quick AST-only
.\scripts\Update-Graphify.ps1 -Quick
```

#### On Linux/Mac (Bash):
```bash
# Full update
./scripts/update-graphify.sh

# Force full rebuild
./scripts/update-graphify.sh --force

# Quick AST-only
./scripts/update-graphify.sh --quick
```

### Querying the Graph

Once the graph is updated, you can query it:

```bash
# Semantic search
graphify query "How does ensemble prediction work?"

# Find relationships between entities
graphify path "run_lstm" "run_ensemble"

# Explain a concept
graphify explain "ensemble_stacking"
```

## Graph Structure

The knowledge graph is stored in `graphify-out/`:

```
graphify-out/
├── graph.json                 # Core graph data (10k+ nodes)
├── GRAPH_REPORT.md           # Human-readable analysis
├── manifest.json             # File metadata & hashes
├── cache/                    # (ignored in git) AST cache
│   └── ast/
└── .graphify_*               # (ignored in git) Internal files
```

### Key Statistics

```
Nodes: 10,572 (code entities: functions, classes, modules)
Edges: 17,445 (relationships: imports, calls, dependencies)
Communities: 867 (functional clusters)
Files: 239
Extraction: 88% direct, 12% inferred
```

## Tips & Best Practices

### 1. **Commit the Graph**
Always commit `graphify-out/graph.json` and `GRAPH_REPORT.md`. This lets:
- Team members see architecture without building locally
- CI artifacts track graph evolution
- Analysis tools access the graph

### 2. **Ignore Large Refactors**
If you rename 20+ functions, the graph update might take longer:
```bash
# Skip hook for this commit
git commit --no-verify -m "refactor: rename model classes"

# Then manually update after commit
./scripts/Update-Graphify.ps1 --force
git add graphify-out/
git commit -m "docs: update graph after refactor"
```

### 3. **Use for Impact Analysis**
Before big changes:
```bash
# Find all callers of a function
graphify path "old_function" "main"

# Understand dependencies
graphify query "What modules import from src/models/?"

# Find dead code
graphify query "unused functions"
```

### 4. **Share Query Results**
```bash
# Save graph query to document
graphify query "ensemble voting logic" > architecture-notes.txt

# Use in pull requests as architecture proof
```

## Troubleshooting

### Hook not running?

```bash
# Verify hook is enabled
git config core.hooksPath

# Should output: .githooks

# Check hook exists
ls -la .githooks/pre-commit-graphify  # Linux/Mac
dir .githooks\pre-commit-graphify     # Windows

# Make hook executable (Linux/Mac)
chmod +x .githooks/pre-commit-graphify
```

### Graph update slow?

```bash
# Use quick update (AST-only, no inference)
./scripts/Update-Graphify.ps1 -Quick

# Or skip hook for this commit
git commit --no-verify -m "message"
```

### Graphify not installed?

```bash
pip install graphify

# Verify
graphify --version
```

### Graph is stale?

```bash
# Force rebuild from scratch
./scripts/Update-Graphify.ps1 -Force

# Or via CLI
graphify update . --force
```

## CI/CD Pipeline Details

The GitHub Actions workflow (``.github/workflows/ci.yml``) includes:

1. **graphify-update job** (runs first)
   - Installs graphify
   - Updates graph
   - Commits changes back to PR/branch
   
2. **type-check-and-test job** (depends on graphify-update)
   - Runs after graph is updated
   - Ensures code still passes type checking
   - Runs all tests

This ensures the graph is always fresh before running the expensive type-check and test steps.

## Graph Refresh Schedule

- **Local**: Before every commit (via pre-commit hook)
- **CI/CD**: After every push to main/develop
- **Manual**: Anytime via `Update-Graphify.ps1` / `update-graphify.sh`

**Update frequency**: Graphs built in ~2-5 seconds (AST-only)
**Full rebuild**: ~10-15 seconds (with inference)

## Next Steps (Recommended)

1. ✅ **Install graphify** - `pip install graphify`
2. ✅ **Enable hook** - `git config core.hooksPath .githooks`
3. ✅ **Make a test commit** - Verify hook runs
4. 📖 **Read GRAPH_REPORT.md** - Understand architecture
5. 🔍 **Try queries** - `graphify query "<question>"`
6. 📚 **Create wiki** (optional) - Document core communities

## Questions?

See:
- `graphify --help` - CLI documentation
- `graphify-out/GRAPH_REPORT.md` - Architecture overview
- Session memory: `lstm_analysis.md` and `graphify_analysis.md`

---

**Last Updated**: May 29, 2026
**Integration Status**: ✅ Active
**Auto-Updates**: ✅ Enabled (local + CI/CD)
