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

def check_container_exists():
    """Sprawdza czy kontener już istnieje (kompatybilne z Windows)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False
        )
        return "claude-code-container" in result.stdout
    except:
        return False

def get_available_drives():
    """Sprawdza jakie dyski są dostępne w systemie Windows."""
    if sys.platform != "win32":
        return []

    available_drives = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            available_drives.append(letter.lower())
    return available_drives

def generate_docker_compose(drives):
    """Generuje docker-compose.yml z dostępnymi dyskami."""
    content = """services:
  claude-code:
    build: .
    container_name: claude-code-container
    stdin_open: true
    tty: true
    volumes:"""

    if drives:
        content += "\n      # Mapping available Windows drives"
        for drive in drives:
            content += f"\n      - {drive.upper()}:/:/mnt/{drive}"
    else:
        # Fallback dla systemów Linux/Mac
        content += "\n      - ./:/workspace"

    content += "\n    working_dir: /workspace"

    return content

def main():
    print("=== Setup Claude Code Container ===\n")

    # Sprawdzenie czy Docker jest zainstalowany
    if run_command("docker --version") != 0:
        print("❌ Docker nie jest zainstalowany!")
        sys.exit(1)

    # Sprawdzenie dostępnych dysków
    if sys.platform == "win32":
        available_drives = get_available_drives()
        print(f"🔍 Znalezione dyski: {[d.upper() + ':' for d in available_drives]}")

        # Generowanie docker-compose.yml z dostępnymi dyskami
        docker_compose_content = generate_docker_compose(available_drives)
        with open("docker-compose.yml", "w", encoding="utf-8") as f:
            f.write(docker_compose_content)
        print("📝 Zaktualizowano docker-compose.yml z dostępnymi dyskami\n")
    else:
        # Linux/Mac
        docker_compose_content = generate_docker_compose([])
        with open("docker-compose.yml", "w", encoding="utf-8") as f:
            f.write(docker_compose_content)
        print("📝 Wygenerowano docker-compose.yml dla Linux/Mac\n")

    # Sprawdzenie czy kontener już istnieje
    if check_container_exists():
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

    print(f'\n"{python_path}" "{auto_claude_path}"\n')
    print("3. Kliknij OK i otwórz nowy terminal")
    print("\n🎯 Kontener będzie działał w tle do czasu jego zatrzymania.")
    print("\n💡 Możesz też używać bezpośrednio: python auto_claude.py [argumenty]")

if __name__ == "__main__":
    main()