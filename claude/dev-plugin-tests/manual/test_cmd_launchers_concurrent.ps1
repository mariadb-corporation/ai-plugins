# Copyright (c) 2026, MariaDB plc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2.0,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License, version 2.0, for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

# Manual test of the Windows launchers (mariadb-mcp-launcher.cmd and
# mariadb-lsp-launcher.cmd) started together, on a Windows machine with network
# access to the mariadb-shell releases. Not run by CI.
#
# It copies the launchers from -Src, points them at a scratch prefix and bin
# folder per scenario, starts them as an MCP/LSP client does (stdin and stdout
# piped, stderr to a file), speaks the protocol (MCP: initialize + tools/list,
# LSP: initialize) and checks that stdout carries nothing else. It never touches
# %LOCALAPPDATA%\Programs\mariadb-shell, and deletes each scenario's folders,
# and the temp folders of installers it killed, as soon as they are checked
# (each unpacked shell is a few hundred MB).
#
# Scenarios: two (2 launchers into a fresh prefix), three (3 launchers + the
# LSP launcher, then one more launcher while the servers run), kill (a launcher
# killed with its tree during the install, then a new one), orphan (only the
# launcher's cmd.exe killed, as a harness does, while its installer runs on).
#
# Run it with each PowerShell, since the launchers inherit the caller's
# environment (PowerShell 7's PSModulePath, for one):
#   powershell -NoProfile -ExecutionPolicy Bypass -File test_cmd_launchers_concurrent.ps1 -Src <scripts dir>
#   pwsh       -NoProfile -ExecutionPolicy Bypass -File test_cmd_launchers_concurrent.ps1 -Src <scripts dir>
#
#   -Src           folder with the two .cmd launchers (and a Hermes plugin's
#                  *.SHA256SUMS); default: claude/dev-plugin/scripts beside this suite
#   -InstallerRef  run install.ps1 from this mariadb-shell ref instead of main,
#                  e.g. refs/heads/<branch> (shared launcher only; Hermes pins a commit)
#   -Work          a new, empty folder for the run (default: a new temp folder);
#                  removed at the end
#   -Scenarios     a subset of: two three kill orphan
#   -Timeout       seconds each scenario may take
# Exit code 1 when a check failed.
param(
    [string] $Src = (Join-Path $PSScriptRoot '..\..\dev-plugin\scripts'),
    [string] $InstallerRef = '',
    [string] $Work = (Join-Path ([IO.Path]::GetTempPath()) ('mariadb-launcher-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))),
    [string[]] $Scenarios = @('two', 'three', 'kill', 'orphan'),
    [int] $Timeout = 300
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Check([bool] $ok, [string] $what) {
    if ($ok) { Write-Output "  ok    $what" } else { Write-Output "  FAIL  $what"; $failures.Add("${script:scenario}: $what") }
}
$script:scenario = ''

# taskkill through cmd: a process that is already gone must not raise
# NativeCommandError under $ErrorActionPreference = 'Stop' (PowerShell 5.1).
function Stop-Pid([int] $id, [string] $flags) { & cmd.exe /d /c "taskkill $flags /PID $id >nul 2>&1" | Out-Null }

# --- launcher copies ----------------------------------------------------------
if ((Test-Path $Work) -and @(Get-ChildItem $Work -Force).Count) { throw "-Work must be a new or empty folder: $Work" }
$scripts = Join-Path $Work 'scripts'
New-Item -ItemType Directory -Force $scripts | Out-Null
foreach ($n in 'mariadb-mcp-launcher.cmd', 'mariadb-lsp-launcher.cmd') {
    $t = [IO.File]::ReadAllText((Join-Path $Src $n))
    if ($InstallerRef -and $n -like 'mariadb-mcp*') {
        $from = '/main/install.ps1"'
        if (-not $t.Contains($from)) { throw "no '$from' in $n to point at $InstallerRef" }
        $t = $t.Replace($from, "/$InstallerRef/install.ps1`"")
    }
    [IO.File]::WriteAllText((Join-Path $scripts $n), $t)
}
Get-ChildItem $Src -Filter '*.SHA256SUMS' | Copy-Item -Destination $scripts
$mcpCmd = Join-Path $scripts 'mariadb-mcp-launcher.cmd'
$lspCmd = Join-Path $scripts 'mariadb-lsp-launcher.cmd'
$cleanPath = (($env:Path -split ';') | Where-Object { $_ -and $_ -notmatch 'mariadb-shell' }) -join ';'

function Temp-Leftovers {
    @(Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'mariadb-shell-install-*' -or $_.Name -like 'mariadb-mcp-launcher-*' } |
        ForEach-Object { $_.FullName })
}

# --- processes ----------------------------------------------------------------
function Start-Launcher([string] $name, [string] $dir, [string] $cmd, [string] $kind) {
    $err = Join-Path $dir "$name.err"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $psi.Arguments = "/d /s /c `"`"$cmd`" 2>`"$err`"`""
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $dir
    $envs = $psi.EnvironmentVariables
    foreach ($k in 'MARIADB_SHELL_BIN', 'MARIADB_LSP_BIN', 'MARIADB_SHELL_TAG') { if ($envs.ContainsKey($k)) { $envs.Remove($k) } }
    $envs['Path'] = $cleanPath
    $envs['MARIADB_SHELL_PREFIX'] = Join-Path $dir 'pfx'
    $envs['MARIADB_SHELL_BINDIR'] = Join-Path $dir 'pfx\bin'
    $envs['MARIADB_LSP_WAIT'] = "$Timeout"
    $p = [System.Diagnostics.Process]::Start($psi)
    [pscustomobject]@{ Name = $name; Kind = $kind; P = $p; Err = $err; Out = (New-Object System.Collections.Generic.List[string]); Pending = $null; Started = Get-Date }
}

# Next stdout line, or $null at EOF; throws 'timeout' when none came by $deadline.
function Read-Out($l, [datetime] $deadline) {
    if ($null -eq $l.Pending) { $l.Pending = $l.P.StandardOutput.ReadLineAsync() }
    while (-not $l.Pending.Wait(500)) {
        if ((Get-Date) -gt $deadline) { throw 'timeout' }
    }
    $line = $l.Pending.Result
    $l.Pending = $null
    if ($null -ne $line) { $l.Out.Add($line) }
    return $line
}

function Send-Mcp($l, [string] $json) { $l.P.StandardInput.Write("$json`n"); $l.P.StandardInput.Flush() }

# Wait for the JSON-RPC response with this id; every line before it must be JSON-RPC.
function Wait-Mcp($l, [int] $id, [datetime] $deadline) {
    while ($true) {
        $line = Read-Out $l $deadline
        if ($null -eq $line) { return $null }
        $o = $null
        try { $o = $line | ConvertFrom-Json } catch { }
        if ($null -eq $o -or -not ($o.PSObject.Properties.Name -contains 'jsonrpc')) { throw "not JSON-RPC on stdout: $line" }
        if (($o.PSObject.Properties.Name -contains 'id') -and $o.id -eq $id) { return $o }
    }
}

function Send-Lsp($l, [string] $json) {
    $l.P.StandardInput.Write("Content-Length: $([Text.Encoding]::UTF8.GetByteCount($json))`r`n`r`n$json")
    $l.P.StandardInput.Flush()
}

function Wait-Lsp($l, [int] $id, [datetime] $deadline) {
    while ($true) {
        $len = -1
        while ($true) {
            $h = Read-Out $l $deadline
            if ($null -eq $h) { return $null }
            if ($h -eq '') { break }
            if ($h -match '^Content-Length:\s*(\d+)$') { $len = [int]$Matches[1] }
            elseif ($h -notmatch '^Content-Type:') { throw "not an LSP header on stdout: $h" }
        }
        if ($len -lt 0) { throw 'LSP message without Content-Length' }
        $buf = New-Object char[] $len
        $got = 0
        while ($got -lt $len) {
            $t = $l.P.StandardOutput.ReadAsync($buf, $got, $len - $got)
            while (-not $t.Wait(500)) { if ((Get-Date) -gt $deadline) { throw 'timeout' } }
            if ($t.Result -eq 0) { return $null }
            $got += $t.Result
        }
        $o = (New-Object string($buf, 0, $got)) | ConvertFrom-Json
        if (($o.PSObject.Properties.Name -contains 'id') -and $o.id -eq $id) { return $o }
    }
}

$init = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"launcher-test","version":"1"}}}'

