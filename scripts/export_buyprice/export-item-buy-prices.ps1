#Requires -Version 5.1
<#
.SYNOPSIS
Export hotfixed Forever item prices, the raw Item table, and recipe-item learning evidence.
.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_buyprice\export-item-buy-prices.ps1
.NOTES
BuyPrice and VendorStackCount are raw database fields, not discounted merchant
quotes or evidence that a vendor sells an item. No Python dependency is needed.
#>
[CmdletBinding()]
param(
    [string]$ToolDirectory = '',
    [string]$BaseUrl = 'http://127.0.0.1:5000',
    [string]$OutputPath = 'output\item-buy-prices.csv',
    [string]$ItemOutputPath = 'output\item.csv',
    [string]$RecipeItemOutputPath = 'output\recipe-item-specializations.csv',
    [string]$LearningSnapshotPath = '',
    [ValidateRange(1, 3600)][int]$StartupTimeoutSec = 180,
    [ValidateRange(1, 3600)][int]$RequestTimeoutSec = 300
)

$script:ItemPriceScriptDirectory = $PSScriptRoot
$script:ItemPriceRepositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:ItemPriceRunLog = $null

function Write-ItemPriceLog {
    param([string]$Message)
    $line = '[{0}] {1}' -f [DateTime]::Now.ToString('HH:mm:ss'), $Message
    Write-Host $line
    if ($script:ItemPriceRunLog) {
        try { [IO.File]::AppendAllText($script:ItemPriceRunLog, $line + [Environment]::NewLine, [Text.UTF8Encoding]::new($false)) }
        catch { Write-Warning ('Could not append the export log: {0}' -f $_.Exception.Message) }
    }
}

function Resolve-ItemPricePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'A file or directory path is empty.' }
    if (-not [IO.Path]::IsPathRooted($Path)) {
        $Path = Join-Path $script:ItemPriceScriptDirectory $Path
    }
    return [IO.Path]::GetFullPath($Path)
}

