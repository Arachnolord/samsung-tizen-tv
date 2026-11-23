@echo off
REM Samsung Tizen TV - Windows-Starter fuer setup.sh.
REM Sucht Git-Bash oder WSL und fuehrt das Einrichtungs-Skript aus.
REM Voraussetzung: Docker Desktop laeuft, und Git for Windows (Git-Bash) oder WSL ist installiert.
setlocal
set "DIR=%~dp0"

REM 1) bash im PATH (z. B. Git-Bash)?
where bash >nul 2>&1
if %ERRORLEVEL%==0 (
  bash "%DIR%setup.sh"
  goto :done
)

REM 2) Git-Bash am Standardort?
if exist "%ProgramFiles%\Git\bin\bash.exe" (
  "%ProgramFiles%\Git\bin\bash.exe" "%DIR%setup.sh"
  goto :done
)
if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" (
  "%ProgramFiles(x86)%\Git\bin\bash.exe" "%DIR%setup.sh"
  goto :done
)

REM 3) WSL?
where wsl >nul 2>&1
if %ERRORLEVEL%==0 (
  wsl bash ./setup.sh
  goto :done
)

echo.
echo Es wurde keine bash-Umgebung gefunden.
echo Bitte "Git for Windows" (Git-Bash) oder WSL installieren - und Docker Desktop starten.
echo.
pause

:done
endlocal
