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

def find_and_setup_claude_config():
    """Znajdź i skonfiguruj Claude Code aby używał Opus."""
    print("\nSprawdzanie instalacji Claude Code...")

    # Najpierw sprawdź czy claude w ogóle istnieje
    check_result = subprocess.run(
        'docker exec claude-code-container which claude',
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    if not check_result.stdout.strip():
        print("   UWAGA: Claude Code nie jest zainstalowany!")
        print("\n   Probuję zainstalować Claude Code...")

        # Próba instalacji
        install_cmd = 'docker exec claude-code-container bash -c "npm install -g @anthropic-ai/claude-code 2>&1"'
        install_result = subprocess.run(
            install_cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if install_result.returncode != 0:
            print("   Instalacja globalna nie powiodła się.")
            print("\n   Kontener działa jako środowisko deweloperskie z:")
            print("   - Node.js, Python, Java, Ruby, PHP")
            print("   - Selenium, Chrome/Chromium")
            print("   - LaTeX (pełny zestaw)")
            print("   - Docker CLI, Git, vim, nano")
            print("   - Wszystkie biblioteki Python (anthropic, fastapi, etc.)")
            return False
        else:
            print("   Claude Code zainstalowany pomyślnie!")
            # Odśwież PATH
            run_command('docker exec claude-code-container bash -c "hash -r"', show_output=False)
    else:
        print(f"   Claude znaleziony: {check_result.stdout.strip()}")

    # Konfiguracja modelu na Opus - różne podejścia
    print("\nKonfiguracja modelu na Opus...")

    # 1. Przez zmienne środowiskowe (już ustawione w Dockerfile)
    print("   - Zmienne środowiskowe CLAUDE_MODEL=opus ustawione")

    # 2. Uruchom claude raz żeby utworzył pliki konfiguracyjne
    print("   - Inicjalizacja plików konfiguracyjnych...")
    run_command('docker exec claude-code-container bash -c "timeout 2 claude --help 2>/dev/null || true"', show_output=False)
    time.sleep(1)

    # 3. Szukaj plików konfiguracyjnych w różnych lokalizacjach
    config_locations = [
        "/root/.claude",
        "/root/.config/claude",
        "/root/.config/claude-code",
        "/root/.anthropic",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/config",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/.config"
    ]

    for location in config_locations:
        print(f"   - Sprawdzam {location}...")
        find_cmd = f'docker exec claude-code-container find {location} -name "*.json" -o -name "*.yml" -o -name "*.yaml" 2>/dev/null'
        find_result = subprocess.run(
            find_cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if find_result.stdout:
            for config_file in find_result.stdout.strip().split('\n'):
                if config_file:
                    print(f"     Znaleziono: {config_file}")

                    # Sprawdź zawartość
                    cat_cmd = f'docker exec claude-code-container cat "{config_file}"'
                    content = subprocess.run(
                        cat_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )

                    if content.stdout and ("model" in content.stdout.lower() or "claude" in content.stdout.lower()):
                        # Aktualizuj plik
                        if config_file.endswith('.json'):
                            update_cmd = f'''docker exec claude-code-container bash -c "cp '{config_file}' '{config_file}.bak' && sed -i 's/\\"model\\"[[:space:]]*:[[:space:]]*\\"[^\\"]*\\"/\\"model\\": \\"opus\\"/g; s/\\"defaultModel\\"[[:space:]]*:[[:space:]]*\\"[^\\"]*\\"/\\"defaultModel\\": \\"opus\\"/g; s/\\"claude-[^\\"]*\\"/\\"claude-opus-4\\"/g' '{config_file}'"'''
                        else:  # YAML
                            update_cmd = f'''docker exec claude-code-container bash -c "cp '{config_file}' '{config_file}.bak' && sed -i 's/model:[[:space:]]*[^[:space:]]*/model: opus/g; s/defaultModel:[[:space:]]*[^[:space:]]*/defaultModel: opus/g' '{config_file}'"'''

                        if run_command(update_cmd, show_output=False):
                            print(f"     Zaktualizowano na model opus")

    # 4. Sprawdź czy istnieje plik .claude-coderc
    print("   - Tworzenie .claude-coderc z modelem opus...")
    create_rc_cmd = '''docker exec claude-code-container bash -c "echo '{\\"model\\": \\"opus\\", \\"defaultModel\\": \\"opus\\"}' > /root/.claude-coderc"'''
    run_command(create_rc_cmd, show_output=False)

    print("\nKonfiguracja zakończona.")
    return True

def main():
    print("=== Setup Claude Code Container ===\n")

    # Szybkie sprawdzenie Dockera
    print("Sprawdzanie Dockera...")
    if not run_command("docker version > /dev/null 2>&1", check=False):
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

    # Próba automatycznej konfiguracji Opus
    find_and_setup_claude_config()

    # Pełna ścieżka do claude.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    claude_py_path = os.path.join(current_dir, "claude.py")

    print("\nWszystko gotowe!")

    print("\nKonfiguracja IntelliJ IDEA:")
    print("1. Settings -> Tools -> Terminal")
    print("2. W 'Shell path' wpisz:\n")
    print(f"   python {claude_py_path}\n")
    print("3. OK -> nowy terminal")

    print("\nUzycie:")
    print(f"   python {claude_py_path}              # Uruchom Claude Code")
    print(f"   python {claude_py_path} [komenda]    # Z argumentami")

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

    # Sprawdź claude
    claude_check = subprocess.run(
        'docker exec claude-code-container which claude',
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    if claude_check.stdout.strip():
        print(f"   claude: {claude_check.stdout.strip()}")
        # Sprawdź czy to symlink czy plik
        run_command('docker exec claude-code-container ls -la $(which claude)', show_output=True)
    else:
        print("   claude: NIE ZNALEZIONY!")
        print("\n   Szukam w alternatywnych lokalizacjach...")
        run_command('docker exec claude-code-container find /usr/local -name "claude" -type f 2>/dev/null | head -5', show_output=True)
        run_command('docker exec claude-code-container ls -la /usr/local/lib/node_modules/.bin/ 2>/dev/null | grep claude || echo "Brak claude w .bin"', show_output=True)

    run_command('docker exec claude-code-container node --version', show_output=True)
    run_command('docker exec claude-code-container python --version', show_output=True)

    # Pokaż PATH
    print("\n   PATH w kontenerze:")
    run_command('docker exec claude-code-container echo $PATH', show_output=True)

    # Pokaż zmienne Claude
    print("\n   Zmienne środowiskowe Claude:")
    run_command('docker exec claude-code-container env | grep -i claude', show_output=True)

if __name__ == "__main__":
    main()