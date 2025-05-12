@echo off
echo Kompilowanie pliku CopilotLauncher.cs do EXE...

REM Skompiluj plik C# do EXE (aplikacja okienkowa)
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe /nologo /target:winexe /reference:System.Drawing.dll CopilotLauncher.cs

echo.
if exist CopilotLauncher.exe (
    echo Kompilacja zakończona sukcesem!
    echo Utworzono plik CopilotLauncher.exe
) else (
    echo Wystąpił błąd podczas kompilacji.
    echo Sprawdź komunikat błędu powyżej.
)

echo.
echo Naciśnij dowolny klawisz, aby zakończyć...
pause > nul