function Begin-Session($l) {
    if ($l.Kind -eq 'mcp') { Send-Mcp $l $init }
    else { Send-Lsp $l '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":null,"capabilities":{}}}' }
}

# Initialize answered (MCP: plus a tools/list), stdout protocol only.
function Check-Session($l, [datetime] $deadline) {
    $what = "$($l.Name) ($($l.Kind)) answers initialize, stdout is protocol only"
    try {
        if ($l.Kind -eq 'mcp') {
            $r = Wait-Mcp $l 1 $deadline
            if ($null -eq $r) { Check $false "$what -- stdout closed"; return }
            Send-Mcp $l '{"jsonrpc":"2.0","method":"notifications/initialized"}'
            Send-Mcp $l '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
            $t = Wait-Mcp $l 2 $deadline
            Check ($null -ne $t -and @($t.result.tools).Count -gt 0) "$what; tools/list has $(if ($t) { @($t.result.tools).Count } else { 0 }) tools [$([int]((Get-Date) - $l.Started).TotalSeconds)s]"
        } else {
            $r = Wait-Lsp $l 1 $deadline
            Check ($null -ne $r -and ($r.PSObject.Properties.Name -contains 'result')) "$what [$([int]((Get-Date) - $l.Started).TotalSeconds)s]"
        }
    } catch {
        Check $false "$what -- $($_.Exception.Message)"
    }
}

