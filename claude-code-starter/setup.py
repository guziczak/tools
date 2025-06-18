#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import time

# Włączamy BuildKit globalnie
os.environ['DOCKER_BUILDKIT'] = '1'
os.environ['COMPOSE_DOCKER_CLI_BUILD'] = '1'

def run_command(cmd, check=True, show_output=False):
    """Uruchamia komendę z opcją pokazywania outputu."""
    try:
        # Wymuszamy kodowanie UTF-8 dla subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Zastąp Unix-owe przekierowania na Windows
        if sys.platform == "win32" and isinstance(cmd, str):
            cmd = cmd.replace(' > /dev/null 2>&1', ' >NUL 2>&1')
            cmd = cmd.replace(' 2>/dev/null', ' 2>NUL')
            cmd = cmd.replace(' >/dev/null', ' >NUL')

        if show_output:
            # Dla komend gdzie chcemy widzieć output
            if sys.platform == "win32":
                # Na Windows używamy startupinfo żeby ukryć okno konsoli
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(cmd, shell=True, env=env, startupinfo=startupinfo)
            else:
                result = subprocess.run(cmd, shell=True, env=env)
            return result.returncode == 0
        else:
            # Dla cichych komend
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            if check and result.returncode != 0:
                if result.stderr:
                    print(f"Blad: {result.stderr}")
                return False
            return True
    except Exception as e:
        if check:
            print(f"Blad wykonania komendy: {e}")
        return False

def check_claude_installation():
    """Sprawdza czy Claude Code jest zainstalowany."""
    print("\nSprawdzanie instalacji Claude Code...")
    
    check_result = subprocess.run(
        ["docker", "exec", "claude-code-container", "which", "claude"],
        capture_output=True,
        text=True
    )
    
    if check_result.returncode == 0:
        print(f"   Claude znaleziony: {check_result.stdout.strip()}")
        return True
    else:
        print("   UWAGA: Claude Code nie jest zainstalowany!")
        print("   Kontener działa jako środowisko deweloperskie.")
        print("\n   Możesz spróbować zainstalować ręcznie:")
        print("   docker exec -it claude-code-container bash")
        print("   npm install -g @anthropic-ai/claude-code")
        return False

