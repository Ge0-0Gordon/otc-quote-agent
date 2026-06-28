$ErrorActionPreference = "Stop"

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

function Invoke-Sample {
    param(
        [string]$InputFile,
        [string]$OutputDirectory
    )

    & $python (Join-Path $projectRoot "cli.py") `
        --input (Join-Path $projectRoot $InputFile) `
        --output (Join-Path $projectRoot $OutputDirectory)
    if ($LASTEXITCODE -ne 0) {
        throw "Sample failed: $InputFile (exit code $LASTEXITCODE)"
    }
}

Invoke-Sample "sample_data/snowball_inquiry_zh.txt" "outputs/sample_snowball"
Invoke-Sample "sample_data/fcn_quote_zh.txt" "outputs/sample_fcn"
Invoke-Sample "sample_data/european_option_email_en.txt" "outputs/sample_option"
Invoke-Sample "sample_data/reference_case_09_limited_loss_snowball.txt" "outputs/reference_case_09"
Invoke-Sample "sample_data/reference_case_11_dcn_unsupported.txt" "outputs/reference_case_11"
Invoke-Sample "sample_data/reference_case_12_sharkfin_unsupported.txt" "outputs/reference_case_12"
Invoke-Sample "sample_data/reference_case_13_snowball_two_choices.txt" "outputs/reference_case_13"
