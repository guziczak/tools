@echo off
setlocal EnableDelayedExpansion
title Instalator Claude Code

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
echo source ~/.bashrc
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
echo # Sprawdź czy podano parametr z katalogiem
echo if [ "$1" != "" ]; then
echo   cd "$1" ^|^| echo "Nie można zmienić katalogu na $1"
echo fi
echo claude
) > "%TEMP%\run-claude.sh"

:: Konwersja CRLF do LF i kopiowanie do WSL
powershell -Command "(Get-Content '%TEMP%\run-claude.sh') -join [char]10 | Set-Content -NoNewline '%TEMP%\run-claude-unix.sh' -Encoding ASCII"
type "%TEMP%\run-claude-unix.sh" | wsl -d Ubuntu -e bash -c "cat > ~/run-claude.sh && chmod +x ~/run-claude.sh"

:: Tworzenie skryptu BAT do uruchamiania
echo [INFO] Tworzenie skryptu do uruchamiania Claude Code w Windows...
(
echo @echo off
echo echo Uruchamianie Claude Code...
echo setlocal
echo :: Konwersja ścieżki Windows na ścieżkę WSL
echo for /f "tokens=*" %%%%a in ^('wsl -d Ubuntu -e bash -c "wslpath '%%%%~dp0'"'^) do set WSL_PATH=%%%%a
echo :: Uruchom Claude Code w katalogu, gdzie znajduje się ten plik bat
echo wsl -d Ubuntu -e bash -c "~/run-claude.sh %%WSL_PATH%%"
echo pause
) > "%~dp0Run-Claude-Code.bat"

echo.
echo ===== Instalacja zakończona! =====
echo.
echo Aby uruchomić Claude Code:
echo 1. W terminalu WSL, wpisz: claude
echo 2. Lub użyj skryptu: ~/run-claude.sh
echo 3. Z Windows użyj: Run-Claude-Code.bat
echo.
echo [INFO] Naciśnij dowolny klawisz, aby zakończyć...
pause >nul