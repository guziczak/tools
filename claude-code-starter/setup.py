#!/usr/bin/env python3
import subprocess
import sys
import os

def run_command(cmd):
    """Uruchamia komendę i wyświetla output."""
    print(f"Wykonuję: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode

def main():
    print("=== Setup Claude Code Container ===\n")

    # Sprawdzenie czy Docker jest zainstalowany
    if run_command("docker --version") != 0:
        print("❌ Docker nie jest zainstalowany!")
        sys.exit(1)

    # Sprawdzenie czy kontener już istnieje
    check_container = subprocess.run(
        "docker ps -a --format '{{.Names}}' | grep -q ^claude-code-container$",
        shell=True
    )

    if check_container.returncode == 0:
        print("⚠️  Kontener 'claude-code-container' już istnieje.")
        print("Zatrzymywanie i usuwanie starego kontenera...")
        run_command("docker stop claude-code-container")
        run_command("docker rm claude-code-container")

    # Budowanie i uruchamianie kontenera
    print("\n📦 Budowanie obrazu Docker...")
    if run_command("docker-compose build") != 0:
        print("❌ Błąd podczas budowania obrazu!")
        sys.exit(1)

    print("\n🚀 Uruchamianie kontenera w tle...")
    if run_command("docker-compose up -d") != 0:
        print("❌ Błąd podczas uruchamiania kontenera!")
        sys.exit(1)

    print("\n✅ Kontener został uruchomiony!")
    print("\n📋 Instrukcja konfiguracji IntelliJ IDEA:")
    print("1. Otwórz Settings → Tools → Terminal")
    print("2. W polu 'Shell path' wpisz:")

    # Ścieżka do interpretera Python i auto_claude.py
    python_path = sys.executable
    auto_claude_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_claude.py")

    print(f"\n{python_path} {auto_claude_path}\n")
    print("3. Kliknij OK i otwórz nowy terminal")
    print("\n🎯 Kontener będzie działał w tle do czasu jego zatrzymania.")

if __name__ == "__main__":
    main()