# Windows installation

Use native Windows and WSL as two independent installations. Do not share
wrapper files, home directories, or configuration folders between them.

## Requirements

- Windows 10/11 with PowerShell or Command Prompt.
- Python 3.10+ available as `python` or `python3`.
- Install each optional CLI (Claude Code, Codex, Antigravity, Graphify) in the
  same native-Windows environment in which you intend to use it.

## Install

Open PowerShell in the cloned repository and run:

```powershell
.\install.bat --all --force
```

For the Antigravity account wrapper only:

```powershell
python .\install-agy.py
```

Native Windows wrappers are installed in:

```text
%LOCALAPPDATA%\ai-coding-config\bin
```

Add that directory to the **User PATH**, close the terminal, open a new one,
then verify:

```powershell
ai-config status
codex --version
agy status
graphify --help
```

## Windows behavior

- RTK is intentionally not configured on native Windows. Run `graphify` directly.
- Graphify's upstream `.exe`/`.cmd` launcher is never replaced by this installer.
- Wrapper backups are ordinary files; the installer never creates symlinks.
- Re-run `install.bat --all --force` after updating this repository.

## WSL is separate

Install from inside WSL with `python3 install.py --all --force`. Its wrappers
remain in `~/.local/bin` and its configs remain under the WSL home directory.
Do not add the Windows wrapper directory to WSL PATH, and do not add the WSL
directory to Windows PATH.

### Running a Windows smoke test from WSL

`/mnt/c` is WSL's mount of the Windows C: drive. It is useful for invoking a
native Windows executable from WSL (for example `cmd.exe` or `powershell.exe`),
but it does not merge the two environments. Windows processes still use Windows
executables and Windows profile/config paths; WSL processes still use Linux
executables and the WSL home directory.

CMD cannot use a `\\wsl.localhost\\...` UNC path as its starting directory. Use
`pushd` to map it temporarily before running a batch command:

```bash
/mnt/c/Windows/System32/cmd.exe /d /c \
  'pushd \\wsl.localhost\Ubuntu-24.04\path\to\ai-coding-config && call install.bat --help && popd'
```

Use this only for a smoke test. For a real Windows installation, open a native
Windows terminal and follow the install steps above.

## Uninstall

Run from the same environment that performed the installation:

```powershell
.\install.bat --uninstall
python .\install-agy.py --uninstall
```
