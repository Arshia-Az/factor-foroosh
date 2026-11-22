# Contributing

Thanks for your interest in Factor Foroosh! Bug reports, ideas and pull requests are welcome.

## Development setup

```bash
git clone https://github.com/Arshia-Az/factor-foroosh.git
cd factor-foroosh
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
python app.py
```

## Before you open a pull request

```bash
ruff check .          # lint (syntax errors, undefined names, unused imports)
pytest                # runs the headless end-to-end suite (tests/run_checks.py)
```

The suite drives the real app on Qt's `offscreen` platform against a throw-away database, so it needs no display.
Please add a check to `tests/run_checks.py` for every bug you fix or feature you add.
On Linux you may need: `libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1`.

## Guidelines

- **One module on purpose.** `app.py` is a single file organised in clearly separated sections (see `docs/ARCHITECTURE.md`). Keep it that way unless a section becomes unmanageable.
- **Persian/RTL first.** Test new screens with long Persian text and Persian digits. Numbers go through `fa()`, `money()` and `NumEdit` so digits and separators stay consistent.
- **Never lose user data.** Database changes must be additive migrations in `DB.init()` (`NEW_COLUMNS`); existing databases must keep working.
- **Dialogs:** keep the dialog object alive until you have read its values (a temporary dialog is destroyed after `exec()` and its widgets with it).
- **Batch files stay ASCII + CRLF.** Persian text inside `.bat` files breaks `cmd.exe` (a test enforces this).
- **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`.

## Releasing (maintainers)

See "Versioning and releases" in the README: bump with `scripts/bump_version.py`, update `CHANGELOG.md`, tag `vX.Y.Z`, push the tag.
