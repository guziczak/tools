# TODO - Claude Code Docker Improvements

## Security/Safety
- [ ] **a) Custom seccomp/apparmor** - Blokuje niebezpieczne syscalls (reboot, ptrace) ale pozwala mount/unshare
- [ ] **b) Ograniczenie sudo (blacklist)** - `claude ALL=(ALL) NOPASSWD: ALL, !/usr/bin/rm, !/usr/bin/dd, !/sbin/reboot, !/sbin/shutdown, !/usr/bin/mkfs, !/sbin/fdisk` etc. Zablokować niebezpieczne komendy. **UWAGA**: Łatwe do obejścia (`sudo sh -c "rm..."`). Punkt a) (seccomp/apparmor) chroni hosta bez tego - jeśli zależy tylko na ochronie hosta (nie kontenera), ten punkt może być niepotrzebny
- [ ] **c) Auto-detection dysków Windows** - Zamiast hardcoded C:/, D:/ wykryć wszystkie dyski

## Code Quality
- [ ] **d) Path conversion bug** - Fix dla colonów w nazwach plików (Windows alternate streams)
- [ ] **e) Race conditions** - PID file może być czytany podczas atomic rename, brak flock() w cleanup daemon
- [ ] **f) Kimi coupling** - Tight coupling, brak abstraction dla innych API providers

## Error Handling
- [ ] **g) Broken error recovery** - Gdy container nie startuje, brak docker logs/inspect, zero debug info
- [ ] **h) Setup rollback** - Przy failed build brak cleanup partial image/volumes

## Edge Cases
- [ ] **i) Session ID collision risk** - Słaby generation (timestamp[-6:])
- [ ] **j) Zombie process risk** - bash -c + sudo chain może tworzyć zombie
- [ ] **k) Log rotation** - Tylko 1 backup (.old), każda kolejna nadpisuje
- [ ] **l) Mount namespace cleanup** - trap EXIT który prawdopodobnie nie działa (ale może nieistotny)

## Current Issues
- [x] **Model fix** - Zmienić opus → sonnet-4.5 (Dockerfile:19-21 i linia 220) ✅ DONE
