#Requires -Version 5.1
<#
.SYNOPSIS
Export NPC reputation affiliations from an existing WTL service or a frozen snapshot.
.NOTES
Does not start WTL, download/reload hotfixes, generate Lua, or infer player A/H/N access.
#>
[CmdletBinding()]
param(
    [string]$Build = '',
    [string]$BaseUrl = 'http://127.0.0.1:5000',
    [string]$InputSnapshotPath = '',
    [string]$OutputDirectory = 'output',
    [string]$NpcCsvPath = '',
    [string]$HotfixCachePath = '',
    [switch]$WithoutHotfixes,
    [ValidateRange(1,3600)][int]$RequestTimeoutSec = 300
)

$script:NFScriptDirectory = $PSScriptRoot
$script:NFRepositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Resolve-NFPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'An input/output path is empty.' }
    if (-not [IO.Path]::IsPathRooted($Path)) { $Path = Join-Path $script:NFScriptDirectory $Path }
    return [IO.Path]::GetFullPath($Path)
}

function Assert-NFOutputPath([string]$Path) {
    $root = $script:NFRepositoryRoot.TrimEnd([char[]]@('\','/'))
    if (-not $Path.StartsWith($root + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Output must stay inside the current repository.'
    }
    $candidate = $Path
    while ($candidate) {
        if (Test-Path -LiteralPath $candidate) {
            if ((Get-Item -LiteralPath $candidate -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Output ancestors must not be junctions or symbolic links.'
            }
        }
        $candidate = [IO.Path]::GetDirectoryName($candidate)
    }
}

function Get-NFSHA([byte[]]$Bytes) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hasher.ComputeHash($Bytes)).Replace('-','').ToLowerInvariant() }
    finally { $hasher.Dispose() }
}

function Get-NFProperty($Object,[string]$Name) {
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}

function Get-NFText([byte[]]$Bytes) {
    return ([Text.UTF8Encoding]::new($false,$true)).GetString($Bytes).TrimStart([char]0xFEFF)
}

function Invoke-NFGet([uri]$BaseUri,[string]$RelativeUrl,[int]$TimeoutSec) {
    Add-Type -AssemblyName System.Net.Http
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
    $response = $null
    try {
        $response = $client.GetAsync([uri]::new($BaseUri,$RelativeUrl)).GetAwaiter().GetResult()
        if ([int]$response.StatusCode -ne 200) { throw ('HTTP {0}: {1}' -f [int]$response.StatusCode,$RelativeUrl) }
        $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        return ,$bytes
    }
    finally { if ($null -ne $response) { $response.Dispose() }; $client.Dispose() }
}

function ConvertTo-NFNumber($Value,[string]$Label,[uint32]$Minimum = 0) {
    $text = [string]$Value
    $number = [uint32]0
    if ($text -notmatch '^\d+$' -or -not [uint32]::TryParse($text,[ref]$number) -or $number -lt $Minimum) {
        throw ('Invalid unsigned integer {0}: {1}' -f $Label,$text)
    }
    return $number
}

function Read-NFCsv([byte[]]$Bytes,[string[]]$Required,[string]$Label) {
    Add-Type -AssemblyName Microsoft.VisualBasic
    $reader = [IO.StringReader]::new((Get-NFText $Bytes))
    $parser = [Microsoft.VisualBasic.FileIO.TextFieldParser]::new($reader)
    $parser.TextFieldType = [Microsoft.VisualBasic.FileIO.FieldType]::Delimited
    $parser.SetDelimiters(',')
    $parser.HasFieldsEnclosedInQuotes = $true
    $parser.TrimWhiteSpace = $false
    try {
        if ($parser.EndOfData) { throw ('Empty CSV: {0}' -f $Label) }
        $headers = $parser.ReadFields()
        $unique = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($field in $headers) {
            if ([string]::IsNullOrWhiteSpace($field) -or -not $unique.Add($field)) { throw ('Invalid/duplicate header in {0}' -f $Label) }
        }
        foreach ($field in $Required) { if ($headers -cnotcontains $field) { throw ('Missing column {0} in {1}' -f $field,$Label) } }
        $rows = [Collections.Generic.List[object]]::new()
        $byID = @{}
        while (-not $parser.EndOfData) {
            $values = $parser.ReadFields()
            if ($values.Length -ne $headers.Length) { throw ('Wrong CSV field count in {0}' -f $Label) }
            $row = @{}
            for ($i=0; $i -lt $headers.Length; $i++) { $row[$headers[$i]] = $values[$i] }
            $id = ConvertTo-NFNumber $row.ID ($Label + '.ID') 1
            if ($byID.ContainsKey($id)) { throw ('Duplicate ID {0} in {1}' -f $id,$Label) }
            $byID[$id] = $row
            $rows.Add($row)
        }
        return [pscustomobject]@{ Headers=$headers; Rows=$rows; ByID=$byID }
    }
    finally { $parser.Dispose(); $reader.Dispose() }
}

function Get-NFFactionLocale([byte[]]$Bytes) {
    if ($Bytes.Length -lt 40) { throw 'Truncated Faction DB2 locale evidence.' }
    $magic = [Text.Encoding]::ASCII.GetString($Bytes,0,4)
    if ($magic -notmatch '^WDC[1-5]$') { throw 'Unsupported Faction DB2 locale evidence.' }
    $header = if ($magic -eq 'WDC5') { 136 } else { 4 }
    if ($Bytes.Length -lt $header+36 -or [BitConverter]::ToUInt32($Bytes,$header+16) -ne 116794583) {
        throw 'Wrong Faction DB2 table hash or truncated header.'
    }
    return [BitConverter]::ToUInt32($Bytes,$header+32)
}

function Write-NFCsv([string]$Path,[string[]]$Headers,$Rows) {
    $writer = [IO.StreamWriter]::new($Path,$false,[Text.UTF8Encoding]::new($true))
    try {
        $writer.WriteLine(($Headers | ForEach-Object { '"' + $_.Replace('"','""') + '"' }) -join ',')
        foreach ($row in $Rows) {
            $writer.WriteLine(($Headers | ForEach-Object { '"' + ([string]$row[$_]).Replace('"','""') + '"' }) -join ',')
        }
    }
    finally { $writer.Dispose() }
}

function Read-NFSnapshotFile([string]$Directory,[string]$Relative,[string]$Hash) {
    if ($Relative -notmatch '^(raw/)?[a-zA-Z0-9_.-]+$') { throw 'Invalid snapshot relative filename.' }
    $path = [IO.Path]::GetFullPath((Join-Path $Directory $Relative))
    if (-not $path.StartsWith($Directory.TrimEnd([char[]]@('\','/'))+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Snapshot file escapes its directory.'
    }
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($Hash -notmatch '^[a-fA-F0-9]{64}$' -or (Get-NFSHA $bytes) -ne $Hash.ToLowerInvariant()) { throw ('Snapshot SHA256 mismatch: {0}' -f $Relative) }
    return ,$bytes
}

function Invoke-NPCFactionExport {
    [CmdletBinding()]
    param([string]$Build,[string]$BaseUrl='http://127.0.0.1:5000',[string]$InputSnapshotPath='',
        [string]$OutputDirectory='output',[string]$NpcCsvPath='',[string]$HotfixCachePath='',
        [switch]$WithoutHotfixes,[int]$RequestTimeoutSec=300)
    Set-StrictMode -Version 2
    $ErrorActionPreference = 'Stop'
    if ($Build -notmatch '^\d+\.\d+\.\d+\.(\d+)$') { throw 'Build must have four numeric components.' }
    $buildNumber = ConvertTo-NFNumber $Matches[1] 'Build' 1
    $destination = Resolve-NFPath $OutputDirectory
    Assert-NFOutputPath $destination
    if (Test-Path -LiteralPath $destination) { throw 'OutputDirectory must be new; existing snapshots are never overwritten.' }
    $raw = @{}; $tables = [Collections.Generic.List[object]]::new(); $headers = @{}
    $hotfix = [ordered]@{ requested=$false; build=$null; serverAttested=$false; reason='No hotfixes requested.' }
    $requirements = @{ creaturedifficulty=@('ID','CreatureID','FactionTemplateID'); factiontemplate=@('ID','Faction'); faction=@('ID','Name_lang') }
    $foreignKeys = @{ creaturedifficulty=@{ CreatureID='Creature::ID'; FactionTemplateID='FactionTemplate::ID' }; factiontemplate=@{ Faction='Faction::ID' }; faction=@{} }
    $localeMasks = @{ enUS=[uint32]1; zhCN=[uint32]16; zhTW=[uint32]32 }
    $snapshotInput = $null; $manifest = $null
    if ($InputSnapshotPath) {
        if ($HotfixCachePath -or $WithoutHotfixes) { throw 'Snapshot replay takes hotfix evidence from its manifest.' }
        $snapshotInput = Resolve-NFPath $InputSnapshotPath
        $manifest = Get-Content -LiteralPath (Join-Path $snapshotInput 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($manifest.schema -ne 1 -or $manifest.producer -ne 'DungeonsForever.NPCFactionExport' -or $manifest.build -ne $Build) { throw 'Snapshot schema/producer/build mismatch.' }
        foreach ($file in $manifest.files.PSObject.Properties) {
            $bytes = Read-NFSnapshotFile $snapshotInput $file.Name $file.Value.sha256
            if ($bytes.Length -ne $file.Value.bytes) { throw 'Snapshot byte-count mismatch.' }
        }
        $hotfix = $manifest.hotfix
        foreach ($entry in $manifest.tables) {
            $key = $entry.table + '_' + $entry.locale
            if ($raw.ContainsKey($entry.file)) { throw 'Duplicate snapshot table file.' }
            $raw[$entry.file] = Read-NFSnapshotFile $snapshotInput $entry.file $entry.sha256
            $raw[$entry.header.file] = Read-NFSnapshotFile $snapshotInput $entry.header.file $entry.header.sha256
            if ($null -ne (Get-NFProperty $entry 'localeProof')) {
                $raw[$entry.localeProof.file] = Read-NFSnapshotFile $snapshotInput $entry.localeProof.file $entry.localeProof.sha256
            }
            $tables.Add($entry)
        }
        if ($hotfix.requested) {
            $raw[$hotfix.file] = Read-NFSnapshotFile $snapshotInput $hotfix.file $hotfix.sha256
        }
        if ($null -ne $manifest.targets) {
            $raw[$manifest.targets.file] = Read-NFSnapshotFile $snapshotInput $manifest.targets.file $manifest.targets.sha256
        }
    }
    else {
        $baseUri = [uri]($BaseUrl.TrimEnd('/')+'/')
        if (-not $baseUri.IsAbsoluteUri -or $baseUri.Scheme -ne 'http' -or -not $baseUri.IsLoopback -or $baseUri.AbsolutePath -ne '/' -or $baseUri.Query -or $baseUri.Fragment -or $baseUri.UserInfo) { throw 'BaseUrl must be a loopback HTTP origin.' }
        if (-not $WithoutHotfixes -and -not $HotfixCachePath) { throw 'Supply HotfixCachePath or explicitly use WithoutHotfixes.' }
        if ($WithoutHotfixes -and $HotfixCachePath) { throw 'WithoutHotfixes and HotfixCachePath are mutually exclusive.' }
        if ($HotfixCachePath) {
            $cache = [IO.File]::ReadAllBytes((Resolve-NFPath $HotfixCachePath))
            if ($cache.Length -lt 44 -or [Text.Encoding]::ASCII.GetString($cache,0,4) -ne 'XFTH' -or [BitConverter]::ToUInt32($cache,4) -notin @(8,9) -or [BitConverter]::ToUInt32($cache,8) -ne $buildNumber) { throw 'Hotfix cache magic/version/build mismatch.' }
            $raw['raw/DBCache.bin'] = $cache
            $hotfix = [ordered]@{ requested=$true; build=$buildNumber; formatVersion=[BitConverter]::ToUInt32($cache,4); file='raw/DBCache.bin'; sha256=(Get-NFSHA $cache); serverAttested=$false; reason='Matching nominated cache retained; WTL provides no attestation that this exact cache was applied. Operator must load it before export.' }
        }
        $activeBuild = (Get-NFText (Invoke-NFGet $baseUri 'casc/buildname' $RequestTimeoutSec)).Trim()
        if ($activeBuild -ne $Build) { throw 'WTL active build differs from requested Build.' }
        $escapedBuild = [uri]::EscapeDataString($Build)
        foreach ($table in @('creaturedifficulty','factiontemplate','faction')) {
            $headerUrl = 'dbc/header/'+$table+'?build='+$escapedBuild
            $headerBytes = Invoke-NFGet $baseUri $headerUrl $RequestTimeoutSec
            $headerFile = 'raw/'+$table+'.header.json'; $raw[$headerFile] = $headerBytes
            $locales = if ($table -eq 'faction') { @('enUS','zhCN','zhTW') } else { @('enUS') }
            foreach ($locale in $locales) {
                $query = 'dbc/export/?name='+$table+'&build='+$escapedBuild+'&useHotfixes='+([string][bool]$hotfix.requested).ToLowerInvariant()+'&newLinesInStrings=true&locale='+$locale
                $bytes = Invoke-NFGet $baseUri $query $RequestTimeoutSec
                $file = 'raw/'+$table+'_'+$locale+'.csv'; $raw[$file] = $bytes
                $entry = [ordered]@{ table=$table; locale=$locale; file=$file; sha256=(Get-NFSHA $bytes); sourceUrl=([uri]::new($baseUri,$query).AbsoluteUri); header=@{file=$headerFile;sha256=(Get-NFSHA $headerBytes);sourceUrl=([uri]::new($baseUri,$headerUrl).AbsoluteUri)} }
                if ($table -eq 'faction') {
                    $binaryUrl = 'dbc/export/db2?tableName=faction&fullBuild='+$escapedBuild+'&locale='+$locale
                    $binary = Invoke-NFGet $baseUri $binaryUrl $RequestTimeoutSec
                    $binaryFile = 'raw/faction_'+$locale+'.db2'; $raw[$binaryFile] = $binary
                    $entry.localeProof = @{file=$binaryFile;sha256=(Get-NFSHA $binary);sourceUrl=([uri]::new($baseUri,$binaryUrl).AbsoluteUri)}
                }
                $tables.Add([pscustomobject]$entry)
            }
        }
        if ((Get-NFText (Invoke-NFGet $baseUri 'casc/buildname' $RequestTimeoutSec)).Trim() -ne $Build) { throw 'WTL build changed during export.' }
    }
    if ($hotfix.requested) {
        $cache = $raw[$hotfix.file]
        if ($cache.Length -lt 44 -or [Text.Encoding]::ASCII.GetString($cache,0,4) -ne 'XFTH' -or [BitConverter]::ToUInt32($cache,4) -notin @(8,9) -or [BitConverter]::ToUInt32($cache,8) -ne $buildNumber -or $hotfix.build -ne $buildNumber) { throw 'Snapshot hotfix magic/version/build mismatch.' }
    }
    $data = @{}; $localeState = @{}
    foreach ($entry in $tables) {
        $table = $entry.table; $locale = $entry.locale; $key = $table+'_'+$locale
        if (-not $requirements.ContainsKey($table) -or -not $localeMasks.ContainsKey($locale) -or $data.ContainsKey($key)) { throw 'Unexpected/duplicate snapshot table or locale.' }
        $header = Get-NFText $raw[$entry.header.file] | ConvertFrom-Json
        if ($header.error) { throw ('WTL header error: '+$header.error) }
        foreach ($field in $requirements[$table]) { if ($header.headers -cnotcontains $field) { throw ('WTL header lacks '+$field) } }
        foreach ($field in $foreignKeys[$table].Keys) {
            if ((Get-NFProperty $header.fks $field) -cne $foreignKeys[$table][$field]) { throw ('WTL foreign key mismatch: '+$table+'.'+$field) }
        }
        $parsed = Read-NFCsv $raw[$entry.file] $requirements[$table] $key
        $data[$key] = $parsed
        $entry | Add-Member -NotePropertyName headers -NotePropertyValue $parsed.Headers -Force
        $entry | Add-Member -NotePropertyName rows -NotePropertyValue $parsed.Rows.Count -Force
        if ($table -eq 'faction') {
            $mask = Get-NFFactionLocale $raw[$entry.localeProof.file]
            $verified = $mask -eq $localeMasks[$locale]
            $localeState[$locale] = @{verified=$verified;db2LocaleMask=$mask;expectedMask=$localeMasks[$locale];reason=if($verified){'Matching Faction DB2 locale mask.'}else{'Requested locale was not confirmed by returned DB2; names omitted.'}}
        }
    }
    foreach ($key in @('creaturedifficulty_enUS','factiontemplate_enUS','faction_enUS','faction_zhCN','faction_zhTW')) { if (-not $data.ContainsKey($key)) { throw ('Missing snapshot table '+$key) } }
    $factionIDs = [Collections.Generic.SortedSet[uint32]]::new()
    foreach ($locale in @('enUS','zhCN','zhTW')) { foreach ($id in $data['faction_'+$locale].ByID.Keys) { [void]$factionIDs.Add($id) } }
    $factionRows = [Collections.Generic.List[object]]::new()
    foreach ($id in $factionIDs) {
        $row = @{ ID=$id;Name_enUS='';Name_zhCN='';Name_zhTW='' }
        foreach ($locale in @('enUS','zhCN','zhTW')) {
            if ($localeState[$locale].verified -and $data['faction_'+$locale].ByID.ContainsKey($id)) { $row['Name_'+$locale]=$data['faction_'+$locale].ByID[$id].Name_lang }
        }
        $factionRows.Add($row)
    }
    $templates = $data.factiontemplate_enUS.ByID
    foreach ($id in @($templates.Keys)) { $templates[$id].Faction = ConvertTo-NFNumber $templates[$id].Faction 'FactionTemplate.Faction' }
    $npcGroups = @{}
    foreach ($row in $data.creaturedifficulty_enUS.Rows) {
        $npc = ConvertTo-NFNumber $row.CreatureID 'CreatureDifficulty.CreatureID' 1
        $row.FactionTemplateID = ConvertTo-NFNumber $row.FactionTemplateID 'CreatureDifficulty.FactionTemplateID'
        if (-not $npcGroups.ContainsKey($npc)) { $npcGroups[$npc] = [Collections.Generic.List[object]]::new() }
        $npcGroups[$npc].Add($row)
    }
    $targets = [Collections.Generic.SortedSet[uint32]]::new()
    $npcInput = $null
    if ($NpcCsvPath -or (($null -ne $snapshotInput) -and ($null -ne $manifest.targets))) {
        if ($NpcCsvPath) {
            $npcPath = Resolve-NFPath $NpcCsvPath; $npcBytes = [IO.File]::ReadAllBytes($npcPath)
        }
        else { $npcPath=$manifest.targets.sourcePath; $npcBytes=$raw[$manifest.targets.file] }
        $raw['raw/npc-targets.csv'] = $npcBytes
        $npcText = Get-NFText $npcBytes
        $npcRecords = @($npcText | ConvertFrom-Csv)
        if (-not $npcRecords.Count) { throw 'NpcCsvPath contains no NPC rows.' }
        $columns = @($npcRecords[0].PSObject.Properties.Name)
        $npcField = @('npc_id','NPCID','ID') | Where-Object { $columns -ccontains $_ } | Select-Object -First 1
        if (-not $npcField) { throw 'NpcCsvPath needs npc_id, NPCID, or ID.' }
        foreach ($record in $npcRecords) { [void]$targets.Add((ConvertTo-NFNumber $record.$npcField 'NPC target' 1)) }
        $npcInput = @{file='raw/npc-targets.csv';sourcePath=$npcPath;sha256=(Get-NFSHA $npcBytes);rows=$npcRecords.Count;uniqueNPCs=$targets.Count}
    }
    else { foreach ($npc in $npcGroups.Keys) { [void]$targets.Add($npc) } }
    $npcRows = [Collections.Generic.List[object]]::new(); $details = [Collections.Generic.List[object]]::new()
    $counts = @{'resolved'=0;'missing-template'=0;'missing-faction'=0;'conflict'=0;'no-faction'=0}
    foreach ($npc in $targets) {
        $candidates = [Collections.Generic.List[object]]::new(); $resolved = [Collections.Generic.SortedSet[uint32]]::new()
        $templateIDs = [Collections.Generic.SortedSet[uint32]]::new(); $difficultyIDs = [Collections.Generic.SortedSet[uint32]]::new()
        $missingTemplate=$false; $missingFaction=$false; $zeroFaction=$false
        if ($npcGroups.ContainsKey($npc)) {
            foreach ($row in $npcGroups[$npc]) {
                $difficulty = ConvertTo-NFNumber $row.ID 'CreatureDifficulty.ID' 1; [void]$difficultyIDs.Add($difficulty)
                $template = $row.FactionTemplateID; [void]$templateIDs.Add($template); $faction = $null
                if ($template -eq 0) { $zeroFaction=$true }
                elseif (-not $templates.ContainsKey($template)) { $missingTemplate=$true }
                else {
                    $faction = $templates[$template].Faction
                    if ($faction -eq 0) { $zeroFaction=$true }
                    elseif (-not $factionIDs.Contains($faction)) { $missingFaction=$true }
                    else { [void]$resolved.Add($faction) }
                }
                $candidates.Add(@{creatureDifficultyID=$difficulty;factionTemplateID=$template;factionID=$faction})
            }
        }
        $status='no-faction'; $factionID=''
        if (($resolved.Count -gt 1) -or (($resolved.Count -eq 1) -and $zeroFaction)) { $status='conflict' }
        elseif ($missingTemplate) { $status='missing-template' }
        elseif ($missingFaction) { $status='missing-faction' }
        elseif ($resolved.Count -eq 1) { $status='resolved'; $factionID=@($resolved)[0] }
        $npcRows.Add(@{npc_id=$npc;faction_id=$factionID;status=$status;faction_template_ids=(@($templateIDs)-join ';');creature_difficulty_ids=(@($difficultyIDs)-join ';')})
        $details.Add(@{npc_id=$npc;status=$status;candidates=@($candidates);reason=if(-not $difficultyIDs.Count){'No observed CreatureDifficulty record; absence does not prove no affiliation.'}elseif($status -eq 'no-faction'){'Observed zero FactionTemplateID or Faction value.'}else{$status}})
        $counts[$status]++
    }
    $parent = [IO.Path]::GetDirectoryName($destination)
    [void][IO.Directory]::CreateDirectory($parent)
    $staging = Join-Path $parent ('.npc-factions-'+[Guid]::NewGuid().ToString('N')+'.tmp')
    Assert-NFOutputPath $staging
    try {
        [void][IO.Directory]::CreateDirectory((Join-Path $staging 'raw'))
        foreach ($relative in $raw.Keys) { [IO.File]::WriteAllBytes((Join-Path $staging $relative),$raw[$relative]) }
        Write-NFCsv (Join-Path $staging 'factions.csv') @('ID','Name_enUS','Name_zhCN','Name_zhTW') $factionRows
        Write-NFCsv (Join-Path $staging 'npc-factions.csv') @('npc_id','faction_id','status','faction_template_ids','creature_difficulty_ids') $npcRows
        $report = @{counts=$counts;localeEvidence=$localeState;npcs=@($details);limitations=@('NPC affiliation is not player A/H/N merchant access.','Missing client evidence is not proof of no affiliation.','Language columns require the returned Faction DB2 locale mask to match.')}
        [IO.File]::WriteAllText((Join-Path $staging 'report.json'),($report|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
        $artifacts = @{}
        foreach ($file in @('factions.csv','npc-factions.csv','report.json')) { $artifacts[$file]=@{file=$file;sha256=(Get-NFSHA ([IO.File]::ReadAllBytes((Join-Path $staging $file))))} }
        $files = @{}
        foreach ($file in Get-ChildItem -LiteralPath $staging -Recurse -File) {
            $relative = $file.FullName.Substring($staging.Length+1).Replace('\','/')
            $files[$relative]=@{sha256=(Get-NFSHA ([IO.File]::ReadAllBytes($file.FullName)));bytes=$file.Length}
        }
        $manifest = [ordered]@{schema=1;producer='DungeonsForever.NPCFactionExport';build=$Build;hotfix=$hotfix;tables=@($tables);localeEvidence=$localeState;targets=$npcInput;counts=$counts;artifacts=$artifacts;files=$files;replayOf=$snapshotInput}
        [IO.File]::WriteAllText((Join-Path $staging 'manifest.json'),($manifest|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $destination) { throw 'OutputDirectory appeared during export.' }
        Move-Item -LiteralPath $staging -Destination $destination
        return [pscustomobject]@{Directory=$destination;Counts=$counts;Factions=$factionRows.Count;NPCs=$npcRows.Count}
    }
    finally {
        if (Test-Path -LiteralPath $staging) { Assert-NFOutputPath $staging; Remove-Item -LiteralPath $staging -Recurse -Force }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $result = Invoke-NPCFactionExport -Build $Build -BaseUrl $BaseUrl -InputSnapshotPath $InputSnapshotPath `
            -OutputDirectory $OutputDirectory -NpcCsvPath $NpcCsvPath -HotfixCachePath $HotfixCachePath `
            -WithoutHotfixes:$WithoutHotfixes -RequestTimeoutSec $RequestTimeoutSec
        $result | ConvertTo-Json -Depth 4
        exit 0
    }
    catch { Write-Error -Message $_.Exception.Message -ErrorAction Continue; exit 1 }
}
