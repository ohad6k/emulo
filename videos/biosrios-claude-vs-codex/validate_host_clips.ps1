param(
    [string]$PackageRoot = $PSScriptRoot,
    [string]$FfprobePath = $env:FFPROBE_PATH
)

$ErrorActionPreference = "Stop"

$mapPath = Join-Path $PackageRoot "HOST-CLIP-REPLACEMENT-MAP.json"
$videosRoot = Split-Path -Parent $PackageRoot
$longProject = Join-Path $videosRoot "biosrios-claude-vs-codex-long"
$shortsProject = Join-Path $videosRoot "biosrios-claude-vs-codex-shorts"
$longClips = Join-Path $longProject "assets\host-clips"
$shortsClips = Join-Path $shortsProject "assets\host-clips"

if ([string]::IsNullOrWhiteSpace($FfprobePath)) {
    $ffprobeCommand = Get-Command ffprobe -ErrorAction SilentlyContinue
    if ($ffprobeCommand) {
        $FfprobePath = $ffprobeCommand.Source
    }
}
if ([string]::IsNullOrWhiteSpace($FfprobePath) -or -not (Test-Path -LiteralPath $FfprobePath)) {
    throw "ffprobe was not found. Add it to PATH, pass -FfprobePath, or set FFPROBE_PATH."
}

function Get-FrameRate([string]$fraction) {
    $parts = $fraction -split "/"
    if ($parts.Count -ne 2 -or [double]$parts[1] -eq 0) {
        return 0
    }
    return [double]$parts[0] / [double]$parts[1]
}

function Get-LiveHtmlSource([string]$compositionPath) {
    $source = Get-Content -LiteralPath $compositionPath -Raw
    $options = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    $source = [regex]::Replace($source, "<!--.*?-->", "", $options)
    # HyperFrames sub-compositions intentionally keep their live markup inside
    # a body <template>, so only truly inert executable/fallback blocks are removed.
    $source = [regex]::Replace(
        $source,
        "<(script|noscript)\b[^>]*>.*?</\1\s*>",
        "",
        $options
    )
    return $source
}

function Test-Selector([string]$compositionPath, [string]$selector) {
    $source = Get-LiveHtmlSource $compositionPath
    if ($selector -match "^#([A-Za-z0-9_-]+)") {
        $id = [regex]::Escape($Matches[1])
        return $source -match "id\s*=\s*[`"']$id[`"']"
    }
    if ($selector -match "^\.([A-Za-z0-9_-]+)") {
        $className = [regex]::Escape($Matches[1])
        return $source -match "class\s*=\s*[`"'][^`"']*(?<![A-Za-z0-9_-])$className(?![A-Za-z0-9_-])[^`"']*[`"']"
    }
    return $false
}

function Get-IntegrationMode($spec) {
    $mode = [string]$spec.integrationMode
    if ([string]::IsNullOrWhiteSpace($mode)) {
        return "selector"
    }
    return $mode
}

function Test-IsRequired($spec) {
    if ($null -eq $spec.required) {
        return $true
    }
    return [bool]$spec.required
}

function Test-MapSpec($spec, [string]$projectRoot) {
    $compositionPath = Join-Path $projectRoot $spec.composition
    if (-not (Test-Path -LiteralPath $compositionPath)) {
        return "$($spec.id): composition missing: $($spec.composition)"
    }
    if ($null -eq $spec.start -or [double]$spec.start -lt 0) {
        return "$($spec.id): invalid non-negative start value"
    }
    $integrationMode = Get-IntegrationMode $spec
    if ($integrationMode -eq "character-led-retired") {
        return $null
    }
    if ($integrationMode -ne "selector") {
        return "$($spec.id): unsupported integration mode '$integrationMode'"
    }
    if (-not (Test-Selector $compositionPath $spec.selector)) {
        return "$($spec.id): selector missing: $($spec.selector)"
    }
    if ($spec.selector -notmatch "^#([A-Za-z0-9_-]+)$") {
        return "$($spec.id): integration selector must be one exact element id"
    }
    $source = Get-LiveHtmlSource $compositionPath
    $id = [regex]::Escape($Matches[1])
    $target = [regex]::Match(
        $source,
        "<(?:img|video)\b(?=[^>]*\bid\s*=\s*[`"']$id[`"'])[^>]*>",
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if (-not $target.Success) {
        return "$($spec.id): selector does not point to an img/video element"
    }
    $className = [regex]::Escape([string]$spec.className)
    if (-not $className -or $target.Value -notmatch "class\s*=\s*[`"'][^`"']*(?<![A-Za-z0-9_-])$className(?![A-Za-z0-9_-])[^`"']*[`"']") {
        return "$($spec.id): target is missing class '$($spec.className)'"
    }
    if ($spec.rootMirror) {
        $mirrorPath = Join-Path $projectRoot $spec.rootMirror
        if (-not (Test-Path -LiteralPath $mirrorPath) -or -not (Test-Selector $mirrorPath $spec.selector)) {
            return "$($spec.id): root mirror selector missing: $($spec.rootMirror) $($spec.selector)"
        }
    }
    return $null
}

