@echo off
setlocal EnableDelayedExpansion
title Instalator Claude Code dla VS Code

:: Przygotowanie skryptu instalacyjnego
echo [INFO] Przygotowanie skryptu instalacyjnego...

:: Tworzenie skryptu instalacyjnego z prawidłowymi zakończeniami linii
(
echo #!/bin/bash
echo set -e
echo echo "Instalacja Claude Code..."
echo sudo apt-get update
echo sudo apt-get install -y curl build-essential
echo echo "Instalacja NVM..."
echo curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh ^| bash
echo export NVM_DIR="$HOME/.nvm"
echo [ -s "$NVM_DIR/nvm.sh" ] ^&^& \. "$NVM_DIR/nvm.sh"
echo echo "Instalacja Node.js..."
echo nvm install --lts
echo echo "Instalacja Claude Code..."
echo npm install -g @anthropic-ai/claude-code
echo echo "Sprawdzanie instalacji..."
echo which claude
echo echo "Instalacja zakończona!"
) > "%TEMP%\install-claude.sh"

:: Konwersja CRLF do LF i kopiowanie do WSL
powershell -Command "(Get-Content '%TEMP%\install-claude.sh') -join [char]10 | Set-Content -NoNewline '%TEMP%\install-claude-unix.sh' -Encoding ASCII"
type "%TEMP%\install-claude-unix.sh" | wsl -d Ubuntu -e bash -c "cat > ~/install-claude.sh && chmod +x ~/install-claude.sh"

:: Uruchomienie skryptu instalacyjnego
echo [INFO] Instalowanie Claude Code (to może potrwać kilka minut)...
wsl -d Ubuntu -e bash -c "cd ~ && ./install-claude.sh"

:: Tworzenie skryptu uruchamiającego z prawidłowymi zakończeniami linii
(
echo #!/bin/bash
echo export NVM_DIR="$HOME/.nvm"
echo [ -s "$NVM_DIR/nvm.sh" ] ^&^& \. "$NVM_DIR/nvm.sh"
echo claude "$@"
) > "%TEMP%\run-claude.sh"

:: Konwersja CRLF do LF i kopiowanie do WSL
powershell -Command "(Get-Content '%TEMP%\run-claude.sh') -join [char]10 | Set-Content -NoNewline '%TEMP%\run-claude-unix.sh' -Encoding ASCII"
type "%TEMP%\run-claude-unix.sh" | wsl -d Ubuntu -e bash -c "cat > ~/run-claude.sh && chmod +x ~/run-claude.sh"

echo [INFO] Tworzenie skryptu Run-Claude-Code.bat...

:: Tworzenie skryptu BAT do uruchamiania Claude Code
echo @echo off > "%~dp0Run-Claude-Code.bat"
echo setlocal EnableDelayedExpansion >> "%~dp0Run-Claude-Code.bat"
echo title Uruchamianie Claude Code >> "%~dp0Run-Claude-Code.bat"
echo. >> "%~dp0Run-Claude-Code.bat"
echo rem Konwertuj aktualną ścieżkę Windows na ścieżkę WSL >> "%~dp0Run-Claude-Code.bat"
echo for /f "delims=" %%%%a in ('wsl -d Ubuntu -e bash -c "wslpath '%%CD%%'"') do set "WSL_PATH=%%%%a" >> "%~dp0Run-Claude-Code.bat"
echo. >> "%~dp0Run-Claude-Code.bat"
echo echo Uruchamianie Claude Code w katalogu projektu: %%CD%% >> "%~dp0Run-Claude-Code.bat"
echo echo Ścieżka WSL: %%WSL_PATH%% >> "%~dp0Run-Claude-Code.bat"
echo. >> "%~dp0Run-Claude-Code.bat"
echo rem Uruchom Claude Code w aktualnym katalogu projektu >> "%~dp0Run-Claude-Code.bat"
echo wsl -d Ubuntu -e bash -c "cd '%%WSL_PATH%%' ^&^& ~/run-claude.sh %%*" >> "%~dp0Run-Claude-Code.bat"
echo. >> "%~dp0Run-Claude-Code.bat"
echo pause >> "%~dp0Run-Claude-Code.bat"

echo [INFO] Tworzenie konfiguracji dla VS Code...
if not exist "%~dp0.vscode" mkdir "%~dp0.vscode"

:: Tworzenie pliku tasks.json (linia po linii, aby uniknąć błędów)
echo { > "%~dp0.vscode\tasks.json"
echo     "version": "2.0.0", >> "%~dp0.vscode\tasks.json"
echo     "tasks": [ >> "%~dp0.vscode\tasks.json"
echo         { >> "%~dp0.vscode\tasks.json"
echo             "label": "Claude Code", >> "%~dp0.vscode\tasks.json"
echo             "type": "shell", >> "%~dp0.vscode\tasks.json"
echo             "command": "for /f \"delims=\" %%%%a in ('wsl -d Ubuntu -e bash -c \"wslpath '${fileDirname}'\"') do wsl -d Ubuntu -e bash -c \"cd '%%%%a' ^&^& ~/run-claude.sh '${fileBasename}'\"", >> "%~dp0.vscode\tasks.json"
echo             "group": { >> "%~dp0.vscode\tasks.json"
echo                 "kind": "build", >> "%~dp0.vscode\tasks.json"
echo                 "isDefault": true >> "%~dp0.vscode\tasks.json"
echo             }, >> "%~dp0.vscode\tasks.json"
echo             "presentation": { >> "%~dp0.vscode\tasks.json"
echo                 "reveal": "always", >> "%~dp0.vscode\tasks.json"
echo                 "panel": "new" >> "%~dp0.vscode\tasks.json"
echo             }, >> "%~dp0.vscode\tasks.json"
echo             "problemMatcher": [] >> "%~dp0.vscode\tasks.json"
echo         } >> "%~dp0.vscode\tasks.json"
echo     ] >> "%~dp0.vscode\tasks.json"
echo } >> "%~dp0.vscode\tasks.json"

echo.
echo ===== Instalacja zakończona! =====
echo.
echo Aby uruchomić Claude Code w VS Code:
echo 1. Otwórz VS Code w tym folderze
echo 2. Naciśnij Ctrl+Shift+B aby uruchomić Claude Code dla aktualnie otwartego pliku
echo 3. Lub użyj skryptu: Run-Claude-Code.bat w bieżącym katalogu
echo.
echo Możesz też uruchomić zadanie Claude Code z palety poleceń:
echo 1. Naciśnij Ctrl+Shift+P
echo 2. Wpisz "Tasks: Run Task"
echo 3. Wybierz "Claude Code"
echo.
echo [INFO] Naciśnij dowolny klawisz, aby zakończyć...
pause >nul