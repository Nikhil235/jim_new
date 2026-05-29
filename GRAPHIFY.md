# Graphify Integration Guide

Graphify is a knowledge graph tool that maps codebase structure, detects relationships, and enables semantic search across the JIM trading system.

## 1. Quick Setup (5 Minutes)

**Step 1: Install Graphify**
```powershell
uv tool install graphifyy
# Or if uv is unavailable: pip install graphifyy
```

**Step 2: Configure PATH (Windows)**
Add `C:\Users\amita\.local\bin` to your System PATH or PowerShell profile:
```powershell
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"
```

**Step 3: Enable Pre-commit Hook**
The hook auto-updates the graph before each commit.
```powershell
git config core.hooksPath .githooks
```

**Step 4: Set LLM API Key (Required for Semantic Inference)**
Graphify needs an LLM API key (Google Gemini is free and recommended).
```powershell
[Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-gemini-key", "User")
# Restart PowerShell for this to take effect.
```
*(Without a key, you must use `--no-viz` for AST-only updates).*

## 2. Usage & Common Commands

Once configured, the graph auto-updates on local `git commit` and via CI/CD on `git push`.

**Manual Graph Updates**
```powershell
# Quick update (AST only)
.\scripts\Update-Graphify.ps1 -Quick

# Force full rebuild (with LLM inference)
.\scripts\Update-Graphify.ps1 -Force
```

**Querying the Graph**
```powershell
# Semantic search
graphify query "How does ensemble prediction work?"

# Find relationships between components
graphify path "run_lstm" "run_ensemble"

# Explain a specific concept
graphify explain "feature_engineering"
```

## 3. Architecture & File Structure

All generated graph data is stored in the `graphify-out/` directory:
- `graph.json`: Core graph data (Tracked in Git)
- `GRAPH_REPORT.md`: Human-readable architecture overview (Tracked in Git)
- `manifest.json`: File metadata & hashes (Tracked in Git)
- `cache/`: AST cache (Ignored in Git)

*Tip: Always commit the updated graph files so the entire team benefits from the architecture map.*

## 4. Troubleshooting

| Issue | Solution |
|-------|----------|
| **`graphify: command not found`** | Ensure `C:\Users\amita\.local\bin` is in your PATH. |
| **`no LLM API key found`** | Set `GOOGLE_API_KEY` (or `OPENAI_API_KEY`) environment variable, or run with `--update --no-viz`. |
| **Pre-commit hook not running** | Run `git config core.hooksPath .githooks` to enable it. |
| **PyTorch GPU network timeouts** | **Ignore it.** PyTorch CPU is already installed and is fully sufficient for this project. |
| **Skip graph update for a commit**| Run `git commit --no-verify -m "message"` |