function Test-Clip($spec, [string]$clipsRoot, [string]$projectRoot) {
    $required = Test-IsRequired $spec
    $candidate = Get-ChildItem -LiteralPath $clipsRoot -Filter $spec.filenamePattern -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $candidate) {
        return [pscustomobject]@{
            Id = $spec.id
            Status = "MISSING"
            Required = $required
            File = ""
            Details = $spec.filenamePattern
        }
    }

    $probeText = & $FfprobePath -v error -show_streams -show_format -print_format json $candidate.FullName
    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{
            Id = $spec.id
            Status = "FAIL"
            Required = $required
            File = $candidate.Name
            Details = "ffprobe failed"
        }
    }

    $probe = $probeText | ConvertFrom-Json
    $video = $probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1
    $audio = $probe.streams | Where-Object { $_.codec_type -eq "audio" } | Select-Object -First 1
    $duration = [double]$probe.format.duration
    $fps = Get-FrameRate $video.avg_frame_rate
    $issues = @()

    if (-not $video) { $issues += "no video stream" }
    if ($video.codec_name -ne "h264") { $issues += "codec=$($video.codec_name), expected h264" }
    if ([int]$video.width -ne [int]$spec.width -or [int]$video.height -ne [int]$spec.height) {
        $issues += "size=$($video.width)x$($video.height), expected $($spec.width)x$($spec.height)"
    }
    if ([math]::Abs($fps - 30.0) -gt 0.15) {
        $issues += "fps=$([math]::Round($fps, 3)), expected 30"
    }
    if ($duration + 0.05 -lt [double]$spec.minimumDuration) {
        $issues += "duration=$([math]::Round($duration, 2))s, minimum $($spec.minimumDuration)s"
    }

    $compositionPath = Join-Path $projectRoot $spec.composition
    if (-not (Test-Path -LiteralPath $compositionPath)) {
        $issues += "composition missing: $($spec.composition)"
    } elseif ((Get-IntegrationMode $spec) -eq "selector" -and -not (Test-Selector $compositionPath $spec.selector)) {
        $issues += "selector missing: $($spec.selector)"
    }

    $audioNote = if ($audio) { "embedded audio present; integration must mute video track" } else { "silent video" }
    return [pscustomobject]@{
        Id = $spec.id
        Status = if ($issues.Count) { "FAIL" } else { "PASS" }
        Required = $required
        File = $candidate.Name
        Details = if ($issues.Count) { $issues -join "; " } else {
            "$($video.width)x$($video.height), $([math]::Round($fps, 3)) fps, $([math]::Round($duration, 2))s, $audioNote"
        }
    }
}

$map = Get-Content -LiteralPath $mapPath -Raw | ConvertFrom-Json
$mapErrors = @()
$mapErrors += $map.long | ForEach-Object { Test-MapSpec $_ $longProject } | Where-Object { $_ }
$mapErrors += $map.shorts | ForEach-Object { Test-MapSpec $_ $shortsProject } | Where-Object { $_ }
if ($mapErrors.Count) {
    $mapErrors | ForEach-Object { Write-Error $_ }
    exit 1
}
Write-Output "Replacement map integration modes validated."

$results = @()
$results += $map.long | ForEach-Object { Test-Clip $_ $longClips $longProject }
$results += $map.shorts | ForEach-Object { Test-Clip $_ $shortsClips $shortsProject }
$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Required -and $_.Status -ne "PASS" })
if ($failed.Count) {
    Write-Error "$($failed.Count) required host clip(s) are missing or invalid."
    exit 1
}

$optionalMissing = @($results | Where-Object { -not $_.Required -and $_.Status -eq "MISSING" })
Write-Output "All required host clips passed technical validation."
if ($optionalMissing.Count) {
    Write-Output "$($optionalMissing.Count) optional host clip(s) are not present."
}
