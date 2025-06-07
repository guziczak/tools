#!/usr/bin/env python3
import subprocess
import sys
import os
import time

def run_command(cmd, check=True):
    """Uruchamia komendę bez zbędnego wyświetlania."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if check and result.returncode != 0:
        if result.stderr:
            print(f"❌ Błąd: {result.stderr}")
        return False
    return True

def main():
    print("=== Setup Claude Code Container ===\n")

    # Szybkie sprawdzenie Dockera
    if not run_command("docker version > /dev/null 2>&1", check=False):
        print("❌ Docker nie jest zainstalowany!")
        sys.exit(1)

    # Sprawdzenie i czyszczenie starego kontenera (jeden krok)
    if run_command("docker ps -aq -f name=claude-code-container", check=False):
        print("🔄 Usuwanie starego kontenera...")
        run_command("docker rm -f claude-code-container > /dev/null 2>&1", check=False)

    # Budowanie tylko jeśli obraz nie istnieje
    print("📦 Sprawdzanie obrazu Docker...")
    if not run_command("docker images -q claude-code-container 2>/dev/null", check=False):
        print("🔨 Budowanie obrazu (pierwsze uruchomienie)...")
        if not run_command("docker compose build -q"):
            print("❌ Błąd podczas budowania!")
            sys.exit(1)

    # Uruchamianie kontenera
    print("🚀 Uruchamianie kontenera...")
    if not run_command("docker compose up -d"):
        print("❌ Błąd podczas uruchamiania!")
        sys.exit(1)

    # Czekanie aż kontener będzie gotowy (max 2 sekundy)
    for i in range(4):
        if run_command('docker exec claude-code-container echo "ready" > /dev/null 2>&1', check=False):
            break
        time.sleep(0.5)

    print("\n✅ Kontener gotowy!")

    # Pełna ścieżka do claude.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    claude_py_path = os.path.join(current_dir, "claude.py")

    print("\n📋 Konfiguracja IntelliJ IDEA:")
    print("1. Settings → Tools → Terminal")
    print("2. W 'Shell path' wpisz:\n")
    print(f"python {claude_py_path}\n")
    print("3. OK → nowy terminal")

if __name__ == "__main__":
    main()