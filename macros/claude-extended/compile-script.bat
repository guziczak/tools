@echo off
echo Kompilowanie programu C# do pliku wykonywalnego...

:: Ustaw ścieżkę do kompilatora C#
set CSC="C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"

:: Kompiluj program
%CSC% /target:winexe /out:ClaudeExtendedThinking.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll KeyboardMacro.cs

:: Sprawdź, czy kompilacja się powiodła
if exist ClaudeExtendedThinking.exe (
    echo Kompilacja zakończona sukcesem! Plik ClaudeExtendedThinking.exe został utworzony.
    echo.
    echo WAŻNE INFORMACJE:
    echo 1. W kodzie ustawiona jest ścieżka do Claude Desktop:
    echo    C:\Users\guzic\AppData\Local\AnthropicClaude\claude.exe
    echo.
    echo 2. Program będzie ustawiał okno Claude w ŚRODKU EKRANU z rozmiarem 1200x650
    echo    aby uniknąć efektu przyciągania do krawędzi w Windows 11.
    echo.
    echo 3. Współrzędne kliknięć w UI są dostosowane dla tego rozmiaru okna.
    echo.
    echo 4. Debugowanie jest domyślnie wyłączone dla płynnego działania makra.
    echo.
    echo 5. Czasy zostały zoptymalizowane dla większej szybkości działania.
    echo.
    echo UWAGA: Jeśli program nie działa prawidłowo, można włączyć tryb debugowania
    echo zmieniając wartość "debugMode = false" na "debugMode = true" w pliku KeyboardMacro.cs
    echo i ponownie skompilować.
) else (
    echo Kompilacja nie powiodła się.
)

echo.
echo Naciśnij dowolny klawisz, aby zakończyć...
pause > nul