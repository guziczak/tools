using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Diagnostics;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

class DiskDriveVerifier
{
    private const string TEST_DIR_NAME = "VerifyTest";
    private const string CHECKSUMS_FILE = "checksums.dat";
    private const long CHUNK_SIZE = 64L * 1024L * 1024L;
    private const double USAGE_PERCENT = 0.95; // 95% dostępnej przestrzeni
    private const int CHART_WIDTH = 60;
    private const int CHART_HEIGHT = 16;
    private const int MAX_DISPLAY_BARS = 10; // Zmniejszono maksymalną liczbę słupków dla lepszej czytelności
    private const int BUFFER_SIZE = 128 * 1024 * 1024; // Zwiększono do 128 MB dla lepszej wydajności
    
    // Klasa do przechowywania pomiarów szybkości
    private class SpeedMeasurement
    {
        public string FileName { get; set; }    // Nazwa pliku
        public long FileSize { get; set; }      // Rozmiar pliku w bajtach
        public double SpeedMBps { get; set; }   // Szybkość w MB/s
    }

    static void Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.WriteLine("Program do weryfikacji pojemności dysków i pendriveów");
        Console.WriteLine("===================================================");
        
        bool exit = false;
        while (!exit)
        {
            Console.WriteLine("\nWybierz operację:");
            Console.WriteLine("1. Zapisz dane testowe na dysku");
            Console.WriteLine("2. Zweryfikuj dane na dysku");
            Console.WriteLine("3. Sprawdź częściową pojemność dysku");
            Console.WriteLine("4. Wyjdź z programu");
            Console.Write("\nTwój wybór: ");
            
            string choice = Console.ReadLine().Trim();
            
            switch (choice)
            {
                case "1":
                    WriteTestData();
                    break;
                case "2":
                    VerifyTestData();
                    break;
                case "3":
                    CheckPartialCapacity();
                    break;
                case "4":
                    exit = true;
                    break;
                default:
                    Console.WriteLine("Nieprawidłowy wybór. Spróbuj ponownie.");
                    break;
            }
        }
    }
    
    // Metoda do uzyskania katalogu programu
    static string GetProgramDirectory()
    {
        return AppDomain.CurrentDomain.BaseDirectory;
    }
    
    static void WriteTestData()
    {
        // Znajdź dostępne dyski
        DriveInfo selectedDrive = SelectDrive();
        if (selectedDrive == null)
            return;
        
        Console.WriteLine($"\nWybrany dysk: {selectedDrive.Name}");
        Console.WriteLine($"Deklarowana pojemność: {FormatBytes(selectedDrive.TotalSize)}");
        Console.WriteLine($"Dostępne miejsce: {FormatBytes(selectedDrive.AvailableFreeSpace)}");
        
        // Ostrzeżenie i potwierdzenie
        Console.WriteLine("\nUWAGA: Test spowoduje utworzenie plików testowych na wybranym dysku.");
        Console.WriteLine("Zalecane jest wykonanie kopii zapasowej ważnych danych.");
        
        // Dodatkowe ostrzeżenie dla dysków niewymiennych
        if (selectedDrive.DriveType != DriveType.Removable)
        {
            Console.WriteLine("\n!!! OSTRZEŻENIE !!!");
            Console.WriteLine("Wybrany dysk nie jest dyskiem wymiennym (pendrive).");
            Console.WriteLine("Test może spowodować intensywne zużycie dysku i skrócić jego żywotność.");
            Console.WriteLine("Upewnij się, że wybrano właściwy dysk.");
        }
        
        Console.Write("Czy chcesz kontynuować? (T/N): ");
        
        if (Console.ReadLine().Trim().ToUpper() != "T")
        {
            Console.WriteLine("Operacja anulowana.");
            return;
        }
        
        // Użyj 100% dostępnej pojemności dla pełnego testu
        WriteTestDataWithPercentage(selectedDrive, 100);
    }
    
    static void CheckPartialCapacity()
    {
        // Znajdź dostępne dyski
        DriveInfo selectedDrive = SelectDrive();
        if (selectedDrive == null)
            return;
        
        Console.WriteLine($"\nWybrany dysk: {selectedDrive.Name}");
        Console.WriteLine($"Deklarowana pojemność: {FormatBytes(selectedDrive.TotalSize)}");
        Console.WriteLine($"Dostępne miejsce: {FormatBytes(selectedDrive.AvailableFreeSpace)}");
        
        // Ostrzeżenie i potwierdzenie
        Console.WriteLine("\nUWAGA: Test spowoduje utworzenie plików testowych na wybranym dysku.");
        Console.WriteLine("Zalecane jest wykonanie kopii zapasowej ważnych danych.");
        
        // Dodatkowe ostrzeżenie dla dysków niewymiennych
        if (selectedDrive.DriveType != DriveType.Removable)
        {
            Console.WriteLine("\n!!! OSTRZEŻENIE !!!");
            Console.WriteLine("Wybrany dysk nie jest dyskiem wymiennym (pendrive).");
            Console.WriteLine("Test może spowodować intensywne zużycie dysku i skrócić jego żywotność.");
            Console.WriteLine("Upewnij się, że wybrano właściwy dysk.");
        }
        
        Console.Write("Czy chcesz kontynuować? (T/N): ");
        
        if (Console.ReadLine().Trim().ToUpper() != "T")
        {
            Console.WriteLine("Operacja anulowana.");
            return;
        }
        
        // Pytanie o procent pojemności do sprawdzenia
        int percentToTest = 0;
        bool validPercent = false;
        
        while (!validPercent)
        {
            Console.Write("\nPodaj procent pojemności do sprawdzenia (1-100): ");
            if (int.TryParse(Console.ReadLine().Trim(), out percentToTest) && 
                percentToTest > 0 && percentToTest <= 100)
            {
                validPercent = true;
            }
            else
            {
                Console.WriteLine("Nieprawidłowa wartość. Podaj liczbę od 1 do 100.");
            }
        }
        
        WriteTestDataWithPercentage(selectedDrive, percentToTest);
    }
    
    static void VerifyTestData()
    {
        // Znajdź dostępne dyski
        DriveInfo selectedDrive = SelectDrive();
        if (selectedDrive == null)
            return;
        
        // Sprawdź czy istnieje katalog testowy
        string testDir = Path.Combine(selectedDrive.RootDirectory.FullName, TEST_DIR_NAME);
        string sourceChecksumFile = Path.Combine(testDir, CHECKSUMS_FILE);
        
        // Katalog programu do tymczasowego przechowywania sum kontrolnych
        string programDir = GetProgramDirectory();
        string localChecksumFile = Path.Combine(programDir, CHECKSUMS_FILE);
        
        if (!Directory.Exists(testDir) || !File.Exists(sourceChecksumFile))
        {
            Console.WriteLine("\nNie znaleziono danych testowych na wybranym dysku.");
            Console.WriteLine("Upewnij się, że wybrałeś właściwy dysk i najpierw wykonaj operację zapisu danych testowych.");
            Console.WriteLine("\nNaciśnij dowolny klawisz, aby kontynuować...");
            Console.ReadKey();
            return;
        }
        
        // Kopiuj plik sum kontrolnych do katalogu programu
        try 
        {
            File.Copy(sourceChecksumFile, localChecksumFile, true);
            Console.WriteLine("Skopiowano plik sum kontrolnych do katalogu programu.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Błąd podczas kopiowania pliku sum kontrolnych: {ex.Message}");
            Console.WriteLine("\nNaciśnij dowolny klawisz, aby kontynuować...");
            Console.ReadKey();
            return;
        }
        
        try
        {
            // Upewnij się, że mamy katalog programu do przechowywania tymczasowych plików
            string localTempDir = Path.Combine(GetProgramDirectory(), "Temp");
            if (Directory.Exists(localTempDir))
            {
                Directory.Delete(localTempDir, true);
            }
            Directory.CreateDirectory(localTempDir);
            
            Console.WriteLine("\nRozpoczynanie weryfikacji danych testowych...");
            
            // Lista do przechowywania pomiarów szybkości
            List<SpeedMeasurement> speedMeasurements = new List<SpeedMeasurement>();
            
            // Odczytaj sumy kontrolne z lokalnej kopii pliku
            Dictionary<string, byte[]> savedChecksums = LoadChecksums(localChecksumFile);
            
            if (savedChecksums.Count == 0)
            {
                Console.WriteLine("Błąd: Plik sum kontrolnych jest pusty lub uszkodzony.");
                return;
            }
            
            Console.WriteLine($"Znaleziono {savedChecksums.Count} plików testowych do weryfikacji.");
            
            // Mierzenie całkowitego czasu odczytu
            Stopwatch totalStopwatch = new Stopwatch();
            totalStopwatch.Start();
            
            // Weryfikuj każdy plik
            int verifiedFiles = 0;
            int corruptedFiles = 0;
            int missingFiles = 0;
            long verifiedBytes = 0;
            int fileIndex = 0;
            
            // Oblicz całkowity rozmiar wszystkich plików do wyświetlenia postępu
            long totalBytes = 0;
            foreach (var checksumEntry in savedChecksums)
            {
                string sourceFilePath = Path.Combine(testDir, checksumEntry.Key);
                if (File.Exists(sourceFilePath))
                {
                    FileInfo fileInfo = new FileInfo(sourceFilePath);
                    totalBytes += fileInfo.Length;
                }
            }
            
            // Dodaj pasek postępu przed pętlą weryfikującą
            Console.WriteLine("\nPostęp weryfikacji:");
            DrawProgressBar(0, totalBytes, 50, "Postęp: ");
            
            foreach (var checksumEntry in savedChecksums)
            {
                string fileName = checksumEntry.Key;
                byte[] expectedChecksum = checksumEntry.Value;
                
                string sourceFilePath = Path.Combine(testDir, fileName);
                string localFilePath = Path.Combine(localTempDir, fileName);
                
                if (!File.Exists(sourceFilePath))
                {
                    Console.WriteLine($"BŁĄD: Brakujący plik: {fileName}");
                    missingFiles++;
                    continue;
                }
                
                FileInfo fileInfo = new FileInfo(sourceFilePath);
                
                // Tworzenie przyjaznej nazwy pliku
                string friendlyName = fileName.Equals("quicktest.bin", StringComparison.OrdinalIgnoreCase) 
                                     ? "Quick" 
                                     : $"Plik {++fileIndex}";
                
                Console.Write($"Kopiowanie i weryfikacja pliku {fileName} ({FormatBytes(fileInfo.Length)})... ");
                
                // Mierzenie czasu kopiowania i weryfikacji pliku
                Stopwatch fileStopwatch = new Stopwatch();
                fileStopwatch.Start();
                
                try
                {
                    // Kopiuj plik do lokalnego katalogu
                    File.Copy(sourceFilePath, localFilePath, true);
                    
                    // Weryfikuj sumę kontrolną skopiowanego pliku
                    byte[] actualChecksum = CalculateFileChecksum(localFilePath);
                    
                    fileStopwatch.Stop();
                    // Prędkość w MB/s (uwzględnia czas kopiowania)
                    double speedMBps = fileInfo.Length / (1024.0 * 1024.0) / fileStopwatch.Elapsed.TotalSeconds;
                    
                    // Dodaj pomiar prędkości
                    speedMeasurements.Add(new SpeedMeasurement
                    {
                        FileName = friendlyName,
                        FileSize = fileInfo.Length,
                        SpeedMBps = speedMBps
                    });
                    
                    // Usuń lokalną kopię pliku po weryfikacji
                    File.Delete(localFilePath);
                    
                    if (CompareChecksums(expectedChecksum, actualChecksum))
                    {
                        Console.WriteLine($"OK ({speedMBps:F2} MB/s)");
                        verifiedFiles++;
                    }
                    else
                    {
                        Console.WriteLine("USZKODZONY");
                        corruptedFiles++;
                    }
                    
                    verifiedBytes += fileInfo.Length;
                    
                    // Aktualizuj pasek postępu po każdym pliku
                    DrawProgressBar(verifiedBytes, totalBytes, 50, "Postęp: ");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Błąd: {ex.Message}");
                    corruptedFiles++;
                    
                    // Upewnij się, że lokalna kopia zostanie usunięta w przypadku błędu
                    if (File.Exists(localFilePath))
                    {
                        try { File.Delete(localFilePath); } catch { }
                    }
                }
            }
            
            totalStopwatch.Stop();
            
            // Usuń katalog tymczasowy
            try
            {
                Directory.Delete(localTempDir, true);
            }
            catch { /* Ignoruj błędy przy usuwaniu katalogu tymczasowego */ }
            
            // Podsumowanie
            Console.WriteLine("\n--- WYNIKI WERYFIKACJI ---");
            Console.WriteLine($"Całkowita liczba plików: {savedChecksums.Count}");
            Console.WriteLine($"Poprawnych plików: {verifiedFiles}");
            Console.WriteLine($"Uszkodzonych plików: {corruptedFiles}");
            Console.WriteLine($"Brakujących plików: {missingFiles}");
            Console.WriteLine($"Zweryfikowano danych: {FormatBytes(verifiedBytes)}");
            Console.WriteLine($"Całkowity czas odczytu: {totalStopwatch.Elapsed.TotalSeconds:F1} sekund");
            
            // Rysuj wykres szybkości odczytu ze średnią (ważoną, ale bez tego słowa)
            DrawSimpleSpeedChart(speedMeasurements, "WYKRES SZYBKOŚCI ODCZYTU", "MB/s");
            
            if (corruptedFiles == 0 && missingFiles == 0)
            {
                Console.WriteLine("\n✓ WERYFIKACJA ZAKOŃCZONA POMYŚLNIE");
                Console.WriteLine("Wszystkie dane na dysku są poprawne.");
            }
            else
            {
                Console.WriteLine("\n✗ WERYFIKACJA ZAKOŃCZONA NIEPOWODZENIEM");
                Console.WriteLine("Dysk może być uszkodzony lub sfałszowany.");
            }
            
            // Pytanie o usunięcie plików testowych
            Console.WriteLine("\nCzy chcesz usunąć pliki testowe? (T/N): ");
            if (Console.ReadLine().Trim().ToUpper() == "T")
            {
                try
                {
                    Directory.Delete(testDir, true);
                    Console.WriteLine("Pliki testowe zostały usunięte.");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Nie można usunąć plików testowych: {ex.Message}");
                }
            }
            
            // Clean up the local checksum file
            try 
            {
                if (File.Exists(localChecksumFile)) 
                {
                    File.Delete(localChecksumFile);
                    Console.WriteLine("Usunięto lokalny plik sum kontrolnych.");
                }
            } 
            catch (Exception ex) 
            {
                Console.WriteLine($"Nie można usunąć pliku sum kontrolnych: {ex.Message}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"\nWystąpił błąd podczas weryfikacji: {ex.Message}");
            
            // Try to clean up even if there was an error
            try 
            {
                if (File.Exists(localChecksumFile)) 
                {
                    File.Delete(localChecksumFile);
                }
            } 
            catch { /* Ignore errors during cleanup */ }
        }
        
        Console.WriteLine("\nNaciśnij dowolny klawisz, aby kontynuować...");
        Console.ReadKey();
    }
    
    // Metoda do wyboru dysku
    static DriveInfo SelectDrive()
    {
        // Znajdź wszystkie dostępne dyski
        DriveInfo[] allDrives = DriveInfo.GetDrives();
        List<DriveInfo> availableDrives = new List<DriveInfo>();
        
        foreach (DriveInfo drive in allDrives)
        {
            // Sprawdź, czy dysk jest gotowy i nie jest dyskiem C:
            if (drive.IsReady && !drive.Name.StartsWith("C", StringComparison.OrdinalIgnoreCase))
            {
                availableDrives.Add(drive);
            }
        }
        
        if (availableDrives.Count == 0)
        {
            Console.WriteLine("Nie znaleziono żadnych podłączonych dysków (oprócz dysku systemowego C:).");
            Console.WriteLine("Podłącz dysk lub pendrive i spróbuj ponownie.");
            return null;
        }
        
        // Wyświetl dostępne dyski
        Console.WriteLine("\nDostępne dyski:");
        for (int i = 0; i < availableDrives.Count; i++)
        {
            DriveInfo drive = availableDrives[i];
            string driveType = drive.DriveType == DriveType.Removable ? "Dysk wymienny (pendrive)" : drive.DriveType.ToString();
            Console.WriteLine($"{i + 1}. Dysk {drive.Name} - {FormatBytes(drive.TotalSize)} - {drive.VolumeLabel} - {driveType}");
        }
        
        // Wybierz dysk
        Console.Write("\nWybierz numer dysku: ");
        int selectedDriveIndex;
        while (!int.TryParse(Console.ReadLine(), out selectedDriveIndex) || 
               selectedDriveIndex < 1 || 
               selectedDriveIndex > availableDrives.Count)
        {
            Console.Write("Nieprawidłowy wybór. Wybierz numer dysku: ");
        }
        
        return availableDrives[selectedDriveIndex - 1];
    }
    
    static void WriteTestDataWithPercentage(DriveInfo selectedDrive, int percentToTest)
    {
        // Oblicz parametry testu
        long totalBytes = selectedDrive.TotalSize;
        long availableBytes = selectedDrive.AvailableFreeSpace;
        
        // Utwórz katalog testowy
        string testDir = Path.Combine(selectedDrive.RootDirectory.FullName, TEST_DIR_NAME);
        
        // Katalog programu do tymczasowego przechowywania sum kontrolnych
        string programDir = GetProgramDirectory();
        string tempChecksumFile = Path.Combine(programDir, CHECKSUMS_FILE);
        string targetChecksumFile = Path.Combine(testDir, CHECKSUMS_FILE);
        
        try
        {
            // Lista do przechowywania pomiarów szybkości
            List<SpeedMeasurement> speedMeasurements = new List<SpeedMeasurement>();
            
            // Wyczyść poprzednie pliki testowe
            if (Directory.Exists(testDir))
            {
                Console.WriteLine("Czyszczenie poprzednich plików testowych...");
                Directory.Delete(testDir, true);
            }
            
            Directory.CreateDirectory(testDir);
            
            // Katalog tymczasowy w katalogu programu
            string localTempDir = Path.Combine(GetProgramDirectory(), "Temp");
            if (Directory.Exists(localTempDir))
            {
                Directory.Delete(localTempDir, true);
            }
            Directory.CreateDirectory(localTempDir);
            
            // 1. Szybki test - zapisz mały plik, aby sprawdzić podstawową funkcjonalność
            Console.WriteLine("\nWykonywanie szybkiego testu zapisu...");
            string localQuickTestFile = Path.Combine(localTempDir, "quicktest.bin");
            string targetQuickTestFile = Path.Combine(testDir, "quicktest.bin");
            
            Stopwatch quickStopwatch = new Stopwatch();
            byte[] quickChecksum = null;
            
            try
            {
                // Najpierw generujemy lokalny plik
                GenerateTestFile(localQuickTestFile, 1024 * 1024, 0);
                
                // Obliczamy sumę kontrolną
                quickChecksum = CalculateFileChecksum(localQuickTestFile);
                
                // Następnie mierzymy czas kopiowania
                quickStopwatch.Start();
                File.Copy(localQuickTestFile, targetQuickTestFile, true);
                quickStopwatch.Stop();
                
                // Usuwamy lokalny plik po skopiowaniu
                File.Delete(localQuickTestFile);
                
                double quickSpeed = (1.0 / quickStopwatch.Elapsed.TotalSeconds);
                Console.WriteLine($"Zakończono zapis: 1,00 MB w {quickStopwatch.Elapsed.TotalSeconds:F1} s ({quickSpeed:F2} MB/s)");
                
                speedMeasurements.Add(new SpeedMeasurement
                {
                    FileName = "Quick",
                    FileSize = 1024 * 1024,
                    SpeedMBps = quickSpeed
                });
                
                Console.WriteLine("Szybki test zapisu zakończony pomyślnie.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\nBŁĄD: Szybki test nie powiódł się! {ex.Message}");
                Console.WriteLine("Możliwy problem z dyskiem lub dostępem do niego.");
                
                // Upewnij się, że lokalny plik zostanie usunięty w przypadku błędu
                if (File.Exists(localQuickTestFile))
                {
                    try { File.Delete(localQuickTestFile); } catch { }
                }
                
                return;
            }
            
            // 2. Pełna weryfikacja pojemności
            Console.WriteLine("\nRozpoczynanie zapisywania danych testowych...");
            
            // Oblicz rozmiar testu (użyj określonego procentu dostępnej przestrzeni)
            double capacityPercent = percentToTest / 100.0;
            // Zastosuj USAGE_PERCENT dla bezpieczeństwa
            long testSize = (long)(availableBytes * capacityPercent * USAGE_PERCENT);
            
            Console.WriteLine($"Testowanie {percentToTest}% pojemności: {FormatBytes(testSize)}");
            
            // Rozmiar każdej porcji do testowania
            int totalChunks = (int)Math.Ceiling((double)testSize / CHUNK_SIZE);
            
            Console.WriteLine($"Liczba plików testowych: {totalChunks}");
            
            // Słownik do przechowywania sum kontrolnych
            Dictionary<string, byte[]> checksums = new Dictionary<string, byte[]>();
            checksums.Add(Path.GetFileName(targetQuickTestFile), quickChecksum);
            
            // Mierzenie całkowitego czasu zapisu
            Stopwatch totalStopwatch = new Stopwatch();
            totalStopwatch.Start();
            
            long writtenSize = 0;
            bool testFailed = false;
            
            // Inicjalizacja paska postępu przed pętlą
            Console.WriteLine("\nPostęp całkowity:");
            DrawProgressBar(0, testSize, 50, "Postęp: ");
            
            for (int i = 0; i < totalChunks; i++)
            {
                if (testFailed)
                    break;
                
                // Oblicz bieżący rozmiar porcji
                long currentChunkSize = Math.Min(CHUNK_SIZE, testSize - writtenSize);
                if (currentChunkSize <= 0)
                    break;
                
                string localChunkFile = Path.Combine(localTempDir, $"test_{i:D4}.bin");
                string targetChunkFile = Path.Combine(testDir, $"test_{i:D4}.bin");
                Console.WriteLine($"\nTest {i+1}/{totalChunks}: Zapisywanie {FormatBytes(currentChunkSize)}...");
                
                try
                {
                    // Generujemy lokalny plik - zoptymalizowane generowanie
                    GenerateTestFile(localChunkFile, currentChunkSize, i + 1);
                    
                    // Obliczamy sumę kontrolną
                    byte[] checksum = CalculateFileChecksum(localChunkFile);
                    
                    // Mierzymy czas kopiowania
                    Stopwatch chunkStopwatch = new Stopwatch();
                    chunkStopwatch.Start();
                    
                    // Kopiujemy plik do dysku docelowego z zoptymalizowanym buforem
                    using (var sourceStream = new FileStream(localChunkFile, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan))
                    using (var destStream = new FileStream(targetChunkFile, FileMode.Create, FileAccess.Write, FileShare.None, 1024 * 1024, FileOptions.WriteThrough))
                    {
                        byte[] buffer = new byte[BUFFER_SIZE]; // Użyj większego bufora
                        int bytesRead;
                        long copiedBytes = 0;
                        
                        while ((bytesRead = sourceStream.Read(buffer, 0, buffer.Length)) > 0)
                        {
                            destStream.Write(buffer, 0, bytesRead);
                            copiedBytes += bytesRead;
                            
                            // Aktualizuj pasek postępu dla bieżącego pliku
                            if (currentChunkSize > 10 * 1024 * 1024) // tylko dla plików > 10MB
                            {
                                Console.Write("\r");
                                Console.Write($"Kopiowanie: [{new string('#', (int)(30 * copiedBytes / currentChunkSize))}{new string(' ', 30 - (int)(30 * copiedBytes / currentChunkSize))}] {(copiedBytes * 100.0 / currentChunkSize):F1}%");
                            }
                        }
                        
                        if (currentChunkSize > 10 * 1024 * 1024)
                            Console.WriteLine(); // nowa linia po zakończeniu kopiowania
                    }
                    
                    chunkStopwatch.Stop();
                    
                    // Usuwamy lokalny plik po skopiowaniu
                    File.Delete(localChunkFile);
                    
                    // Oblicz prędkość w MB/s
                    double chunkSpeed = currentChunkSize / (1024.0 * 1024.0) / chunkStopwatch.Elapsed.TotalSeconds;
                    
                    Console.WriteLine($"Zakończono zapis: {FormatBytes(currentChunkSize)} w {chunkStopwatch.Elapsed.TotalSeconds:F1} s ({chunkSpeed:F2} MB/s)");
                    
                    // Dodaj pomiar prędkości
                    speedMeasurements.Add(new SpeedMeasurement
                    {
                        FileName = $"Plik {i+1}",
                        FileSize = currentChunkSize,
                        SpeedMBps = chunkSpeed
                    });
                    
                    // Dodaj sumę kontrolną do słownika
                    checksums.Add(Path.GetFileName(targetChunkFile), checksum);
                    
                    writtenSize += currentChunkSize;
                    
                    // Aktualizuj główny pasek postępu
                    DrawProgressBar(writtenSize, testSize, 50, "Postęp: ");
                }
                catch (IOException ex)
                {
                    Console.WriteLine($"\nBŁĄD: {ex.Message}");
                    Console.WriteLine($"Nie można zapisać więcej danych. Zapisano tylko {FormatBytes(writtenSize)}.");
                    testFailed = true;
                    
                    // Upewnij się, że lokalny plik zostanie usunięty w przypadku błędu
                    if (File.Exists(localChunkFile))
                    {
                        try { File.Delete(localChunkFile); } catch { }
                    }
                }
            }
            
            totalStopwatch.Stop();
            
            // Usuń katalog tymczasowy
            try
            {
                Directory.Delete(localTempDir, true);
            }
            catch { /* Ignoruj błędy przy usuwaniu katalogu tymczasowego */ }
            
            // Zapisz sumy kontrolne do pliku tymczasowego w katalogu programu
            if (checksums.Count > 0)
            {
                SaveChecksums(tempChecksumFile, checksums);
                
                // Kopiuj plik sum kontrolnych do katalogu testowego na docelowym dysku
                try
                {
                    File.Copy(tempChecksumFile, targetChecksumFile, true);
                    Console.WriteLine($"Plik sum kontrolnych został skopiowany do katalogu testowego.");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Błąd podczas kopiowania pliku sum kontrolnych: {ex.Message}");
                }
                
                // Zapisz też plik z podstawowymi informacjami o teście
                string infoFile = Path.Combine(testDir, "test_info.txt");
                using (StreamWriter writer = new StreamWriter(infoFile))
                {
                    writer.WriteLine($"Data testu: {DateTime.Now}");
                    writer.WriteLine($"Nazwa dysku: {selectedDrive.Name}");
                    writer.WriteLine($"Etykieta woluminu: {selectedDrive.VolumeLabel}");
                    writer.WriteLine($"Deklarowana pojemność: {FormatBytes(selectedDrive.TotalSize)}");
                    writer.WriteLine($"Testowany procent pojemności: {percentToTest}%");
                    writer.WriteLine($"Zapisano danych: {FormatBytes(writtenSize)}");
                    writer.WriteLine($"Liczba plików testowych: {checksums.Count}");
                    writer.WriteLine($"Całkowity czas zapisu: {totalStopwatch.Elapsed.TotalSeconds:F1} sekund");
                }
            }
            
            // Wyniki
            if (!testFailed)
            {
                Console.WriteLine("\n✓ ZAPIS ZAKOŃCZONY POMYŚLNIE");
                if (percentToTest == 100)
                {
                    Console.WriteLine($"Zapisano {FormatBytes(writtenSize)} z deklarowanej pojemności {FormatBytes(totalBytes)}");
                }
                else
                {
                    Console.WriteLine($"Zapisano {FormatBytes(writtenSize)} ({percentToTest}% pojemności)");
                }
                Console.WriteLine($"Całkowity czas zapisu: {totalStopwatch.Elapsed.TotalSeconds:F1} sekund");
                
                if (percentToTest == 100)
                {
                    if (writtenSize >= totalBytes * 0.95)
                    {
                        Console.WriteLine("Pojemność dysku wydaje się być zgodna z deklarowaną.");
                    }
                    else
                    {
                        Console.WriteLine("Pojemność dysku może być mniejsza niż deklarowana.");
                        Console.WriteLine($"Zapisano tylko {(writtenSize * 100.0 / totalBytes):F1}% deklarowanej pojemności.");
                    }
                }
                
                // Rysuj wykres szybkości zapisu ze średnią (ważoną, ale bez tego słowa)
                DrawSimpleSpeedChart(speedMeasurements, "WYKRES SZYBKOŚCI ZAPISU", "MB/s");
                
                Console.WriteLine("\nMożesz teraz bezpiecznie odłączyć dysk (jeśli jest wymiennym nośnikiem).");
                Console.WriteLine("Aby zweryfikować dane, podłącz ponownie dysk i wybierz opcję 'Zweryfikuj dane na dysku'.");
            }
            
            // Clean up the temporary checksum file
            try 
            {
                if (File.Exists(tempChecksumFile)) 
                {
                    File.Delete(tempChecksumFile);
                    Console.WriteLine("Usunięto tymczasowy plik sum kontrolnych.");
                }
            } 
            catch (Exception ex) 
            {
                Console.WriteLine($"Nie można usunąć pliku sum kontrolnych: {ex.Message}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"\nWystąpił błąd podczas testu: {ex.Message}");
            
            // Try to clean up even if there was an error
            try 
            {
                if (File.Exists(tempChecksumFile)) 
                {
                    File.Delete(tempChecksumFile);
                }
            } 
            catch { /* Ignore errors during cleanup */ }
        }
        
        Console.WriteLine("\nNaciśnij dowolny klawisz, aby kontynuować...");
        Console.ReadKey();
    }
    
    // Zoptymalizowana metoda do generowania pliku testowego
    static void GenerateTestFile(string filePath, long size, int seed)
    {
        // Użyj większego bufora dla lepszej wydajności
        byte[] buffer = new byte[BUFFER_SIZE]; // 128 MB bufor
        Random rnd = new Random(seed);
        
        // Wygeneruj losowe dane tylko raz
        rnd.NextBytes(buffer);
        
        // Użyj optymalizacji dostępu sekwencyjnego i większy bufor
        using (FileStream fs = new FileStream(filePath, FileMode.Create, FileAccess.Write, FileShare.None, 1024 * 1024, FileOptions.WriteThrough))
        {
            long remainingBytes = size;
            long totalWritten = 0;
            int chunkIndex = 0;
            
            // Inicjalizacja paska postępu tylko dla dużych plików
            bool showProgress = size > 100 * 1024 * 1024;
            if (showProgress)
            {
                Console.WriteLine("Generowanie pliku testowego:");
                DrawProgressBar(0, size, 40, "Postęp: ");
            }
            
            while (remainingBytes > 0)
            {
                // Określ ile zapisać w tej iteracji
                int bytesToWrite = (int)Math.Min(BUFFER_SIZE, remainingBytes);
                
                // Zmodyfikuj bufor dla kolejnych bloków, aby zapewnić losowość
                // Szybsza metoda modyfikacji bufora
                if (chunkIndex > 0)
                {
                    // Szybka modyfikacja bufora - XOR pierwszych kilku bajtów z wartością zależną od indeksu
                    byte xorValue = (byte)((chunkIndex * 13 + seed * 7) & 0xFF);
                    for (int i = 0; i < 4096 && i < bytesToWrite; i += 64)
                    {
                        buffer[i] ^= xorValue;
                    }
                }
                
                // Zapisz bufor
                fs.Write(buffer, 0, bytesToWrite);
                
                // Aktualizuj liczniki
                remainingBytes -= bytesToWrite;
                totalWritten += bytesToWrite;
                chunkIndex++;
                
                // Pokaż postęp dla dużych plików
                if (showProgress && totalWritten % (16 * 1024 * 1024) == 0)
                {
                    DrawProgressBar(totalWritten, size, 40, "Postęp: ");
                }
            }
            
            fs.Flush();
            
            // Finalizacja paska postępu
            if (showProgress)
            {
                DrawProgressBar(size, size, 40, "Postęp: ");
                Console.WriteLine("Zakończono generowanie pliku testowego.");
            }
        }
    }
    
    // Oblicz sumę kontrolną pliku
    static byte[] CalculateFileChecksum(string filePath)
    {
        using (var md5 = MD5.Create())
        using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read, 4 * 1024 * 1024, FileOptions.SequentialScan))
        {
            byte[] buffer = new byte[8 * 1024 * 1024]; // Zwiększono do 8 MB bufor
            int bytesRead;
            long totalBytesRead = 0;
            long fileSize = new FileInfo(filePath).Length;
            
            // Pokaż pasek postępu tylko dla dużych plików
            bool showProgress = fileSize > 100 * 1024 * 1024;
            if (showProgress)
            {
                Console.WriteLine("Obliczanie sumy kontrolnej:");
                DrawProgressBar(0, fileSize, 40, "Postęp: ");
            }
            
            while ((bytesRead = stream.Read(buffer, 0, buffer.Length)) > 0)
            {
                md5.TransformBlock(buffer, 0, bytesRead, buffer, 0);
                
                totalBytesRead += bytesRead;
                
                // Pokaż postęp dla dużych plików
                if (showProgress && totalBytesRead % (32 * 1024 * 1024) == 0)
                {
                    DrawProgressBar(totalBytesRead, fileSize, 40, "Postęp: ");
                }
            }
            
            md5.TransformFinalBlock(new byte[0], 0, 0);
            
            // Finalizacja paska postępu
            if (showProgress)
            {
                DrawProgressBar(fileSize, fileSize, 40, "Postęp: ");
                Console.WriteLine("Zakończono obliczanie sumy kontrolnej.");
            }
            
            return md5.Hash;
        }
    }
    
    // Zapisz sumy kontrolne do pliku
    static void SaveChecksums(string filePath, Dictionary<string, byte[]> checksums)
    {
        using (FileStream fs = new FileStream(filePath, FileMode.Create, FileAccess.Write))
        using (BinaryWriter writer = new BinaryWriter(fs))
        {
            // Zapisz liczbę wpisów
            writer.Write(checksums.Count);
            
            // Zapisz każdą parę (nazwa pliku, suma kontrolna)
            foreach (var entry in checksums)
            {
                writer.Write(entry.Key);
                writer.Write(entry.Value.Length);
                writer.Write(entry.Value);
            }
        }
        
        Console.WriteLine($"Zapisano sumy kontrolne dla {checksums.Count} plików.");
    }
    
    // Odczytaj sumy kontrolne z pliku
    static Dictionary<string, byte[]> LoadChecksums(string filePath)
    {
        Dictionary<string, byte[]> checksums = new Dictionary<string, byte[]>();
        
        using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
        using (BinaryReader reader = new BinaryReader(fs))
        {
            // Odczytaj liczbę wpisów
            int count = reader.ReadInt32();
            
            // Odczytaj każdą parę (nazwa pliku, suma kontrolna)
            for (int i = 0; i < count; i++)
            {
                string fileName = reader.ReadString();
                int checksumLength = reader.ReadInt32();
                byte[] checksum = reader.ReadBytes(checksumLength);
                
                checksums.Add(fileName, checksum);
            }
        }
        
        return checksums;
    }
    
    // Porównaj dwie sumy kontrolne
    static bool CompareChecksums(byte[] checksum1, byte[] checksum2)
    {
        if (checksum1 == null || checksum2 == null)
            return false;
            
        if (checksum1.Length != checksum2.Length)
            return false;
            
        for (int i = 0; i < checksum1.Length; i++)
        {
            if (checksum1[i] != checksum2[i])
                return false;
        }
        
        return true;
    }
    
    // Klasa do przechowywania zagregowanych pomiarów z min/max wartościami
    private class AggregatedSpeedMeasurement : SpeedMeasurement
    {
        public double MinSpeed { get; set; }
        public double MaxSpeed { get; set; }
    }
    
    // Agreguj pomiary prędkości dla lepszej wizualizacji
    static List<AggregatedSpeedMeasurement> AggregateSpeedMeasurements(List<SpeedMeasurement> measurements, int targetCount)
    {
        List<AggregatedSpeedMeasurement> result = new List<AggregatedSpeedMeasurement>();
        
        if (measurements.Count <= targetCount)
        {
            // Konwertuj pojedyncze pomiary na zagregowane
            foreach (var m in measurements)
            {
                result.Add(new AggregatedSpeedMeasurement
                {
                    FileName = m.FileName,
                    FileSize = m.FileSize,
                    SpeedMBps = m.SpeedMBps,
                    MinSpeed = m.SpeedMBps,
                    MaxSpeed = m.SpeedMBps
                });
            }
            return result;
        }
        
        // Kopiujemy wszystkie pomiary oprócz szybkiego testu, który wykluczamy z wykresu
        List<SpeedMeasurement> filesToAggregate = measurements.Where(m => m.FileName != "Quick").ToList();
        
        if (filesToAggregate.Count == 0)
            return new List<AggregatedSpeedMeasurement>(); // Jeśli nie ma pomiarów po filtrowaniu
            
        // Oblicz ile pomiarów połączyć w jedną grupę
        int groupSize = (int)Math.Ceiling(filesToAggregate.Count / (double)targetCount);
        
        // Grupuj pomiary
        for (int i = 0; i < filesToAggregate.Count; i += groupSize)
        {
            // Pobierz grupę pomiarów
            var group = filesToAggregate.Skip(i).Take(groupSize).ToList();
            
            if (group.Count > 0)
            {
                // Oblicz średnią ważoną prędkość dla tej grupy, ważoną rozmiarem pliku
                long totalSizeInGroup = group.Sum(m => m.FileSize);
                double weightedAvgSpeed = 0;
                double minSpeed = group.Min(m => m.SpeedMBps);
                double maxSpeed = group.Max(m => m.SpeedMBps);
                
                foreach (var m in group)
                {
                    double weight = (double)m.FileSize / totalSizeInGroup;
                    weightedAvgSpeed += m.SpeedMBps * weight;
                }
                
                // Określ zakres plików w tej grupie
                int startIdx = int.MaxValue;
                int endIdx = int.MinValue;
                
                foreach (var m in group)
                {
                    if (m.FileName.StartsWith("Plik "))
                    {
                        string numPart = m.FileName.Substring(5);
                        int num;
                        if (int.TryParse(numPart, out num))
                        {
                            startIdx = Math.Min(startIdx, num);
                            endIdx = Math.Max(endIdx, num);
                        }
                    }
                }
                
                // Jeśli nie udało się ustalić zakresu, użyj numeru indeksu grupy
                if (startIdx == int.MaxValue || endIdx == int.MinValue)
                {
                    startIdx = i / groupSize + 1;
                    endIdx = startIdx;
                }
                
                // Utwórz nowy pomiar reprezentujący tę grupę
                // Jeśli grupa zawiera tylko jeden plik, nie używaj zakresu
                string fileName;
                if (startIdx == endIdx) {
                    fileName = $"{startIdx}";
                } else {
                    fileName = $"{startIdx}-{endIdx}";
                }
                
                result.Add(new AggregatedSpeedMeasurement
                {
                    FileName = fileName,
                    FileSize = totalSizeInGroup,
                    SpeedMBps = weightedAvgSpeed,
                    MinSpeed = minSpeed,
                    MaxSpeed = maxSpeed
                });
            }
        }
        
        return result;
    }
    
    // Rysuj uproszczony wykres szybkości w konsoli z lepszymi etykietami
    static void DrawSimpleSpeedChart(List<SpeedMeasurement> measurements, string title, string unit)
    {
        if (measurements == null || measurements.Count == 0)
            return;
            
        // Oblicz średnią ważoną bez szybkiego testu
        var measurementsWithoutQuick = measurements.Where(m => m.FileName != "Quick").ToList();
        if (measurementsWithoutQuick.Count == 0)
            return;
        
        // Oblicz średnią ważoną na podstawie rozmiarów plików (bez quick testu)
        double totalSize = measurementsWithoutQuick.Sum(m => m.FileSize);
        double weightedAvg = 0;
        foreach (var m in measurementsWithoutQuick)
        {
            double weight = (double)m.FileSize / totalSize;
            weightedAvg += m.SpeedMBps * weight;
        }
        
        // Utwórz zagregowane pomiary, jeśli mamy za dużo (również bez quick testu)
        List<AggregatedSpeedMeasurement> displayMeasurements;
        bool isAggregated = false;
        
        if (measurementsWithoutQuick.Count > MAX_DISPLAY_BARS)
        {
            isAggregated = true;
            displayMeasurements = AggregateSpeedMeasurements(measurementsWithoutQuick, MAX_DISPLAY_BARS);
        }
        else
        {
            // Przekształć standardowe pomiary na zagregowane z min/max
            displayMeasurements = new List<AggregatedSpeedMeasurement>();
            foreach (var m in measurementsWithoutQuick)
            {
                displayMeasurements.Add(new AggregatedSpeedMeasurement
                {
                    FileName = m.FileName,
                    FileSize = m.FileSize,
                    SpeedMBps = m.SpeedMBps,
                    MinSpeed = m.SpeedMBps,
                    MaxSpeed = m.SpeedMBps
                });
            }
        }
        
        if (displayMeasurements.Count == 0)
            return;
            
        Console.WriteLine($"\n{title}");
        Console.WriteLine(new string('=', title.Length));
        
        // Oblicz statystyki z pomiarów (bez quick testu)
        double originalMin = measurementsWithoutQuick.Min(m => m.SpeedMBps);
        double originalMax = measurementsWithoutQuick.Max(m => m.SpeedMBps);
        
        // Dla wykresu, użyj zakresu od 0 do max * 1.1, zaokrąglonego do najbliższej 5
        double minSpeed = 0; // Zacznij od 0 dla lepszego odniesienia wizualnego
        double maxSpeed = Math.Ceiling(Math.Max(originalMax, weightedAvg) * 1.1 / 5) * 5;
        
        // Wyświetl statystyki
        Console.WriteLine($"Min: {originalMin:F2} {unit}, Max: {originalMax:F2} {unit}");
        Console.WriteLine($"Średnia: {weightedAvg:F2} {unit}");
        
        if (isAggregated)
        {
            Console.WriteLine($"(Zagregowano {measurementsWithoutQuick.Count} pomiarów do {displayMeasurements.Count} słupków)");
            
            // Wyświetl legendę agregacji
            Console.WriteLine("\nLegenda słupków:");
            
            const int legendItemsPerRow = 3;
            int legendItemsCount = 0;
            
            foreach (var m in displayMeasurements)
            {
                string legendItem;
                
                if (m.FileName == "Quick")
                {
                    legendItem = "Q = Szybki test (quicktest.bin)";
                }
                else if (m.FileName.Contains("-"))
                {
                    // To jest zakres plików
                    string[] parts = m.FileName.Split('-');
                    if (parts.Length == 2)
                    {
                        int start, end;
                        if (int.TryParse(parts[0], out start) && int.TryParse(parts[1], out end))
                        {
                            legendItem = $"{parts[0]}-{parts[1]} = Pliki {start} do {end}";
                        }
                        else
                        {
                            legendItem = $"{m.FileName} = Zagregowana grupa plików";
                        }
                    }
                    else
                    {
                        legendItem = $"{m.FileName} = Zagregowana grupa plików";
                    }
                }
                else
                {
                    // Pojedynczy plik
                    legendItem = $"{m.FileName} = Plik {m.FileName}";
                }
                
                // Wyrównaj szerokość legendy
                Console.Write(legendItem.PadRight(30));
                
                legendItemsCount++;
                if (legendItemsCount % legendItemsPerRow == 0)
                {
                    Console.WriteLine();
                }
            }
            
            // Jeśli ostatni wiersz nie był pełny, dodaj nową linię
            if (legendItemsCount % legendItemsPerRow != 0)
            {
                Console.WriteLine();
            }
            
            Console.WriteLine();
        }
        
        // Oblicz wysokość słupków dla każdego pomiaru
        double speedRange = maxSpeed - minSpeed;
        if (speedRange <= 0) speedRange = 1; // Unikaj dzielenia przez zero
        
        // Tablica przechowująca wysokości słupków, min i max wartości
        int[] barHeights = new int[displayMeasurements.Count];
        int[] minHeights = new int[displayMeasurements.Count];
        int[] maxHeights = new int[displayMeasurements.Count];
        
        for (int i = 0; i < displayMeasurements.Count; i++)
        {
            // Wysokość słupka (wartość średnia)
            double normalizedHeight = (displayMeasurements[i].SpeedMBps - minSpeed) / speedRange;
            barHeights[i] = (int)Math.Round(normalizedHeight * (CHART_HEIGHT - 1));
            barHeights[i] = Math.Max(0, Math.Min(CHART_HEIGHT - 1, barHeights[i]));
            
            // Wysokość minimalnej wartości
            double normalizedMin = (displayMeasurements[i].MinSpeed - minSpeed) / speedRange;
            minHeights[i] = (int)Math.Round(normalizedMin * (CHART_HEIGHT - 1));
            minHeights[i] = Math.Max(0, Math.Min(CHART_HEIGHT - 1, minHeights[i]));
            
            // Wysokość maksymalnej wartości
            double normalizedMax = (displayMeasurements[i].MaxSpeed - minSpeed) / speedRange;
            maxHeights[i] = (int)Math.Round(normalizedMax * (CHART_HEIGHT - 1));
            maxHeights[i] = Math.Max(0, Math.Min(CHART_HEIGHT - 1, maxHeights[i]));
        }
        
        // Oblicz dokładną wysokość dla średniej (teraz używamy średniej ważonej bez quicktestu)
        double exactAvgLinePosition = ((weightedAvg - minSpeed) / speedRange) * (CHART_HEIGHT - 1);
        int avgLineHeight = (int)Math.Round(exactAvgLinePosition);
        avgLineHeight = Math.Min(avgLineHeight, CHART_HEIGHT - 1);
        avgLineHeight = Math.Max(avgLineHeight, 0);
        
        // Ustal szerokość słupków i odstępy
        int barWidth = 2;       // Stała szerokość słupka dla lepszej czytelności
        int spaceWidth = 5;     // Zwiększono odstęp między słupkami dla lepszej czytelności
        
        // Rysuj wykres słupkowy
        for (int y = CHART_HEIGHT - 1; y >= 0; y--)
        {
            // Oblicz wartość prędkości dla tej linii
            double speed = minSpeed + (y / (double)(CHART_HEIGHT - 1)) * speedRange;
            
            // Rysuj wartość na osi Y (wyrównana do prawej) z jednostką
            Console.Write($"{speed,6:F1} MB/s │");
            
            // Rysuj poziomą linię wykresu z wartościami dla każdego pliku
            for (int i = 0; i < displayMeasurements.Count; i++)
            {
                // Rysuj słupek i "wąsy" min-max
                for (int x = 0; x < barWidth; x++)
                {
                    char charToDraw = ' ';
                    
                    // POPRAWIONA LOGIKA RYSOWANIA
                    // Określ wartości logiczne dla różnych pozycji na wykresie
                    bool isAtMax = y == maxHeights[i];
                    bool isAtMin = y == minHeights[i] && minHeights[i] != barHeights[i];
                    bool isAtAvgLine = y == avgLineHeight;
                    bool isBelowOrAtBar = y <= barHeights[i]; // Na lub poniżej średniej (pełne bloki)
                    bool isAboveBarBelowMax = y > barHeights[i] && y <= maxHeights[i]; // Między średnią a max
                    
                    // Ustal priorytety rysowania (od najwyższego)
                    if (isAtMax)
                    {
                        charToDraw = 'T'; // Górny "wąs"
                    }
                    else if (isAtMin)
                    {
                        charToDraw = '┴'; // Dolny "wąs"
                    }
                    else if (isBelowOrAtBar)
                    {
                        charToDraw = '█'; // Pełny blok dla części poniżej i na poziomie średniej
                    }
                    else if (isAboveBarBelowMax)
                    {
                        charToDraw = '░'; // Lekki blok dla części między średnią a max
                    }
                    else if (isAtAvgLine)
                    {
                        charToDraw = '─'; // Linia średniej ma najniższy priorytet
                    }
                    
                    Console.Write(charToDraw);
                }
                
                // Dodaj odstęp między słupkami
                if (i < displayMeasurements.Count - 1)
                {
                    for (int s = 0; s < spaceWidth; s++)
                    {
                        // Draw average line across gaps
                        if (y == avgLineHeight)
                        {
                            Console.Write('─');
                        }
                        else
                        {
                            Console.Write(' ');
                        }
                    }
                }
            }
            
            Console.WriteLine();
        }
        
        // Rysuj oś X jako ciągłą linię - z dostosowanym marginesem dla etykiet MB/s
        Console.Write("            └"); // 12 spacji
        
        // Oblicz całkowitą długość linii osi X
        int totalXAxisLength = displayMeasurements.Count * barWidth + 
                              (displayMeasurements.Count - 1) * spaceWidth;
        
        // Rysuj ciągłą linię
        Console.Write(new string('─', totalXAxisLength));
        Console.WriteLine("→");
        
        // Przygotuj etykiety osi X
        List<string> startLabels = new List<string>();  // Początek zakresu lub pojedyncza wartość
        List<string> endLabels = new List<string>();    // Koniec zakresu (jeśli istnieje)
        List<bool> hasRange = new List<bool>();         // Czy dana etykieta ma zakres
        
        foreach (var m in displayMeasurements)
        {
            if (m.FileName == "Quick")
            {
                startLabels.Add("Q");
                endLabels.Add("");
                hasRange.Add(false);
            }
            else if (m.FileName.Contains("-"))
            {
                // Dla zakresów plików, rozdzielamy na dwie części
                string[] parts = m.FileName.Split('-');
                startLabels.Add(parts[0]);
                endLabels.Add(parts.Length > 1 ? parts[1] : "");
                hasRange.Add(true);
            }
            else
            {
                // Dla pojedynczych plików, usuwamy prefiks "Plik "
                string label = m.FileName.StartsWith("Plik ") ? m.FileName.Substring(5) : m.FileName;
                startLabels.Add(label);
                endLabels.Add("");
                hasRange.Add(false);
            }
        }
        
        // Rysuj znaczniki pod słupkami - z dostosowanym marginesem dla etykiet MB/s
        Console.Write("             "); // 13 spacji
        for (int i = 0; i < displayMeasurements.Count; i++)
        {
            // Znacznik dla słupka 
            Console.Write(hasRange[i] ? "┬" : "│");
            
            // Wypełnienie reszty szerokości słupka
            Console.Write(new string(' ', barWidth - 1));
            
            // Dodaj odstęp po słupku
            if (i < displayMeasurements.Count - 1)
            {
                Console.Write(new string(' ', spaceWidth));
            }
        }
        Console.WriteLine();
        
        // Generowanie etykiet
        StringBuilder topLine = new StringBuilder();
        StringBuilder bottomLine = new StringBuilder();
        
        // Początkowo wypełnij oba wiersze spacjami
        for (int i = 0; i < 200; i++) {
            topLine.Append(' ');
            bottomLine.Append(' ');
        }
        
        // Pozycje początkowe dla każdej etykiety w górnym wierszu
        int[] topLabelPos = new int[displayMeasurements.Count];
        for (int i = 0; i < displayMeasurements.Count; i++) {
            topLabelPos[i] = i * (barWidth + spaceWidth);
            
            // Wstaw etykietę górnego wiersza
            string label = startLabels[i];
            for (int j = 0; j < label.Length; j++) {
                topLine[topLabelPos[i] + j] = label[j];
            }
        }
        
        // Umieść dolny wiersz etykiet dokładnie pod odpowiednimi górnymi etykietami
        for (int i = 0; i < displayMeasurements.Count; i++) {
            if (hasRange[i]) {
                // Pozycja znaku └ (pod PIERWSZYM znakiem górnej etykiety)
                int arrowPos = topLabelPos[i]; // Pierwsza cyfra
                bottomLine[arrowPos] = '└';
                
                // Wstaw etykietę dolnego wiersza zaraz po znaku └
                string label = endLabels[i];
                for (int j = 0; j < label.Length; j++) {
                    bottomLine[arrowPos + 1 + j] = label[j];
                }
                
                // Dostosowanie pozycji następnych etykiet
                if (i < displayMeasurements.Count - 1) {
                    // Znajdź pozycję końca obecnej etykiety dolnego wiersza
                    int currentEndPos = arrowPos + 1 + label.Length;
                    
                    // Oblicz minimalną pozycję dla początku następnej etykiety górnego wiersza
                    int nextMinPos = currentEndPos + 2;  // 2 spacje minimalnego odstępu
                    
                    // Jeśli następna etykieta górnego wiersza koliduje, przesuń ją
                    if (topLabelPos[i+1] < nextMinPos) {
                        // Oblicz o ile musimy przesunąć
                        int shift = nextMinPos - topLabelPos[i+1];
                        
                        // Przesuń wszystkie pozostałe etykiety
                        for (int j = i+1; j < displayMeasurements.Count; j++) {
                            topLabelPos[j] += shift;
                            
                            // Aktualizuj górny wiersz (wyczyść starą pozycję i wstaw w nowej)
                            // Najpierw wyczyść stary region
                            for (int k = 0; k < startLabels[j].Length; k++) {
                                topLine[topLabelPos[j] - shift + k] = ' ';
                            }
                            
                            // Wstaw etykietę w nowej pozycji
                            for (int k = 0; k < startLabels[j].Length; k++) {
                                topLine[topLabelPos[j] + k] = startLabels[j][k];
                            }
                        }
                    }
                }
            }
        }
        
        // Przytnij obie linie do ich faktycznej długości
        int maxLength = 0;
        for (int i = 199; i >= 0; i--) {
            if (topLine[i] != ' ' || bottomLine[i] != ' ') {
                maxLength = i + 1;
                break;
            }
        }
        
        // Wyświetl linie z odpowiednim wcięciem - dostosowanym dla etykiet MB/s
        Console.WriteLine("             " + topLine.ToString().Substring(0, maxLength)); // 13 spacji
        if (hasRange.Any(h => h)) {
            Console.WriteLine("             " + bottomLine.ToString().Substring(0, maxLength)); // 13 spacji
        }
        
        // Dodaj legendę dla średniej i wąsów
        Console.WriteLine();
        Console.WriteLine($"─── Linia średniej (ogólna): {weightedAvg:F2} {unit}");
        Console.WriteLine($"█ Wypełnione bloki kończą się na poziomie średniej dla każdego słupka");
        Console.WriteLine($"░ Lekkie bloki pokazują przedział od średniej do max");
        Console.WriteLine($"T┴ Wąsy wskazują min-max wartości dla każdego słupka");
    }
    
    // Metoda rysująca pasek postępu
    static void DrawProgressBar(long current, long total, int width = 50, string prefix = "")
    {
        // Oblicz procent ukończenia
        double percent = (double)current / total;
        percent = Math.Min(1.0, Math.Max(0.0, percent)); // Upewnij się, że wartość jest w zakresie 0-1
        
        int completeWidth = (int)(width * percent);
        
        // Stwórz pasek postępu
        string progressBar = "[";
        for (int i = 0; i < width; i++)
        {
            if (i < completeWidth)
                progressBar += "█"; // Wypełniona część
            else if (i == completeWidth && i < width)
                progressBar += ">"; // Wskaźnik aktualnej pozycji
            else
                progressBar += "░"; // Niewypełniona część (użyto jaśniejszego znaku dla lepszego kontrastu)
        }
        progressBar += "]";
        
        // Stwórz pełny tekst z paskiem, procentem i informacją o rozmiarze
        string display = $"\r{prefix}{progressBar} {percent:P1} ({FormatBytes(current)}/{FormatBytes(total)})";
        
        // Wypisz do konsoli (nadpisując poprzednią linię)
        Console.Write(display);
        
        // Dodaj nową linię jeśli ukończono
        if (current >= total)
            Console.WriteLine();
    }
    
    // Metoda pomocnicza do formatowania rozmiarów w bajtach
    static string FormatBytes(long bytes)
    {
        string[] suffix = { "B", "KB", "MB", "GB", "TB" };
        int i;
        double dblSByte = bytes;
        
        for (i = 0; i < suffix.Length && bytes >= 1024; i++, bytes /= 1024)
        {
            dblSByte = bytes / 1024.0;
        }
        
        return $"{dblSByte:N2} {suffix[i]}";
    }
}