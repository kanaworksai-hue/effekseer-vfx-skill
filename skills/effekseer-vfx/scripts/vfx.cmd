@echo off
rem effekseer-vfx command line for Windows (cmd or PowerShell): <skill>\scripts\vfx.cmd <command>; `vfx.cmd --help` lists
rem the commands. Same as `sh <skill>/scripts/vfx` elsewhere. Uses the toolchain installed by setup.ps1 in
rem EFFEKSEER_VFX_HOME (default %USERPROFILE%\.cache\effekseer-vfx).
setlocal
set "SCRIPTS=%~dp0"
set "SCRIPTS=%SCRIPTS:~0,-1%"
set "TOOLCHAIN=%USERPROFILE%\.cache\effekseer-vfx"
if defined EFFEKSEER_VFX_HOME set "TOOLCHAIN=%EFFEKSEER_VFX_HOME%"
set "PYTHON=%TOOLCHAIN%\venv\Scripts\python.exe"
set "PYARGS="
if exist "%PYTHON%" goto run
rem doctor and --help run on the system Python so an agent can find out what to install.
set "PYTHON=py"
set "PYARGS=-3"
where py >nul 2>nul && goto run
set "PYARGS="
set "PYTHON=python"
where python >nul 2>nul && goto run
echo {"ok": false, "error": {"type": "SetupRequired", "message": "Python is not installed"}}
exit /b 2

:run
set "EFFEKSEER_VFX_HOME=%TOOLCHAIN%"
set "DOTNET_ROOT=%TOOLCHAIN%\dotnet"
set "EFFEKSEER_AI_BIN_DIR=%TOOLCHAIN%\effekseer\Effekseer1.80.7Win\Tool\bin"
set "SEARCH=%SCRIPTS%"
if defined PYTHONPATH set "SEARCH=%SCRIPTS%;%PYTHONPATH%"
set "PYTHONPATH=%SEARCH%"
set "PYTHONDONTWRITEBYTECODE=1"
rem Keep the current directory (the game project) off sys.path: a project file named like a module must not shadow it.
set "PYTHONSAFEPATH=1"
rem Read and write every text file as UTF-8, whatever the system code page (cp936, cp932, cp1252...).
set "PYTHONUTF8=1"
"%PYTHON%" %PYARGS% -m vfxkit %*
exit /b %ERRORLEVEL%