function Assert-WtlRepositoryPath {
    param([string]$Path)
    $root = (Get-WtlOutputIdentity $script:ItemPriceRepositoryRoot).Path.TrimEnd([char[]]@('\', '/'))
    $resolved = (Get-WtlOutputIdentity $Path).Path
    if (-not [string]::Equals($resolved, $root, [StringComparison]::OrdinalIgnoreCase) -and
        -not $resolved.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw ('Path must stay inside the current repository: {0}' -f $resolved)
    }
    return $resolved
}

# The final path resolves directory junctions as well as lexical aliases. File
# identities additionally catch two existing hard links to the same output.
function Get-WtlOutputIdentity {
    param([string]$Path)
    if (-not ('WtlExportFileIdentity' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class WtlExportFileIdentity {
    [StructLayout(LayoutKind.Sequential)]
    private struct FileInfo {
        public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Created, Accessed, Written;
        public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern uint GetFinalPathNameByHandle(SafeFileHandle file, StringBuilder name, uint size, uint flags);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle file, out FileInfo info);
    public static string[] Read(string path) {
        using (var file=CreateFile(path,0,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero)) {
            if(file.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
            var buffer=new StringBuilder(32768);
            uint length=GetFinalPathNameByHandle(file,buffer,(uint)buffer.Capacity,0);
            if(length==0 || length>=buffer.Capacity) throw new Win32Exception(Marshal.GetLastWin32Error());
            FileInfo info;
            if(!GetFileInformationByHandle(file,out info)) throw new Win32Exception(Marshal.GetLastWin32Error());
            return new string[] {buffer.ToString(), info.Volume.ToString("X8")+":"+info.IndexHigh.ToString("X8")+info.IndexLow.ToString("X8")};
        }
    }
}
'@ -ErrorAction Stop
    }
    $existing = $Path
    $suffix = [Collections.Generic.List[string]]::new()
    while (-not (Test-Path -LiteralPath $existing)) {
        $suffix.Insert(0, [IO.Path]::GetFileName($existing))
        $parent = [IO.Path]::GetDirectoryName($existing)
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $existing) { throw ('Cannot resolve output path: {0}' -f $Path) }
        $existing = $parent
    }
    $identity = [WtlExportFileIdentity]::Read($existing)
    $canonical = $identity[0]
    foreach ($part in $suffix) { $canonical = [IO.Path]::Combine($canonical, $part) }
    $fileId = if ($suffix.Count -eq 0) { $identity[1] } else { $null }
    return [pscustomobject]@{ Path = $canonical.ToLowerInvariant(); FileId = $fileId }
}

function Invoke-WtlTextRequest {
    param([uri]$BaseUri, [string]$RelativeUrl, [int]$TimeoutSec)
    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
    $response = $null
    $url = [uri]::new($BaseUri, $RelativeUrl)
    try {
        $response = $client.GetAsync($url).GetAwaiter().GetResult()
        if ([int]$response.StatusCode -ne 200) {
            throw ('HTTP {0} from {1}' -f [int]$response.StatusCode, $url)
        }
        $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        # The export endpoint uses application/octet-stream without a charset.
        # Do not let Windows PowerShell guess ANSI for Chinese CSV contents.
        $encoding = [Text.UTF8Encoding]::new($false, $true)
        return $encoding.GetString($bytes).TrimStart([char]0xFEFF)
    }
    catch { throw ('Request failed: {0}: {1}' -f $url, $_.Exception.Message) }
    finally {
        if ($null -ne $response) { $response.Dispose() }
        $client.Dispose()
    }
}

function Get-WtlListener {
    param([uri]$BaseUri)
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $BaseUri.Port -ErrorAction SilentlyContinue)
    if ($BaseUri.Host -eq '127.0.0.1') {
        $listeners = @($listeners | Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::') })
    }
    elseif ($BaseUri.Host -eq '[::1]' -or $BaseUri.Host -eq '::1') {
        $listeners = @($listeners | Where-Object { $_.LocalAddress -in @('::1', '::') })
    }
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -eq 0) { return $null }
    if ($owners.Count -ne 1) { throw 'The service port has multiple listener processes; refusing to select one.' }
    $processInfo = Get-CimInstance Win32_Process -Filter ('ProcessId={0}' -f $owners[0]) -ErrorAction Stop
    if ($null -eq $processInfo -or [string]::IsNullOrEmpty($processInfo.ExecutablePath)) {
        throw 'Cannot verify the executable owning the service port.'
    }
    return [pscustomobject]@{ Id = [int]$owners[0]; ExecutablePath = $processInfo.ExecutablePath }
}

function Assert-WtlListener {
    param($Listener, [string]$ExecutablePath, $OwnedProcess)
    if ($null -eq $Listener) { return }
    $actual = [IO.Path]::GetFullPath($Listener.ExecutablePath)
    if (-not [string]::Equals($actual, $ExecutablePath, [StringComparison]::OrdinalIgnoreCase)) {
        throw ('The service port belongs to another executable: {0}' -f $actual)
    }
    if ($null -ne $OwnedProcess -and $Listener.Id -ne $OwnedProcess.Id) {
        throw 'Another process took the service port while wow.tools.local was starting.'
    }
}

function Start-WtlService {
    param([string]$ExecutablePath, [string]$ToolDirectory, [uri]$BaseUri, [string]$LogDirectory)
    [void][IO.Directory]::CreateDirectory($LogDirectory)
    $runId = '{0}-{1}' -f [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'), [Guid]::NewGuid().ToString('N')
    $stdout = Join-Path $LogDirectory ('wow-tools-{0}.stdout.log' -f $runId)
    $stderr = Join-Path $LogDirectory ('wow-tools-{0}.stderr.log' -f $runId)
    Write-ItemPriceLog ('Starting wow.tools.local. Server logs: {0}' -f $LogDirectory)
    $process = Start-Process -FilePath $ExecutablePath -WorkingDirectory $ToolDirectory `
        -ArgumentList @('--urls', $BaseUri.AbsoluteUri.TrimEnd('/')) -WindowStyle Hidden `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -ErrorAction Stop
    $process | Add-Member -NotePropertyName WtlStartedAtUtcTicks -NotePropertyValue $process.StartTime.ToUniversalTime().Ticks
    return $process
}

function Stop-WtlOwnedProcess {
    param([Diagnostics.Process]$Process, [string]$ExecutablePath)
    if ($null -eq $Process) { return }
    $Process.Refresh()
    if ($Process.HasExited) { return }
    $actual = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
    if ($null -eq $actual) { return }
    if ($actual.StartTime.ToUniversalTime().Ticks -ne $Process.WtlStartedAtUtcTicks -or
        -not [string]::Equals($actual.Path, $ExecutablePath, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Owned-process identity changed; refusing to terminate it.'
    }
    Write-ItemPriceLog ('Closing the wow.tools.local process started by this run (PID {0}).' -f $actual.Id)
    if ($actual.CloseMainWindow() -and $actual.WaitForExit(3000)) { return }
    Stop-Process -InputObject $actual -ErrorAction Stop
    if (-not $actual.WaitForExit(5000)) { throw 'The owned wow.tools.local process did not stop.' }
}

function Get-WtlCacheSnapshot {
    param([string]$CacheDirectory)
    $snapshot = @{}
    if (Test-Path -LiteralPath $CacheDirectory -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $CacheDirectory -Filter 'DBCache-Raidbots-classic_beta-*.bin' -File) {
            $snapshot[$file.FullName] = [pscustomobject]@{
                Length = $file.Length; Ticks = $file.LastWriteTimeUtc.Ticks
                Hash = Get-WtlFileSHA256 $file.FullName
            }
        }
    }
    return $snapshot
}

function Get-WtlFileSHA256 {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '') }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}

function Get-WtlFreshCache {
    param([string]$CacheDirectory, [hashtable]$Before, [uint32]$ExpectedBuild)
    $changed = @()
    if (Test-Path -LiteralPath $CacheDirectory -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $CacheDirectory -Filter 'DBCache-Raidbots-classic_beta-*.bin' -File) {
            $old = $Before[$file.FullName]
            $hash = Get-WtlFileSHA256 $file.FullName
            if ($null -eq $old -or $file.Length -ne $old.Length -or
                $file.LastWriteTimeUtc.Ticks -ne $old.Ticks -or $hash -ne $old.Hash) {
                $changed += [pscustomobject]@{ File = $file; Hash = $hash }
            }
        }
    }
    if ($changed.Count -eq 0) {
        throw 'Hotfix download did not create or update a Classic Beta cache. HTTP 200 alone is not proof of success.'
    }
    $latest = $changed | Sort-Object { $_.File.LastWriteTimeUtc } -Descending | Select-Object -First 1
    if ($latest.File.Length -lt 44) { throw 'The downloaded hotfix cache is truncated (header requires at least 44 bytes).' }
    $stream = [IO.File]::OpenRead($latest.File.FullName)
    $reader = [IO.BinaryReader]::new($stream)
    try {
        $magic = [Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
        $version = $reader.ReadUInt32()
        $buildNumber = $reader.ReadUInt32()
    }
    finally { $reader.Dispose() }
    if ($magic -ne 'XFTH' -or $version -notin @(8, 9)) {
        throw ('Invalid or unsupported hotfix cache header: magic={0}, version={1}.' -f $magic, $version)
    }
    if ($buildNumber -ne $ExpectedBuild) {
        throw ('Latest hotfix build {0} does not match current client build {1}. Update/load the matching client before exporting.' -f $buildNumber, $ExpectedBuild)
    }
    return [pscustomobject]@{ Path = $latest.File.FullName; Build = $buildNumber; Version = $version; SHA256 = $latest.Hash }
}

function ConvertTo-ItemPriceUInt32 {
    param([string]$Value, [string]$Description, [switch]$Positive)
    $number = [uint32]0
    if ($Value -notmatch '^[0-9]+$' -or
        -not [uint32]::TryParse($Value, [Globalization.NumberStyles]::None, [Globalization.CultureInfo]::InvariantCulture, [ref]$number) -or
        ($Positive -and $number -eq 0)) {
        throw ('Invalid unsigned integer for {0}: "{1}".' -f $Description, $Value)
    }
    return $number
}

function ConvertFrom-WtlItemCsv {
    param([string]$Text, [string]$TableName, [string]$Locale)
    if ([string]::IsNullOrWhiteSpace($Text)) { throw ('Empty CSV for {0}/{1}.' -f $TableName, $Locale) }
    if ($Text.Contains([string][char]0xFFFD)) { throw ('Invalid replacement characters in {0}/{1} CSV.' -f $TableName, $Locale) }
    Add-Type -AssemblyName Microsoft.VisualBasic -ErrorAction Stop
    $inputReader = [IO.StringReader]::new($Text)
    $parser = [Microsoft.VisualBasic.FileIO.TextFieldParser]::new($inputReader)
    $parser.SetDelimiters([string[]]@(','))
    $parser.HasFieldsEnclosedInQuotes = $true
    $parser.TrimWhiteSpace = $false
    $records = [Collections.Generic.Dictionary[uint32, object]]::new()
    try {
        $headers = $parser.ReadFields()
        if ($null -eq $headers) { throw 'Missing CSV header.' }
        $columns = @{}
        for ($i = 0; $i -lt $headers.Length; $i++) {
            if ([string]::IsNullOrWhiteSpace($headers[$i]) -or $columns.ContainsKey($headers[$i])) { throw 'Empty or duplicate CSV column.' }
            $columns[$headers[$i]] = $i
        }
        $required = @('ID')
        if ($TableName -eq 'item') { $required += @('ClassID', 'SubclassID') }
        if ($TableName -eq 'itemsparse') { $required += @('Display_lang', 'BuyPrice', 'VendorStackCount') }
        foreach ($name in $required) {
            if (-not $columns.ContainsKey($name)) { throw ('Missing CSV column {0} in {1}/{2}.' -f $name, $TableName, $Locale) }
        }
        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            if ($fields.Length -ne $headers.Length) { throw ('Malformed CSV row in {0}/{1}.' -f $TableName, $Locale) }
            $itemId = ConvertTo-ItemPriceUInt32 $fields[$columns['ID']] 'Item ID' -Positive
            if ($records.ContainsKey($itemId)) { throw ('Duplicate item ID {0} in {1}/{2}.' -f $itemId, $TableName, $Locale) }
            if ($TableName -eq 'itemsparse') {
                $ability = $null
                if ($columns.ContainsKey('RequiredAbility') -and $fields[$columns['RequiredAbility']] -ne '') {
                    $ability = ConvertTo-ItemPriceUInt32 $fields[$columns['RequiredAbility']] ('RequiredAbility for item {0}' -f $itemId)
                }
                $requiredSkill = $null
                if ($columns.ContainsKey('RequiredSkill') -and $fields[$columns['RequiredSkill']] -ne '') {
                    $requiredSkill = ConvertTo-ItemPriceUInt32 $fields[$columns['RequiredSkill']] ('RequiredSkill for item {0}' -f $itemId)
                }
                $records.Add($itemId, [pscustomobject]@{
                    Name = $fields[$columns['Display_lang']]
                    BuyPrice = ConvertTo-ItemPriceUInt32 $fields[$columns['BuyPrice']] ('BuyPrice for item {0}' -f $itemId)
                    VendorStackCount = ConvertTo-ItemPriceUInt32 $fields[$columns['VendorStackCount']] ('VendorStackCount for item {0}' -f $itemId)
                    RequiredAbility = $ability
                    RequiredSkill = $requiredSkill
                })
            }
            else {
                $records.Add($itemId, [pscustomobject]@{
                    ClassID = ConvertTo-ItemPriceUInt32 $fields[$columns['ClassID']] ('ClassID for item {0}' -f $itemId)
                    SubclassID = ConvertTo-ItemPriceUInt32 $fields[$columns['SubclassID']] ('SubclassID for item {0}' -f $itemId)
                })
            }
        }
    }
    catch { throw ('CSV validation failed ({0}/{1}): {2}' -f $TableName, $Locale, $_.Exception.Message) }
    finally { $parser.Dispose(); $inputReader.Dispose() }
    if ($records.Count -eq 0) { throw ('No records in {0}/{1}.' -f $TableName, $Locale) }
    return ,$records
}

