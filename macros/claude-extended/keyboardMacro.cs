using System;
using System.Windows.Forms;
using System.Threading;
using System.Runtime.InteropServices;
using System.Text;
using System.Diagnostics;
using System.Collections.Generic;
using System.Drawing;

namespace KeyboardMacro
{
    public class KeyboardMacroApp : Form
    {
        // Import funkcji Windows API dla klawiatury
        [DllImport("user32.dll")]
        public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
        
        // Funkcje Windows API dla myszy
        [DllImport("user32.dll")]
        public static extern bool SetCursorPos(int x, int y);
        
        [DllImport("user32.dll")]
        public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, UIntPtr dwExtraInfo);
        
        // Funkcje do zarządzania oknami
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();
        
        [DllImport("user32.dll")]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
        
        [DllImport("user32.dll")]
        private static extern int GetWindowTextLength(IntPtr hWnd);
        
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
        
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsWindowVisible(IntPtr hWnd);
        
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SetForegroundWindow(IntPtr hWnd);
        
        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
        
        [DllImport("user32.dll")]
        private static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
        
        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        
        [DllImport("user32.dll")]
        private static extern IntPtr SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
        
        // Import dla natywnego MessageBox (zawsze na wierzchu)
        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto, EntryPoint = "MessageBoxW")]
        private static extern int NativeMessageBox(IntPtr hWnd, String text, String caption, uint type);
        
        // Stałe dla ShowWindow
        const int SW_RESTORE = 9;
        const int SW_NORMAL = 1;
        
        // Stałe dla SetWindowPos
        static readonly IntPtr HWND_TOP = new IntPtr(0);
        const uint SWP_SHOWWINDOW = 0x0040;
        
        // Stałe dla natywnego MessageBox
        private const uint MB_OK = 0x00000000;
        private const uint MB_OKCANCEL = 0x00000001; // OK i Anuluj
        private const uint MB_ICONINFORMATION = 0x00000040;
        private const uint MB_TOPMOST = 0x00040000; // Zawsze na wierzchu
        
        // Zwracane wartości z MessageBox
        private const int IDOK = 1;
        private const int IDCANCEL = 2;
        
        // Struktura do przechowywania koordynatów okna
        [StructLayout(LayoutKind.Sequential)]
        public struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
            
            public int Width { get { return Right - Left; } }
            public int Height { get { return Bottom - Top; } }
            
            public override string ToString()
            {
                return string.Format("Left: {0}, Top: {1}, Right: {2}, Bottom: {3}, Width: {4}, Height: {5}", 
                    Left, Top, Right, Bottom, Width, Height);
            }
        }
        
        // Delegat dla funkcji EnumWindows
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        
        // Stałe dla operacji myszy
        const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        const uint MOUSEEVENTF_LEFTUP = 0x0004;
        
        // Stałe potrzebne do symulacji klawiszy
        const byte VK_CTRL = 0x11;    // Klawisz Control
        const byte VK_SHIFT = 0x10;   // Klawisz Shift
        const byte VK_C = 0x43;       // Klawisz C
        const byte VK_V = 0x56;       // Klawisz V
        const byte VK_A = 0x41;       // Klawisz A
        const byte VK_T = 0x54;       // Klawisz T
        const byte VK_RETURN = 0x0D;  // Enter/Return
        const byte VK_LWIN = 0x5B;    // Lewy klawisz Windows
        const byte VK_H = 0x48;       // Klawisz H
        const byte VK_DELETE = 0x2E;  // Klawisz Delete
        const uint KEYEVENTF_KEYDOWN = 0x0000;
        const uint KEYEVENTF_KEYUP = 0x0002;
        
        // Maksymalny czas oczekiwania na Claude w milisekundach (15 sekund)
        const int MAX_WAIT_TIME = 15000;
        
        // Docelowy rozmiar i pozycja okna Claude - z dala od krawędzi ekranu
        const int CLAUDE_WINDOW_WIDTH = 1200;  // Zmienione z 1500 na 1200
        const int CLAUDE_WINDOW_HEIGHT = 600;  // Zmienione z 500 na 600
        
        // Współrzędne elementów interfejsu jako procent szerokości/wysokości okna
        const double NEW_CHAT_BUTTON_X_PERCENT = 0.02;  // Bez zmian
        const double NEW_CHAT_BUTTON_Y_PERCENT = 0.197; // Przesunięte minimalnie w dół (z 0.195)
        
        const double TEXT_FIELD_X_PERCENT = 0.45;       // Bez zmian
        const double TEXT_FIELD_Y_PERCENT = 0.58;       // Zmienione z 0.65 na 0.58 - przesunięte wyżej
        
        const double EXTENDED_THINKING_X_PERCENT = 0.29; // Przesunięte bardziej w prawo (z 0.26)
        const double EXTENDED_THINKING_Y_PERCENT = 0.669; // Dostosowane do tej samej wysokości co NEXT_BUTTON_Y_PERCENT
        
        // Stała dla przycisku wyłączającego Extended Thinking (kilkadziesiąt pikseli obok)
        const double DISABLE_EXTENDED_THINKING_X_PERCENT = 0.29 + 0.033; // Przesunięte w prawo od Extended Thinking
        const double DISABLE_EXTENDED_THINKING_Y_PERCENT = 0.669; // Ta sama wysokość
        
        // Nowa stała dla przycisku po prawej stronie Extended Thinking
        const double NEXT_BUTTON_X_PERCENT = 0.382; // Minimalne dodatkowe przesunięcie w prawo
        const double NEXT_BUTTON_Y_PERCENT = 0.669; // Przesunięcie do góry (względem EXTENDED_THINKING_Y_PERCENT = 0.67)
        
        // Stała dla przycisku wyłączającego Extended Thinking gdy pasek boczny jest rozwinięty
        const double DISABLE_EXTENDED_THINKING_EXPANDED_X_PERCENT = 0.382 + 0.033; // Przesunięte w prawo od NEXT_BUTTON
        const double DISABLE_EXTENDED_THINKING_EXPANDED_Y_PERCENT = 0.669; // Ta sama wysokość
        
        // Opcjonalne stałe koordynatów absolutnych - można używać alternatywnie do procentowych
        const int NEW_CHAT_BUTTON_X = 40;  // Przesunięte troszeczeczkę w prawo (z 38)
        const int NEW_CHAT_BUTTON_Y = 125;  // Przesunięte troszeczeczkę w dół (z 122)
        
        const int TEXT_FIELD_X = 510;      // Bez zmian
        const int TEXT_FIELD_Y = 470;      // Zmienione z 510 na 470 - przesunięte wyżej
        
        const int EXTENDED_THINKING_X = 280;      // Przesunięte w prawo (z 250)
        const int EXTENDED_THINKING_Y = 399;      // Dostosowane do tej samej wysokości co NEXT_BUTTON_Y
        
        // Stała dla przycisku wyłączającego Extended Thinking (w pikselach)
        const int DISABLE_EXTENDED_THINKING_X = 280 + 40;  // 40 pikseli w prawo od Extended Thinking
        const int DISABLE_EXTENDED_THINKING_Y = 399;       // Ta sama wysokość
        
        // Nowa stała dla przycisku po prawej stronie Extended Thinking
        const int NEXT_BUTTON_X = 402;      // Minimalne dodatkowe przesunięcie w prawo
        const int NEXT_BUTTON_Y = 399;      // Przesunięcie do góry (względem EXTENDED_THINKING_Y = 400)
        
        // Stała dla przycisku wyłączającego Extended Thinking gdy pasek boczny jest rozwinięty (w pikselach)
        const int DISABLE_EXTENDED_THINKING_EXPANDED_X = 402 + 40; // 40 pikseli w prawo od NEXT_BUTTON
        const int DISABLE_EXTENDED_THINKING_EXPANDED_Y = 399;      // Ta sama wysokość
        
        // Flaga do wyboru metody pozycjonowania: True = procentowe, False = absolutne
        const bool USE_PERCENTAGE_POSITIONING = true;
        
        // Ścieżka do pliku wykonywalnego Claude Desktop
        private string claudeExePath = @"C:\Users\guzic\AppData\Local\AnthropicClaude\claude.exe";
        
        // Włącz debugowanie aby zobaczyć komunikaty o pozycjach kliknięć
        private bool debugMode = false; // Zmienione na false, aby nie wyświetlać komunikatów
        
        // Dodana zmienna, która pozwoli kontrolować wyświetlanie komunikatów po każdym kroku
        private bool showStepMessages = false; // Wyłącz komunikaty po każdym kroku
        
        public KeyboardMacroApp()
        {
            // Ukryj okno aplikacji - zoptymalizowane ustawienia
            this.FormBorderStyle = FormBorderStyle.None;
            this.WindowState = FormWindowState.Minimized;
            this.ShowInTaskbar = false;
            this.Opacity = 0;
            
            // Natychmiastowe uruchomienie makra bez zbędnego timera
            this.Load += (sender, e) => RunMacro();
        }
        
        // Pokazuje okno debugowania z informacją
        private void DebugMessage(string message)
        {
            if (debugMode)
            {
                NativeMessageBox(IntPtr.Zero, message, "Debug Info", MB_OK | MB_ICONINFORMATION | MB_TOPMOST);
            }
        }
        
        // Pokazuje komunikat po wykonaniu kroku (zawsze na pierwszym planie, z focusem na OK)
        // Zwraca true jeśli użytkownik kliknął OK, false jeśli Anuluj
        private bool ShowStepMessage(string stepName, string details)
        {
            if (showStepMessages)
            {
                // Użyj natywnego MessageBox z flagą MB_TOPMOST, aby był zawsze na wierzchu
                string message = "Wykonano krok: " + stepName + "\n\n" + details + "\n\nOK - kontynuuj, Anuluj - zakończ program";
                string title = "Informacja o kroku";
                
                // MB_OKCANCEL | MB_ICONINFORMATION | MB_TOPMOST - zapewni że komunikat będzie zawsze na wierzchu
                int result = NativeMessageBox(IntPtr.Zero, message, title, MB_OKCANCEL | MB_ICONINFORMATION | MB_TOPMOST);
                
                // Jeśli użytkownik kliknął Anuluj, zakończ program
                if (result == IDCANCEL)
                {
                    return false; // Sygnalizuj, że użytkownik chce zakończyć program
                }
            }
            return true; // Kontynuuj program
        }
        
        // Pobiera tytuł aktywnego okna
        private string GetActiveWindowTitle()
        {
            IntPtr handle = GetForegroundWindow();
            return GetWindowTitle(handle);
        }
        
        // Pobiera tytuł okna na podstawie jego uchwytu
        private string GetWindowTitle(IntPtr hWnd)
        {
            int length = GetWindowTextLength(hWnd);
            if (length == 0) return "";
            
            StringBuilder builder = new StringBuilder(length + 1);
            GetWindowText(hWnd, builder, builder.Capacity);
            return builder.ToString();
        }
        
        // Sprawdza, czy tytuł okna wskazuje na okno Claude
        private bool IsClaudeWindow(string windowTitle)
        {
            // Dostosuj tę linię do rzeczywistego tytułu okna Claude Desktop
            return windowTitle.Contains("Claude");
        }
        
        // Pobiera listę wszystkich widocznych okien Claude
        private List<IntPtr> GetAllClaudeWindows()
        {
            List<IntPtr> claudeWindows = new List<IntPtr>();
            
            EnumWindows((hWnd, lParam) => {
                if (IsWindowVisible(hWnd))
                {
                    string title = GetWindowTitle(hWnd);
                    if (IsClaudeWindow(title))
                    {
                        claudeWindows.Add(hWnd);
                    }
                }
                return true;
            }, IntPtr.Zero);
            
            return claudeWindows;
        }
        
        // Ustawia okno w określonym położeniu i rozmiarze - zoptymalizowana wersja
        private bool SetWindowSizeAndPosition(IntPtr hWnd, int x, int y, int width, int height)
        {
            // Przywróć okno, jeśli jest zmaksymalizowane
            ShowWindow(hWnd, SW_RESTORE);
            Thread.Sleep(15); // Pozostawione bez zmian zgodnie z prośbą
            
            // Bezpośrednie ustawienie rozmiaru i pozycji
            SetWindowPos(hWnd, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW);
            Thread.Sleep(15); // Pozostawione bez zmian zgodnie z prośbą
            
            return true;
        }
        
        // Wykonuje kliknięcie lewym przyciskiem myszy w podanej pozycji - absolutne minimum
        private void LeftClick(int x, int y)
        {
            // Przesuń kursor do pozycji - bez opóźnienia
            SetCursorPos(x, y);
            
            // Wykonaj kliknięcie lewym przyciskiem myszy - bez opóźnienia
            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(1); // Minimalne opóźnienie zapewniające, że kliknięcie zostanie zarejestrowane
        }
        
        // Symuluje naciśnięcie kombinacji klawiszy - absolutne minimum
        private void SendKeyCombo(byte[] keys, int delay = 2) // Minimalne opóźnienie
        {
            // Naciśnij wszystkie klawisze - bez opóźnień
            foreach (byte key in keys)
            {
                keybd_event(key, 0, KEYEVENTF_KEYDOWN, UIntPtr.Zero);
            }
            
            // Minimalne opóźnienie
            Thread.Sleep(delay);
            
            // Zwolnij klawisze w odwrotnej kolejności - bez opóźnień
            for (int i = keys.Length - 1; i >= 0; i--)
            {
                keybd_event(keys[i], 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }
            
            // Minimalne opóźnienie po kombinacji klawiszy
            Thread.Sleep(3);
        }
        

        
        // Główna funkcja makra
        private void RunMacro()
        {
            try
            {
                // Szybkie kopiowanie zaznaczonego tekstu bez zbędnych operacji
                string initialClipboard = "";
                try { initialClipboard = Clipboard.GetText(); } catch {}
                
                SendKeys.SendWait("^c");
                Thread.Sleep(5); // ZMNIEJSZONE z 10ms
                
                string currentClipboard = "";
                bool clipboardChanged = false;
                try 
                { 
                    currentClipboard = Clipboard.GetText();
                    clipboardChanged = !string.Equals(initialClipboard, currentClipboard) && !string.IsNullOrEmpty(currentClipboard);
                } 
                catch {}

                // Sprawdź, czy Claude już jest uruchomiony - zoptymalizowane sprawdzanie
                List<IntPtr> existingClaudeWindows = GetAllClaudeWindows();
                IntPtr claudeWindow = IntPtr.Zero;
                bool claudeAlreadyRunning = false;
                
                if (existingClaudeWindows.Count > 0)
                {
                    claudeWindow = existingClaudeWindows[0];
                    claudeAlreadyRunning = true;
                }
                
                // Jeśli Claude nie jest uruchomiony, uruchom go
                if (!claudeAlreadyRunning)
                {
                    try
                    {
                        Process claudeProcess = new Process();
                        claudeProcess.StartInfo.FileName = claudeExePath;
                        claudeProcess.Start();
                    }
                    catch (Exception ex)
                    {
                        NativeMessageBox(IntPtr.Zero, "Nie udało się uruchomić Claude: " + ex.Message, "Błąd", MB_OK | MB_ICONINFORMATION | MB_TOPMOST);
                        Application.Exit();
                        return;
                    }
                    
                    // Czekaj na załadowanie Claude Desktop - zoptymalizowane oczekiwanie
                    Stopwatch stopwatch = new Stopwatch();
                    stopwatch.Start();
                    
                    while (stopwatch.ElapsedMilliseconds < MAX_WAIT_TIME && claudeWindow == IntPtr.Zero)
                    {
                        List<IntPtr> claudeWindows = GetAllClaudeWindows();
                        if (claudeWindows.Count > 0)
                        {
                            claudeWindow = claudeWindows[0];
                            break;
                        }
                        
                        Thread.Sleep(15); // ZMNIEJSZONE z 25ms
                    }
                    
                    if (claudeWindow == IntPtr.Zero)
                    {
                        NativeMessageBox(IntPtr.Zero, "Nie udało się znaleźć okna Claude.", "Błąd", MB_OK | MB_ICONINFORMATION | MB_TOPMOST);
                        Application.Exit();
                        return;
                    }
                }
                
                // Aktywuj okno Claude
                SetForegroundWindow(claudeWindow);
                Thread.Sleep(15); // ZMNIEJSZONE z 30ms
                
                // Pobierz wymiary ekranu i ustaw okno Claude na środku - zoptymalizowane
                int screenWidth = Screen.PrimaryScreen.Bounds.Width;
                int screenHeight = Screen.PrimaryScreen.Bounds.Height;
                
                int windowX = (screenWidth - CLAUDE_WINDOW_WIDTH) / 2;
                int windowY = (screenHeight - CLAUDE_WINDOW_HEIGHT) / 2;
                
                SetWindowSizeAndPosition(claudeWindow, windowX, windowY, CLAUDE_WINDOW_WIDTH, CLAUDE_WINDOW_HEIGHT);
                
                // Pobierz faktyczną pozycję okna
                RECT windowRect;
                if (!GetWindowRect(claudeWindow, out windowRect))
                {
                    Application.Exit();
                    return;
                }
                
                int newChatX, newChatY, textFieldX, textFieldY, extendedThinkingX, extendedThinkingY;
                int nextButtonX, nextButtonY, disableExtendedThinkingX, disableExtendedThinkingY;
                int disableExtendedThinkingExpandedX, disableExtendedThinkingExpandedY;
                
                // Oblicz współrzędne UI elementów
                if (USE_PERCENTAGE_POSITIONING)
                {
                    // Użyj pozycjonowania procentowego
                    newChatX = windowRect.Left + (int)(windowRect.Width * NEW_CHAT_BUTTON_X_PERCENT);
                    newChatY = windowRect.Top + (int)(windowRect.Height * NEW_CHAT_BUTTON_Y_PERCENT);
                    
                    textFieldX = windowRect.Left + (int)(windowRect.Width * TEXT_FIELD_X_PERCENT);
                    textFieldY = windowRect.Top + (int)(windowRect.Height * TEXT_FIELD_Y_PERCENT);
                    
                    extendedThinkingX = windowRect.Left + (int)(windowRect.Width * EXTENDED_THINKING_X_PERCENT);
                    extendedThinkingY = windowRect.Top + (int)(windowRect.Height * EXTENDED_THINKING_Y_PERCENT);
                    
                    // Przycisk wyłączający Extended Thinking
                    disableExtendedThinkingX = windowRect.Left + (int)(windowRect.Width * DISABLE_EXTENDED_THINKING_X_PERCENT);
                    disableExtendedThinkingY = windowRect.Top + (int)(windowRect.Height * DISABLE_EXTENDED_THINKING_Y_PERCENT);
                    
                    // Przycisk wyłączający Extended Thinking gdy pasek boczny jest rozwinięty
                    disableExtendedThinkingExpandedX = windowRect.Left + (int)(windowRect.Width * DISABLE_EXTENDED_THINKING_EXPANDED_X_PERCENT);
                    disableExtendedThinkingExpandedY = windowRect.Top + (int)(windowRect.Height * DISABLE_EXTENDED_THINKING_EXPANDED_Y_PERCENT);
                    
                    // Nowy przycisk na prawo od Extended Thinking
                    nextButtonX = windowRect.Left + (int)(windowRect.Width * NEXT_BUTTON_X_PERCENT);
                    nextButtonY = windowRect.Top + (int)(windowRect.Height * NEXT_BUTTON_Y_PERCENT);
                }
                else
                {
                    // Użyj stałych współrzędnych
                    newChatX = windowRect.Left + NEW_CHAT_BUTTON_X;
                    newChatY = windowRect.Top + NEW_CHAT_BUTTON_Y;
                    
                    textFieldX = windowRect.Left + TEXT_FIELD_X;
                    textFieldY = windowRect.Top + TEXT_FIELD_Y;
                    
                    extendedThinkingX = windowRect.Left + EXTENDED_THINKING_X;
                    extendedThinkingY = windowRect.Top + EXTENDED_THINKING_Y;
                    
                    // Przycisk wyłączający Extended Thinking
                    disableExtendedThinkingX = windowRect.Left + DISABLE_EXTENDED_THINKING_X;
                    disableExtendedThinkingY = windowRect.Top + DISABLE_EXTENDED_THINKING_Y;
                    
                    // Przycisk wyłączający Extended Thinking gdy pasek boczny jest rozwinięty
                    disableExtendedThinkingExpandedX = windowRect.Left + DISABLE_EXTENDED_THINKING_EXPANDED_X;
                    disableExtendedThinkingExpandedY = windowRect.Top + DISABLE_EXTENDED_THINKING_EXPANDED_Y;
                    
                    // Nowy przycisk na prawo od Extended Thinking
                    nextButtonX = windowRect.Left + NEXT_BUTTON_X;
                    nextButtonY = windowRect.Top + NEXT_BUTTON_Y;
                }
                
                // Wyświetl informacje o obliczonych pozycjach kliknięć tylko w trybie debug
                if (debugMode)
                {
                    string clickPositions = 
                        string.Format("Nowy Czat: X={0}, Y={1}\n" +
                        "Pole tekstowe: X={2}, Y={3}\n" +
                        "Wyłącz Extended Thinking: X={4}, Y={5}\n" +
                        "Extended Thinking: X={6}, Y={7}\n" +
                        "Następny przycisk: X={8}, Y={9}\n" +
                        "Wyłącz Extended Thinking (rozwinięty): X={10}, Y={11}",
                        newChatX, newChatY, textFieldX, textFieldY, 
                        disableExtendedThinkingX, disableExtendedThinkingY,
                        extendedThinkingX, extendedThinkingY, 
                        nextButtonX, nextButtonY,
                        disableExtendedThinkingExpandedX, disableExtendedThinkingExpandedY);
                    DebugMessage(clickPositions);
                }
                
                // Krok 1: Kliknij przycisk "Nowy czat"
                LeftClick(newChatX, newChatY);
                Thread.Sleep(1200); // Pozostawione bez zmian zgodnie z prośbą
                
                // Krok 2: Kliknij w pole tekstowe do wprowadzania promptu
                LeftClick(textFieldX, textFieldY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // NOWY KROK: Zaznacz cały tekst (Ctrl+A) po kroku 2
                SendKeyCombo(new byte[] { VK_CTRL, VK_A });
                Thread.Sleep(5); // ZMNIEJSZONE z 15ms
                
                // NOWY KROK: Naciśnij Delete, aby usunąć zaznaczony tekst
                keybd_event(VK_DELETE, 0, KEYEVENTF_KEYDOWN, UIntPtr.Zero);
                Thread.Sleep(2); // ZMNIEJSZONE z 5ms
                keybd_event(VK_DELETE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                Thread.Sleep(5); // ZMNIEJSZONE z 15ms
                
                // NOWY KROK: Kliknij w przycisk wyłączający Extended Thinking (aby upewnić się, że jest wyłączony)
                LeftClick(disableExtendedThinkingX, disableExtendedThinkingY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // =========== PIERWSZA SEKWENCJA (dla zwiniętego paska bocznego) ===========
                
                // Krok 3: Kliknij w przycisk ustawień, aby otworzyć menu
                LeftClick(extendedThinkingX, extendedThinkingY);
                Thread.Sleep(50); // ZMNIEJSZONE z 90ms
                
                // Krok 3.1: Kliknij w przełącznik (toggle) przy opcji Extended Thinking
                // Współrzędne przełącznika są przesunięte w prawo i w dół względem menu
                int toggleX = extendedThinkingX + 150; // Przesunięcie w prawo do przełącznika
                int toggleY = extendedThinkingY + 70;  // Przesunięcie w dół o 70 pikseli
                LeftClick(toggleX, toggleY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // Krok 3.2: Kliknij w przycisk wyłączający Extended Thinking gdy pasek boczny jest rozwinięty
                LeftClick(disableExtendedThinkingExpandedX, disableExtendedThinkingExpandedY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // Krok 4: Kliknij w przycisk na prawo od Extended Thinking 
                LeftClick(nextButtonX, nextButtonY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // Krok 4.1: Kliknij w przełącznik (toggle) odpowiadający opcji po prawej stronie Extended Thinking
                // Przesunięty w prawo tak samo jak krok 4 jest przesunięty względem kroku 3
                int toggle4X = nextButtonX + 150; // Przesunięcie w prawo do przełącznika
                int toggle4Y = nextButtonY + 70;  // Przesunięcie w dół o 70 pikseli (jak w kroku 3.1)
                LeftClick(toggle4X, toggle4Y);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // NOWY KROK 4.2: Kliknij ponownie w pole tekstowe po konfiguracji opcji
                LeftClick(textFieldX, textFieldY);
                Thread.Sleep(20); // ZMNIEJSZONE z 40ms
                
                // Wklej tekst tylko jeśli została wykryta zmiana zawartości schowka
                if (clipboardChanged)
                {
                    SendKeyCombo(new byte[] { VK_CTRL, VK_V });
                    Thread.Sleep(5); // ZMNIEJSZONE z 15ms
                }
                
                // OSTATNIA OPERACJA: Uruchom dyktowanie i natychmiast zakończ program
                keybd_event(VK_LWIN, 0, KEYEVENTF_KEYDOWN, UIntPtr.Zero);
                keybd_event(VK_H, 0, KEYEVENTF_KEYDOWN, UIntPtr.Zero);
                keybd_event(VK_H, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                
                // Końcowe czyszczenie i zamknięcie programu po wykonaniu wszystkich operacji
                Application.Exit();
            }
            catch (Exception ex)
            {
                if (debugMode)
                {
                    NativeMessageBox(IntPtr.Zero, "Błąd podczas wykonywania makra: " + ex.Message, "Błąd", MB_OK | MB_ICONINFORMATION | MB_TOPMOST);
                }
            }
        }
        
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            try
            {
                Application.Run(new KeyboardMacroApp());
            }
            catch (Exception)
            {
                // Ignoruj wyjątki i zakończ program
                Application.Exit();
            }
        }
    }
}