function Kill-Tree($l) { if (-not $l.P.HasExited) { Stop-Pid $l.P.Id "/F /T" } }

function Stop-Session($l) {
    try { $l.P.StandardInput.Close() } catch { }
    if (-not $l.P.WaitForExit(15000)) { Kill-Tree $l }
}

function Err-Text($l) {
    if (-not (Test-Path $l.Err)) { return '' }
    $fs = New-Object IO.FileStream($l.Err, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try { (New-Object IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Dispose() }
}

function Check-Prefix([string] $dir) {
    $pfx = Join-Path $dir 'pfx'
    $all = @(Get-ChildItem $pfx -Force -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    $versions = @($all | Where-Object { $_ -match '^\d+(\.\d+)+$' })
    $other = @($all | Where-Object { $_ -notmatch '^\d+(\.\d+)+$' -and $_ -ne 'bin' })
    Check ($versions.Count -eq 1) "one version folder in the prefix: $($versions -join ', ')"
    Check ($other.Count -eq 0) "no leftover folders in the prefix: $($other -join ', ')"
    Check (Test-Path (Join-Path $pfx 'bin\mariadb-shell.cmd')) 'bin\mariadb-shell.cmd exists'
}

function Show-Err($ls) {
    foreach ($l in $ls) {
        Write-Output "  --- $($l.Name) stderr (launcher lines):"
        (Err-Text $l) -split "`r?`n" | Where-Object { $_ -match 'launcher:|install\.ps1:|error|Error|Keeping|waiting' } | Select-Object -First 25 | ForEach-Object { "      $_" }
    }
}

function New-ScenarioDir([string] $name) {
    $d = Join-Path $Work $name
    New-Item -ItemType Directory -Force $d | Out-Null
    return $d
}

function End-Scenario([string] $dir, $ls, [string[]] $tempBefore) {
    foreach ($l in $ls) { Kill-Tree $l }
    Start-Sleep -Seconds 2
    foreach ($t in (Temp-Leftovers)) { if ($tempBefore -notcontains $t) { Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue } }
    Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
    if (Test-Path $dir) { Write-Output "  note: could not remove $dir completely" }
}

Write-Output "PowerShell $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition)), installer: $(if ($InstallerRef) { $InstallerRef } else { 'as the launcher names it' }), $([Environment]::OSVersion.VersionString), $env:PROCESSOR_ARCHITECTURE"

foreach ($s in $Scenarios) {
    $script:scenario = $s
    $tempBefore = Temp-Leftovers
    $dir = New-ScenarioDir $s
    $deadline = (Get-Date).AddSeconds($Timeout)
    $ls = @()
    Write-Output ""
    switch ($s) {
        'two' {
            Write-Output "== two: 2 MCP launchers started together into a fresh prefix"
            $ls = @(1..2 | ForEach-Object { Start-Launcher "mcp$_" $dir $mcpCmd 'mcp' })
            foreach ($l in $ls) { Begin-Session $l }
            foreach ($l in $ls) { Check-Session $l $deadline }
            foreach ($l in $ls) { Stop-Session $l }
            Check-Prefix $dir
        }
        'three' {
            Write-Output "== three: 3 MCP launchers + 1 LSP launcher together into a fresh prefix, then one more MCP launcher while a server runs"
            $ls = @(1..3 | ForEach-Object { Start-Launcher "mcp$_" $dir $mcpCmd 'mcp' })
            $ls += Start-Launcher 'lsp' $dir $lspCmd 'lsp'
            foreach ($l in $ls) { Begin-Session $l }
            foreach ($l in $ls) { Check-Session $l $deadline }
            $late = Start-Launcher 'mcp-late' $dir $mcpCmd 'mcp'
            Begin-Session $late
            Check-Session $late (Get-Date).AddSeconds(60)
            Check (-not ((Err-Text $late) -match 'installing')) 'the late launcher installed nothing'
            $ls += $late
            foreach ($l in $ls) { Stop-Session $l }
            Check-Prefix $dir
        }
        'kill' {
            Write-Output "== kill: a launcher killed with its tree (taskkill /F /T) during the install, then a new one"
            $first = Start-Launcher 'mcp-killed' $dir $mcpCmd 'mcp'
            $pfx = Join-Path $dir 'pfx'
            $until = (Get-Date).AddSeconds(240)
            while ((Get-Date) -lt $until -and -not (Get-ChildItem $pfx -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'bin' })) { Start-Sleep -Milliseconds 200 }
            Check ([bool](Get-ChildItem $pfx -Force -Directory -ErrorAction SilentlyContinue)) 'the first install got as far as unpacking'
            Kill-Tree $first
            Start-Sleep -Seconds 2
            foreach ($t in (Temp-Leftovers)) { if ($tempBefore -notcontains $t) { Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue } }
            $second = Start-Launcher 'mcp-next' $dir $mcpCmd 'mcp'
            Begin-Session $second
            Check-Session $second $deadline
            Stop-Session $second
            $ls = @($first, $second)
            Check-Prefix $dir
        }
        'orphan' {
            Write-Output "== orphan: only the launcher's cmd.exe killed during the install (as a harness does), its installer runs on; a new launcher meanwhile"
            $first = Start-Launcher 'mcp-stopped' $dir $mcpCmd 'mcp'
            $pfx = Join-Path $dir 'pfx'
            $until = (Get-Date).AddSeconds(240)
            while ((Get-Date) -lt $until -and -not (Get-ChildItem $pfx -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'bin' })) { Start-Sleep -Milliseconds 200 }
            $kids = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($first.P.Id)" | ForEach-Object { $_.ProcessId })
            Stop-Pid $first.P.Id "/F"
            $second = Start-Launcher 'mcp-next' $dir $mcpCmd 'mcp'
            Begin-Session $second
            Check-Session $second $deadline
            $until = (Get-Date).AddSeconds(300)
            while ((Get-Date) -lt $until -and @($kids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }).Count -gt 0) { Start-Sleep -Seconds 1 }
            Check (@($kids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }).Count -eq 0) 'the orphaned installer finished'
            Stop-Session $second
            $ls = @($first, $second)
            foreach ($k in $kids) { Stop-Pid $k "/F /T" }
            Check-Prefix $dir
        }
        default { throw "unknown scenario $s" }
    }
    Show-Err $ls
    End-Scenario $dir $ls $tempBefore
}

Remove-Item -Recurse -Force $Work -ErrorAction SilentlyContinue
Write-Output ""
if ($failures.Count) { Write-Output "FAILED ($($failures.Count)):"; $failures | ForEach-Object { "  $_" }; exit 1 }
Write-Output 'ALL PASSED'
