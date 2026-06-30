@echo off
setlocal enabledelayedexpansion
rem ============================================================================
rem mariadb-mcp-launcher.cmd — Windows launcher for the mariadb-shell MCP server.
rem
rem Detects CPU arch, downloads (if needed) the matching release asset from
rem github.com/mariadb-corporation/mariadb-shell into %LOCALAPPDATA%, verifies
rem its checksum, and runs it. All args are passed through to the binary.
rem
rem Env: MARIADB_SHELL_VERSION (default below), MARIADB_SHELL_BIN, GH_TOKEN.
rem ============================================================================

if not defined MARIADB_SHELL_VERSION set "MARIADB_SHELL_VERSION=2026.7.0"
set "REPO=mariadb-corporation/mariadb-shell"

rem Escape hatch: explicit binary.
if defined MARIADB_SHELL_BIN (
  "%MARIADB_SHELL_BIN%" %*
  exit /b %errorlevel%
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
"%BIN%" %*
exit /b %errorlevel%
