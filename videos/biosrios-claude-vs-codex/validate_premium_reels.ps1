Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pack = $PSScriptRoot
$project = Join-Path (Split-Path -Parent $pack) 'biosrios-claude-vs-codex-shorts'

$resources = [ordered]@{
    TEST      = 'resources/TEST-fair-agent-benchmark-checklist.md'
    PREFLIGHT = 'resources/PREFLIGHT-agent-run-checklist.md'
    REMATCH   = 'resources/REMATCH-transparent-scoring-sheet.md'
}

$compositions = @(
    [pscustomobject]@{ Id = 'S01'; Keyword = 'TEST';      Path = 'compositions/s01/index.html' }
    [pscustomobject]@{ Id = 'S02'; Keyword = 'PREFLIGHT'; Path = 'compositions/s02/index.html' }
    [pscustomobject]@{ Id = 'S03'; Keyword = 'REMATCH';   Path = 'compositions/s03/index.html' }
)

$media = @(
    '.media/audio/sfx/sfx_001.wav'
    '.media/audio/sfx/sfx_002.wav'
    '.media/audio/sfx/sfx_003.wav'
    '.media/audio/sfx/sfx_004.wav'
    '.media/audio/sfx/sfx_005.wav'
    '.media/images/image_008.png'
    '.media/images/image_009.png'
    '.media/images/image_010.png'
)

$errors = [System.Collections.Generic.List[string]]::new()

foreach ($entry in $resources.GetEnumerator()) {
    $resourcePath = Join-Path $pack $entry.Value
    if (-not (Test-Path -LiteralPath $resourcePath -PathType Leaf)) {
        $errors.Add("$($entry.Key): resource missing: $($entry.Value)")
    }
}

foreach ($relativePath in $media) {
    $mediaPath = Join-Path $project $relativePath
    if (-not (Test-Path -LiteralPath $mediaPath -PathType Leaf)) {
        $errors.Add("media missing: $relativePath")
    }
}

$s01Html = $null
foreach ($composition in $compositions) {
    $compositionPath = Join-Path $project $composition.Path
    if (-not (Test-Path -LiteralPath $compositionPath -PathType Leaf)) {
        $errors.Add("$($composition.Id): composition missing: $($composition.Path)")
        continue
    }

    $html = Get-Content -LiteralPath $compositionPath -Raw
    if ($composition.Id -eq 'S01') {
        $s01Html = $html
    }

    if ($html -notmatch 'premium-reel\.css') {
        $errors.Add("$($composition.Id): premium-reel.css reference missing")
    }

    $ctaAttribute = 'data-cta-keyword\s*=\s*["'']' + [regex]::Escape($composition.Keyword) + '["'']'
    if ($html -notmatch $ctaAttribute) {
        $errors.Add("$($composition.Id): data-cta-keyword must equal $($composition.Keyword)")
    }

    $visibleComment = '(?is)Comment.*' + [regex]::Escape($composition.Keyword) + '(?=<|["''])'
    if ($html -notmatch $visibleComment) {
        $errors.Add("$($composition.Id): visible 'Comment $($composition.Keyword)' CTA copy missing")
    }

    if ($html -notmatch 'VERIFIED LOCAL EXCERPT') {
        $errors.Add("$($composition.Id): VERIFIED LOCAL EXCERPT proof label missing")
    }
    if ($html -notmatch 'resource-cta') {
        $errors.Add("$($composition.Id): resource-cta missing")
    }
    if ($html -notmatch 'sfx_005\.wav') {
        $errors.Add("$($composition.Id): sfx_005.wav cue missing")
    }
    if ($html -match 'FACE-CLONE PREVIEW FALLBACK') {
        $errors.Add("$($composition.Id): FACE-CLONE PREVIEW FALLBACK must be removed")
    }
}

$rootIndex = Join-Path $project 'index.html'
if (-not (Test-Path -LiteralPath $rootIndex -PathType Leaf)) {
    $errors.Add('S01: root index.html mirror missing')
} elseif ($null -ne $s01Html) {
    $rootHtml = Get-Content -LiteralPath $rootIndex -Raw
    if (-not [string]::Equals($s01Html, $rootHtml, [System.StringComparison]::Ordinal)) {
        $errors.Add('S01: compositions/s01/index.html and root index.html must match exactly')
    }
}

if ($errors.Count -gt 0) {
    foreach ($errorMessage in $errors) {
        [Console]::Error.WriteLine($errorMessage)
    }
    throw "$($errors.Count) premium Reel validation error(s)"
}

Write-Output 'Premium Reel validator PASS: resources, media, CTAs, proof labels, and S01 mirror are complete.'