function ConvertFrom-WtlLearningCsv {
    param([string]$Text, [string]$TableName)
    # Select only linkage fields; localized labels never establish a requirement.
    $schemas = @{
        itemeffect = @('SpellID', 'TriggerType')
        itemxitemeffect = @('ItemID', 'ItemEffectID')
        spelleffect = @('SpellID', 'Effect', 'EffectTriggerSpell')
        spelllearnspell = @('SpellID', 'LearnSpellID')
        skilllineability = @('SkillLine', 'Spell')
        skillline = @('ParentSkillLineID')
        spellname = @()
    }
    if (-not $schemas.ContainsKey($TableName)) { throw ('Unsupported learning table: {0}' -f $TableName) }
    if ([string]::IsNullOrWhiteSpace($Text) -or $Text.Contains([string][char]0xFFFD)) { throw ('Empty or invalid CSV for {0}.' -f $TableName) }
    Add-Type -AssemblyName Microsoft.VisualBasic -ErrorAction Stop
    $inputReader = [IO.StringReader]::new($Text)
    $parser = [Microsoft.VisualBasic.FileIO.TextFieldParser]::new($inputReader)
    $parser.SetDelimiters([string[]]@(','))
    $parser.HasFieldsEnclosedInQuotes = $true
    $parser.TrimWhiteSpace = $false
    $records = [Collections.Generic.Dictionary[uint32, object]]::new()
    try {
        $headers = $parser.ReadFields()
        if ($null -eq $headers) { throw 'Missing CSV header.' }
        $columns = @{}
        for ($i = 0; $i -lt $headers.Length; $i++) {
            if ([string]::IsNullOrWhiteSpace($headers[$i]) -or $columns.ContainsKey($headers[$i])) { throw 'Empty or duplicate CSV column.' }
            $columns[$headers[$i]] = $i
        }
        $selected = @('ID') + $schemas[$TableName]
        foreach ($name in $selected) {
            if (-not $columns.ContainsKey($name)) { throw ('Missing CSV column {0}.' -f $name) }
        }
        if ($TableName -eq 'spellname' -and -not $columns.ContainsKey('Name_lang')) { throw 'Missing CSV column Name_lang.' }
        $optional = @()
        if ($TableName -eq 'itemeffect') { $optional += 'ParentItemID' }
        if ($TableName -eq 'spelleffect') { $optional += @('EffectItemType', 'EffectMiscValue[0]') }
        foreach ($name in $optional) { if ($columns.ContainsKey($name)) { $selected += $name } }
        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            if ($fields.Length -ne $headers.Length) { throw 'Malformed CSV row.' }
            $id = ConvertTo-ItemPriceUInt32 $fields[$columns['ID']] ($TableName + ' ID') -Positive
            if ($records.ContainsKey($id)) { throw ('Duplicate record ID {0}.' -f $id) }
            $record = @{}
            foreach ($name in $selected) {
                $value = $fields[$columns[$name]]
                if ($name -in $optional -and $value -eq '') { $record[$name] = $null }
                elseif ($name -in @('EffectTriggerSpell', 'EffectMiscValue[0]') -and $value -match '^-[0-9]+$') {
                    # Signed fields can contain sentinels; evidence requires positive IDs.
                    $number = [int]0
                    if (-not [int]::TryParse($value, [ref]$number)) { throw ('Invalid signed integer for {0}: {1}.' -f $name, $value) }
                    $record[$name] = $number
                }
                else { $record[$name] = ConvertTo-ItemPriceUInt32 $value ($TableName + '.' + $name) }
            }
            $records.Add($id, $record)
        }
    }
    catch { throw ('CSV validation failed ({0}): {1}' -f $TableName, $_.Exception.Message) }
    finally { $parser.Dispose(); $inputReader.Dispose() }
    # A valid header-only table is distinct from an HTTP/parse failure.
    return ,$records
}

function Assert-WtlEmptySnapshotDirectory {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) { throw 'LearningSnapshotPath must be a directory.' }
    if ([IO.Directory]::Exists($Path) -and [IO.Directory]::GetFileSystemEntries($Path).Length -gt 0) {
        throw 'LearningSnapshotPath must not exist or must be empty; existing snapshots are never overwritten.'
    }
}

function Write-WtlNewSnapshotFile {
    param([string]$Path, [string]$Text, [bool]$Bom, [Collections.Generic.List[string]]$CreatedFiles)
    $stream = $null; $writer = $null
    try {
        # CreateNew also protects against a file appearing after the empty-directory check.
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $CreatedFiles.Add($Path)
        $writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($Bom))
        $writer.Write($Text)
    }
    finally {
        if ($null -ne $writer) { $writer.Dispose() }
        elseif ($null -ne $stream) { $stream.Dispose() }
    }
}

