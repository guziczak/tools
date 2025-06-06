@echo off
echo Uruchamianie Claude Code...
setlocal
:: Konwersja ścieżki Windows na ścieżkę WSL
for /f "tokens=*" %%a in ('wsl -d Ubuntu -e bash -c "wslpath '%%~dp0'"') do set WSL_PATH=%%a
:: Uruchom Claude Code w katalogu, gdzie znajduje się ten plik bat
wsl -d Ubuntu -e bash -c "~/run-claude.sh %WSL_PATH%"
pause
