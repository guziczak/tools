@echo off
echo Creating .NET project for USB Drive Verifier...
echo.

if not exist UsbDriveVerifier (
    mkdir UsbDriveVerifier
    cd UsbDriveVerifier
    dotnet new console
) else (
    cd UsbDriveVerifier
)

echo Copying program code...
copy /Y ..\pendrive-verify-program.cs Program.cs

echo Building USB Drive Verifier...
dotnet build -c Release

echo.
echo Running USB Drive Verifier...
echo.
dotnet run -c Release

echo.
echo Press any key to exit...
pause > nul