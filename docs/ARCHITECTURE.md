# Architecture

Factor Foroosh is deliberately small: **one Python file (`app.py`)**, **one SQLite file**, **no server**.

## Layers inside `app.py`

| Section | What it contains |
|---|---|
| Helpers | Persian digits (`fa`), money formatting (`money`), number parsing (`parse_num`), Shamsi dates (`today`, `valid_date`), CSV writer |
| Icons | Inline SVG icons rendered to `QIcon` (`ico`, `nav_icon`), app icon |
| Database (`DB`) | Schema, additive migrations, queries (`balances`, `finance`, `save_invoice`, `backup`, `restore`) |
| Receipt | `receipt_html` → `render_receipt` (80 mm bitmap, pure black/white) → `print_image` (driver page, offset) · `calibration_image` |
| Widgets | `NumEdit` (live thousands separators), `NumDelegate`, tables, buttons, cards |
| Dialogs | `FormDialog` base + customer/product/payment/expense/supplier/purchase dialogs, receipt preview, statements, About |
| Pages | `DashboardPage`, `InvoicePage`, `InvoicesPage`, `CustomersPage`, `ProductsPage`, `FinancePage` (+ `BarChart`), `SettingsPage` |
| Main window | Sidebar navigation, shortcuts, toasts, printing glue, global exception hook |

## Data model (SQLite)

```
settings(key, value)                       shop info, tax/discount/shipping switches, printer, next invoice number
customers(id, name, phone, address)
products(id, name, unit, price, cost, barcode, category)
invoices(id, number, date, time, customer_id, customer_name, subtotal, discount, shipping, tax, tax_pct,
         total, paid, prev_balance, note)
invoice_items(id, invoice_id, name, unit, qty, price, total, cost)   -- name/price/cost are copied at sale time
payments(id, customer_id, amount, date, note)                        -- money received from customers
expenses(id, date, category, amount, note)
suppliers(id, name, phone)
supplier_tx(id, supplier_id, kind['purchase'|'payment'], amount, date, note)
```

- Dates are stored as Shamsi strings `YYYY/MM/DD` (zero-padded), so range queries are plain string comparisons.
- Invoice rows keep a **copy** of customer name, item names, prices and costs, so editing a product later never changes history.
- Amounts are whole numbers of the shop currency (Toman); quantities may be decimal.

## Conventions

- **Customer balance** = Σ(invoice.total − invoice.paid) − Σ(payments). Positive = customer owes you.
- **Supplier balance** = Σ purchases − Σ payments. Positive = you owe the supplier.
- `prev_balance` on an invoice is the customer's balance *before* that invoice; it is printed on the receipt and kept when you edit the invoice.

## Finance definitions (`DB.finance`)

| Figure | Formula |
|---|---|
| Sales | Σ invoice totals in the period |
| Cash received | Σ invoice `paid` + Σ customer payments |
| Net cash | cash received − expenses − supplier payments |
| Revenue | sales − tax |
| Gross profit | revenue − Σ(qty × cost price) |
| Net profit (estimate) | gross profit − expenses |

Items without a cost price count as cost 0; the Finance page warns when this affects the profit figure.

## Receipt printing pipeline

1. `receipt_html` builds styled HTML (tables are laid out left-to-right in Qt, so cells are emitted in physical order).
2. `QTextDocument` renders it at `receipt_px()` pixels wide (203 dpi × print width).
3. `to_black_white` darkens and thresholds the bitmap (thermal heads halftone grey).
4. `print_image` sets an 80 mm page, scales 1:1 and applies the horizontal offset.

## Testing

`tests/run_checks.py` boots the real `Main` window headlessly (`QT_QPA_PLATFORM=offscreen`) on a temporary database and drives it like a user: real modal dialogs (answered by timers), invoice save/edit/copy/delete, finance numbers against a hand-computed scenario, printing to PDF, backup/restore, CSV export, migration from an old database file, and batch-file encoding. `tests/test_app.py` wraps it for `pytest`.

## Design decisions

- **Single file** keeps distribution trivial (PyInstaller, one `app.py`). Sections are clearly separated if it ever needs splitting.
- **Bitmap receipts** instead of ESC/POS text: correct Persian shaping and identical preview/print output.
- **SQLite + additive migrations**: the user's data file survives every upgrade.
