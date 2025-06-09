#!/usr/bin/env python3
import subprocess
import sys
import os
import time

def run_command(cmd, check=True, show_output=False):
    """Uruchamia komendę z opcją pokazywania outputu."""
    try:
        if show_output:
            # Dla komend gdzie chcemy widzieć output
            result = subprocess.run(cmd, shell=True, text=True, encoding='utf-8', errors='ignore')
            return result.returncode == 0
        else:
            # Dla cichych komend
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if check and result.returncode != 0:
                if result.stderr:
                    print(f"❌ Błąd: {result.stderr}")
                return False
            return True
    except Exception as e:
        if check:
            print(f"❌ Błąd wykonania komendy: {e}")
        return False

def main():
    print("=== Setup Claude Code Container ===\n")

    # Szybkie sprawdzenie Dockera
    print("🔍 Sprawdzanie Dockera...")
    if not run_command("docker version > /dev/null 2>&1", check=False):
        print("❌ Docker nie jest zainstalowany lub nie działa!")
        print("   Upewnij się, że Docker Desktop jest uruchomiony.")
        sys.exit(1)
    print("✅ Docker działa")

    # Sprawdzenie i czyszczenie starego kontenera
    print("\n🔍 Sprawdzanie istniejących kontenerów...")
    existing = subprocess.run(
        "docker ps -aq -f name=claude-code-container",
        shell=True,
        capture_output=True,
        text=True
    ).stdout.strip()

    if existing:
        print("🔄 Usuwanie starego kontenera...")
        if not run_command("docker rm -f claude-code-container", show_output=True):
            print("⚠️  Nie udało się usunąć starego kontenera, kontynuuję...")

    # Sprawdzenie obrazu
    print("\n📦 Sprawdzanie obrazu Docker...")
    image_exists = subprocess.run(
        "docker images -q claude-code-container",
        shell=True,
        capture_output=True,
        text=True
    ).stdout.strip()

    if not image_exists:
        print("🔨 Budowanie obrazu (pierwsze uruchomienie, to może potrwać kilka minut)...")
        if not run_command("docker compose build", show_output=True):
            print("❌ Błąd podczas budowania obrazu!")
            sys.exit(1)
    else:
        print("✅ Obraz już istnieje")

    # Uruchamianie kontenera
    print("\n🚀 Uruchamianie kontenera...")
    if not run_command("docker compose up -d", show_output=True):
        print("❌ Błąd podczas uruchamiania kontenera!")
        print("   Sprawdź logi: docker compose logs")
        sys.exit(1)

    # Czekanie aż kontener będzie gotowy
    print("\n⏳ Czekanie na gotowość kontenera...")
    max_attempts = 10
    for i in range(max_attempts):
        # Sprawdzenie czy kontener działa
        status = subprocess.run(
            'docker ps -f name=claude-code-container --format "{{.Status}}"',
            shell=True,
            capture_output=True,
            text=True
        ).stdout.strip()

        if "Up" in status:
            # Sprawdzenie czy można wykonać komendę w kontenerze
            if run_command('docker exec claude-code-container echo "ready"', check=False):
                print("✅ Kontener gotowy!")
                break

        print(f"   Próba {i+1}/{max_attempts}...")
        time.sleep(1)
    else:
        print("❌ Kontener nie odpowiada po 10 sekundach!")
        print("   Sprawdź status: docker ps")
        print("   Sprawdź logi: docker logs claude-code-container")
        sys.exit(1)

    # Pełna ścieżka do claude.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    claude_py_path = os.path.join(current_dir, "claude.py")

    print("\n✅ Wszystko gotowe!")
    print("\n📋 Konfiguracja IntelliJ IDEA:")
    print("1. Settings → Tools → Terminal")
    print("2. W 'Shell path' wpisz:\n")
    print(f"   python {claude_py_path}\n")
    print("3. OK → nowy terminal")

    print("\n💡 Możesz też używać bezpośrednio:")
    print(f"   python {claude_py_path} [komendy claude]")

if __name__ == "__main__":
    main()