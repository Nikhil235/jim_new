# Quick Fix: Graphify + PyTorch Issues

## Issue 1: Graphify Needs API Key ❌→✅

**Error**: 
```
error: no LLM API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY...
```

**Solution** (Choose ONE):

### Option A: Use Free Google Gemini (2 minutes)
```powershell
# 1. Get key (free, no credit card)
# Visit: https://aistudio.google.com/app/apikey
# Copy the key

# 2. Set in PowerShell
[Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "paste-key-here", "User")

# 3. Restart PowerShell
# 4. Test
graphify . --update --no-viz
```

### Option B: Skip Graphify (0 minutes)
```powershell
# Everything works WITHOUT graphify:
# - Models ✓
# - API ✓  
# - Backtesting ✓
# - Git hooks still work ✓
# Just won't build knowledge graph

# Just don't run graphify commands
```

---

## Issue 2: PyTorch GPU Installation Timing Out ❌→✅

**Problem**: Network timeouts downloading 2.7GB PyTorch wheel

**Status**: ✅ Not a problem - PyTorch CPU is already installed!
```powershell
python -c "import torch; print(torch.__version__)"
# Output: 2.11.0+cpu
```

**Options**:

### Option A: Use Existing CPU Version (RECOMMENDED)
```powershell
# PyTorch CPU is fine for:
# - Training models ✓
# - Running predictions ✓
# - Most scientific computing ✓
# No GPU needed for your current setup
```

### Option B: Install GPU Version (if you really need it)
```powershell
# Use uv (faster, better resume):
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# If uv times out too:
# - You can skip GPU version (CPU works fine)
# - Or try again later when network is better
```

### Option C: Don't Install Anything
```powershell
# Everything works with CPU PyTorch
# GPU would just be faster, not required
```

---

## 🎯 Recommended: Do This Now (2 minutes)

```powershell
# Option 1: Get free API key
# A. Visit: https://aistudio.google.com/app/apikey
# B. Copy the key
# C. Run:
[Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "paste-key-here", "User")

# D. Restart PowerShell
# E. Test graphify
graphify . --update --no-viz

# Done! ✓
```

---

## ✅ What Works Right Now (No Changes Needed)

```powershell
# All your models
python main.py --mode demo        ✓
python main.py --mode api         ✓
python main.py --mode paper       ✓

# All your tests
pytest tests/ -v                  ✓

# All your git workflow
git add .
git commit -m "feature: xyz"      ✓ (without graphify update)

# Everything except graphify features
```

---

## Summary

| Issue | Status | Action |
|-------|--------|--------|
| **Graphify API key** | ❌ Blocking | Set GOOGLE_API_KEY (2 min) or skip graphify |
| **PyTorch GPU** | ✅ Not needed | CPU version already works |
| **Network timeouts** | ℹ️ Network issue | Not your code, can't fix |
| **Your system** | ✅ Working | All features functional |

---

## Questions?

- **Want graphify?** → Get free API key from Google (links above)
- **Don't want graphify?** → Everything works fine without it
- **GPU PyTorch?** → Not needed, CPU version is installed and works

**Recommendation**: Get the free Google API key (30 seconds) → rest works automatically.

---

**Updated**: May 29, 2026
