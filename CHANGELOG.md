# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.3.0] - 2026-11-14

### Added
- Horizontal offset setting and a **calibration print** sheet to align receipts with the printer.
- Receipts are rendered at the printer's native resolution (203 dpi) at the configured width.

### Changed
- Receipt output is pure black-and-white with bolder, larger small text, so thin Persian text no longer prints faint on thermal paper.
- The developer credit at the bottom of the receipt is always printed (the setting to hide it was removed).

## [1.2.0] - 2026-11-13

### Added
- **Finance section**: overview with period selector and 6-month chart, expenses, suppliers (purchases, payments, balances), cash-flow ledger.
- Cost price on products; gross/net profit estimates.
- Developer credit on receipts, sidebar block and About dialog.
- Application icon for the `.exe`.

### Fixed
- `build_exe.bat` failed with `rm is not recognized` on Windows: batch files are now ASCII-only with CRLF line endings.

## [1.1.0] - 2026-11-12

### Added
- Dashboard, invoice **edit/copy**, customer statements, payments received.
- Barcode and category on products; CSV export; backup and restore; keyboard shortcuts.
- Live thousands separators in every amount field (including inside the invoice table).
- Icons, calmer visual design, global error log (`error.log`).

### Fixed
- Saving a new customer or product failed with an error (dialog was destroyed before its values were read).
- Table selection was lost after saving; settings could be stale on the invoice page.

## [1.0.0] - 2026-11-11

### Added
- First release: invoices with Shamsi dates, customers with balances, product list, optional tax/discount/shipping,
  sequential invoice numbers, 80 mm thermal receipt printing, SQLite storage and automatic daily backup.

[Unreleased]: https://github.com/Arshia-Az/factor-foroosh/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Arshia-Az/factor-foroosh/releases/tag/v1.3.0

<!-- Versions 1.0.0 - 1.2.0 were development builds made before this repository existed. -->
