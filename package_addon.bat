@echo off
setlocal DisableDelayedExpansion
set "DF_PACKAGE_SCRIPT=%~f0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$text = [IO.File]::ReadAllText($env:DF_PACKAGE_SCRIPT); $parts = $text -split '(?m)^# POWERSHELL_BEGIN\r?$', 2; if ($parts.Count -ne 2) { throw 'Package script is incomplete.' }; & ([ScriptBlock]::Create($parts[1]))"
set "DF_PACKAGE_EXIT=%ERRORLEVEL%"
if /i not "%~1"=="--no-pause" pause
exit /b %DF_PACKAGE_EXIT%

# POWERSHELL_BEGIN
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetDirectoryName($env:DF_PACKAGE_SCRIPT)
$rootPrefix = $root + [IO.Path]::DirectorySeparatorChar
$addon = 'DungeonsForever'
$files = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$temporaryZip = $null

function Resolve-Reference([string]$reference, [string]$directory) {
    $reference = $reference.Replace('/', '\')
    if ([IO.Path]::IsPathRooted($reference)) {
        throw "Absolute manifest reference is not supported: $reference"
    }
    foreach ($base in @($directory, $root)) {
        $candidate = [IO.Path]::GetFullPath([IO.Path]::Combine($base, $reference))
        if ($candidate.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase) -and
            [IO.File]::Exists($candidate)) {
            return $candidate
        }
    }
    throw "Missing manifest file: $reference (from $directory)"
}

function Add-RuntimeFile([string]$path) {
    $path = [IO.Path]::GetFullPath($path)
    if (-not $path.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Package file is outside the addon directory: $path"
    }
    if (-not [IO.File]::Exists($path)) { throw "Required file is missing: $path" }
    if (-not $files.Add($path)) { return }
    if ([IO.Path]::GetExtension($path) -ieq '.xml') {
        $document = [Xml.XmlDocument]::new()
        $document.XmlResolver = $null
        $document.LoadXml([IO.File]::ReadAllText($path))
        foreach ($node in $document.SelectNodes('//*[local-name()="Script" or local-name()="Include"][@file]')) {
            Add-RuntimeFile (Resolve-Reference $node.GetAttribute('file') ([IO.Path]::GetDirectoryName($path)))
        }
    }
}

try {
    $toc = Join-Path $root "$addon.toc"
    if (-not [IO.File]::Exists($toc)) { throw "Cannot find $addon.toc beside this BAT file." }
    $tocText = [IO.File]::ReadAllText($toc)
    $versionMatch = [regex]::Match($tocText, '(?m)^##\s*Version:\s*([^\r\n]+)')
    if (-not $versionMatch.Success) { throw 'The TOC does not declare a version.' }
    $version = $versionMatch.Groups[1].Value.Trim()
    $safeVersion = [regex]::Replace($version, '[^A-Za-z0-9._-]', '_')

    Add-RuntimeFile $toc
    foreach ($line in ($tocText -split '\r?\n')) {
        $reference = $line.Trim()
        if (-not $reference -or $reference.StartsWith('#')) { continue }
        # Include every language, regardless of the current Windows locale.
        $reference = ($reference -replace '\s+\[.*\]\s*$', '').Trim()
        Add-RuntimeFile (Resolve-Reference $reference $root)
    }
    Add-RuntimeFile (Join-Path $root 'LICENSE')

    $media = Join-Path $root 'Media'
    if (-not [IO.Directory]::Exists($media)) { throw 'The Media directory is missing.' }
    # Only resource formats belong in Media in a release, not logs or work files.
    $assetTypes = @('.blp', '.tga', '.png', '.jpg', '.jpeg', '.dds',
        '.ttf', '.otf', '.ogg', '.mp3', '.wav', '.m2', '.skin', '.anim', '.wmo')
    foreach ($file in (Get-ChildItem -LiteralPath $media -Recurse -File)) {
        if ($file.Extension.ToLowerInvariant() -in $assetTypes) {
            Add-RuntimeFile $file.FullName
        }
    }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $output = Join-Path $root "$addon-$safeVersion-$stamp.zip"
    $temporaryZip = Join-Path $root ('.DungeonsForever-package-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $entryNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $stream = $null
    $archive = $null
    try {
        $stream = [IO.File]::Open($temporaryZip, [IO.FileMode]::CreateNew,
            [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        $archive = [IO.Compression.ZipArchive]::new($stream,
            [IO.Compression.ZipArchiveMode]::Create, $true, [Text.Encoding]::UTF8)
        foreach ($path in ($files | Sort-Object)) {
            $relative = $path.Substring($rootPrefix.Length).Replace('\', '/')
            $entryName = "$addon/$relative"
            [void]$entryNames.Add($entryName)
            [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive,
                $path, $entryName, [IO.Compression.CompressionLevel]::Optimal)
        }
    }
    finally {
        if ($archive) { $archive.Dispose() }
        if ($stream) { $stream.Dispose() }
    }

    # Publish only a complete archive with the expected single addon folder.
    $check = [IO.Compression.ZipFile]::OpenRead($temporaryZip)
    try {
        if ($check.Entries.Count -ne $files.Count) { throw 'ZIP file count verification failed.' }
        foreach ($entry in $check.Entries) {
            if (-not $entryNames.Contains($entry.FullName)) {
                throw "Unexpected ZIP entry: $($entry.FullName)"
            }
        }
    }
    finally { $check.Dispose() }
    $size = [IO.FileInfo]::new($temporaryZip).Length / 1MB
    $sha = [Security.Cryptography.SHA256]::Create()
    $reader = [IO.File]::OpenRead($temporaryZip)
    try { $hash = [BitConverter]::ToString($sha.ComputeHash($reader)).Replace('-', '') }
    finally { $reader.Dispose(); $sha.Dispose() }
    [IO.File]::Move($temporaryZip, $output)
    $temporaryZip = $null
    Write-Host ''
    Write-Host "Created: $output" -ForegroundColor Green
    Write-Host ('Version: {0} | Files: {1} | ZIP: {2:N2} MiB' -f $version, $files.Count, $size)
    Write-Host "SHA256: $hash"
    Write-Host 'Extract DungeonsForever into World of Warcraft/Interface/AddOns to install.'
    exit 0
}
catch {
    if ($temporaryZip -and [IO.File]::Exists($temporaryZip)) {
        Remove-Item -LiteralPath $temporaryZip -Force -ErrorAction SilentlyContinue
    }
    Write-Host ("Package failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
