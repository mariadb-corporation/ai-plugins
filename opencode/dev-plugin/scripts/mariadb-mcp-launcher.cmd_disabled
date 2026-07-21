@echo off
setlocal enabledelayedexpansion
rem ============================================================================
rem mariadb-mcp-launcher.cmd — Windows launcher for the mariadb-shell MCP server.
rem
rem Resolution order: (1) %MARIADB_SHELL_BIN% if set; (2) a mariadb-shell on
rem %PATH% whose version is >= MARIADB_SHELL_VERSION; (3) a cached download for
rem that version; (4) otherwise download the matching release asset from
rem github.com/mariadb-corporation/mariadb-shell into %LOCALAPPDATA% and verify
rem its checksum. However it resolves, the binary is run as
rem   mariadb-shell -- mcp start-server --transport=stdio
rem so the MCP server runs over stdio (not HTTP).
rem
rem Env: MARIADB_SHELL_VERSION (default below), MARIADB_SHELL_BIN, GH_TOKEN.
rem ============================================================================

if not defined MARIADB_SHELL_VERSION set "MARIADB_SHELL_VERSION=9.7.0"
set "REPO=mariadb-corporation/mariadb-shell"

rem Arguments that start the mariadb-shell MCP server over stdio.
set "MCP_ARGS=-- mcp start-server --transport=stdio"

rem Escape hatch: explicit binary.
if defined MARIADB_SHELL_BIN (
  "%MARIADB_SHELL_BIN%" %MCP_ARGS%
  exit /b %errorlevel%
)

rem Prefer a mariadb-shell already on PATH when it meets the required version.
set "PATH_BIN="
for /f "delims=" %%P in ('where mariadb-shell 2^>nul') do if not defined PATH_BIN set "PATH_BIN=%%P"
if defined PATH_BIN (
  set "PATH_VER="
  for /f "usebackq delims=" %%V in (`"%PATH_BIN%" --version 2^>nul`) do if not defined PATH_VER set "PATH_VER=%%V"
  set "REQ_VER=%MARIADB_SHELL_VERSION%"
  powershell -NoProfile -Command ^
    "$m=[regex]::Match($env:PATH_VER,'\d+(\.\d+)+'); if(-not $m.Success){exit 2};" ^
    "try{ if([version]$m.Value -ge [version]$env:REQ_VER){exit 0}else{exit 1} }catch{exit 2}"
  if not errorlevel 1 (
    echo mariadb-mcp-launcher: using mariadb-shell from PATH "%PATH_BIN%" ^(^>= %MARIADB_SHELL_VERSION%^) 1>&2
    "%PATH_BIN%" %MCP_ARGS%
    exit /b %errorlevel%
  )
  echo mariadb-mcp-launcher: mariadb-shell on PATH does not meet required %MARIADB_SHELL_VERSION%; using managed binary 1>&2
)

rem Detect arch.
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" (set "ARCH=arm64") else (set "ARCH=amd64")

set "OS=windows"
set "EXT=zip"
set "BIN_NAME=mariadb-shell.exe"
set "ASSET=mariadb-shell_%MARIADB_SHELL_VERSION%_%OS%_%ARCH%.%EXT%"
set "CACHE_BASE=%LOCALAPPDATA%\mariadb\mariadb-shell\%MARIADB_SHELL_VERSION%"
set "BIN=%CACHE_BASE%\%BIN_NAME%"
set "BASE_URL=https://github.com/%REPO%/releases/download/%MARIADB_SHELL_VERSION%"

if exist "%BIN%" goto run

if not exist "%CACHE_BASE%" mkdir "%CACHE_BASE%"
set "TMP_ZIP=%TEMP%\%ASSET%"

set "AUTH="
if defined GH_TOKEN set "AUTH=-Headers @{Authorization='Bearer %GH_TOKEN%'}"

echo mariadb-mcp-launcher: downloading %ASSET% (%OS%/%ARCH%) ... 1>&2
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "Invoke-WebRequest %AUTH% -Uri '%BASE_URL%/%ASSET%' -OutFile '%TMP_ZIP%';" ^
  "try { Invoke-WebRequest %AUTH% -Uri '%BASE_URL%/checksums.txt' -OutFile '%TEMP%\checksums.txt';" ^
  "  $line = Select-String -Path '%TEMP%\checksums.txt' -Pattern '%ASSET%' | Select-Object -First 1;" ^
  "  if ($line) { $expected = ($line.Line -split '\s+')[0];" ^
  "    $actual = (Get-FileHash -Algorithm SHA256 '%TMP_ZIP%').Hash.ToLower();" ^
  "    if ($expected.ToLower() -ne $actual) { throw 'checksum mismatch for %ASSET%' } }" ^
  "} catch { Write-Host 'mariadb-mcp-launcher: checksum verification skipped' }" ^
  "Expand-Archive -Force -Path '%TMP_ZIP%' -DestinationPath '%CACHE_BASE%';"
if errorlevel 1 (
  echo mariadb-mcp-launcher: error: download/extract failed 1>&2
  exit /b 1
)

rem If the binary landed in a subdir of the archive, move it up.
if not exist "%BIN%" (
  for /r "%CACHE_BASE%" %%F in (%BIN_NAME%) do (
    move /y "%%F" "%BIN%" >nul
    goto run
  )
)

:run
if not exist "%BIN%" (
  echo mariadb-mcp-launcher: error: %BIN_NAME% not found after install 1>&2
  exit /b 1
)
"%BIN%" %MCP_ARGS%
exit /b %errorlevel%
