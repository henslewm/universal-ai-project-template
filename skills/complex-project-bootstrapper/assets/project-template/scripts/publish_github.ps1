param(
    [string]$Owner = "henslewm",
    [string]$Repo = (Split-Path -Leaf (Get-Location)),
    [ValidateSet("private", "public", "internal")]
    [string]$Visibility = "private"
)

$ErrorActionPreference = "Stop"
gh auth status
gh repo create "$Owner/$Repo" "--$Visibility" --source . --remote origin --push