def main():
    print("=== Setup Claude Code Container ===\n")

    # Szybkie sprawdzenie Dockera
    print("Sprawdzanie Dockera...")
    # Używamy listy argumentów zamiast stringa shell - działa na wszystkich platformach
    docker_check = subprocess.run(
        ["docker", "version"],
        capture_output=True,
        text=True
    )
    if docker_check.returncode != 0:
        print("Docker nie jest zainstalowany lub nie dziala!")
        print("Upewnij sie, ze Docker Desktop jest uruchomiony.")
        sys.exit(1)
    print("Docker dziala")

    # Sprawdzenie i czyszczenie starego kontenera
    print("\nSprawdzanie istniejacych kontenerow...")
    existing = subprocess.run(
        "docker ps -aq -f name=claude-code-container",
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    ).stdout.strip()

    if existing:
        print("Usuwanie starego kontenera...")
        if not run_command("docker rm -f claude-code-container", show_output=True):
            print("Nie udalo sie usunac starego kontenera, kontynuuje...")

    # Sprawdzenie obrazu
    print("\nSprawdzanie obrazu Docker...")
    image_exists = subprocess.run(
        "docker images -q claude-code-container",
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    ).stdout.strip()

    if not image_exists:
        print("Budowanie obrazu (pierwsze uruchomienie)...")
        print("\n   Opcje budowania:")
        print("   1. Normalne (z cache) - szybsze")
        print("   2. Pelne (--no-cache) - swieze pakiety")

        build_choice = input("\nWybor (1-2) [1]: ").strip() or "1"

        print("\nDocker BuildKit wlaczony automatycznie dla szybszego budowania!")

        if build_choice == "2":
            print("\nBudowanie pelnego obrazu (bez cache)...")
            build_cmd = "docker compose build --no-cache"
        else:
            print("\nBudowanie obrazu (z cache)...")
            build_cmd = "docker compose build"

        start_time = time.time()
        if not run_command(build_cmd, show_output=True):
            print("Blad podczas budowania obrazu!")
            sys.exit(1)

        build_time = time.time() - start_time
        print(f"\nBudowanie zakonczone w {build_time:.0f} sekund ({build_time/60:.1f} minut)")
    else:
        print("Obraz juz istnieje")
        print("   Wskazowka: Aby przebudowac z nowymi zaleznosci uzyj:")
        print("      docker compose build --no-cache")

    # Uruchamianie kontenera
    print("\nUruchamianie kontenera...")
    print("Montowanie dysków C:, D:, E: do kontenera...")
    
    if not run_command("docker compose up -d", show_output=True):
        print("Blad podczas uruchamiania kontenera!")
        print("   Sprawdz logi: docker compose logs")
        sys.exit(1)

    # Czekanie aż kontener będzie gotowy
    print("\nCzekanie na gotowosc kontenera...")
    max_attempts = 10
    for i in range(max_attempts):
        # Sprawdzenie czy kontener działa
        status = subprocess.run(
            'docker ps -f name=claude-code-container --format "{{.Status}}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        ).stdout.strip()

        if "Up" in status:
            # Sprawdzenie czy można wykonać komendę w kontenerze
            if run_command('docker exec claude-code-container echo "ready"', check=False):
                print("Kontener gotowy!")
                break

        print(f"   Proba {i+1}/{max_attempts}...")
        time.sleep(1)
    else:
        print("Kontener nie odpowiada po 10 sekundach!")
        print("   Sprawdz status: docker ps")
        print("   Sprawdz logi: docker logs claude-code-container")
        sys.exit(1)

    # Sprawdzenie instalacji Claude
    check_claude_installation()

    # Pełna ścieżka do claude.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    claude_py_path = os.path.join(current_dir, "claude.py")

    print("\nWszystko gotowe!")

    print("\nKonfiguracja IntelliJ IDEA:")
    print("1. Settings -> Tools -> Terminal")
    print("2. W 'Shell path' wpisz:\n")
    # Cytujemy ścieżkę jeśli zawiera spacje
    if ' ' in claude_py_path:
        print(f'   python "{claude_py_path}"\n')
    else:
        print(f"   python {claude_py_path}\n")
    print("3. OK -> nowy terminal")

    print("\nUzycie:")
    print(f"   python {claude_py_path}              # Uruchom Claude Code")
    print(f"   python {claude_py_path} [komenda]    # Z argumentami")
    
    print("\n⚠️  Bezpieczeństwo sesji:")
    print("   - Każda sesja Claude widzi TYLKO swój katalog projektu")
    print("   - Narzędzia i instalacje są współdzielone między sesjami")
    print("   - Możesz pracować na wielu projektach jednocześnie")

    print("\nDodane narzędzia i biblioteki:")
    print("   Języki programowania:")
    print("   - Node.js 20 + npm")
    print("   - Python 3 + pip")
    print("   - Java 17 (OpenJDK) + Maven + Gradle")
    print("   - Ruby")
    print("   - PHP + Composer")
    print("\n   Narzędzia deweloperskie:")
    print("   - Git, vim, nano")
    print("   - ripgrep, fd-find, fzf")
    print("   - Docker CLI")
    print("   - shellcheck")
    print("\n   Python biblioteki:")
    print("   - anthropic, selenium, fastapi, uvicorn")
    print("   - beautifulsoup4, requests, pytest, black")
    print("   - pydantic, pyyaml, lxml, rich")
    print("\n   Inne:")
    print("   - Chromium + ChromeDriver (dla Selenium)")
    print("   - LaTeX (texlive-full z polskim wsparciem)")
    print("   - ImageMagick, ffmpeg")
    print("   - SQLite3")

    # Diagnostyka końcowa
    print("\nDiagnostyka:")
    
    # Sprawdź podstawowe narzędzia
    tools = [
        ("Node.js", "node --version"),
        ("Python", "python --version"),
        ("Java", "java --version | head -1"),
        ("Bubblewrap", "bwrap --version")
    ]
    
    for tool_name, cmd in tools:
        result = subprocess.run(
            f"docker exec claude-code-container {cmd}",
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"   {tool_name}: {version}")
        else:
            print(f"   {tool_name}: NIE ZNALEZIONY")
    
    # Sprawdź session manager
    sm_check = subprocess.run(
        ["docker", "exec", "claude-code-container", "test", "-x", "/usr/local/bin/claude-session"],
        capture_output=True
    )
    if sm_check.returncode == 0:
        print("   Session Manager: ZAINSTALOWANY")
    else:
        print("   Session Manager: BRAK!")

if __name__ == "__main__":
    main()