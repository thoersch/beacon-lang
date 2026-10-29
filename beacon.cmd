@echo off
setlocal
set "ROOT=%~dp0"
set "HOST=%ROOT%bootstrap\stage0\Beacon.Compiler.dll"
set "COMPILER=%ROOT%compiler\compiler.beacon"
set "BEACON_HOME=%ROOT%"

if not exist "%HOST%" (
  echo Beacon bootstrap seed not found: %HOST% 1>&2
  echo Run tools\finalize-bootstrap.ps1 before using this checkout. 1>&2
  exit /b 2
)

if "%~1"=="" goto :usage

if /I "%~1"=="self-host" (
  dotnet "%HOST%" "%COMPILER%" --self-host
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="plan" (
  if "%~2"=="" goto :usage
  dotnet "%HOST%" "%COMPILER%" --stage1 "%~f2"
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="run" (
  if "%~2"=="" goto :usage
  dotnet "%HOST%" "%COMPILER%" --stage1-run "%~f2"
  exit /b %ERRORLEVEL%
)

dotnet "%HOST%" "%COMPILER%" --stage1-run "%~f1"
exit /b %ERRORLEVEL%

:usage
echo Usage:
echo   beacon file.beacon
echo   beacon run file.beacon
echo   beacon plan file.beacon
echo   beacon self-host
exit /b 2
