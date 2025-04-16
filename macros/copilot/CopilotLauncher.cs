using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

class CopilotLauncher
{
    // Importy Windows API - tylko niezbędne
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool GetWindowRect(IntPtr hwnd, out RECT lpRect);

    [DllImport("user32.dll")]
    static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, IntPtr dwExtraInfo);
    
    [DllImport("user32.dll")]
    static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, IntPtr dwExtraInfo);

    // Struktura RECT 
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    // Stałe
    const int SW_RESTORE = 9;
    const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    const uint MOUSEEVENTF_LEFTUP = 0x0004;
    const byte VK_TAB = 0x09;
    const byte VK_ESCAPE = 0x1B;
    const byte VK_SHIFT = 0x10;
    const uint KEYEVENTF_KEYUP = 0x0002;

    static void Main()
    {
        try
        {
            // Uruchom Copilota (bezpośrednio)
            Process.Start("explorer.exe", "shell:AppsFolder\\Microsoft.MicrosoftOfficeHub_8wekyb3d8bbwe!Microsoft.MicrosoftOfficeHub");
            
            // Aktywne czekanie na okno - sprawdzamy co 50ms
            IntPtr hWnd = IntPtr.Zero;
            int attempts = 0;
            
            while (hWnd == IntPtr.Zero && attempts < 20) // 20 * 50ms = 1000ms max
            {
                hWnd = FindWindow(null, "Microsoft 365 Copilot");
                if (hWnd == IntPtr.Zero) hWnd = FindWindow(null, "Copilot");
                if (hWnd == IntPtr.Zero) hWnd = FindWindow(null, "Microsoft Copilot");
                
                if (hWnd == IntPtr.Zero)
                {
                    Thread.Sleep(50);
                    attempts++;
                }
            }
            
            if (hWnd != IntPtr.Zero)
            {
                // Aktywuj okno
                ShowWindow(hWnd, SW_RESTORE);
                SetForegroundWindow(hWnd);
                
                // Krótkie opóźnienie
                Thread.Sleep(50);
                
                // Pobierz położenie okna
                RECT windowRect;
                if (GetWindowRect(hWnd, out windowRect))
                {
                    int centerX = (windowRect.Left + windowRect.Right) / 2;
                    int width = windowRect.Right - windowRect.Left;
                    int height = windowRect.Bottom - windowRect.Top;
                    
                    // Oblicz współrzędne kliknięcia bardziej precyzyjnie
                    // Kliknij w środku szerokości, ale dokładnie celując w pole tekstowe
                    // (zwykle 70-80 pikseli od dołu okna, wyżej niż przycisk załączania pliku)
                    int bottomY = windowRect.Bottom - 80; // Wyżej niż poprzednio, aby uniknąć przycisku załączania
                    
                    // Wykonaj kliknięcie
                    SetCursorPos(centerX, bottomY);
                    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, IntPtr.Zero);
                    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, IntPtr.Zero);
                    
                    // Jeśli przez przypadek kliknęliśmy w przycisk załączania, spróbuj nacisnąć Escape
                    Thread.Sleep(10);
                    keybd_event(VK_ESCAPE, 0, 0, IntPtr.Zero);
                    keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, IntPtr.Zero);
                    
                    // Spróbuj jeszcze raz kliknąć w pole tekstowe
                    Thread.Sleep(10);
                    bottomY = windowRect.Bottom - 75; // Lekko zmieniona pozycja
                    SetCursorPos(centerX, bottomY);
                    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, IntPtr.Zero);
                    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, IntPtr.Zero);
                }
            }
        }
        catch
        {
            // Ignoruj błędy dla szybkości działania
        }
    }
}