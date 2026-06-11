# Run all 5 methods over the full telecom_small set and write one CSV per method.
# Resumable: a method whose CSV already exists is SKIPPED, so you can Ctrl-C and rerun.
# Usage (venv active, key set):
#   $env:OPENAI_API_KEY="sk-..."; ./scripts/run_all.ps1
# Optional overrides:
#   ./scripts/run_all.ps1 -Trials 4 -Config configs/openai.yaml

param(
    [string]$Config = "configs/openai.yaml",
    [int]$Trials = 2,
    [int]$Limit = 0          # 0 = all tasks in the set
)

$env:PYTHONUTF8 = "1"

# Order: cheap/no-verifier first (fast, establishes baselines), verifier methods last.
$methods = @("vanilla", "action_verifier", "self_verify", "guidance_verify", "guidance_verify_repair")

foreach ($m in $methods) {
    $csv = "results/cost_log_$m.csv"
    if (Test-Path $csv) {
        Write-Host "[run_all] SKIP $m (found $csv)" -ForegroundColor Yellow
        continue
    }
    Write-Host "[run_all] === running $m ===" -ForegroundColor Cyan
    $args = @("-m", "src.eval.run", "--config", $Config, "--method", $m, "--trials", $Trials)
    if ($Limit -gt 0) { $args += @("--limit", $Limit) }
    & python @args 2>&1 | Select-Object -Last 14
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run_all] $m FAILED (exit $LASTEXITCODE). Stopping." -ForegroundColor Red
        break
    }
}
Write-Host "[run_all] done. CSVs in results/. Run scripts/aggregate.py for the comparison table." -ForegroundColor Green
