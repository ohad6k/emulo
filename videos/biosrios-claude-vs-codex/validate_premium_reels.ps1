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

function Get-VisibleMarkup([string]$html) {
    $withoutComments = [regex]::Replace($html, '<!--.*?-->', '', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $withoutScripts = [regex]::Replace($withoutComments, '<script\b[^>]*>.*?</script\s*>', '', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline)
    return [regex]::Replace($withoutScripts, '<template\b[^>]*>.*?</template\s*>', '', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline)
}

function Test-OpeningTagHasClassToken([string]$openingTag, [string]$classToken) {
    $classAttribute = [regex]::Match($openingTag, '(?<=\s)(?i:class)\s*=\s*["''](?<value>[^"'']*)["'']')
    if (-not $classAttribute.Success) {
        return $false
    }

    $tokenPattern = '(?<![A-Za-z0-9_-])' + [regex]::Escape($classToken) + '(?![A-Za-z0-9_-])'
    return $classAttribute.Groups['value'].Value -cmatch $tokenPattern
}

function Test-OpeningTagHasExactAttribute([string]$openingTag, [string]$name, [string]$value, [bool]$valueCaseInsensitive = $false) {
    $attributePattern = '(?<=\s)(?i:' + [regex]::Escape($name) + ')\s*=\s*["''](?<value>[^"'']*)["'']'
    $attribute = [regex]::Match($openingTag, $attributePattern)
    if (-not $attribute.Success) {
        return $false
    }

    if ($valueCaseInsensitive) {
        return [string]::Equals($attribute.Groups['value'].Value, $value, [System.StringComparison]::OrdinalIgnoreCase)
    }

    return $attribute.Groups['value'].Value -ceq $value
}

function Test-OpeningTagIsVisible([string]$openingTag) {
    if ($openingTag -match '(?i)(?<=\s)hidden(?=\s|=|/?>)') {
        return $false
    }

    $styleAttribute = [regex]::Match($openingTag, '(?<=\s)(?i:style)\s*=\s*["''](?<value>[^"'']*)["'']')
    if (-not $styleAttribute.Success) {
        return $true
    }

    $style = $styleAttribute.Groups['value'].Value
    return $style -notmatch '(?i)(?<![A-Za-z0-9_-])(?:display\s*:\s*none|visibility\s*:\s*hidden)\b'
}

function Get-MatchingElementInnerHtml([string]$markup, [System.Text.RegularExpressions.Match]$openingTag) {
    $tagName = $openingTag.Groups['tag'].Value
    $tagPattern = [regex]::new('<(?<closing>/)?(?<tag>[A-Za-z][A-Za-z0-9:-]*)\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $depth = 1

    foreach ($tag in $tagPattern.Matches($markup, $openingTag.Index + $openingTag.Length)) {
        if (-not [string]::Equals($tag.Groups['tag'].Value, $tagName, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }

        if ($tag.Groups['closing'].Success) {
            $depth--
            if ($depth -eq 0) {
                return $markup.Substring($openingTag.Index + $openingTag.Length, $tag.Index - ($openingTag.Index + $openingTag.Length))
            }
        } elseif ($tag.Value -notmatch '/\s*>$') {
            $depth++
        }
    }

    return $null
}

function Get-DirectChildElements([string]$innerHtml) {
    $tagPattern = [regex]::new('<(?<closing>/)?(?<tag>[A-Za-z][A-Za-z0-9:-]*)\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $voidTags = @('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr')
    $stack = [System.Collections.Generic.List[string]]::new()
    $children = [System.Collections.Generic.List[object]]::new()
    $childOpeningTag = $null
    $childStart = 0

    foreach ($tag in $tagPattern.Matches($innerHtml)) {
        $tagName = $tag.Groups['tag'].Value
        if ($tag.Groups['closing'].Success) {
            if ($stack.Count -eq 0 -or -not [string]::Equals($stack[$stack.Count - 1], $tagName, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }

            if ($stack.Count -eq 1) {
                $children.Add([pscustomobject]@{
                    OpeningTag = $childOpeningTag
                    InnerHtml = $innerHtml.Substring($childStart, $tag.Index - $childStart)
                })
                $childOpeningTag = $null
            }
            $stack.RemoveAt($stack.Count - 1)
        } elseif ($tag.Value -notmatch '/\s*>$' -and $voidTags -notcontains $tagName.ToLowerInvariant()) {
            if ($stack.Count -eq 0) {
                $childOpeningTag = $tag.Value
                $childStart = $tag.Index + $tag.Length
            }
            $stack.Add($tagName)
        }
    }

    return $children
}

function Test-ResourceCtaCopy([string]$markup, [string]$keyword) {
    $openingTagPattern = [regex]::new('<(?<tag>[A-Za-z][A-Za-z0-9:-]*)\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    foreach ($openingTag in $openingTagPattern.Matches($markup)) {
        if (-not (Test-OpeningTagIsVisible $openingTag.Value) -or -not (Test-OpeningTagHasClassToken $openingTag.Value 'resource-cta') -or -not (Test-OpeningTagHasExactAttribute $openingTag.Value 'data-cta-keyword' $keyword)) {
            continue
        }

        $ctaInnerHtml = Get-MatchingElementInnerHtml $markup $openingTag
        if ($null -eq $ctaInnerHtml) {
            continue
        }

        $children = @(Get-DirectChildElements $ctaInnerHtml)
        for ($commentIndex = 0; $commentIndex -lt $children.Count; $commentIndex++) {
            if (-not (Test-OpeningTagIsVisible $children[$commentIndex].OpeningTag) -or $children[$commentIndex].InnerHtml -cnotmatch '^\s*Comment\s*$' -or -not (Test-OpeningTagHasClassToken $children[$commentIndex].OpeningTag 'comment')) {
                continue
            }

            for ($keywordIndex = $commentIndex + 1; $keywordIndex -lt $children.Count; $keywordIndex++) {
                $keywordText = '^\s*["'']?' + [regex]::Escape($keyword) + '["'']?\s*$'
                if ((Test-OpeningTagIsVisible $children[$keywordIndex].OpeningTag) -and (Test-OpeningTagHasClassToken $children[$keywordIndex].OpeningTag 'keyword') -and $children[$keywordIndex].InnerHtml -cmatch $keywordText) {
                    return $true
                }
            }
        }
    }

    return $false
}

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

$sharedStylesheet = Join-Path $project 'assets/styles/premium-reel.css'
if (-not (Test-Path -LiteralPath $sharedStylesheet -PathType Leaf)) {
    $errors.Add('Missing shared asset: assets\styles\premium-reel.css')
}

$s01Html = $null
foreach ($composition in $compositions) {
    $compositionPath = Join-Path $project $composition.Path
    if (-not (Test-Path -LiteralPath $compositionPath -PathType Leaf)) {
        $errors.Add("$($composition.Id): composition missing: $($composition.Path)")
        continue
    }

    $html = Get-Content -LiteralPath $compositionPath -Raw
    $markup = Get-VisibleMarkup $html
    if ($composition.Id -eq 'S01') {
        $s01Html = $html
    }

    $openingTagPattern = [regex]::new('<(?<tag>[A-Za-z][A-Za-z0-9:-]*)\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    $stylesheetLinks = @($openingTagPattern.Matches($markup) | Where-Object {
        [string]::Equals($_.Groups['tag'].Value, 'link', [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-OpeningTagIsVisible $_.Value) -and
        (Test-OpeningTagHasExactAttribute $_.Value 'rel' 'stylesheet' $true) -and
        (Test-OpeningTagHasExactAttribute $_.Value 'href' 'assets/styles/premium-reel.css')
    })
    if ($stylesheetLinks.Count -eq 0) {
        $errors.Add("$($composition.Id): premium-reel.css reference missing")
    }

    $resourceCtas = @($openingTagPattern.Matches($markup) | Where-Object { (Test-OpeningTagIsVisible $_.Value) -and (Test-OpeningTagHasClassToken $_.Value 'resource-cta') })
    $matchingResourceCtas = @($resourceCtas | Where-Object { Test-OpeningTagHasExactAttribute $_.Value 'data-cta-keyword' $composition.Keyword })
    if ($matchingResourceCtas.Count -eq 0) {
        $errors.Add("$($composition.Id): data-cta-keyword must equal $($composition.Keyword)")
    }

    if (-not (Test-ResourceCtaCopy $markup $composition.Keyword)) {
        $errors.Add("$($composition.Id): visible 'Comment $($composition.Keyword)' CTA copy missing")
    }

    $proofLabels = @([regex]::Matches($markup, '(?<opening>(?i:<[A-Za-z][A-Za-z0-9:-]*\b[^>]*>))\s*(?-i:VERIFIED LOCAL EXCERPT)\s*(?i:</[A-Za-z][A-Za-z0-9:-]*\s*>)') | Where-Object { Test-OpeningTagIsVisible $_.Groups['opening'].Value })
    if ($proofLabels.Count -eq 0) {
        $errors.Add("$($composition.Id): VERIFIED LOCAL EXCERPT proof label missing")
    }
    if ($resourceCtas.Count -eq 0) {
        $errors.Add("$($composition.Id): resource-cta missing")
    }
    $audioCues = @($openingTagPattern.Matches($markup) | Where-Object {
        [string]::Equals($_.Groups['tag'].Value, 'audio', [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-OpeningTagIsVisible $_.Value) -and
        ([regex]::IsMatch($_.Value, '(?<=\s)(?i:src)\s*=\s*["''][^"'']*sfx_005\.wav["'']'))
    })
    if ($audioCues.Count -eq 0) {
        $errors.Add("$($composition.Id): sfx_005.wav cue missing")
    }
    if ($markup -cmatch 'FACE-CLONE PREVIEW FALLBACK') {
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