function Write-WtlLearningSnapshot {
    param([string]$Directory, [hashtable]$Tables, [string]$Build, $Cache)
    Assert-WtlEmptySnapshotDirectory $Directory
    [void][IO.Directory]::CreateDirectory($Directory)
    $created = [Collections.Generic.List[string]]::new()
    $metadata = [ordered]@{}
    try {
        foreach ($name in $Tables.Keys | Sort-Object) {
            $path = Join-Path $Directory ($name + '.csv')
            Write-WtlNewSnapshotFile $path $Tables[$name].Text $true $created
            $metadata[$name] = [ordered]@{
                url = $Tables[$name].Url
                sha256 = (Get-WtlFileSHA256 $path).ToLowerInvariant()
                rows = $Tables[$name].Rows
            }
        }
        $manifest = [ordered]@{
            schemaVersion = 1
            build = $Build
            hotfixBuild = $Cache.Build
            hotfixSHA256 = $Cache.SHA256
            useHotfixes = $true
            fetchedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fff'Z'")
            tables = $metadata
        }
        # The manifest is last: its presence denotes a fully written snapshot.
        Write-WtlNewSnapshotFile (Join-Path $Directory 'manifest.json') ($manifest | ConvertTo-Json -Depth 6) $false $created
    }
    catch {
        $problem = $_.Exception.Message
        for ($i = $created.Count - 1; $i -ge 0; $i--) {
            try { [IO.File]::Delete($created[$i]) }
            catch { $problem += (' Snapshot cleanup failed for {0}: {1}' -f $created[$i], $_.Exception.Message) }
        }
        throw ('Learning snapshot failed: {0}' -f $problem)
    }
}

function Get-WtlRecipeItemRows {
    param($Items, [hashtable]$Sparse, [hashtable]$Tables, [string]$Build, [uint32]$HotfixBuild)
    $professionSkills = [Collections.Generic.HashSet[uint32]]::new()
    foreach ($skill in @(129, 164, 165, 171, 182, 185, 186, 197, 202, 333, 356, 393)) { [void]$professionSkills.Add([uint32]$skill) }
    # Follow children (including Forever's engineering child skill); categories
    # also contain non-professions and do not identify a specialization.
    do {
        $added = $false
        foreach ($row in $Tables.skillline.Values) {
            if ($professionSkills.Contains($row.ParentSkillLineID) -and $professionSkills.Add($row.ID)) { $added = $true }
        }
    } while ($added)
    $professionSpells = [Collections.Generic.HashSet[uint32]]::new()
    $nonProfessionSpells = [Collections.Generic.HashSet[uint32]]::new()
    foreach ($row in $Tables.skilllineability.Values) {
        if ($row.Spell -gt 0 -and $professionSkills.Contains($row.SkillLine)) { [void]$professionSpells.Add($row.Spell) }
        elseif ($row.Spell -gt 0) { [void]$nonProfessionSpells.Add($row.Spell) }
    }
    $rankSpells = [Collections.Generic.HashSet[uint32]]::new()
    $craftEvidence = @{}
    $edges = @{}
    foreach ($row in $Tables.spelleffect.Values) {
        if ($row.Effect -in @(44, 118)) { [void]$rankSpells.Add($row.SpellID) }
        $craftField = $null
        if ($row.Effect -eq 24) { $craftField = 'EffectItemType' }
        elseif ($row.Effect -in @(53, 54)) { $craftField = 'EffectMiscValue[0]' }
        if ($row.SpellID -gt 0 -and $null -ne $craftField -and $row.ContainsKey($craftField) -and $row[$craftField] -gt 0) {
            if (-not $craftEvidence.ContainsKey($row.SpellID)) { $craftEvidence[$row.SpellID] = [Collections.Generic.List[string]]::new() }
            $craftEvidence[$row.SpellID].Add(('SpellEffect[{0}].Effect={1}/{2}={3}' -f $row.ID, $row.Effect, $craftField, $row[$craftField]))
        }
        if ($row.SpellID -gt 0 -and $row.Effect -eq 36 -and $row.EffectTriggerSpell -gt 0) {
            if (-not $edges.ContainsKey($row.SpellID)) { $edges[$row.SpellID] = [Collections.Generic.List[object]]::new() }
            $edges[$row.SpellID].Add([pscustomobject]@{
                Spell = [uint32]$row.EffectTriggerSpell
                Path = ('SpellEffect[{0}].Effect=36/EffectTriggerSpell={1}' -f $row.ID, $row.EffectTriggerSpell)
            })
        }
    }
    foreach ($row in $Tables.spelllearnspell.Values) {
        if ($row.SpellID -gt 0 -and $row.LearnSpellID -gt 0) {
            if (-not $edges.ContainsKey($row.SpellID)) { $edges[$row.SpellID] = [Collections.Generic.List[object]]::new() }
            $edges[$row.SpellID].Add([pscustomobject]@{
                Spell = $row.LearnSpellID
                Path = ('SpellLearnSpell[{0}].LearnSpellID={1}' -f $row.ID, $row.LearnSpellID)
            })
        }
    }
    $links = @{}
    foreach ($row in $Tables.itemxitemeffect.Values) {
        if (-not $Items.ContainsKey($row.ItemID) -or $Items[$row.ItemID].ClassID -ne 9) { continue }
        if (-not $links.ContainsKey($row.ItemID)) { $links[$row.ItemID] = [Collections.Generic.List[object]]::new() }
        $links[$row.ItemID].Add([pscustomobject]@{
            Effect = $row.ItemEffectID
            Path = ('Item[{0}].ClassID=9 -> ItemXItemEffect[{1}].ItemEffectID={2}' -f $row.ItemID, $row.ID, $row.ItemEffectID)
        })
    }
    foreach ($row in $Tables.itemeffect.Values) {
        if ($row.ContainsKey('ParentItemID') -and $row.ParentItemID -gt 0 -and
            $Items.ContainsKey($row.ParentItemID) -and $Items[$row.ParentItemID].ClassID -eq 9) {
            if (-not $links.ContainsKey($row.ParentItemID)) { $links[$row.ParentItemID] = [Collections.Generic.List[object]]::new() }
            $links[$row.ParentItemID].Add([pscustomobject]@{
                Effect = $row.ID
                Path = ('Item[{0}].ClassID=9 -> ItemEffect[{1}].ParentItemID={0}' -f $row.ParentItemID, $row.ID)
            })
        }
    }
    foreach ($itemId in $Items.Keys | Sort-Object) {
        if ($Items[$itemId].ClassID -ne 9) { continue }
        $ability = $null; $requiredSkill = $null; $referenceFound = $false
        foreach ($locale in @('enUS', 'zhTW', 'zhCN')) {
            if (-not $Sparse[$locale].ContainsKey($itemId)) { continue }
            $value = $Sparse[$locale][$itemId].RequiredAbility
            if ($referenceFound -and $value -ne $ability) { throw ('Conflicting RequiredAbility for item {0} in locale {1}.' -f $itemId, $locale) }
            $skillValue = $Sparse[$locale][$itemId].RequiredSkill
            if ($referenceFound -and $skillValue -ne $requiredSkill) { throw ('Conflicting RequiredSkill for item {0} in locale {1}.' -f $itemId, $locale) }
            $ability = $value; $requiredSkill = $skillValue; $referenceFound = $true
        }
        $targets = @{}
        $problems = [Collections.Generic.SortedSet[string]]::new()
        $unresolvedPaths = [Collections.Generic.SortedSet[string]]::new()
        $queue = [Collections.Generic.Queue[object]]::new()
        if (-not $links.ContainsKey($itemId)) { [void]$problems.Add('missing_item_effect') }
        else {
            foreach ($link in $links[$itemId]) {
                if (-not $Tables.itemeffect.ContainsKey($link.Effect)) {
                    [void]$problems.Add('missing_linked_item_effect'); [void]$unresolvedPaths.Add($link.Path); continue
                }
                $effect = $Tables.itemeffect[$link.Effect]
                $path = $link.Path + (' -> ItemEffect[{0}].SpellID={1}/TriggerType={2}' -f $effect.ID, $effect.SpellID, $effect.TriggerType)
                if ($effect.SpellID -gt 0 -and ($effect.TriggerType -eq 6 -or $edges.ContainsKey($effect.SpellID))) {
                    $queue.Enqueue([pscustomobject]@{ Spell = $effect.SpellID; Path = $path; Visited = [uint32[]]@() })
                }
                else { [void]$unresolvedPaths.Add($path) }
            }
        }
        $steps = 0
        while ($queue.Count -gt 0) {
            $node = $queue.Dequeue(); $steps++
            if ($steps -gt 4096 -or $node.Visited.Length -ge 64) {
                [void]$problems.Add('learning_graph_limit'); [void]$unresolvedPaths.Add($node.Path); break
            }
            if ($node.Spell -in $node.Visited) {
                [void]$problems.Add('learning_cycle'); [void]$unresolvedPaths.Add($node.Path); continue
            }
            if ($edges.ContainsKey($node.Spell)) {
                foreach ($edge in $edges[$node.Spell] | Sort-Object Spell, Path) {
                    $queue.Enqueue([pscustomobject]@{
                        Spell = $edge.Spell; Path = $node.Path + ' -> ' + $edge.Path
                        Visited = [uint32[]]@($node.Visited + $node.Spell)
                    })
                }
            }
            elseif ($professionSpells.Contains($node.Spell) -and -not $rankSpells.Contains($node.Spell)) {
                if (-not $targets.ContainsKey($node.Spell)) { $targets[$node.Spell] = [Collections.Generic.SortedSet[string]]::new() }
                [void]$targets[$node.Spell].Add($node.Path)
            }
            elseif ($null -ne $requiredSkill -and $professionSkills.Contains($requiredSkill) -and
                $craftEvidence.ContainsKey($node.Spell) -and -not $rankSpells.Contains($node.Spell) -and
                -not $nonProfessionSpells.Contains($node.Spell)) {
                # Some explicit taught recipes lack SkillLineAbility. Require both
                # the item's profession requirement and a concrete craft/enchant
                # effect. A book subclass, name or tradeskill flag is insufficient.
                if (-not $targets.ContainsKey($node.Spell)) { $targets[$node.Spell] = [Collections.Generic.SortedSet[string]]::new() }
                foreach ($evidence in $craftEvidence[$node.Spell]) {
                    [void]$targets[$node.Spell].Add(($node.Path + (' -> ItemSparse[{0}].RequiredSkill={1} + {2}' -f $itemId, $requiredSkill, $evidence)))
                }
            }
            else { [void]$unresolvedPaths.Add($node.Path) }
        }
        if ($targets.Count -eq 0) { [void]$problems.Add('no_profession_recipe_target') }
        if ($targets.Count -gt 1) { [void]$problems.Add('ambiguous_recipe_spells') }
        if ($null -eq $ability) { [void]$problems.Add('missing_required_ability') }
        elseif ($ability -eq 0) { [void]$problems.Add('zero_required_ability') }
        $status = if ($problems.Count -eq 0) { 'confirmed' } else { 'pending' }
        $reason = if ($problems.Count -eq 0) { 'item_required_ability' } else { [string]::Join(';', [string[]]@($problems)) }
        $spellIds = @($null)
        if ($targets.Count -gt 0) { $spellIds = @($targets.Keys | Sort-Object) }
        foreach ($spellId in $spellIds) {
            $paths = if ($null -eq $spellId) { @($unresolvedPaths) } else { @($targets[$spellId]) + @($unresolvedPaths) }
            [pscustomobject]@{
                RecipeItemID = $itemId; RecipeSpellID = $spellId; RequiredAbility = $ability
                Status = $status; Reason = $reason; LearningPath = (@($paths | Sort-Object -Unique) -join ' | ')
                Build = $Build; HotfixBuild = $HotfixBuild; Source = 'wow.tools.local:ItemSparse.RequiredAbility'
            }
        }
    }
}

