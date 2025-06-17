#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import time

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
    if sys.platform == "win32" and len(cwd) > 1 and cwd[1] == ':':
        # C:\path\to\dir -> /c/path/to/dir
        container_dir = f"/{cwd[0].lower()}{cwd[2:].replace(chr(92), '/')}"
    else:
        container_dir = cwd

    # Przygotowanie argumentów
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # Budowanie komendy
    docker_cmd = [
        "docker", "exec", "-it",
        "-w", container_dir,
        "claude-code-container",
        "claude"
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

            print("\n2. Sprawdzam /usr/local/lib/node_modules/.bin/...")
            bin_check = subprocess.run(
                ["docker", "exec", "claude-code-container", "ls", "-la", "/usr/local/lib/node_modules/.bin/"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if bin_check.stdout:
                for line in bin_check.stdout.split('\n'):
                    if 'claude' in line:
                        print(f"   ZNALEZIONO: {line}")

            print("\n3. Szukam plików claude...")
            find_check = subprocess.run(
                ["docker", "exec", "claude-code-container", "find", "/usr/local",
                 "-name", "*claude*", "-type", "f", "-o", "-type", "l"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if find_check.stdout:
                lines = find_check.stdout.strip().split('\n')
                claude_files = [l for l in lines if 'claude' in l and ('bin' in l or '.js' in l)]
                if claude_files:
                    print(f"Znaleziono {len(claude_files)} plików claude:")
                    for f in claude_files[:5]:  # Pokaż max 5
                        print(f"   {f}")

                    # Spróbuj uruchomić pierwszy znaleziony
                    for file_path in claude_files:
                        if '/claude-code/' in file_path and file_path.endswith('.js'):
                            print(f"\n4. Próbuję uruchomić: {file_path}")
                            alt_docker_cmd = [
                                "docker", "exec", "-it",
                                "-w", container_dir,
                                "claude-code-container",
                                "node", file_path
                            ] + args

                            subprocess.run(alt_docker_cmd, check=False)
                            return
                        elif file_path.endswith('/claude') and '/bin/' in file_path:
                            print(f"\n4. Próbuję uruchomić bezpośrednio: {file_path}")
                            alt_docker_cmd = [
                                "docker", "exec", "-it",
                                "-w", container_dir,
                                "claude-code-container",
                                file_path
                            ] + args

                            subprocess.run(alt_docker_cmd, check=False)
                            return

            print("\n5. Nie znaleziono działającego claude.")
            print("   Uruchom: docker compose build --no-cache")
            print("   Następnie: python setup.py")

    except KeyboardInterrupt:
        print("\nDo zobaczenia!")
    except Exception as e:
        print(f"Blad: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()