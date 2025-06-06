#!/usr/bin/env python3
import subprocess
import os
import sys

def main():
    # Sprawdzenie czy kontener działa
    check_running = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )

    if "claude-code-container" not in check_running.stdout:
        print("❌ Kontener 'claude-code-container' nie działa!")
        print("Uruchom najpierw: python setup.py")
        sys.exit(1)

    # Pobranie aktualnego katalogu
    current_dir = os.getcwd()

    # Konwersja ścieżki Windows na format kontenera
    if sys.platform == "win32":
        # C:\Users\... → /c/Users/...
        if len(current_dir) >= 2 and current_dir[1] == ':':
            container_dir = f"/{current_dir[0].lower()}{current_dir[2:].replace(chr(92), '/')}"
        else:
            container_dir = current_dir.replace(chr(92), '/')
    else:
        container_dir = current_dir

    # Uruchomienie Claude Code w kontenerze
    docker_cmd = [
        "docker", "exec", "-it",
        "-w", container_dir,
        "claude-code-container",
        "claude"
    ]

    # Przekazanie argumentów do Claude Code
    docker_cmd.extend(sys.argv[1:])

    # Wykonanie komendy
    subprocess.run(docker_cmd)

if __name__ == "__main__":
    main()