function Write-ItemPriceCsvRecord {
    param([IO.StreamWriter]$Writer, [object[]]$Fields)
    $quoted = foreach ($value in $Fields) {
        $text = if ($null -eq $value) { '' } else { [Convert]::ToString($value, [Globalization.CultureInfo]::InvariantCulture) }
        '"' + $text.Replace('"', '""') + '"'
    }
    $Writer.WriteLine([string]::Join(',', [string[]]$quoted))
}

# Each file replacement is atomic; the output set requires compensating rollback.
# Keep any unrestored backup if the OS prevents recovery, and report its path.
function Publish-WtlCsvPair {
    param([object[]]$Files)
    $published = [Collections.Generic.List[object]]::new()
    $committed = $false
    try {
        foreach ($file in $Files) {
            $entry = [pscustomobject]@{
                OutputPath = $file.OutputPath; StagingPath = $file.StagingPath
                BackupPath = $file.StagingPath + '.previous'; Previous = [IO.File]::Exists($file.OutputPath)
                Restored = $false; DiscardPath = $file.StagingPath + '.rollback'
            }
            if ($entry.Previous) { [IO.File]::Replace($entry.StagingPath, $entry.OutputPath, $entry.BackupPath) }
            else { [IO.File]::Move($entry.StagingPath, $entry.OutputPath) }
            $published.Add($entry)
        }
        $committed = $true
    }
    catch {
        $problem = $_.Exception.Message
        $recovery = @()
        for ($i = $published.Count - 1; $i -ge 0; $i--) {
            $entry = $published[$i]
            try {
                if ($entry.Previous) {
                    if ([IO.File]::Exists($entry.OutputPath)) {
                        [IO.File]::Replace($entry.BackupPath, $entry.OutputPath, $entry.DiscardPath)
                    }
                    else { [IO.File]::Move($entry.BackupPath, $entry.OutputPath) }
                }
                else { [IO.File]::Delete($entry.OutputPath) }
                $entry.Restored = $true
            }
            catch { $recovery += ('Recovery failed for {0}; previous data retained at {1}: {2}' -f $entry.OutputPath, $entry.BackupPath, $_.Exception.Message) }
        }
        if ($recovery.Count -gt 0) { $problem += ' ' + ($recovery -join ' ') }
        throw ('CSV publication failed: {0}' -f $problem)
    }
    finally {
        foreach ($entry in $published) {
            $cleanup = @($entry.DiscardPath)
            if ($committed -or $entry.Restored) { $cleanup += $entry.BackupPath }
            foreach ($temporary in $cleanup) {
                if ([IO.File]::Exists($temporary)) {
                    try { [IO.File]::Delete($temporary) }
                    catch { Write-Warning ('Could not remove publication temporary file {0}: {1}' -f $temporary, $_.Exception.Message) }
                }
            }
        }
    }
}

