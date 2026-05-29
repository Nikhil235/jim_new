# Graphify Update Script (Windows PowerShell)
# Manual trigger to update the knowledge graph
#
# Usage:
#   .\scripts\Update-Graphify.ps1              # Full update
#   .\scripts\Update-Graphify.ps1 -Force       # Force rebuild
#   .\scripts\Update-Graphify.ps1 -Quick       # AST-only (fast)

param(
    [switch]$Force,
    [switch]$Quick
)

# Ensure graphify is in PATH
$env:PATH = "C:\Users\amita\.local\bin;$env:PATH"

# Colors for output
function Write-Green {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Yellow {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Red {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Write-Blue {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

# Header
Write-Blue "╔═══════════════════════════════════════════╗"
Write-Blue "║  Graphify Knowledge Graph Update Tool     ║"
Write-Blue "╚═══════════════════════════════════════════╝"

# Check if graphify is installed
try {
    $null = graphify --version
    Write-Green "✓ graphify found"
} catch {
    Write-Red "✗ graphify not found"
    Write-Yellow "Install it with:"
    Write-Host "  uv tool install graphifyy"
    Write-Yellow "Then add to PATH:"
    Write-Host '  $env:PATH = "C:\Users\amita\.local\bin;$env:PATH"'
    exit 1
}

# Determine mode
if ($Force) {
    Write-Yellow "Mode: Full rebuild with community detection"
    $FLAGS = @("--force")
} elseif ($Quick) {
    Write-Yellow "Mode: AST-only update (fast, no LLM)"
    $FLAGS = @("--update", "--no-viz")
} else {
    Write-Yellow "Mode: Incremental update with LLM inference"
    $FLAGS = @("--update")
}

# Check current graph size
if (Test-Path "graphify-out") {
    $SIZE = (Get-Item "graphify-out" | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Yellow "Current graph size: $([Math]::Round($SIZE, 2)) MB"
}

# Run update
Write-Yellow "Updating graph..."
Write-Host ""

& graphify . $FLAGS

if ($LASTEXITCODE -ne 0) {
    Write-Yellow "⚠ Graph update completed with warnings"
} else {
    Write-Host ""
    Write-Green "✓ Update complete"
}

# Show new size
if (Test-Path "graphify-out") {
    $NEW_SIZE = (Get-Item "graphify-out" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Yellow "New graph size: $([Math]::Round($NEW_SIZE, 2)) MB"
}

# Show stats
if (Test-Path "graphify-out\GRAPH_REPORT.md") {
    $REPORT = Get-Content "graphify-out\GRAPH_REPORT.md" -Head 20
    $STATS = $REPORT | Select-String -Pattern "nodes|edges|communities"
    if ($STATS) {
        Write-Blue "Graph Statistics:"
        $STATS | ForEach-Object { Write-Host $_.Line }
    }
}

Write-Green "✓ Done"
Write-Host ""
Write-Yellow "Next: commit the changes"
Write-Host "  git add graphify-out/"
Write-Host "  git commit -m \"docs: update knowledge graph\""
