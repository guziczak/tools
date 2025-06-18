#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import time
from pathlib import Path

# Włączamy BuildKit globalnie
os.environ['DOCKER_BUILDKIT'] = '1'
os.environ['COMPOSE_DOCKER_CLI_BUILD'] = '1'

def check_container():
    """Sprawdza stan kontenera z lepszą obsługą błędów."""
    try:
        # Wymuszamy kodowanie UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        # Sprawdzenie czy kontener istnieje i działa
        result = subprocess.run(
            ["docker", "ps", "-f", "name=claude-code-container", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Docker nie odpowiada"

        status = result.stdout.strip()
        if not status:
            return False, "Kontener nie istnieje"

        if "Up" not in status:
            return False, f"Kontener zatrzymany: {status}"

        # Dodatkowe sprawdzenie czy kontener odpowiada
        test_result = subprocess.run(
            ["docker", "exec", "claude-code-container", "echo", "test"],
            capture_output=True,
            env=env,
            timeout=2
        )

        if test_result.returncode != 0:
            return False, "Kontener nie odpowiada"

        return True, "OK"

    except subprocess.TimeoutExpired:
        return False, "Timeout podczas sprawdzania kontenera"
    except Exception as e:
        return False, f"Blad: {str(e)}"


def get_container_path(windows_path):
    """Bezpieczna konwersja ścieżek z walidacją."""
    try:
        path = Path(windows_path).resolve()
    except Exception as e:
        print(f"BŁĄD: Nieprawidłowa ścieżka: {windows_path}")
        print(f"Szczegóły: {e}")
        sys.exit(1)
    
    # Walidacja istnienia
    if not path.exists():
        print(f"BŁĄD: Ścieżka nie istnieje: {path}")
        sys.exit(1)
    
    if not path.is_dir():
        print(f"BŁĄD: Ścieżka nie jest katalogiem: {path}")
        sys.exit(1)
    
    # Sprawdzenie ścieżek UNC
    if sys.platform == "win32" and str(path).startswith('\\\\'):
        print("BŁĄD: Ścieżki sieciowe UNC nie są wspierane!")
        print("Proszę skopiować pliki lokalnie lub zamapować dysk sieciowy.")
        sys.exit(1)
    
    if sys.platform == "win32":
        # Użyj pathlib do konwersji
        drive = path.drive[0].lower() if path.drive else 'c'
        path_without_drive = str(path).replace(path.drive, '', 1)
        return f"/{drive}{path_without_drive.replace(os.sep, '/')}"
    else:
        return str(path)

def main():
    # Sprawdzenie kontenera
    is_running, message = check_container()

    if not is_running:
        print(f"Kontener nie dziala: {message}")
        print("Uruchom: python setup.py")

        # Opcjonalne: próba automatycznego uruchomienia
        response = input("\nCzy chcesz sprobowac uruchomic kontener automatycznie? (t/n): ")
        if response.lower() == 't':
            setup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup.py")
            subprocess.run([sys.executable, setup_path])
            # Poczekaj chwilę i sprawdź ponownie
            time.sleep(2)
            is_running, message = check_container()
            if not is_running:
                print(f"Nadal nie dziala: {message}")
                sys.exit(1)
        else:
            sys.exit(1)

    # Konwersja ścieżki dla Windows
    cwd = os.getcwd()
    container_dir = get_container_path(cwd)

    # Przygotowanie argumentów
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # Budowanie komendy z session managerem
    docker_cmd = [
        "docker", "exec", "-it",
        "claude-code-container",
        "claude-session", container_dir
    ] + args

    try:
        # Uruchom Claude normalnie
        result = subprocess.run(docker_cmd, check=False)

        # Jeśli claude nie znaleziony, spróbuj alternatyw
        if result.returncode == 126 or result.returncode == 127:
            print("\nKomenda 'claude' nie znaleziona. Diagnostyka...")

            # Sprawdź czy istnieje claude-code
            print("\n1. Sprawdzam zainstalowane pakiety npm...")
            npm_list = subprocess.run(
                ["docker", "exec", "claude-code-container", "npm", "list", "-g", "--depth=0"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if npm_list.stdout:
                print(npm_list.stdout)

            print("\n2. Claude Code nie jest zainstalowany w kontenerze.")
            print("   Spróbuj:")
            print("   - docker compose build --no-cache")
            print("   - python setup.py")
            print("\n   Lub ręcznie w kontenerze:")
            print("   - docker exec -it claude-code-container bash")
            print("   - npm install -g @anthropic-ai/claude-code")

    except KeyboardInterrupt:
        print("\nDo zobaczenia!")
    except Exception as e:
        print(f"Blad: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()