function Invoke-ItemBuyPriceExport {
    [CmdletBinding()]
    param(
        [string]$ToolDirectory = '',
        [string]$BaseUrl = 'http://127.0.0.1:5000',
        [string]$OutputPath = 'output\item-buy-prices.csv',
        [string]$ItemOutputPath = 'output\item.csv',
        [string]$RecipeItemOutputPath = 'output\recipe-item-specializations.csv',
        [string]$LearningSnapshotPath = '',
        [ValidateRange(1, 3600)][int]$StartupTimeoutSec = 180,
        [ValidateRange(1, 3600)][int]$RequestTimeoutSec = 300
    )
    Set-StrictMode -Version 2
    $ErrorActionPreference = 'Stop'
    if ([string]::IsNullOrWhiteSpace($ToolDirectory)) {
        $ToolDirectory = Join-Path $script:ItemPriceRepositoryRoot '.pipeline-runtime\wow.tools.local'
    }
    $toolPath = Resolve-ItemPricePath $ToolDirectory
    if ($toolPath.Length -gt [IO.Path]::GetPathRoot($toolPath).Length) {
        $toolPath = $toolPath.TrimEnd([char[]]@('\', '/'))
    }
    $outputFile = Resolve-ItemPricePath $OutputPath
    $itemOutputFile = Resolve-ItemPricePath $ItemOutputPath
    $recipeOutputFile = Resolve-ItemPricePath $RecipeItemOutputPath
    $null = Assert-WtlRepositoryPath $toolPath
    foreach ($candidate in @($outputFile, $itemOutputFile, $recipeOutputFile,
                            (Join-Path $toolPath 'cache'), (Join-Path $toolPath 'caches'))) {
        $null = Assert-WtlRepositoryPath $candidate
    }
    if ($LearningSnapshotPath -ne '') {
        $null = Assert-WtlRepositoryPath (Resolve-ItemPricePath $LearningSnapshotPath)
    }
    foreach ($entry in @(Get-ChildItem -LiteralPath $toolPath -Force -Recurse -ErrorAction Stop)) {
        $null = Assert-WtlRepositoryPath $entry.FullName
    }
    $executable = Join-Path $toolPath 'wow.tools.local.exe'
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw ('Cannot find {0}' -f $executable) }
    if ([IO.Path]::GetExtension($outputFile) -ne '.csv') { throw 'OutputPath must end in .csv.' }
    if ([IO.Path]::GetExtension($itemOutputFile) -ne '.csv') { throw 'ItemOutputPath must end in .csv.' }
    if ([IO.Path]::GetExtension($recipeOutputFile) -ne '.csv') { throw 'RecipeItemOutputPath must end in .csv.' }
    $priceIdentity = Get-WtlOutputIdentity $outputFile
    $itemIdentity = Get-WtlOutputIdentity $itemOutputFile
    $recipeIdentity = Get-WtlOutputIdentity $recipeOutputFile
    $identities = @($priceIdentity, $itemIdentity, $recipeIdentity)
    for ($i = 0; $i -lt $identities.Count; $i++) {
        for ($j = $i + 1; $j -lt $identities.Count; $j++) {
            if ($identities[$i].Path -eq $identities[$j].Path -or
                ($null -ne $identities[$i].FileId -and $identities[$i].FileId -eq $identities[$j].FileId)) {
                throw 'CSV destinations refer to the same file; three separate CSV destinations are required.'
            }
        }
    }
    foreach ($destination in @($outputFile, $itemOutputFile, $recipeOutputFile)) {
        if (Test-Path -LiteralPath $destination -PathType Container) { throw ('CSV destination is a directory: {0}' -f $destination) }
    }
    $snapshotDirectory = $null; $snapshotIdentity = $null
    if ($LearningSnapshotPath -ne '') {
        $snapshotDirectory = Resolve-ItemPricePath $LearningSnapshotPath
        $snapshotIdentity = Get-WtlOutputIdentity $snapshotDirectory
        $snapshotKey = $snapshotIdentity.Path.TrimEnd([char]'\')
        foreach ($identity in $identities) {
            $outputKey = $identity.Path.TrimEnd([char]'\')
            if ($snapshotKey -eq $outputKey -or $outputKey.StartsWith($snapshotKey + '\', [StringComparison]::OrdinalIgnoreCase) -or
                $snapshotKey.StartsWith($outputKey + '\', [StringComparison]::OrdinalIgnoreCase)) {
                throw 'LearningSnapshotPath overlaps a CSV output file or its containing directory; use a separate snapshot directory.'
            }
        }
        Assert-WtlEmptySnapshotDirectory $snapshotDirectory
    }
    $baseUri = [uri]($BaseUrl.TrimEnd('/') + '/')
    if (-not $baseUri.IsAbsoluteUri -or $baseUri.Scheme -ne 'http' -or -not $baseUri.IsLoopback -or
        $baseUri.AbsolutePath -ne '/' -or $baseUri.Query -or $baseUri.Fragment -or $baseUri.UserInfo) {
        throw 'BaseUrl must be a loopback HTTP origin, for example http://127.0.0.1:5000.'
    }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $lockKey = [BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($toolPath.ToLowerInvariant()))).Replace('-', '') }
    finally { $hasher.Dispose() }
    $mutex = [Threading.Mutex]::new($false, ('Local\DungeonsForever.ItemPriceExport.' + $lockKey))
    $lockHeld = $false; $owned = $null; $stagingFile = $null; $itemStagingFile = $null; $recipeStagingFile = $null
    $outputLocks = [Collections.Generic.List[object]]::new()
    try {
        try { $lockHeld = $mutex.WaitOne(0) }
        catch [Threading.AbandonedMutexException] { $lockHeld = $true }
        if (-not $lockHeld) { throw 'Another item-price export is already running for this service.' }
        $outputKeys = @($identities | ForEach-Object { $_.Path; if ($null -ne $_.FileId) { 'file-id:' + $_.FileId } })
        if ($null -ne $snapshotIdentity) { $outputKeys += $snapshotIdentity.Path }
        foreach ($pathKey in $outputKeys | Sort-Object -Unique) {
            $outputHasher = [Security.Cryptography.SHA256]::Create()
            try { $outputKey = [BitConverter]::ToString($outputHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($pathKey))).Replace('-', '') }
            finally { $outputHasher.Dispose() }
            $outputMutex = [Threading.Mutex]::new($false, ('Local\DungeonsForever.ItemPriceOutput.' + $outputKey))
            $outputHeld = $false
            try { $outputHeld = $outputMutex.WaitOne(0) }
            catch [Threading.AbandonedMutexException] { $outputHeld = $true }
            if (-not $outputHeld) { $outputMutex.Dispose(); throw 'Another export is already writing one of these CSV destinations.' }
            $outputLocks.Add($outputMutex)
        }
        if ($null -ne $snapshotDirectory) { Assert-WtlEmptySnapshotDirectory $snapshotDirectory }
        $listener = Get-WtlListener $baseUri
        Assert-WtlListener $listener $executable $null
        $outputDirectory = [IO.Path]::GetDirectoryName($outputFile)
        [void][IO.Directory]::CreateDirectory($outputDirectory)
        $itemOutputDirectory = [IO.Path]::GetDirectoryName($itemOutputFile)
        [void][IO.Directory]::CreateDirectory($itemOutputDirectory)
        $recipeOutputDirectory = [IO.Path]::GetDirectoryName($recipeOutputFile)
        [void][IO.Directory]::CreateDirectory($recipeOutputDirectory)
        $logDirectory = Join-Path $outputDirectory 'logs'
        [void][IO.Directory]::CreateDirectory($logDirectory)
        $script:ItemPriceRunLog = Join-Path $logDirectory ('export-{0}-{1}.log' -f [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'), [Guid]::NewGuid().ToString('N'))
        Write-ItemPriceLog ('Export log: {0}' -f $script:ItemPriceRunLog)
        if ($null -eq $listener) {
            $owned = Start-WtlService $executable $toolPath $baseUri $logDirectory
            $timer = [Diagnostics.Stopwatch]::StartNew()
            $ready = $false; $lastProblem = 'No listening socket yet.'
            while ($timer.Elapsed.TotalSeconds -lt $StartupTimeoutSec) {
                $owned.Refresh()
                if ($owned.HasExited) { throw 'wow.tools.local exited during startup. See the server logs.' }
                $listener = Get-WtlListener $baseUri
                Assert-WtlListener $listener $executable $owned
                if ($null -ne $listener) {
                    try {
                        $remaining = [Math]::Max(1, [Math]::Ceiling($StartupTimeoutSec - $timer.Elapsed.TotalSeconds))
                        $probe = Invoke-WtlTextRequest $baseUri 'casc/buildname' ([int][Math]::Min(3, $remaining))
                        if (-not [string]::IsNullOrWhiteSpace($probe)) { $ready = $true; break }
                    }
                    catch { $lastProblem = $_.Exception.Message }
                }
                Start-Sleep -Milliseconds 250
            }
            if (-not $ready) { throw ('Service startup timed out: {0}' -f $lastProblem) }
        }
        else { Write-ItemPriceLog ('Reusing the existing wow.tools.local process (PID {0}).' -f $listener.Id) }

        $build = (Invoke-WtlTextRequest $baseUri 'casc/buildname' $RequestTimeoutSec).Trim()
        if ($build -notmatch '^1\.60\.\d+\.(\d+)$') { throw ('Expected an active Forever 1.60.x client build, received: {0}' -f $build) }
        $buildNumber = ConvertTo-ItemPriceUInt32 $Matches[1] 'Client build' -Positive
        Write-ItemPriceLog ('Current client: {0}. Downloading latest classic_beta hotfixes.' -f $build)
        $cacheDirectory = Join-Path $toolPath 'caches'
        $before = Get-WtlCacheSnapshot $cacheDirectory
        $null = Invoke-WtlTextRequest $baseUri 'dbc/hotfixes/downloadLatest?branch=classic_beta' $RequestTimeoutSec
        $cache = Get-WtlFreshCache $cacheDirectory $before $buildNumber
        Write-ItemPriceLog ('Fresh hotfix cache: {0}; SHA256={1}' -f $cache.Path, $cache.SHA256)
        $reload = Invoke-WtlTextRequest $baseUri 'dbc/reloadHotfixes' $RequestTimeoutSec
        if ([string]::IsNullOrWhiteSpace($reload)) { throw 'Empty response while reloading hotfixes.' }

        $commonQuery = '&build=' + [uri]::EscapeDataString($build) + '&useHotfixes=true&newLinesInStrings=true&locale='
        $snapshotTables = @{}
        $relativeUrl = 'dbc/export/?name=item' + $commonQuery + 'enUS'
        $itemText = Invoke-WtlTextRequest $baseUri $relativeUrl $RequestTimeoutSec
        $items = ConvertFrom-WtlItemCsv $itemText 'item' 'enUS'
        if ($null -ne $snapshotDirectory) {
            $snapshotTables.item = @{ Text = $itemText; Url = [uri]::new($baseUri, $relativeUrl).AbsoluteUri; Rows = $items.Count }
        }
        $locales = @('enUS', 'zhTW', 'zhCN')
        $sparse = @{}
        foreach ($locale in $locales) {
            Write-ItemPriceLog ('Reading ItemSparse ({0}).' -f $locale)
            $relativeUrl = 'dbc/export/?name=itemsparse' + $commonQuery + $locale
            $text = Invoke-WtlTextRequest $baseUri $relativeUrl $RequestTimeoutSec
            $sparse[$locale] = ConvertFrom-WtlItemCsv $text 'itemsparse' $locale
            if ($null -ne $snapshotDirectory -and $locale -eq 'enUS') {
                $snapshotTables.itemsparse = @{ Text = $text; Url = [uri]::new($baseUri, $relativeUrl).AbsoluteUri; Rows = $sparse[$locale].Count }
            }
            $text = $null
        }
        $learningTables = @{}
        foreach ($tableName in @('itemeffect', 'itemxitemeffect', 'spelleffect', 'spelllearnspell', 'skilllineability', 'skillline')) {
            Write-ItemPriceLog ('Reading {0} learning evidence.' -f $tableName)
            $relativeUrl = 'dbc/export/?name=' + $tableName + $commonQuery + 'enUS'
            $text = Invoke-WtlTextRequest $baseUri $relativeUrl $RequestTimeoutSec
            $learningTables[$tableName] = ConvertFrom-WtlLearningCsv $text $tableName
            if ($null -ne $snapshotDirectory) {
                $snapshotTables[$tableName] = @{ Text = $text; Url = [uri]::new($baseUri, $relativeUrl).AbsoluteUri; Rows = $learningTables[$tableName].Count }
            }
            $text = $null
        }
        if ($null -ne $snapshotDirectory) {
            Write-ItemPriceLog 'Reading SpellName for the learning snapshot.'
            $relativeUrl = 'dbc/export/?name=spellname' + $commonQuery + 'enUS'
            $text = Invoke-WtlTextRequest $baseUri $relativeUrl $RequestTimeoutSec
            $spellNames = ConvertFrom-WtlLearningCsv $text 'spellname'
            $snapshotTables.spellname = @{ Text = $text; Url = [uri]::new($baseUri, $relativeUrl).AbsoluteUri; Rows = $spellNames.Count }
            $spellNames = $null; $text = $null
        }
        $recipeRows = @(Get-WtlRecipeItemRows $items $sparse $learningTables $build $cache.Build)
        $ids = [Collections.Generic.SortedSet[uint32]]::new()
        foreach ($itemId in $items.Keys) { [void]$ids.Add($itemId) }
        foreach ($locale in $locales) { foreach ($itemId in $sparse[$locale].Keys) { [void]$ids.Add($itemId) } }
        $stagingFile = Join-Path $outputDirectory ('.item-buy-prices-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        $itemStagingFile = Join-Path $itemOutputDirectory ('.item-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        $recipeStagingFile = Join-Path $recipeOutputDirectory ('.recipe-item-specializations-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        # Preserve all Item columns, values and row order from this same request.
        [IO.File]::WriteAllText($itemStagingFile, $itemText, [Text.UTF8Encoding]::new($true))
        $itemText = $null
        $writer = [IO.StreamWriter]::new($stagingFile, $false, [Text.UTF8Encoding]::new($true))
        $counts = @{ priced = 0; zero = 0; missing_item_sparse = 0 }
        $missingNames = @{ enUS = 0; zhTW = 0; zhCN = 0 }
        try {
            Write-ItemPriceCsvRecord $writer @('ItemID', 'Name_enUS', 'Name_zhTW', 'Name_zhCN', 'BuyPriceCopper', 'VendorStackCount', 'PriceStatus', 'Build', 'HotfixBuild')
            foreach ($itemId in $ids) {
                $names = @{}; $reference = $null
                foreach ($locale in $locales) {
                    $row = if ($sparse[$locale].ContainsKey($itemId)) { $sparse[$locale][$itemId] } else { $null }
                    $names[$locale] = if ($null -ne $row) { $row.Name } else { '' }
                    if ([string]::IsNullOrEmpty($names[$locale])) { $missingNames[$locale]++ }
                    if ($null -ne $row) {
                        if ($null -eq $reference) { $reference = $row }
                        elseif ($row.BuyPrice -ne $reference.BuyPrice -or $row.VendorStackCount -ne $reference.VendorStackCount) {
                            throw ('Conflicting price or VendorStackCount for item {0} in locale {1}.' -f $itemId, $locale)
                        }
                    }
                }
                $price = $null; $quantity = $null; $status = 'missing_item_sparse'
                if ($null -ne $reference) {
                    $price = $reference.BuyPrice; $quantity = $reference.VendorStackCount
                    $status = if ($price -eq 0) { 'zero' } else { 'priced' }
                }
                $counts[$status]++
                Write-ItemPriceCsvRecord $writer @($itemId, $names.enUS, $names.zhTW, $names.zhCN, $price, $quantity, $status, $build, $cache.Build)
            }
        }
        finally { $writer.Dispose() }
        $recipeWriter = [IO.StreamWriter]::new($recipeStagingFile, $false, [Text.UTF8Encoding]::new($true))
        $recipeCounts = @{ confirmed = 0; pending = 0 }
        try {
            Write-ItemPriceCsvRecord $recipeWriter @('RecipeItemID', 'RecipeSpellID', 'RequiredAbility', 'Status', 'Reason', 'LearningPath', 'Build', 'HotfixBuild', 'Source')
            foreach ($row in $recipeRows) {
                $recipeCounts[$row.Status]++
                Write-ItemPriceCsvRecord $recipeWriter @($row.RecipeItemID, $row.RecipeSpellID, $row.RequiredAbility, $row.Status, $row.Reason, $row.LearningPath, $row.Build, $row.HotfixBuild, $row.Source)
            }
        }
        finally { $recipeWriter.Dispose() }
        $finalBuild = (Invoke-WtlTextRequest $baseUri 'casc/buildname' $RequestTimeoutSec).Trim()
        if ($finalBuild -ne $build -or (Get-WtlFileSHA256 $cache.Path) -ne $cache.SHA256) {
            throw 'The active client build or downloaded cache changed during export. Retry without changing the tool settings.'
        }
        if ($null -ne $snapshotDirectory) {
            Write-WtlLearningSnapshot $snapshotDirectory $snapshotTables $build $cache
            Write-ItemPriceLog ('Learning snapshot: {0}' -f $snapshotDirectory)
        }
        Publish-WtlCsvPair @(
            [pscustomobject]@{ OutputPath = $outputFile; StagingPath = $stagingFile },
            [pscustomobject]@{ OutputPath = $itemOutputFile; StagingPath = $itemStagingFile },
            [pscustomobject]@{ OutputPath = $recipeOutputFile; StagingPath = $recipeStagingFile }
        )
        $stagingFile = $null; $itemStagingFile = $null; $recipeStagingFile = $null
        Write-ItemPriceLog ('Exported {0} IDs: priced={1}, zero={2}, missing price={3}.' -f $ids.Count, $counts.priced, $counts.zero, $counts.missing_item_sparse)
        Write-ItemPriceLog ('Missing names: enUS={0}, zhTW={1}, zhCN={2}.' -f $missingNames.enUS, $missingNames.zhTW, $missingNames.zhCN)
        Write-ItemPriceLog ('CSV: {0}' -f $outputFile)
        Write-ItemPriceLog ('Raw Item CSV: {0} ({1} rows).' -f $itemOutputFile, $items.Count)
        Write-ItemPriceLog ('Recipe-item CSV: {0} ({1} rows; confirmed={2}, pending={3}).' -f $recipeOutputFile, $recipeRows.Count, $recipeCounts.confirmed, $recipeCounts.pending)
        return [pscustomobject]@{
            OutputPath = $outputFile; ItemOutputPath = $itemOutputFile; ItemCount = $items.Count
            RecipeItemOutputPath = $recipeOutputFile; RecipeItemCount = $recipeRows.Count; RecipeItemCounts = $recipeCounts
            LearningSnapshotPath = $snapshotDirectory
            Build = $build; HotfixBuild = $cache.Build
            HotfixSHA256 = $cache.SHA256; Count = $ids.Count
            PriceCounts = $counts; MissingNames = $missingNames; LogPath = $script:ItemPriceRunLog
        }
    }
    catch {
        Write-ItemPriceLog ('FAILED: {0}' -f $_.Exception.Message)
        throw
    }
    finally {
        foreach ($temporaryFile in @($stagingFile, $itemStagingFile, $recipeStagingFile)) {
            if ($null -ne $temporaryFile -and [IO.File]::Exists($temporaryFile)) {
                try { [IO.File]::Delete($temporaryFile) }
                catch { Write-Warning ('Could not remove temporary file {0}: {1}' -f $temporaryFile, $_.Exception.Message) }
            }
        }
        if ($null -ne $owned) {
            try { Stop-WtlOwnedProcess $owned $executable }
            catch { Write-Warning ('Could not close the process started by this run: {0}' -f $_.Exception.Message) }
        }
        if ($lockHeld) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
        foreach ($outputMutex in $outputLocks) { $outputMutex.ReleaseMutex(); $outputMutex.Dispose() }
        $script:ItemPriceRunLog = $null
    }
}

# Dot sourcing exposes helpers for offline tests without launching the exporter.
if ($MyInvocation.InvocationName -ne '.') {
    try {
        $null = Invoke-ItemBuyPriceExport -ToolDirectory $ToolDirectory -BaseUrl $BaseUrl -OutputPath $OutputPath `
            -ItemOutputPath $ItemOutputPath -RecipeItemOutputPath $RecipeItemOutputPath `
            -LearningSnapshotPath $LearningSnapshotPath `
            -StartupTimeoutSec $StartupTimeoutSec -RequestTimeoutSec $RequestTimeoutSec
        exit 0
    }
    catch { Write-Error -Message $_.Exception.Message -ErrorAction Continue; exit 1 }
}
