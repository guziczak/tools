#!/usr/bin/env python3
import subprocess
import os
import sys
import time

def check_container():
    """Sprawdza stan kontenera z lepszą obsługą błędów."""
    try:
        # Sprawdzenie czy kontener istnieje i działa
        result = subprocess.run(
            ["docker", "ps", "-f", "name=claude-code-container", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            encoding='utf-8',
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
            timeout=2
        )

        if test_result.returncode != 0:
            return False, "Kontener nie odpowiada"

        return True, "OK"

    except subprocess.TimeoutExpired:
        return False, "Timeout podczas sprawdzania kontenera"
    except Exception as e:
        return False, f"Błąd: {str(e)}"

def main():
    # Sprawdzenie kontenera
    is_running, message = check_container()

    if not is_running:
        print(f"❌ Kontener nie działa: {message}")
        print("🔧 Uruchom: python setup.py")

        # Opcjonalne: próba automatycznego uruchomienia
        response = input("\nCzy chcesz spróbować uruchomić kontener automatycznie? (t/n): ")
        if response.lower() == 't':
            setup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup.py")
            subprocess.run([sys.executable, setup_path])
            # Poczekaj chwilę i sprawdź ponownie
            time.sleep(2)
            is_running, message = check_container()
            if not is_running:
                print(f"❌ Nadal nie działa: {message}")
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
        # Wykonanie claude
        subprocess.run(docker_cmd, check=False)
    except KeyboardInterrupt:
        # Graceful handling of Ctrl+C
        print("\n👋 Do zobaczenia!")
    except Exception as e:
        print(f"❌ Błąd: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()