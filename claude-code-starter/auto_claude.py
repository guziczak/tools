#!/usr/bin/env python3
import subprocess
import os
import sys

def windows_path_to_container_path(windows_path):
    """Konwertuje ścieżkę Windows na ścieżkę kontenera."""
    if sys.platform == "win32":
        # Normalizacja ścieżki
        normalized_path = os.path.normpath(windows_path)

        # Sprawdzenie czy to ścieżka absolutna z dyskiem
        if len(normalized_path) >= 2 and normalized_path[1] == ':':
            drive_letter = normalized_path[0].lower()
            path_without_drive = normalized_path[2:].replace('\\', '/')

            # Mapowanie na strukturę /mnt/dysk
            container_path = f"/mnt/{drive_letter}{path_without_drive}"
            return container_path
        else:
            # Relatywna ścieżka - pozostaw bez zmian
            return normalized_path.replace('\\', '/')
    else:
        # Linux/Mac - bez zmian
        return windows_path

def main():
    # Sprawdzenie czy kontener działa
    try:
        check_running = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        print("❌ Nie można sprawdzić statusu kontenera Docker!")
        print("Sprawdź czy Docker Desktop jest uruchomiony.")
        sys.exit(1)

    if "claude-code-container" not in check_running.stdout:
        print("❌ Kontener 'claude-code-container' nie działa!")
        print("Uruchom najpierw: python setup.py")
        sys.exit(1)

    # Pobranie aktualnego katalogu
    current_dir = os.getcwd()

    # Konwersja ścieżki na format kontenera
    container_dir = windows_path_to_container_path(current_dir)

    print(f"📁 Katalog lokalny: {current_dir}")
    print(f"📁 Katalog w kontenerze: {container_dir}")

    # Uruchomienie Claude Code w kontenerze
    docker_cmd = [
        "docker", "exec", "-it",
        "-w", container_dir,
        "claude-code-container",
        "claude"
    ]

    # Przekazanie argumentów do Claude Code
    docker_cmd.extend(sys.argv[1:])

    print(f"🚀 Uruchamianie: {' '.join(docker_cmd)}")

    try:
        # Wykonanie komendy
        subprocess.run(docker_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd podczas uruchamiania Claude Code: {e}")
        print("\n💡 Sprawdź czy:")
        print("   - Kontener działa poprawnie")
        print("   - Katalog jest dostępny w kontenerze")
        print("   - Claude Code jest poprawnie zainstalowany")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Przerwano przez użytkownika")
        sys.exit(0)

if __name__ == "__main__":
    main()