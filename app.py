# -*- coding: utf-8 -*-
"""Factor Foroosh (فاکتور فروش) - offline invoicing and finance app for small shops.

Persian/RTL desktop app (PySide6 + SQLite) with Shamsi (Jalali) dates and 80 mm thermal-receipt printing.
Layout of this file (top to bottom): helpers -> icons -> database -> receipt rendering/printing -> widgets
-> dialogs -> pages (dashboard, invoice, invoices, customers, products, finance, settings) -> main window.
"""
import sys, os, csv, html, sqlite3, datetime, traceback
from pathlib import Path

import jdatetime
from PySide6.QtCore import Qt, QSizeF, QMarginsF, QRectF, Signal, QTimer, QByteArray, QSize
from PySide6.QtGui import (QPen, QFont, QFontDatabase, QImage, QPainter, QTextDocument, QPageSize, QPageLayout,
                           QPixmap, QIcon, QColor, QKeySequence, QShortcut)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFormLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QScrollArea, QMessageBox, QFileDialog,
    QStyledItemDelegate, QGraphicsDropShadowEffect, QTabWidget)

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA = Path(os.environ.get("SHOP_DATA") or (Path(os.environ.get("APPDATA", Path.home())) / "ShopInvoice"))
FONT = "Vazirmatn"
APP_VERSION = "1.3.0"
DEVELOPER = {"name": "Arshia Azizade", "email": "arshiaazizade.dev@gmail.com"}   # نام و ایمیل سازنده (روی فاکتور و داخل برنامه)
UNITS = ["عدد", "بسته", "کارتن", "پاکت", "کیلوگرم", "گرم", "فنجان"]
WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

# ---------------------------------------------------------------- helpers
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def fa(x): return str(x).translate(FA)
def money(n): return fa(f"{int(round(n)):,}".replace(",", "٬"))
def qty_txt(q): return fa(("%.3f" % q).rstrip("0").rstrip(".").replace(".", "٫"))
def today(): return jdatetime.date.today().strftime("%Y/%m/%d")
def now_time(): return datetime.datetime.now().strftime("%H:%M")
def long_date():
    d = jdatetime.date.today()
    return f"{WEEKDAYS[d.weekday()]} {fa(d.day)} {MONTHS[d.month - 1]} {fa(d.year)}"

def parse_num(t):
    t = str(t).translate(TO_EN)
    for ch in "٬,،": t = t.replace(ch, "")
    t = t.replace("٫", ".")
    try:
        v = float(t)
        return int(v) if v == int(v) else v
    except ValueError:
        return 0

def valid_date(s):
    try:
        y, m, d = [int(p) for p in s.translate(TO_EN).strip().split("/")]
        jdatetime.date(y, m, d)
        return f"{y:04d}/{m:02d}/{d:02d}"
    except Exception:
        return None

def load_fonts():
    for f in (BASE / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))

def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: اکسل فارسی را درست نشان می‌دهد
        w = csv.writer(f); w.writerow(headers); w.writerows(rows)

# ---------------------------------------------------------------- icons (inline SVG)
ICONS = {
 "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
 "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
 "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
 "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
 "box": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
 "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
 "printer": '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
 "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
 "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
 "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
 "copy": '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
 "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
 "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
 "dollar": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
 "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
 "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
 "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
 "check": '<polyline points="20 6 9 17 4 12"/>',
 "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
 "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
 "truck": '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
}
_icons = {}
def _pix(name, color, size, sw=2):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{sw}" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    pm = QPixmap(size * 2, size * 2); pm.fill(Qt.transparent)
    p = QPainter(pm); QSvgRenderer(QByteArray(svg.encode())).render(p); p.end()
    pm.setDevicePixelRatio(2.0)
    return pm

def ico(name, color="#4A524C", size=18):
    k = (name, color, size)
    if k not in _icons: _icons[k] = QIcon(_pix(name, color, size))
    return _icons[k]

def nav_icon(name):
    i = QIcon()
    i.addPixmap(_pix(name, "#9AA39C", 20), QIcon.Normal, QIcon.Off)
    i.addPixmap(_pix(name, "#F0B94D", 20), QIcon.Normal, QIcon.On)
    return i

def app_icon():
    pm = QPixmap(256, 256); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#B8791F")); p.setPen(Qt.NoPen); p.drawRoundedRect(8, 8, 240, 240, 56, 56)
    p.drawPixmap(48, 48, 160, 160, _pix("file", "#FFFFFF", 80)); p.end()
    return QIcon(pm)

# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', address TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, unit TEXT DEFAULT 'عدد', price REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY, number INTEGER, date TEXT, time TEXT, customer_id INTEGER,
  customer_name TEXT, subtotal REAL, discount REAL, shipping REAL, tax REAL, tax_pct REAL, total REAL, paid REAL, prev_balance REAL);
CREATE TABLE IF NOT EXISTS invoice_items(id INTEGER PRIMARY KEY, invoice_id INTEGER, name TEXT, unit TEXT, qty REAL, price REAL, total REAL);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, date TEXT, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS supplier_tx(id INTEGER PRIMARY KEY, supplier_id INTEGER, kind TEXT, amount REAL, date TEXT, note TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_exp_date ON expenses(date);
CREATE INDEX IF NOT EXISTS ix_suptx ON supplier_tx(supplier_id);
CREATE INDEX IF NOT EXISTS ix_inv_cust ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS ix_inv_date ON invoices(date);
CREATE INDEX IF NOT EXISTS ix_items_inv ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS ix_pay_cust ON payments(customer_id);
"""
NEW_COLUMNS = [("products", "barcode", "TEXT DEFAULT ''"), ("products", "category", "TEXT DEFAULT ''"),
               ("invoices", "note", "TEXT DEFAULT ''"),
               ("products", "cost", "REAL DEFAULT 0"), ("invoice_items", "cost", "REAL DEFAULT 0")]
DEFAULTS = {"shop_name": "دخانیات و قهوه", "shop_sub": "فروش عمده و خرده", "phone": "", "address": "",
            "footer": "از خرید شما سپاسگزاریم", "currency": "تومان", "printer": "", "print_w": "72", "print_dx": "0", "copies": "1",
            "tax_on": "0", "tax_pct": "10", "disc_on": "1", "ship_on": "0", "next_no": "1"}

class DB:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self.init()

    def init(self):
        """ساخت جدول‌ها و به‌روزرسانی دیتابیس نسخه‌های قبلی (بدون پاک شدن اطلاعات)."""
        self.c.executescript(SCHEMA)
        for t, col, decl in NEW_COLUMNS:
            if col not in [r["name"] for r in self.c.execute(f"PRAGMA table_info({t})")]:
                self.c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {decl}")
        for k, v in DEFAULTS.items():
            self.c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
        self.c.commit()

    def q(self, sql, a=()): return self.c.execute(sql, a).fetchall()
    def x(self, sql, a=()):
        cur = self.c.execute(sql, a); self.c.commit(); return cur.lastrowid
    def settings(self): return {r["key"]: r["value"] for r in self.q("SELECT * FROM settings")}
    def set(self, k, v): self.x("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, str(v)))

    def balances(self):
        """مانده همه‌ی مشتری‌ها: مثبت = بدهکار، منفی = بستانکار."""
        rows = self.q("""SELECT c.id, COALESCE(i.s,0) - COALESCE(p.s,0) AS bal FROM customers c
            LEFT JOIN (SELECT customer_id, SUM(total-paid) s FROM invoices GROUP BY customer_id) i ON i.customer_id=c.id
            LEFT JOIN (SELECT customer_id, SUM(amount) s FROM payments GROUP BY customer_id) p ON p.customer_id=c.id""")
        return {r["id"]: r["bal"] for r in rows}

    def balance(self, cid):
        if not cid: return 0
        a = self.q("SELECT COALESCE(SUM(total-paid),0) s FROM invoices WHERE customer_id=?", (cid,))[0]["s"]
        b = self.q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE customer_id=?", (cid,))[0]["s"]
        return a - b

    def supplier_balances(self):
        """مانده‌ی تأمین‌کننده‌ها: مثبت = ما بدهکاریم."""
        rows = self.q("""SELECT s.id, COALESCE(SUM(CASE t.kind WHEN 'purchase' THEN t.amount ELSE -t.amount END),0) bal
                         FROM suppliers s LEFT JOIN supplier_tx t ON t.supplier_id=s.id GROUP BY s.id""")
        return {r["id"]: r["bal"] for r in rows}

    def finance(self, f, t):
        """خلاصه‌ی مالی بازه‌ی [f, t] (تاریخ‌های شمسی به شکل YYYY/MM/DD)."""
        one = lambda sql: self.q(sql, (f, t))[0]
        inv = one("SELECT COALESCE(SUM(total),0) sales, COALESCE(SUM(paid),0) paid, COALESCE(SUM(tax),0) tax, COUNT(*) n FROM invoices WHERE date BETWEEN ? AND ?")
        pay = one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date BETWEEN ? AND ?")["s"]
        exp = one("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date BETWEEN ? AND ?")["s"]
        sup = one("SELECT COALESCE(SUM(amount),0) s FROM supplier_tx WHERE kind='payment' AND date BETWEEN ? AND ?")["s"]
        it = one("""SELECT COALESCE(SUM(ii.qty*COALESCE(ii.cost,0)),0) cogs,
                    COALESCE(SUM(CASE WHEN COALESCE(ii.cost,0)=0 THEN ii.total ELSE 0 END),0) nocost
                    FROM invoice_items ii JOIN invoices i ON i.id=ii.invoice_id WHERE i.date BETWEEN ? AND ?""")
        revenue = inv["sales"] - inv["tax"]
        received = inv["paid"] + pay
        return dict(sales=inv["sales"], count=inv["n"], tax=inv["tax"], revenue=revenue, received=received, expenses=exp,
                    supplier_paid=sup, cash_net=received - exp - sup, cogs=it["cogs"], nocost=it["nocost"],
                    gross=revenue - it["cogs"], net=revenue - it["cogs"] - exp)

    def save_invoice(self, inv, items, edit_id=None):
        c = self.c
        try:
            cid = inv["customer_id"]
            vals = (inv["date"], cid, inv["customer_name"], inv["subtotal"], inv["discount"], inv["shipping"], inv["tax"],
                    inv["tax_pct"], inv["total"], inv["paid"], inv.get("note", ""))
            if edit_id:
                old = c.execute("SELECT customer_id, prev_balance FROM invoices WHERE id=?", (edit_id,)).fetchone()
                prev = old["prev_balance"] if old["customer_id"] == cid else self.balance(cid)
                c.execute("UPDATE invoices SET date=?,customer_id=?,customer_name=?,subtotal=?,discount=?,shipping=?,tax=?,"
                          "tax_pct=?,total=?,paid=?,note=?,prev_balance=? WHERE id=?", vals + (prev, edit_id))
                c.execute("DELETE FROM invoice_items WHERE invoice_id=?", (edit_id,))
                iid = edit_id
            else:
                no = int(self.settings()["next_no"])
                cur = c.execute("INSERT INTO invoices(date,customer_id,customer_name,subtotal,discount,shipping,tax,tax_pct,total,paid,note,"
                                "number,time,prev_balance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                vals + (no, now_time(), self.balance(cid)))
                iid = cur.lastrowid
                c.execute("INSERT OR REPLACE INTO settings VALUES('next_no',?)", (str(no + 1),))
            c.executemany("INSERT INTO invoice_items(invoice_id,name,unit,qty,price,total,cost) VALUES(?,?,?,?,?,?,?)",
                          [(iid, i["name"], i["unit"], i["qty"], i["price"], i["total"], i.get("cost", 0) or 0) for i in items])
            c.commit()
            return iid
        except Exception:
            c.rollback(); raise

    def backup(self, folder, name=None):
        folder.mkdir(parents=True, exist_ok=True)
        dst = sqlite3.connect(folder / (name or f"shop-{datetime.date.today().isoformat()}.db"))
        self.c.backup(dst); dst.close()

    def restore(self, path):
        src = sqlite3.connect(path)
        try:
            src.execute("SELECT 1 FROM invoices LIMIT 1"); src.execute("SELECT 1 FROM customers LIMIT 1")
            self.backup(DATA / "backups", f"before-restore-{datetime.datetime.now():%Y%m%d-%H%M%S}.db")
            src.backup(self.c)
        finally:
            src.close()
        self.c.row_factory = sqlite3.Row
        self.init()

# ---------------------------------------------------------------- receipt (80mm thermal)
def receipt_html(s, inv, items):
    e = html.escape
    cur = e(s["currency"])
    remaining = inv["total"] - inv["paid"]

    def line(label, value, size=21, bold=False, color="#000", meta=False):
        st = f"font-size:{size}px;color:{color};font-weight:bold;"
        wl, wv, av = ("26%", "74%", "right") if meta else ("55%", "45%", "left")
        # جدول‌ها در Qt از چپ به راست چیده می‌شوند، پس ستون مقدار اول می‌آید
        return (f"<tr><td width='{wv}' align='{av}' style='{st}'>{value}</td>"
                f"<td width='{wl}' align='right' style='{st}'>{label}</td></tr>")

    rows = ""
    for i in items:
        rows += (f"<tr><td align='left' style='font-size:21px;font-weight:bold' width='22%'>{money(i['total'])}</td>"
                 f"<td align='center' style='font-size:20px' width='22%'>{money(i['price'])}</td>"
                 f"<td align='center' style='font-size:21px' width='14%'>{qty_txt(i['qty'])}</td>"
                 f"<td align='right' style='font-size:21px;font-weight:bold' width='42%'>{e(i['name'])}"
                 f"<br><span style='font-size:19px;font-weight:bold'>{e(i['unit'] or '')}</span></td></tr>"
                 "<tr><td colspan='4' height='1' style='font-size:1px;border-bottom:1px solid #000'></td></tr>")

    sums = line("جمع اقلام", money(inv["subtotal"]))
    if inv["discount"]: sums += line("تخفیف", money(inv["discount"]))
    if inv["shipping"]: sums += line("هزینه ارسال", money(inv["shipping"]))
    if inv["tax"]: sums += line(f"مالیات ({fa(('%g' % inv['tax_pct']))}٪)", money(inv["tax"]))

    acct = line("پرداخت‌شده", money(inv["paid"]))
    if inv["customer_id"]:
        if remaining: acct += line("مانده این فاکتور", money(remaining), bold=True)
        if inv["prev_balance"]: acct += line("مانده قبلی", money(abs(inv["prev_balance"])) + (" بستانکار" if inv["prev_balance"] < 0 else ""))
        full = inv["prev_balance"] + remaining
        if inv["prev_balance"] or remaining:
            acct += line("مانده کل حساب", money(abs(full)) + (" بستانکار" if full < 0 else ""), 22, True)

    contact = ("تلفن: " + fa(e(s["phone"]))) if s["phone"] else ""
    addr = e(s["address"])
    note = e(inv.get("note") or "")
    credit = (f"<p align='center' style='font-size:19px;font-weight:bold;margin:6px 0 0 0'>طراحی و توسعه</p>"
              f"<p align='center' style='font-size:26px;font-weight:bold;margin:0'>{e(DEVELOPER['name'])}</p>"
              f"<p align='center' style='font-size:19px;font-weight:bold;margin:0'>{e(DEVELOPER['email'])}</p>")
    return f"""
<body dir='rtl' style="font-family:'{FONT}','Tahoma';color:#000">
<p align='center' style='font-size:40px;font-weight:bold;margin:0'>{e(s['shop_name'])}</p>
<p align='center' style='font-size:22px;font-weight:bold;margin:0'>{e(s['shop_sub'])}</p>
<p align='center' style='font-size:20px;font-weight:bold;margin:2px 0 0 0'>{contact}{('<br>' + addr) if addr else ''}</p>
<table width='100%' cellspacing='0' cellpadding='6' style='margin-top:10px'><tr>
<td align='center' bgcolor='#000000' style='color:#ffffff;font-size:24px;font-weight:bold'>فاکتور فروش</td></tr></table>
<table width='100%' cellspacing='0' cellpadding='3' style='margin-top:6px'>
{line('شماره:', fa(inv['number']), 22, True, meta=True)}
{line('تاریخ:', fa(inv['date']) + '  —  ' + fa(inv['time']), 21, meta=True)}
{line('مشتری:', e(inv['customer_name'] or 'متفرقه'), 21, True, meta=True)}
</table>
<table width='100%' cellspacing='0' cellpadding='5' style='margin-top:8px'>
<tr bgcolor='#000000' style='color:#ffffff;font-size:19px;font-weight:bold'>
<td align='left' width='22%'>جمع</td><td align='center' width='22%'>قیمت</td><td align='center' width='14%'>تعداد</td><td align='right' width='42%'>شرح کالا</td></tr>
{rows}
</table>
<table width='100%' cellspacing='0' cellpadding='3' style='margin-top:4px'>{sums}</table>
<table width='100%' cellspacing='0' cellpadding='8' style='margin-top:6px'><tr bgcolor='#000000'>
<td width='55%' align='left' style='color:#ffffff;font-size:28px;font-weight:bold'>{money(inv['total'])} <span style='font-size:18px'>{cur}</span></td>
<td width='45%' align='right' style='color:#ffffff;font-size:24px;font-weight:bold'>قابل پرداخت</td></tr></table>
<table width='100%' cellspacing='0' cellpadding='3' style='margin-top:6px'>{acct}</table>
{f"<p align='center' style='font-size:21px;font-weight:bold;margin-top:8px'>{note}</p>" if note else ""}
<p align='center' style='font-size:22px;font-weight:bold;margin-top:12px'>{e(s['footer'])}</p>
<p align='center' style='font-size:14px;margin:0'>- - - - - - - - - - - - - - - - - - - - - - - -</p>
{credit}
</body>"""

def to_black_white(img):
    """خروجی فقط سیاه و سفید: پرینتر حرارتی خاکستری را نقطه‌چین می‌کند و نوشته‌های ریز کمرنگ می‌شوند.
    ابتدا تصویر کمی تیره می‌شود (ضرب در خودش) تا خطوط نازک پررنگ‌تر شوند، بعد آستانه‌گذاری می‌شود."""
    dark = QImage(img)
    p = QPainter(dark); p.setCompositionMode(QPainter.CompositionMode_Multiply); p.drawImage(0, 0, img); p.end()
    return dark.convertToFormat(QImage.Format_Mono, Qt.ThresholdDither | Qt.AvoidDither).convertToFormat(QImage.Format_RGB32)

HEAD_DPI = 203   # رزولوشن رایج پرینترهای حرارتی ۸۰ میلی‌متری (۸ نقطه در هر میلی‌متر)

def receipt_px(s):
    """عرض تصویر فاکتور به پیکسل: هر پیکسل = یک نقطه‌ی چاپ، تا تصویر موقع چاپ کش نیاید و تار نشود."""
    return max(int(round(float(s.get("print_w") or 72) / 25.4 * HEAD_DPI)), 200)

def render_receipt(s, inv, items, width=None):
    width = width or receipt_px(s)
    doc = QTextDocument()
    doc.setDocumentMargin(10)
    opt = doc.defaultTextOption(); opt.setTextDirection(Qt.RightToLeft); doc.setDefaultTextOption(opt)
    doc.setDefaultFont(QFont(FONT, 12))
    doc.setHtml(receipt_html(s, inv, items))
    doc.setTextWidth(width)
    img = QImage(width, int(doc.size().height()) + 30, QImage.Format_RGB32)
    img.fill(Qt.white)
    p = QPainter(img); p.setRenderHint(QPainter.TextAntialiasing); doc.drawContents(p); p.end()
    return to_black_white(img)

def print_image(img, printer_name, printable_mm, dx_mm=0, printer=None):
    """چاپ تصویر روی کاغذ ۸۰ میلی‌متری. dx_mm: جابه‌جایی افقی (مثبت = راست، منفی = چپ) برای تنظیم دقیق جای محتوا."""
    pr = printer or QPrinter(QPrinter.HighResolution)
    if printer_name and not printer: pr.setPrinterName(printer_name)
    h_mm = img.height() / img.width() * printable_mm
    pr.setPageSize(QPageSize(QSizeF(80, h_mm + 8), QPageSize.Millimeter))
    pr.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter)
    p = QPainter()
    if not p.begin(pr): return False
    r = pr.pageRect(QPrinter.DevicePixel); rm = pr.pageRect(QPrinter.Millimeter)
    k = r.width() / (rm.width() or 80.0)                      # نقطه‌ی دستگاه در هر میلی‌متر (از خود درایور)
    w = printable_mm * k
    x = (r.width() - w) / 2 + dx_mm * k
    p.drawImage(QRectF(x, 0, w, w * img.height() / img.width()), img)
    p.end()
    return True

def calibration_image(s):
    """برگه‌ی تست تراز: قاب و خط‌کش میلی‌متری تا معلوم شود پرینتر کجای کاغذ را چاپ می‌کند."""
    mm = float(s.get("print_w") or 72); dpm = HEAD_DPI / 25.4
    W, H = receipt_px(s), int(round(78 * dpm))
    img = QImage(W, H, QImage.Format_RGB32); img.fill(Qt.white)
    p = QPainter(img); p.setRenderHint(QPainter.TextAntialiasing)
    p.setPen(QPen(Qt.black, 4)); p.drawRect(2, 2, W - 5, H - 5)
    p.setFont(QFont(FONT, 9, QFont.Bold)); p.setPen(QPen(Qt.black, 2))
    for i in range(0, int(mm) + 1, 5):
        x = int(i * dpm) + 2; L = 26 if i % 10 == 0 else 14
        p.drawLine(x, 4, x, 4 + L); p.drawLine(x, H - 6, x, H - 6 - L)
        if i % 10 == 0: p.drawText(QRectF(x - 20, 34, 40, 20), Qt.AlignCenter, fa(i))
    p.drawLine(W // 2, 350, W // 2, H - 60)
    p.setFont(QFont(FONT, 14, QFont.Bold))
    p.drawText(QRectF(10, 62, W - 20, 36), Qt.AlignCenter, "تست تراز چاپ")
    p.setFont(QFont(FONT, 11, QFont.Bold))
    p.drawText(QRectF(10, 108, W - 20, 30), Qt.AlignCenter, f"عرض: \u200e{qty_txt(mm)} mm\u200e     جابه‌جایی: \u200e{qty_txt(float(s.get('print_dx') or 0))} mm\u200e")
    p.drawText(QRectF(14, 160, W / 2 - 20, 30), Qt.AlignLeft | Qt.AlignVCenter, "◄ چپ")
    p.drawText(QRectF(W / 2 + 6, 160, W / 2 - 20, 30), Qt.AlignRight | Qt.AlignVCenter, "راست ►")
    p.setFont(QFont(FONT, 10, QFont.Bold))
    p.drawText(QRectF(18, 210, W - 36, 150), Qt.AlignCenter | Qt.TextWordWrap,
               "اگر خط قاب سمت چپ یا راست روی کاغذ دیده نمی‌شود، همان سمت بریده شده است. "
               "اگر یک سمت خالی بود، «جابه‌جایی افقی» را در تنظیمات عوض کنید. اعداد بالا فاصله از لبه‌ی چپ قاب بر حسب میلی‌متر است.")
    p.end()
    return to_black_white(img)

# ---------------------------------------------------------------- small widgets
class NumEdit(QLineEdit):
    """فیلد عددی: ارقام فارسی/انگلیسی، و جداکننده‌ی سه‌رقمی همان لحظه‌ی تایپ."""
    edited = Signal()
    def __init__(self, value=0, dec=False, parent=None):
        super().__init__(parent)
        self.dec = dec
        self.setAlignment(Qt.AlignCenter)
        self.setValue(value)
        self.textEdited.connect(self._live)
        self.editingFinished.connect(self._done)
    def value(self): return parse_num(self.text())
    def setValue(self, v): self.setText(qty_txt(v) if self.dec else money(v))
    def _live(self, text):
        if not self.dec:
            t = text.translate(TO_EN)
            right = sum(ch.isdigit() for ch in t[self.cursorPosition():])
            digits = "".join(ch for ch in t if ch.isdigit())
            new = money(int(digits)) if digits else ""
            self.blockSignals(True)
            self.setText(new)
            p, cnt = len(new), 0
            while p > 0 and cnt < right:
                p -= 1
                if new[p].isdigit(): cnt += 1
            self.setCursorPosition(p)
            self.blockSignals(False)
        self.edited.emit()
    def _done(self):
        self.setValue(self.value()); self.edited.emit()
    def focusInEvent(self, ev):
        super().focusInEvent(ev); QTimer.singleShot(0, self.selectAll)

class NumDelegate(QStyledItemDelegate):
    """ویرایش تعداد/قیمت داخل جدول با همان جداکننده‌ی هزارگان."""
    def __init__(self, dec, parent=None):
        super().__init__(parent); self.dec = dec
    def createEditor(self, parent, option, index): return NumEdit(0, self.dec, parent)
    def setEditorData(self, ed, index): ed.setValue(index.data(Qt.UserRole) or 0); ed.selectAll()
    def setModelData(self, ed, model, index):
        v = ed.value(); model.setData(index, qty_txt(v) if self.dec else money(v))

def cap(t):
    l = QLabel(t); l.setObjectName("cap"); return l

def card():
    f = QFrame(); f.setObjectName("card"); return f

def shadow():
    s = QGraphicsDropShadowEffect(); s.setBlurRadius(22); s.setOffset(0, 3); s.setColor(QColor(30, 36, 32, 28)); return s

def h1(t):
    l = QLabel(t); l.setObjectName("h1"); return l

def btn(text, kind="", icon=None):
    b = QPushButton(("  " + text) if (icon and text) else text)
    if kind: b.setObjectName(kind)
    if icon:
        color = "#FFFFFF" if kind == "primary" else ("#B3402F" if kind == "danger" else "#5B625C")
        b.setIcon(ico(icon, color)); b.setIconSize(QSize(18, 18))
    b.setCursor(Qt.PointingHandCursor)
    return b

def make_table(headers, stretch=0, row_h=46):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(row_h)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setShowGrid(False)
    t.setFocusPolicy(Qt.NoFocus)
    h = t.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.ResizeToContents)
    h.setSectionResizeMode(stretch, QHeaderView.Stretch)
    return t

def cell(text, align=Qt.AlignCenter, data=None, color=None, bold=False):
    it = QTableWidgetItem(text)
    it.setTextAlignment(align | Qt.AlignVCenter)
    if data is not None: it.setData(Qt.UserRole, data)
    if color: it.setForeground(QColor(color))
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    return it

def selected_id(table):
    r = table.currentRow()
    return table.item(r, 0).data(Qt.UserRole) if r >= 0 else None

def select_id(table, id_):
    """بعد از بازسازی جدول، ردیف انتخاب‌شده‌ی قبلی را دوباره انتخاب می‌کند."""
    if id_ is None: return
    for r in range(table.rowCount()):
        it = table.item(r, 0)
        if it is not None and it.data(Qt.UserRole) == id_:
            table.setCurrentCell(r, 0); return

def msg(parent, text, title="توجه"):
    m = QMessageBox(QMessageBox.Warning, title, text, parent=parent)
    m.addButton("باشه", QMessageBox.AcceptRole); m.exec()

def ask(parent, text):
    m = QMessageBox(QMessageBox.Question, "تأیید", text, parent=parent)
    y = m.addButton("بله", QMessageBox.YesRole); m.addButton("انصراف", QMessageBox.NoRole)
    m.exec()
    return m.clickedButton() is y

def balance_text(b):
    if not b: return "تسویه", "#5B625C"
    return (f"بدهکار  {money(b)}", "#B3402F") if b > 0 else (f"بستانکار  {money(-b)}", "#3E7A4F")

def pick_save_csv(parent, default):
    p, _ = QFileDialog.getSaveFileName(parent, "ذخیره‌ی فایل اکسل (CSV)", default, "CSV (*.csv)")
    return p

# ---------------------------------------------------------------- dialogs
class FormDialog(QDialog):
    """پایه‌ی دیالوگ‌ها. نکته‌ی مهم: خود دیالوگ باید تا خواندن مقدارها زنده نگه داشته شود."""
    def __init__(self, parent, title, rows):
        super().__init__(parent)
        self.setWindowTitle(title); self.setMinimumWidth(440)
        lay = QVBoxLayout(self); lay.setContentsMargins(26, 24, 26, 20); lay.setSpacing(16)
        t = QLabel(title); t.setObjectName("h2"); lay.addWidget(t)
        form = QFormLayout(); form.setSpacing(12); form.setLabelAlignment(Qt.AlignRight)
        for label, w in rows: form.addRow(label, w)
        lay.addLayout(form)
        row = QHBoxLayout(); row.addStretch()
        c = btn("انصراف"); c.clicked.connect(self.reject)
        ok = btn("ذخیره", "primary", "check"); ok.setDefault(True); ok.clicked.connect(self.accept)
        row.addWidget(c); row.addWidget(ok); lay.addLayout(row)
    def check(self): return True
    def accept(self):
        if self.check(): super().accept()

class CustomerDialog(FormDialog):
    def __init__(self, parent, row=None):
        n, p, a = QLineEdit(), QLineEdit(), QLineEdit()
        if row: n.setText(row["name"]); p.setText(fa(row["phone"])); a.setText(row["address"])
        super().__init__(parent, "مشخصات مشتری", [("نام", n), ("تلفن", p), ("آدرس", a)])
        self.n, self.p, self.a = n, p, a
    def check(self):
        if not self.n.text().strip(): msg(self, "نام مشتری را وارد کنید."); return False
        return True
    def values(self): return (self.n.text().strip(), self.p.text().strip().translate(TO_EN), self.a.text().strip())

class ProductDialog(FormDialog):
    def __init__(self, parent, row=None, categories=()):
        n, c, u, pr, b, co = QLineEdit(), QComboBox(), QComboBox(), NumEdit(0), QLineEdit(), NumEdit(0)
        c.setEditable(True); c.addItems([x for x in categories if x]); c.setEditText("")
        u.setEditable(True); u.addItems(UNITS)
        b.setPlaceholderText("اختیاری - با دستگاه بارکدخوان هم پر می‌شود")
        if row:
            n.setText(row["name"]); c.setEditText(row["category"] or ""); u.setEditText(row["unit"])
            pr.setValue(row["price"]); b.setText(row["barcode"] or ""); co.setValue(row["cost"] or 0)
        super().__init__(parent, "مشخصات کالا", [("نام کالا", n), ("دسته‌بندی", c), ("واحد", u), ("قیمت فروش", pr),
                                                 ("قیمت خرید (برای محاسبه‌ی سود)", co), ("بارکد", b)])
        self.n, self.c, self.u, self.pr, self.b, self.co = n, c, u, pr, b, co
    def check(self):
        if not self.n.text().strip(): msg(self, "نام کالا را وارد کنید."); return False
        return True
    def values(self):
        return (self.n.text().strip(), self.u.currentText().strip() or "عدد", self.pr.value(),
                self.b.text().strip().translate(TO_EN), self.c.currentText().strip(), self.co.value())

class PaymentDialog(FormDialog):
    def __init__(self, parent, balance=0, title="ثبت دریافتی از مشتری"):
        a, d, n = NumEdit(0), QLineEdit(fa(today())), QLineEdit()
        d.setAlignment(Qt.AlignCenter)
        if balance > 0: a.setValue(balance)
        super().__init__(parent, title, [("مبلغ", a), ("تاریخ", d), ("توضیح", n)])
        self.a, self.d, self.n = a, d, n
    def check(self):
        if self.a.value() <= 0: msg(self, "مبلغ را وارد کنید."); return False
        if not valid_date(self.d.text()): msg(self, "تاریخ معتبر نیست. نمونه: ۱۴۰۵/۰۸/۲۰"); return False
        return True
    def values(self): return (self.a.value(), valid_date(self.d.text()), self.n.text().strip())

EXPENSE_CATS = ["اجاره", "حقوق و دستمزد", "قبض (برق، آب، گاز، اینترنت)", "حمل و نقل", "تبلیغات", "تعمیرات", "مالیات و عوارض", "سایر"]

class ExpenseDialog(FormDialog):
    def __init__(self, parent, cats, row=None):
        d, c, a, n = QLineEdit(fa(today())), QComboBox(), NumEdit(0), QLineEdit()
        d.setAlignment(Qt.AlignCenter); c.setEditable(True); c.addItems(cats); c.setEditText("")
        if row: d.setText(fa(row["date"])); c.setEditText(row["category"]); a.setValue(row["amount"]); n.setText(row["note"] or "")
        super().__init__(parent, "ثبت هزینه", [("تاریخ", d), ("دسته", c), ("مبلغ", a), ("توضیح", n)])
        self.d, self.c, self.a, self.n = d, c, a, n
    def check(self):
        if not valid_date(self.d.text()): msg(self, "تاریخ معتبر نیست. نمونه: ۱۴۰۵/۰۸/۲۰"); return False
        if self.a.value() <= 0: msg(self, "مبلغ را وارد کنید."); return False
        return True
    def values(self): return (valid_date(self.d.text()), self.c.currentText().strip() or "سایر", self.a.value(), self.n.text().strip())

class SupplierDialog(FormDialog):
    def __init__(self, parent, row=None):
        n, p = QLineEdit(), QLineEdit()
        if row: n.setText(row["name"]); p.setText(fa(row["phone"]))
        super().__init__(parent, "مشخصات تأمین‌کننده", [("نام (شرکت پخش / فروشنده)", n), ("تلفن", p)])
        self.n, self.p = n, p
    def check(self):
        if not self.n.text().strip(): msg(self, "نام تأمین‌کننده را وارد کنید."); return False
        return True
    def values(self): return (self.n.text().strip(), self.p.text().strip().translate(TO_EN))

class PurchaseDialog(FormDialog):
    def __init__(self, parent):
        a, pd, d, n = NumEdit(0), NumEdit(0), QLineEdit(fa(today())), QLineEdit()
        d.setAlignment(Qt.AlignCenter)
        super().__init__(parent, "ثبت خرید از تأمین‌کننده", [("مبلغ خرید", a), ("پرداخت‌شده همین حالا", pd), ("تاریخ", d), ("توضیح", n)])
        self.a, self.pd, self.d, self.n = a, pd, d, n
    def check(self):
        if self.a.value() <= 0: msg(self, "مبلغ خرید را وارد کنید."); return False
        if self.pd.value() > self.a.value(): msg(self, "مبلغ پرداخت‌شده بیشتر از مبلغ خرید است."); return False
        if not valid_date(self.d.text()): msg(self, "تاریخ معتبر نیست. نمونه: ۱۴۰۵/۰۸/۲۰"); return False
        return True
    def values(self): return (self.a.value(), self.pd.value(), valid_date(self.d.text()), self.n.text().strip())

class AboutDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle("درباره‌ی برنامه"); self.setMinimumWidth(500)
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 28, 30, 22); lay.setSpacing(12)
        logo = QLabel(); logo.setPixmap(app_icon().pixmap(60, 60)); logo.setAlignment(Qt.AlignCenter); lay.addWidget(logo)
        t = QLabel("فاکتور فروش"); t.setObjectName("h1"); t.setAlignment(Qt.AlignCenter); lay.addWidget(t)
        for text in (f"نسخه‌ی {fa(APP_VERSION)}", "مدیریت فروش، مشتریان، کالاها و حساب‌های مالی فروشگاه"):
            c = cap(text); c.setAlignment(Qt.AlignCenter); lay.addWidget(c)
        box = card(); bl = QVBoxLayout(box); bl.setContentsMargins(20, 16, 20, 16); bl.setSpacing(4)
        c1 = cap("طراحی و توسعه"); c1.setAlignment(Qt.AlignCenter)
        nm = QLabel(DEVELOPER["name"]); nm.setAlignment(Qt.AlignCenter); nm.setStyleSheet("font-size:20px;font-weight:bold;color:#1E2420;background:transparent")
        ml = QLabel(f'<a href="mailto:{DEVELOPER["email"]}" style="color:#8A5A12;text-decoration:none">{DEVELOPER["email"]}</a>')
        ml.setAlignment(Qt.AlignCenter); ml.setOpenExternalLinks(True); ml.setTextInteractionFlags(Qt.TextBrowserInteraction)
        for w in (c1, nm, ml): bl.addWidget(w)
        lay.addWidget(box)
        keys = cap("میانبرها:  Ctrl+S ذخیره   •   Ctrl+P ذخیره و چاپ   •   F2 جستجوی کالا   •   Ctrl+1 تا Ctrl+7 جابه‌جایی بین بخش‌ها")
        keys.setWordWrap(True); keys.setAlignment(Qt.AlignCenter); lay.addWidget(keys)
        path = cap(f"محل ذخیره‌ی اطلاعات: {DATA}"); path.setWordWrap(True); path.setAlignment(Qt.AlignCenter)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse); lay.addWidget(path)
        row = QHBoxLayout(); row.addStretch(); b = btn("بستن", "primary"); b.clicked.connect(self.accept); row.addWidget(b); row.addStretch(); lay.addLayout(row)

class SupplierStatementDialog(QDialog):
    """صورت‌حساب تأمین‌کننده: خریدها و پرداخت‌ها با مانده‌ی لحظه‌ای (مثبت = ما بدهکاریم)."""
    def __init__(self, win, sid):
        super().__init__(win)
        db = win.db
        su = db.q("SELECT * FROM suppliers WHERE id=?", (sid,))[0]
        self.setWindowTitle("صورت‌حساب تأمین‌کننده"); self.resize(820, 560)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 22, 24, 20); lay.setSpacing(14)
        head = QHBoxLayout(); t = QLabel(su["name"]); t.setObjectName("h2"); head.addWidget(t); head.addStretch()
        txt, col = sup_balance_text(db.supplier_balances().get(sid, 0))
        b = QLabel(txt); b.setStyleSheet(f"color:{col};font-weight:bold;font-size:16px"); head.addWidget(b); lay.addLayout(head)
        ev = sorted((x["date"], 0 if x["kind"] == "purchase" else 1, x["id"], x["note"] or "",
                     x["amount"] if x["kind"] == "purchase" else 0, x["amount"] if x["kind"] == "payment" else 0)
                    for x in db.q("SELECT * FROM supplier_tx WHERE supplier_id=?", (sid,)))
        self.table = make_table(["تاریخ", "شرح", "خرید", "پرداخت", "مانده"], 1); self.table.setRowCount(len(ev)); run = 0
        for r, (d, k, _, note, buy, pay) in enumerate(ev):
            run += buy - pay; tx, cl = sup_balance_text(run)
            self.table.setItem(r, 0, cell(fa(d))); self.table.setItem(r, 1, cell(("خرید" if k == 0 else "پرداخت") + (f" — {note}" if note else ""), Qt.AlignRight))
            self.table.setItem(r, 2, cell(money(buy) if buy else "—")); self.table.setItem(r, 3, cell(money(pay) if pay else "—"))
            self.table.setItem(r, 4, cell(tx, color=cl, bold=True))
        lay.addWidget(self.table)
        row = QHBoxLayout(); c = btn("بستن"); c.clicked.connect(self.accept); row.addStretch(); row.addWidget(c); lay.addLayout(row)

def sup_balance_text(b):
    if not b: return "تسویه", "#5B625C"
    return (f"بدهکاریم  {money(b)}", "#B3402F") if b > 0 else (f"طلبکاریم  {money(-b)}", "#3E7A4F")

class ReceiptDialog(QDialog):
    def __init__(self, win, img, title="پیش‌نمایش فاکتور"):
        super().__init__(win)
        self.win, self.img = win, img
        self.setWindowTitle(title); self.resize(680, 780)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 16)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame); sc.setStyleSheet("background:#D9DCD4")
        lab = QLabel(); lab.setPixmap(QPixmap.fromImage(img)); lab.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lab.setContentsMargins(0, 22, 0, 22)
        sc.setWidget(lab); lay.addWidget(sc)
        row = QHBoxLayout(); row.setContentsMargins(20, 0, 20, 0)
        p = btn("چاپ فاکتور", "primary", "printer"); p.clicked.connect(lambda: win.print_img(img))
        c = btn("بستن"); c.clicked.connect(self.accept)
        row.addWidget(p); row.addWidget(c); row.addStretch(); lay.addLayout(row)

class StatementDialog(QDialog):
    """صورت‌حساب مشتری: همه‌ی فاکتورها و دریافتی‌ها با مانده‌ی لحظه‌ای."""
    def __init__(self, win, cid):
        super().__init__(win)
        db = win.db
        cu = db.q("SELECT * FROM customers WHERE id=?", (cid,))[0]
        self.setWindowTitle("صورت‌حساب مشتری"); self.resize(860, 620)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 22, 24, 20); lay.setSpacing(14)
        head = QHBoxLayout(); t = QLabel(cu["name"]); t.setObjectName("h2"); head.addWidget(t); head.addStretch()
        txt, col = balance_text(db.balance(cid))
        b = QLabel(txt); b.setStyleSheet(f"color:{col};font-weight:bold;font-size:16px"); head.addWidget(b); lay.addLayout(head)
        ev = []
        for i in db.q("SELECT * FROM invoices WHERE customer_id=?", (cid,)):
            ev.append((i["date"], 0, i["id"], f"فاکتور شماره {fa(i['number'])}", i["total"], i["paid"]))
        for p in db.q("SELECT * FROM payments WHERE customer_id=?", (cid,)):
            ev.append((p["date"], 1, p["id"], "دریافتی" + (f" — {p['note']}" if p["note"] else ""), 0, p["amount"]))
        ev.sort()
        self.table = make_table(["تاریخ", "شرح", "بدهکار", "بستانکار", "مانده"], 1)
        self.table.setRowCount(len(ev)); run = 0
        for r, (d, _, _, desc, debit, credit) in enumerate(ev):
            run += debit - credit
            txt, col = balance_text(run)
            self.table.setItem(r, 0, cell(fa(d))); self.table.setItem(r, 1, cell(desc, Qt.AlignRight))
            self.table.setItem(r, 2, cell(money(debit) if debit else "—")); self.table.setItem(r, 3, cell(money(credit) if credit else "—"))
            self.table.setItem(r, 4, cell(txt, color=col, bold=True))
        lay.addWidget(self.table)
        row = QHBoxLayout()
        e = btn("خروجی اکسل", "", "download"); e.clicked.connect(lambda: self.export(ev, cu["name"]))
        c = btn("بستن"); c.clicked.connect(self.accept)
        row.addWidget(e); row.addStretch(); row.addWidget(c); lay.addLayout(row)
        self.ev = ev
    def export(self, ev, name):
        p = pick_save_csv(self, f"statement-{name}.csv")
        if p:
            run = 0; rows = []
            for d, _, _, desc, debit, credit in ev:
                run += debit - credit; rows.append([d, desc, int(debit), int(credit), int(run)])
            write_csv(p, ["تاریخ", "شرح", "بدهکار", "بستانکار", "مانده"], rows)

# ---------------------------------------------------------------- pages
class DashboardPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 26); lay.setSpacing(18)
        head = QHBoxLayout(); t = QVBoxLayout(); t.setSpacing(2)
        t.addWidget(h1("داشبورد")); self.date = cap(""); t.addWidget(self.date); head.addLayout(t); head.addStretch()
        b = btn("فاکتور جدید", "primary", "plus"); b.setMinimumHeight(42); b.clicked.connect(lambda: win.go(1)); head.addWidget(b)
        lay.addLayout(head)
        row = QHBoxLayout(); row.setSpacing(16); self.vals = {}
        for key, title, color in [("sales", "فروش امروز", "#8A5A12"), ("count", "تعداد فاکتور امروز", "#1E2420"),
                                  ("recv", "دریافتی امروز", "#3E7A4F"), ("debt", "مطالبات از مشتریان", "#B3402F")]:
            f = card(); f.setGraphicsEffect(shadow()); v = QVBoxLayout(f); v.setContentsMargins(20, 16, 20, 16); v.setSpacing(4)
            lab = QLabel("۰"); lab.setStyleSheet(f"font-size:26px;font-weight:bold;color:{color};background:transparent")
            unit = cap(""); v.addWidget(cap(title)); v.addWidget(lab); v.addWidget(unit)
            self.vals[key] = (lab, unit); row.addWidget(f, 1)
        lay.addLayout(row)
        low = QHBoxLayout(); low.setSpacing(16)
        c1 = card(); l1 = QVBoxLayout(c1); l1.setContentsMargins(18, 16, 18, 14)
        t1 = QLabel("آخرین فاکتورها"); t1.setObjectName("h2"); l1.addWidget(t1)
        self.recent = make_table(["شماره", "مشتری", "مبلغ", "مانده"], 1, 42); self.recent.doubleClicked.connect(self.open_invoice); l1.addWidget(self.recent)
        c2 = card(); l2 = QVBoxLayout(c2); l2.setContentsMargins(18, 16, 18, 14)
        t2 = QLabel("بیشترین بدهکاران"); t2.setObjectName("h2"); l2.addWidget(t2)
        self.debtors = make_table(["مشتری", "مانده"], 0, 42); l2.addWidget(self.debtors)
        low.addWidget(c1, 3); low.addWidget(c2, 2); lay.addLayout(low, 1)

    def open_invoice(self, *_):
        iid = selected_id(self.recent)
        if iid: ReceiptDialog(self.win, self.win.invoice_image(iid)).exec()

    def refresh(self):
        db, t, cur = self.db, today(), self.win.cur
        self.date.setText(long_date())
        r = db.q("SELECT COALESCE(SUM(total),0) s, COUNT(*) n, COALESCE(SUM(paid),0) p FROM invoices WHERE date=?", (t,))[0]
        pay = db.q("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date=?", (t,))[0]["s"]
        bal = db.balances(); recv = sum(v for v in bal.values() if v > 0)
        for key, v in (("sales", r["s"]), ("count", r["n"]), ("recv", r["p"] + pay), ("debt", recv)):
            lab, unit = self.vals[key]; lab.setText(money(v)); unit.setText("" if key == "count" else cur)
        rows = db.q("SELECT * FROM invoices ORDER BY id DESC LIMIT 8"); self.recent.setRowCount(len(rows))
        for i, x in enumerate(rows):
            rem = x["total"] - x["paid"]
            self.recent.setItem(i, 0, cell(fa(x["number"]), data=x["id"], bold=True))
            self.recent.setItem(i, 1, cell(x["customer_name"] or "متفرقه", Qt.AlignRight))
            self.recent.setItem(i, 2, cell(money(x["total"]), bold=True))
            self.recent.setItem(i, 3, cell(money(rem) if rem else "—", color="#B3402F" if rem > 0 else None))
        names = {c["id"]: c["name"] for c in db.q("SELECT id,name FROM customers")}
        top = sorted(((v, k) for k, v in bal.items() if v > 0), reverse=True)[:8]; self.debtors.setRowCount(len(top))
        for i, (v, k) in enumerate(top):
            self.debtors.setItem(i, 0, cell(names[k], Qt.AlignRight, k, bold=True)); self.debtors.setItem(i, 1, cell(money(v), color="#B3402F", bold=True))


C_NAME, C_UNIT, C_QTY, C_PRICE, C_TOT, C_DEL = range(6)

class InvoicePage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page")
        self.win, self.db = win, win.db
        self.s = self.db.settings()
        self.paid_manual = False; self.edit_id = None; self.edit_no = None; self.tax_pct_override = None; self.cur_cost = 0
        root = QHBoxLayout(self); root.setContentsMargins(30, 26, 30, 26); root.setSpacing(22)

        main = QVBoxLayout(); main.setSpacing(14)
        self.title = h1("فاکتور جدید"); main.addWidget(self.title)
        self.banner = QFrame(); self.banner.setObjectName("banner"); bl = QHBoxLayout(self.banner); bl.setContentsMargins(16, 8, 16, 8)
        self.banner_lbl = QLabel(); self.banner_lbl.setObjectName("bannerlbl"); bl.addWidget(self.banner_lbl); bl.addStretch()
        cb = btn("لغو ویرایش", "", "x"); cb.clicked.connect(self.reset); bl.addWidget(cb); self.banner.hide(); main.addWidget(self.banner)

        top = card(); g = QGridLayout(top); g.setContentsMargins(20, 16, 20, 16); g.setHorizontalSpacing(18)
        self.lbl_no = QLabel(); self.lbl_no.setObjectName("big")
        self.date = QLineEdit(); self.date.setAlignment(Qt.AlignCenter)
        self.cust = QComboBox(); self.cust.setEditable(True); self.cust.setInsertPolicy(QComboBox.NoInsert)
        self.cust.completer().setFilterMode(Qt.MatchContains); self.cust.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.cust.currentTextChanged.connect(self.cust_changed)
        newc = btn("مشتری جدید", "", "plus"); newc.clicked.connect(self.new_customer)
        self.lbl_bal = QLabel(); self.lbl_bal.setObjectName("cap")
        g.addWidget(cap("شماره فاکتور"), 0, 0); g.addWidget(self.lbl_no, 1, 0)
        g.addWidget(cap("تاریخ (شمسی)"), 0, 1); g.addWidget(self.date, 1, 1)
        g.addWidget(cap("مشتری (برای فروش نسیه حتماً انتخاب کنید)"), 0, 2); g.addWidget(self.cust, 1, 2); g.addWidget(newc, 1, 3)
        g.addWidget(self.lbl_bal, 2, 2, 1, 2); g.setColumnStretch(2, 1); g.setColumnMinimumWidth(1, 150)
        main.addWidget(top)

        items = card(); il = QVBoxLayout(items); il.setContentsMargins(20, 16, 20, 14); il.setSpacing(12)
        bar = QGridLayout(); bar.setHorizontalSpacing(12)
        self.prod = QComboBox(); self.prod.setEditable(True); self.prod.setInsertPolicy(QComboBox.NoInsert)
        self.prod.completer().setFilterMode(Qt.MatchContains); self.prod.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.prod.lineEdit().setPlaceholderText("نام یا بارکد کالا")
        self.prod.lineEdit().textChanged.connect(self.pick_product)
        self.prod.lineEdit().returnPressed.connect(self.add_item)
        self.unit = QComboBox(); self.unit.setEditable(True); self.unit.addItems(UNITS)
        self.qty = NumEdit(1, dec=True); self.price = NumEdit(0)
        add = btn("افزودن", "primary", "plus"); add.clicked.connect(self.add_item)
        self.qty.returnPressed.connect(self.add_item); self.price.returnPressed.connect(self.add_item)
        for i, (c, w) in enumerate([("کالا", self.prod), ("واحد", self.unit), ("تعداد", self.qty), ("قیمت واحد", self.price)]):
            bar.addWidget(cap(c), 0, i); bar.addWidget(w, 1, i)
        bar.addWidget(add, 1, 4)
        bar.setColumnStretch(0, 1); bar.setColumnMinimumWidth(1, 100); bar.setColumnMinimumWidth(2, 80); bar.setColumnMinimumWidth(3, 130)
        il.addLayout(bar)
        self.table = make_table(["کالا", "واحد", "تعداد", "قیمت واحد", "جمع", ""], C_NAME)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self._d1, self._d2 = NumDelegate(True, self.table), NumDelegate(False, self.table)
        self.table.setItemDelegateForColumn(C_QTY, self._d1); self.table.setItemDelegateForColumn(C_PRICE, self._d2)
        self.table.itemChanged.connect(self.item_changed)
        self.table.cellClicked.connect(lambda r, c: self.remove_row(r) if c == C_DEL else None)
        self.table.horizontalHeader().setSectionResizeMode(C_DEL, QHeaderView.Fixed); self.table.setColumnWidth(C_DEL, 50)
        QShortcut(QKeySequence.Delete, self.table, activated=lambda: self.remove_row(self.table.currentRow()))
        il.addWidget(self.table, 1)
        self.note = QLineEdit(); self.note.setPlaceholderText("توضیحات فاکتور (اختیاری — روی فاکتور چاپ می‌شود)")
        il.addWidget(self.note)
        il.addWidget(cap("برای تغییر تعداد یا قیمت، روی خانه‌اش دابل‌کلیک کنید. دکمه ✕ ردیف را حذف می‌کند."))
        main.addWidget(items, 1); root.addLayout(main, 1)

        sm = card(); sm.setFixedWidth(350)
        sl = QVBoxLayout(sm); sl.setContentsMargins(22, 20, 22, 20); sl.setSpacing(10)
        self.v_sub = QLabel("۰")
        r = QHBoxLayout(); r.addWidget(QLabel("جمع اقلام")); r.addStretch(); r.addWidget(self.v_sub); sl.addLayout(r)
        self.cb_disc, self.disc, self.row_disc = self.opt_row(sl, "تخفیف")
        self.cb_ship, self.ship, self.row_ship = self.opt_row(sl, "هزینه ارسال")
        self.cb_tax = QCheckBox(); self.v_tax = QLabel("۰")
        self.row_tax = QWidget(); tr = QHBoxLayout(self.row_tax); tr.setContentsMargins(0, 0, 0, 0)
        tr.addWidget(self.cb_tax); tr.addStretch(); tr.addWidget(self.v_tax); sl.addWidget(self.row_tax)
        self.cb_tax.toggled.connect(self.calc)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color:#E3E5DF"); sl.addWidget(line)
        sl.addWidget(cap("مبلغ قابل پرداخت"))
        self.v_total = QLabel("۰"); self.v_total.setObjectName("total"); self.v_total.setAlignment(Qt.AlignCenter); sl.addWidget(self.v_total)
        pr = QHBoxLayout(); pr.addWidget(QLabel("پرداخت‌شده")); pr.addStretch()
        full = QPushButton("کل مبلغ"); full.setObjectName("link"); full.setCursor(Qt.PointingHandCursor)
        full.clicked.connect(lambda: (setattr(self, "paid_manual", False), self.calc())); pr.addWidget(full); sl.addLayout(pr)
        self.paid = NumEdit(0); self.paid.edited.connect(self.paid_edited); sl.addWidget(self.paid)
        rr = QHBoxLayout(); rr.addWidget(QLabel("مانده این فاکتور")); rr.addStretch()
        self.v_rem = QLabel("۰"); self.v_rem.setObjectName("bold"); rr.addWidget(self.v_rem); sl.addLayout(rr)
        sl.addStretch()
        b1 = btn("ذخیره و چاپ فاکتور", "primary", "printer"); b1.setMinimumHeight(48); b1.setToolTip("Ctrl+P"); b1.clicked.connect(lambda: self.save(True))
        b2 = btn("فقط ذخیره", "", "save"); b2.setToolTip("Ctrl+S"); b2.clicked.connect(lambda: self.save(False))
        b3 = btn("پیش‌نمایش", "", "eye"); b3.clicked.connect(self.preview)
        b4 = btn("پاک کردن فرم", "danger", "trash"); b4.clicked.connect(self.reset)
        sl.addWidget(b1); row = QHBoxLayout(); row.addWidget(b2); row.addWidget(b3); sl.addLayout(row); sl.addWidget(b4)
        root.addWidget(sm)

    def opt_row(self, lay, title):
        w = QWidget(); box = QVBoxLayout(w); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(6)
        r = QHBoxLayout(); cb = QCheckBox(title); r.addWidget(cb); r.addStretch(); box.addLayout(r)
        ed = NumEdit(0); ed.setVisible(False); ed.edited.connect(self.calc); box.addWidget(ed)
        cb.toggled.connect(lambda on: (ed.setVisible(on), self.calc()))
        lay.addWidget(w)
        return cb, ed, w

    # -- data / refresh
    def refresh(self):
        s = self.s = self.db.settings()
        self.lbl_no.setText(fa(self.edit_no if self.edit_id else s["next_no"]))
        if not self.date.text(): self.date.setText(fa(today()))
        if not self.table.rowCount() and not self.edit_id: self.cb_tax.setChecked(s["tax_on"] == "1")
        self.row_disc.setVisible(s["disc_on"] == "1" or self.cb_disc.isChecked())
        self.row_ship.setVisible(s["ship_on"] == "1" or self.cb_ship.isChecked())
        self.row_tax.setVisible(s["tax_on"] == "1" or self.cb_tax.isChecked())
        pct = self.tax_pct_override if self.tax_pct_override is not None else float(s["tax_pct"] or 0)
        self.cb_tax.setText(f"مالیات ({qty_txt(pct)}٪)")
        cur = self.cust_id()
        self.cust.blockSignals(True); self.cust.clear(); self.cust.addItem("مشتری متفرقه (بدون ثبت)", None)
        for c in self.db.q("SELECT id,name,phone FROM customers ORDER BY name"):
            self.cust.addItem(c["name"] + (f"  —  {fa(c['phone'])}" if c["phone"] else ""), c["id"])
        self.cust.setCurrentIndex(self.cust.findData(cur) if cur else 0); self.cust.blockSignals(False)
        self.cust_changed()
        txt = self.prod.currentText()
        self.prod.blockSignals(True); self.prod.clear()
        for p in self.db.q("SELECT * FROM products ORDER BY name"): self.prod.addItem(p["name"], (p["unit"], p["price"], p["cost"] or 0))
        self.prod.setCurrentIndex(-1); self.prod.setEditText(txt); self.prod.blockSignals(False)
        self.calc()

    def cust_id(self):
        i = self.cust.findText(self.cust.currentText())
        return self.cust.itemData(i) if i >= 0 else None

    def cust_resolved(self):
        t = self.cust.currentText().strip()
        return self.cust.findText(t) >= 0 or t == ""

    def cust_changed(self, *_):
        cid = self.cust_id()
        if cid:
            t, col = balance_text(self.db.balance(cid))
            self.lbl_bal.setText("وضعیت حساب: " + t); self.lbl_bal.setStyleSheet(f"color:{col}")
        else:
            self.lbl_bal.setText("")

    def new_customer(self):
        d = CustomerDialog(self)
        if d.exec():
            cid = self.db.x("INSERT INTO customers(name,phone,address) VALUES(?,?,?)", d.values())
            self.refresh(); self.cust.setCurrentIndex(self.cust.findData(cid))

    def pick_product(self, text):
        i = self.prod.findText(text, Qt.MatchExactly)
        if i >= 0:
            unit, price, cost = self.prod.itemData(i)
            self.unit.setEditText(unit); self.price.setValue(price); self.cur_cost = cost
        else:
            self.cur_cost = 0

    # -- items table
    def add_item(self):
        text = self.prod.currentText().strip()
        if not text: return
        qty = self.qty.value()
        bc = self.db.q("SELECT * FROM products WHERE barcode=? AND barcode<>''", (text.translate(TO_EN),))
        if bc: name, unit, price, cost = bc[0]["name"], bc[0]["unit"], bc[0]["price"], bc[0]["cost"] or 0
        else: name, unit, price, cost = text, self.unit.currentText().strip(), self.price.value(), self.cur_cost
        if qty <= 0: return self.win.toast("تعداد باید بیشتر از صفر باشد.")
        if price <= 0: return self.win.toast("قیمت واحد را وارد کنید.")
        for r in range(self.table.rowCount()):
            if (self.table.item(r, C_NAME).text(), self.table.item(r, C_UNIT).text(), self.table.item(r, C_PRICE).data(Qt.UserRole)) == (name, unit, price):
                self.set_cell(r, C_QTY, self.table.item(r, C_QTY).data(Qt.UserRole) + qty); break
        else:
            self.append_row(name, unit, qty, price, cost)
        self.prod.setCurrentIndex(-1); self.prod.clearEditText(); self.qty.setValue(1); self.price.setValue(0)
        self.prod.setFocus()

    def append_row(self, name, unit, qty, price, cost=0):
        t = self.table; r = t.rowCount(); t.blockSignals(True); t.insertRow(r)
        t.setItem(r, C_NAME, cell(name, Qt.AlignRight, name, bold=True)); t.setItem(r, C_UNIT, cell(unit))
        t.item(r, C_NAME).setData(Qt.UserRole + 1, cost)
        t.setItem(r, C_QTY, cell("", data=0)); t.setItem(r, C_PRICE, cell("", data=0)); t.setItem(r, C_TOT, cell("", data=0, bold=True))
        t.setItem(r, C_DEL, cell("✕", color="#B3402F"))
        for c in (C_NAME, C_UNIT, C_TOT, C_DEL): t.item(r, c).setFlags(t.item(r, c).flags() & ~Qt.ItemIsEditable)
        t.blockSignals(False)
        self.set_cell(r, C_QTY, qty); self.set_cell(r, C_PRICE, price)

    def set_cell(self, r, c, v):
        t = self.table; t.blockSignals(True)
        it = t.item(r, c); it.setData(Qt.UserRole, v); it.setText(qty_txt(v) if c == C_QTY else money(v))
        q, p = t.item(r, C_QTY).data(Qt.UserRole), t.item(r, C_PRICE).data(Qt.UserRole)
        tot = t.item(r, C_TOT); tot.setData(Qt.UserRole, round(q * p)); tot.setText(money(q * p))
        t.blockSignals(False); self.calc()

    def item_changed(self, it):
        if it.column() in (C_QTY, C_PRICE): self.set_cell(it.row(), it.column(), parse_num(it.text()))

    def remove_row(self, r):
        if 0 <= r < self.table.rowCount(): self.table.removeRow(r); self.calc()

    # -- totals
    def totals(self):
        t = self.table
        sub = sum(t.item(r, C_TOT).data(Qt.UserRole) for r in range(t.rowCount()))
        disc = min(self.disc.value(), sub) if self.cb_disc.isChecked() else 0
        ship = self.ship.value() if self.cb_ship.isChecked() else 0
        pct = self.tax_pct_override if self.tax_pct_override is not None else float(self.s["tax_pct"] or 0)
        tax = round((sub - disc) * pct / 100) if self.cb_tax.isChecked() else 0
        return sub, disc, ship, tax, pct, sub - disc + ship + tax

    def paid_edited(self):
        self.paid_manual = True; self.calc()

    def calc(self, *_):
        sub, disc, ship, tax, pct, total = self.totals()
        self.v_sub.setText(money(sub)); self.v_tax.setText(money(tax)); self.v_total.setText(money(total) + "  " + self.s["currency"])
        if not self.paid_manual: self.paid.setValue(total)
        rem = total - self.paid.value()
        self.v_rem.setText(money(rem) if rem >= 0 else money(-rem) + " (بستانکار)")
        self.v_rem.setStyleSheet("color:#B3402F" if rem > 0 else "color:#3E7A4F")

    def collect(self):
        self.s = self.db.settings()
        sub, disc, ship, tax, pct, total = self.totals(); t = self.table
        items = [dict(name=t.item(r, C_NAME).text(), unit=t.item(r, C_UNIT).text(), qty=t.item(r, C_QTY).data(Qt.UserRole),
                      price=t.item(r, C_PRICE).data(Qt.UserRole), total=t.item(r, C_TOT).data(Qt.UserRole),
                      cost=t.item(r, C_NAME).data(Qt.UserRole + 1) or 0) for r in range(t.rowCount())]
        cid = self.cust_id()
        name = self.db.q("SELECT name FROM customers WHERE id=?", (cid,))[0]["name"] if cid else ""
        prev, tm = self.db.balance(cid), now_time()
        if self.edit_id:
            o = self.db.q("SELECT customer_id, prev_balance, time FROM invoices WHERE id=?", (self.edit_id,))[0]
            tm = o["time"]
            if o["customer_id"] == cid: prev = o["prev_balance"]
        inv = dict(number=self.edit_no or int(self.s["next_no"]), date=valid_date(self.date.text()), time=tm, customer_id=cid,
                   customer_name=name, subtotal=sub, discount=disc, shipping=ship, tax=tax, tax_pct=pct, total=total,
                   paid=self.paid.value(), prev_balance=prev, note=self.note.text().strip())
        return inv, items

    def preview(self):
        inv, items = self.collect()
        if not items: return self.win.toast("ابتدا حداقل یک کالا اضافه کنید.")
        inv["date"] = inv["date"] or today()
        ReceiptDialog(self.win, render_receipt(self.s, inv, items)).exec()

    def save(self, do_print):
        inv, items = self.collect()
        if not items: return self.win.toast("ابتدا حداقل یک کالا اضافه کنید.")
        if not inv["date"]: return self.win.toast("تاریخ معتبر نیست. نمونه: ۱۴۰۵/۰۸/۲۰")
        if not self.cust_resolved(): return self.win.toast("مشتری را از لیست انتخاب کنید یا «مشتری جدید» بزنید.")
        if inv["total"] - inv["paid"] > 0 and not inv["customer_id"]:
            return self.win.toast("برای فروش نسیه (مانده‌دار) باید یک مشتری ثبت‌شده انتخاب کنید.")
        if not self.edit_id and self.db.q("SELECT 1 FROM invoices WHERE number=?", (inv["number"],)):
            if not ask(self, f"فاکتوری با شماره {fa(inv['number'])} قبلاً ثبت شده است. باز هم ذخیره شود؟"): return
        iid = self.db.save_invoice(inv, items, self.edit_id)
        if do_print: self.win.print_invoice(iid)
        self.win.toast(f"فاکتور {fa(inv['number'])} ذخیره شد.")
        self.reset()
        return iid

    def load_invoice(self, iid, copy=False):
        inv = self.db.q("SELECT * FROM invoices WHERE id=?", (iid,))[0]
        items = self.db.q("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (iid,))
        self.reset()
        cid = inv["customer_id"]
        self.cust.setCurrentIndex(self.cust.findData(cid) if cid else 0) ; self.cust_changed()
        self.date.setText(fa(today() if copy else inv["date"])); self.note.setText(inv["note"] or "")
        for it in items: self.append_row(it["name"], it["unit"], it["qty"], it["price"], it["cost"] or 0)
        self.cb_disc.setChecked(inv["discount"] > 0); self.disc.setValue(inv["discount"])
        self.cb_ship.setChecked(inv["shipping"] > 0); self.ship.setValue(inv["shipping"])
        self.cb_tax.setChecked(inv["tax"] > 0)
        if not copy:
            self.edit_id, self.edit_no, self.tax_pct_override = iid, inv["number"], (inv["tax_pct"] or None)
            self.paid_manual = True; self.paid.setValue(inv["paid"])
            self.title.setText("ویرایش فاکتور"); self.banner_lbl.setText(f"در حال ویرایش فاکتور شماره {fa(inv['number'])}")
            self.banner.show()
        self.refresh()

    def reset(self):
        self.table.setRowCount(0); self.paid_manual = False; self.edit_id = self.edit_no = self.tax_pct_override = None
        for cb, ed in ((self.cb_disc, self.disc), (self.cb_ship, self.ship)): cb.setChecked(False); ed.setValue(0)
        self.cb_tax.setChecked(False); self.note.clear(); self.banner.hide(); self.title.setText("فاکتور جدید")
        self.date.setText(fa(today())); self.cust.setCurrentIndex(0)
        self.refresh()


class InvoicesPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 26); lay.setSpacing(16)
        lay.addWidget(h1("فاکتورها"))
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("جستجو: نام مشتری، شماره یا تاریخ"); self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        for text, kind, ic, fn in [("مشاهده و چاپ", "primary", "printer", self.view), ("ویرایش", "", "edit", self.edit),
                                   ("کپی", "", "copy", self.copy), ("اکسل", "", "download", self.export), ("حذف", "danger", "trash", self.delete)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        lay.addLayout(bar)
        self.table = make_table(["شماره", "تاریخ", "مشتری", "مبلغ", "پرداخت‌شده", "مانده", "وضعیت"], 2)
        self.table.doubleClicked.connect(self.view); lay.addWidget(self.table)

    def rows(self):
        t = f"%{self.search.text().strip().translate(TO_EN)}%"
        return self.db.q("SELECT * FROM invoices WHERE customer_name LIKE ? OR CAST(number AS TEXT) LIKE ? OR date LIKE ? ORDER BY id DESC LIMIT 1000", (t, t, t))

    def refresh(self):
        rows = self.rows(); sel = selected_id(self.table); self.table.setRowCount(len(rows))
        for r, i in enumerate(rows):
            rem = i["total"] - i["paid"]
            st, col = ("بدهکار", "#B3402F") if rem > 0 else (("بستانکار", "#3E7A4F") if rem < 0 else ("تسویه", "#5B625C"))
            self.table.setItem(r, 0, cell(fa(i["number"]), data=i["id"], bold=True))
            self.table.setItem(r, 1, cell(fa(i["date"]))); self.table.setItem(r, 2, cell(i["customer_name"] or "متفرقه", Qt.AlignRight))
            self.table.setItem(r, 3, cell(money(i["total"]), bold=True)); self.table.setItem(r, 4, cell(money(i["paid"])))
            self.table.setItem(r, 5, cell(money(abs(rem)) if rem else "—", color=col if rem else None))
            self.table.setItem(r, 6, cell(st, color=col, bold=True))
        select_id(self.table, sel)

    def view(self, *_):
        iid = selected_id(self.table)
        if iid: ReceiptDialog(self.win, self.win.invoice_image(iid)).exec()
        else: self.win.toast("یک فاکتور را انتخاب کنید.")

    def edit(self):
        iid = selected_id(self.table)
        if iid: self.win.edit_invoice(iid)
        else: self.win.toast("یک فاکتور را انتخاب کنید.")

    def copy(self):
        iid = selected_id(self.table)
        if iid: self.win.edit_invoice(iid, copy=True)
        else: self.win.toast("یک فاکتور را انتخاب کنید.")

    def export(self):
        p = pick_save_csv(self, "invoices.csv")
        if p:
            write_csv(p, ["شماره", "تاریخ", "مشتری", "مبلغ", "پرداخت‌شده", "مانده", "توضیحات"],
                      [[i["number"], i["date"], i["customer_name"], int(i["total"]), int(i["paid"]), int(i["total"] - i["paid"]), i["note"] or ""] for i in self.rows()])
            self.win.toast("فایل اکسل ذخیره شد.")

    def delete(self):
        iid = selected_id(self.table)
        if iid and ask(self, "این فاکتور برای همیشه حذف شود؟"):
            self.db.x("DELETE FROM invoice_items WHERE invoice_id=?", (iid,)); self.db.x("DELETE FROM invoices WHERE id=?", (iid,))
            self.refresh()


class CustomersPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 26); lay.setSpacing(16)
        lay.addWidget(h1("مشتریان"))
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("جستجوی نام یا تلفن"); self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        for text, kind, ic, fn in [("مشتری جدید", "primary", "plus", self.add), ("ویرایش", "", "edit", self.edit),
                                   ("صورت‌حساب", "", "book", self.statement), ("ثبت دریافتی", "", "dollar", self.pay),
                                   ("فاکتورها", "", "file", self.invoices), ("اکسل", "", "download", self.export), ("حذف", "danger", "trash", self.delete)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        lay.addLayout(bar)
        self.table = make_table(["نام", "تلفن", "آدرس", "وضعیت حساب"], 2)
        self.table.doubleClicked.connect(self.edit); lay.addWidget(self.table)

    def rows(self):
        t = f"%{self.search.text().strip().translate(TO_EN)}%"
        return self.db.q("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name", (t, t))

    def refresh(self):
        rows = self.rows(); bal = self.db.balances(); sel = selected_id(self.table); self.table.setRowCount(len(rows))
        for r, c in enumerate(rows):
            txt, col = balance_text(bal.get(c["id"], 0))
            self.table.setItem(r, 0, cell(c["name"], Qt.AlignRight, c["id"], bold=True)); self.table.setItem(r, 1, cell(fa(c["phone"])))
            self.table.setItem(r, 2, cell(c["address"], Qt.AlignRight)); self.table.setItem(r, 3, cell(txt, color=col, bold=True))
        select_id(self.table, sel)

    def need(self):
        cid = selected_id(self.table)
        if not cid: self.win.toast("یک مشتری را انتخاب کنید.")
        return cid

    def add(self):
        d = CustomerDialog(self)
        if d.exec():
            self.db.x("INSERT INTO customers(name,phone,address) VALUES(?,?,?)", d.values()); self.refresh(); self.win.toast("مشتری ذخیره شد.")

    def edit(self, *_):
        cid = self.need()
        if not cid: return
        d = CustomerDialog(self, self.db.q("SELECT * FROM customers WHERE id=?", (cid,))[0])
        if d.exec():
            self.db.x("UPDATE customers SET name=?,phone=?,address=? WHERE id=?", d.values() + (cid,))
            self.db.x("UPDATE invoices SET customer_name=? WHERE customer_id=?", (d.values()[0], cid))
            self.refresh(); self.win.toast("تغییرات ذخیره شد.")

    def statement(self):
        cid = self.need()
        if cid: StatementDialog(self.win, cid).exec()

    def pay(self):
        cid = self.need()
        if not cid: return
        d = PaymentDialog(self, self.db.balance(cid))
        if d.exec():
            a, date, note = d.values()
            self.db.x("INSERT INTO payments(customer_id,amount,date,note) VALUES(?,?,?,?)", (cid, a, date, note))
            self.refresh(); self.win.toast("دریافتی ثبت شد.")

    def invoices(self):
        r = self.table.currentRow()
        if r >= 0: self.win.show_invoices(self.table.item(r, 0).text())
        else: self.win.toast("یک مشتری را انتخاب کنید.")

    def export(self):
        p = pick_save_csv(self, "customers.csv")
        if p:
            bal = self.db.balances()
            write_csv(p, ["نام", "تلفن", "آدرس", "مانده (مثبت = بدهکار)"], [[c["name"], c["phone"], c["address"], int(bal.get(c["id"], 0))] for c in self.rows()])
            self.win.toast("فایل اکسل ذخیره شد.")

    def delete(self):
        cid = self.need()
        if not cid: return
        if self.db.q("SELECT 1 FROM invoices WHERE customer_id=? UNION SELECT 1 FROM payments WHERE customer_id=?", (cid, cid)):
            return msg(self, "این مشتری فاکتور یا دریافتی ثبت‌شده دارد و حذف نمی‌شود تا حساب‌ها به‌هم نخورد.\nمی‌توانید اطلاعاتش را «ویرایش» کنید.")
        if ask(self, "مشتری حذف شود؟"): self.db.x("DELETE FROM customers WHERE id=?", (cid,)); self.refresh()


class ProductsPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 26); lay.setSpacing(16)
        lay.addWidget(h1("کالاها"))
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("جستجوی نام، دسته‌بندی یا بارکد"); self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        for text, kind, ic, fn in [("کالای جدید", "primary", "plus", self.add), ("ویرایش", "", "edit", self.edit), ("حذف", "danger", "trash", self.delete)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        lay.addLayout(bar)
        self.table = make_table(["نام کالا", "دسته‌بندی", "واحد", "قیمت فروش", "قیمت خرید", "بارکد"], 0)
        self.table.doubleClicked.connect(self.edit); lay.addWidget(self.table)

    def refresh(self):
        t = f"%{self.search.text().strip().translate(TO_EN)}%"
        rows = self.db.q("SELECT * FROM products WHERE name LIKE ? OR category LIKE ? OR barcode LIKE ? ORDER BY name", (t, t, t))
        sel = selected_id(self.table); self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            self.table.setItem(r, 0, cell(p["name"], Qt.AlignRight, p["id"], bold=True)); self.table.setItem(r, 1, cell(p["category"] or "—"))
            self.table.setItem(r, 2, cell(p["unit"])); self.table.setItem(r, 3, cell(money(p["price"]) + "  " + self.win.cur, bold=True))
            self.table.setItem(r, 4, cell(money(p["cost"]) if p["cost"] else "—")); self.table.setItem(r, 5, cell(fa(p["barcode"]) if p["barcode"] else "—"))
        select_id(self.table, sel)

    def cats(self): return [r["category"] for r in self.db.q("SELECT DISTINCT category FROM products WHERE category<>'' ORDER BY category")]

    def add(self):
        d = ProductDialog(self, None, self.cats())
        if d.exec():
            self.db.x("INSERT INTO products(name,unit,price,barcode,category,cost) VALUES(?,?,?,?,?,?)", d.values()); self.refresh(); self.win.toast("کالا ذخیره شد.")

    def edit(self, *_):
        pid = selected_id(self.table)
        if not pid: return self.win.toast("یک کالا را انتخاب کنید.")
        d = ProductDialog(self, self.db.q("SELECT * FROM products WHERE id=?", (pid,))[0], self.cats())
        if d.exec():
            self.db.x("UPDATE products SET name=?,unit=?,price=?,barcode=?,category=?,cost=? WHERE id=?", d.values() + (pid,)); self.refresh(); self.win.toast("تغییرات ذخیره شد.")

    def delete(self):
        pid = selected_id(self.table)
        if pid and ask(self, "کالا حذف شود؟ (فاکتورهای قبلی تغییری نمی‌کنند)"): self.db.x("DELETE FROM products WHERE id=?", (pid,)); self.refresh()


# ---------------------------------------------------------------- finance
SEG = [("today", "امروز"), ("week", "این هفته"), ("month", "این ماه"), ("year", "امسال"), ("custom", "بازه‌ی دلخواه")]

def period_range(kind, custom=("", "")):
    d = jdatetime.date.today(); f = lambda x: x.strftime("%Y/%m/%d")
    if kind == "today": return f(d), f(d)
    if kind == "week": return f(d - jdatetime.timedelta(days=d.weekday())), f(d)      # هفته از شنبه شروع می‌شود
    if kind == "month": return f(d.replace(day=1)), f(d)
    if kind == "year": return f(d.replace(month=1, day=1)), f(d)
    return valid_date(custom[0]) or "", valid_date(custom[1]) or ""

def compact(n):
    n = abs(n)
    short = lambda x: fa(("%.1f" % x).rstrip("0").rstrip(".").replace(".", "٫"))
    if n >= 1e9: return short(n / 1e9) + " میلیارد"
    if n >= 1e6: return short(n / 1e6) + " میلیون"
    if n >= 1e3: return short(n / 1e3) + " هزار"
    return fa(int(n))

def stat_card(title, color):
    f = card(); f.setGraphicsEffect(shadow()); v = QVBoxLayout(f); v.setContentsMargins(18, 14, 18, 14); v.setSpacing(2)
    lab = QLabel("۰"); lab.setStyleSheet(f"font-size:22px;font-weight:bold;color:{color};background:transparent")
    unit = cap(""); v.addWidget(cap(title)); v.addWidget(lab); v.addWidget(unit)
    return f, lab, unit

class BarChart(QWidget):
    """نمودار میله‌ای ساده: فروش و هزینه‌ی چند ماه اخیر (قدیمی‌ترین ماه سمت راست)."""
    def __init__(self):
        super().__init__(); self.setMinimumHeight(250); self.labels, self.a, self.b = [], [], []; self.div, self.unit = 1e6, "میلیون تومان"
    def set_data(self, labels, a, b):
        self.labels, self.a, self.b = labels, a, b
        self.div, self.unit = (1e6, "میلیون تومان") if max(a + b + [0]) >= 1e6 else (1e3, "هزار تومان")
        self.update()
    def paintEvent(self, ev):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H, n = self.width(), self.height(), len(self.labels)
        if not n: return
        left, right, top, bottom = 10, 10, 48, 30
        ph = H - top - bottom; gw = (W - left - right) / n; mx = max(max(self.a), max(self.b), 1)
        p.setPen(QColor("#ECEEE8"))
        for i in range(5): y = top + ph * i / 4; p.drawLine(int(left), int(y), int(W - right), int(y))
        small = QFont(FONT, 8); p.setFont(small)
        for idx in range(n):
            gx = W - right - (idx + 1) * gw; bw = min(gw * 0.26, 44)
            for k, (val, color) in enumerate([(self.a[idx], "#B8791F"), (self.b[idx], "#5F6B63")]):
                x = gx + gw / 2 + 3 if k == 0 else gx + gw / 2 - bw - 3
                h = ph * val / mx
                p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(x, top + ph - h, bw, max(h, 0)), 4, 4)
                if val > 0:
                    p.setPen(QColor("#5B625C")); p.drawText(QRectF(x - 4, top + ph - h - 17, bw + 8, 15), Qt.AlignCenter, fa(("%.1f" % (val / self.div)).rstrip("0").rstrip(".").replace(".", "٫")))
            p.setPen(QColor("#1B1F1C")); p.drawText(QRectF(gx, H - bottom + 6, gw, 18), Qt.AlignCenter, self.labels[idx])
        x = W - right
        for text, color in (("فروش", "#B8791F"), ("هزینه", "#5F6B63")):
            p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(x - 12, 10, 12, 12), 3, 3)
            p.setPen(QColor("#1B1F1C")); p.drawText(QRectF(x - 70, 7, 54, 18), Qt.AlignRight | Qt.AlignVCenter, text); x -= 90
        p.setPen(QColor("#8A918B")); p.drawText(QRectF(left, 7, 220, 18), Qt.AlignLeft | Qt.AlignVCenter, "ارقام به " + self.unit)

class FinancePage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        self.kind = "month"
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 20); lay.setSpacing(10)
        head = QHBoxLayout(); head.addWidget(h1("مدیریت مالی")); head.addStretch()
        self.seg = {}
        for key, text in SEG:
            b = QPushButton(text); b.setObjectName("seg"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, k=key: self.set_period(k)); head.addWidget(b); self.seg[key] = b
        lay.addLayout(head)
        self.custom = QWidget(); cl = QHBoxLayout(self.custom); cl.setContentsMargins(0, 0, 0, 0)
        self.f_from, self.f_to = QLineEdit(), QLineEdit()
        for w, ph in ((self.f_from, "از تاریخ  ۱۴۰۵/۰۱/۰۱"), (self.f_to, "تا تاریخ  ۱۴۰۵/۱۲/۲۹")): w.setPlaceholderText(ph); w.setAlignment(Qt.AlignCenter); w.setFixedWidth(190); w.editingFinished.connect(self.refresh)
        cl.addStretch(); cl.addWidget(self.f_from); cl.addWidget(self.f_to); lay.addWidget(self.custom); self.custom.hide()
        self.range_lbl = cap(""); lay.addWidget(self.range_lbl)
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True); lay.addWidget(self.tabs, 1)
        self.build_overview(); self.build_expenses(); self.build_suppliers(); self.build_cash()
        self.seg["month"].setChecked(True)

    # ---- period
    def set_period(self, key):
        self.kind = key
        for k, b in self.seg.items(): b.setChecked(k == key)
        self.custom.setVisible(key == "custom")
        if key == "custom" and not self.f_from.text():
            f, t = period_range("month"); self.f_from.setText(fa(f)); self.f_to.setText(fa(t))
        self.refresh()

    def rng(self): return period_range(self.kind, (self.f_from.text(), self.f_to.text()))

    # ---- overview tab
    def build_overview(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 12, 0, 0); v.setSpacing(14)
        grid = QGridLayout(); grid.setSpacing(14); self.cards = {}
        specs = [("sales", "فروش (جمع فاکتورها)", "#8A5A12"), ("received", "دریافتی (نقد فروش + بدهی‌های وصول‌شده)", "#3E7A4F"),
                 ("expenses", "هزینه‌ها", "#B3402F"), ("cash_net", "خالص نقدی (دریافتی − هزینه − پرداخت به تأمین‌کننده)", "#1E2420"),
                 ("gross", "سود ناخالص", "#3E7A4F"), ("net", "سود خالص (تقریبی)", "#1E2420"),
                 ("recv", "مطالبات از مشتریان", "#B3402F"), ("pay", "بدهی به تأمین‌کنندگان", "#B3402F")]
        for i, (key, title, color) in enumerate(specs):
            f, lab, unit = stat_card(title, color); self.cards[key] = (lab, unit); grid.addWidget(f, i // 4, i % 4)
        v.addLayout(grid)
        self.warn = QLabel(); self.warn.setObjectName("warn"); self.warn.setWordWrap(True); self.warn.hide(); v.addWidget(self.warn)
        cc = card(); cl = QVBoxLayout(cc); cl.setContentsMargins(18, 14, 18, 10)
        t = QLabel("فروش و هزینه‌ی ۶ ماه اخیر"); t.setObjectName("h2"); cl.addWidget(t)
        self.chart = BarChart(); cl.addWidget(self.chart, 1); v.addWidget(cc, 1)
        self.tabs.addTab(w, "خلاصه‌ی مالی")

    # ---- expenses tab
    def build_expenses(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 12, 0, 0); v.setSpacing(12)
        bar = QHBoxLayout(); self.exp_total = QLabel(); self.exp_total.setObjectName("bold"); bar.addWidget(self.exp_total); bar.addStretch()
        for text, kind, ic, fn in [("هزینه‌ی جدید", "primary", "plus", self.exp_add), ("ویرایش", "", "edit", self.exp_edit),
                                   ("اکسل", "", "download", self.exp_export), ("حذف", "danger", "trash", self.exp_delete)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        v.addLayout(bar)
        self.exp_table = make_table(["تاریخ", "دسته", "مبلغ", "توضیح"], 3); self.exp_table.doubleClicked.connect(self.exp_edit); v.addWidget(self.exp_table)
        self.tabs.addTab(w, "هزینه‌ها")

    def exp_cats(self):
        used = [r["category"] for r in self.db.q("SELECT DISTINCT category FROM expenses WHERE category<>''")]
        return EXPENSE_CATS + [c for c in used if c not in EXPENSE_CATS]

    def exp_rows(self):
        f, t = self.rng()
        return self.db.q("SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC, id DESC", (f, t))

    def fill_expenses(self):
        rows = self.exp_rows(); sel = selected_id(self.exp_table); self.exp_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            self.exp_table.setItem(r, 0, cell(fa(x["date"]), data=x["id"])); self.exp_table.setItem(r, 1, cell(x["category"], Qt.AlignRight, bold=True))
            self.exp_table.setItem(r, 2, cell(money(x["amount"]), color="#B3402F", bold=True)); self.exp_table.setItem(r, 3, cell(x["note"] or "", Qt.AlignRight))
        select_id(self.exp_table, sel)
        self.exp_total.setText(f"جمع هزینه‌های بازه: {money(sum(x['amount'] for x in rows))} {self.win.cur}")

    def exp_add(self):
        d = ExpenseDialog(self, self.exp_cats())
        if d.exec(): self.db.x("INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)", d.values()); self.refresh(); self.win.toast("هزینه ثبت شد.")

    def exp_edit(self, *_):
        eid = selected_id(self.exp_table)
        if not eid: return self.win.toast("یک هزینه را انتخاب کنید.")
        d = ExpenseDialog(self, self.exp_cats(), self.db.q("SELECT * FROM expenses WHERE id=?", (eid,))[0])
        if d.exec(): self.db.x("UPDATE expenses SET date=?,category=?,amount=?,note=? WHERE id=?", d.values() + (eid,)); self.refresh(); self.win.toast("تغییرات ذخیره شد.")

    def exp_delete(self):
        eid = selected_id(self.exp_table)
        if eid and ask(self, "این هزینه حذف شود؟"): self.db.x("DELETE FROM expenses WHERE id=?", (eid,)); self.refresh()

    def exp_export(self):
        pth = pick_save_csv(self, "expenses.csv")
        if pth: write_csv(pth, ["تاریخ", "دسته", "مبلغ", "توضیح"], [[x["date"], x["category"], int(x["amount"]), x["note"] or ""] for x in self.exp_rows()]); self.win.toast("فایل اکسل ذخیره شد.")

    # ---- suppliers tab
    def build_suppliers(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 12, 0, 0); v.setSpacing(12)
        bar = QHBoxLayout(); self.sup_total = QLabel(); self.sup_total.setObjectName("bold"); bar.addWidget(self.sup_total); bar.addStretch()
        for text, kind, ic, fn in [("تأمین‌کننده‌ی جدید", "primary", "plus", self.sup_add), ("ویرایش", "", "edit", self.sup_edit),
                                   ("ثبت خرید", "", "truck", self.sup_purchase), ("پرداخت به تأمین‌کننده", "", "dollar", self.sup_pay),
                                   ("صورت‌حساب", "", "book", self.sup_statement), ("حذف", "danger", "trash", self.sup_delete)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        v.addLayout(bar)
        self.sup_table = make_table(["تأمین‌کننده", "تلفن", "وضعیت حساب"], 0); self.sup_table.doubleClicked.connect(self.sup_edit); v.addWidget(self.sup_table)
        self.tabs.addTab(w, "تأمین‌کنندگان")

    def fill_suppliers(self):
        rows = self.db.q("SELECT * FROM suppliers ORDER BY name"); bal = self.db.supplier_balances(); sel = selected_id(self.sup_table)
        self.sup_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            tx, cl = sup_balance_text(bal.get(x["id"], 0))
            self.sup_table.setItem(r, 0, cell(x["name"], Qt.AlignRight, x["id"], bold=True)); self.sup_table.setItem(r, 1, cell(fa(x["phone"])))
            self.sup_table.setItem(r, 2, cell(tx, color=cl, bold=True))
        select_id(self.sup_table, sel)
        self.sup_total.setText(f"جمع بدهی به تأمین‌کنندگان: {money(sum(b for b in bal.values() if b > 0))} {self.win.cur}")

    def need_sup(self):
        sid = selected_id(self.sup_table)
        if not sid: self.win.toast("یک تأمین‌کننده را انتخاب کنید.")
        return sid

    def sup_add(self):
        d = SupplierDialog(self)
        if d.exec(): self.db.x("INSERT INTO suppliers(name,phone) VALUES(?,?)", d.values()); self.refresh(); self.win.toast("تأمین‌کننده ذخیره شد.")

    def sup_edit(self, *_):
        sid = self.need_sup()
        if not sid: return
        d = SupplierDialog(self, self.db.q("SELECT * FROM suppliers WHERE id=?", (sid,))[0])
        if d.exec(): self.db.x("UPDATE suppliers SET name=?,phone=? WHERE id=?", d.values() + (sid,)); self.refresh()

    def sup_purchase(self):
        sid = self.need_sup()
        if not sid: return
        d = PurchaseDialog(self)
        if d.exec():
            amount, paid, date, note = d.values()
            self.db.x("INSERT INTO supplier_tx(supplier_id,kind,amount,date,note) VALUES(?,?,?,?,?)", (sid, "purchase", amount, date, note))
            if paid > 0: self.db.x("INSERT INTO supplier_tx(supplier_id,kind,amount,date,note) VALUES(?,?,?,?,?)", (sid, "payment", paid, date, "پرداخت هنگام خرید"))
            self.refresh(); self.win.toast("خرید ثبت شد.")

    def sup_pay(self):
        sid = self.need_sup()
        if not sid: return
        d = PaymentDialog(self, self.db.supplier_balances().get(sid, 0), "پرداخت به تأمین‌کننده")
        if d.exec():
            a, date, note = d.values()
            self.db.x("INSERT INTO supplier_tx(supplier_id,kind,amount,date,note) VALUES(?,?,?,?,?)", (sid, "payment", a, date, note))
            self.refresh(); self.win.toast("پرداخت ثبت شد.")

    def sup_statement(self):
        sid = self.need_sup()
        if sid: SupplierStatementDialog(self.win, sid).exec()

    def sup_delete(self):
        sid = self.need_sup()
        if not sid: return
        if self.db.q("SELECT 1 FROM supplier_tx WHERE supplier_id=?", (sid,)): return msg(self, "این تأمین‌کننده تراکنش ثبت‌شده دارد و حذف نمی‌شود.")
        if ask(self, "تأمین‌کننده حذف شود؟"): self.db.x("DELETE FROM suppliers WHERE id=?", (sid,)); self.refresh()

    # ---- cash flow tab
    def build_cash(self):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 12, 0, 0); v.setSpacing(12)
        bar = QHBoxLayout(); self.cash_total = QLabel(); self.cash_total.setObjectName("bold"); bar.addWidget(self.cash_total); bar.addStretch()
        b = btn("اکسل", "", "download"); b.clicked.connect(self.cash_export); bar.addWidget(b); v.addLayout(bar)
        self.cash_table = make_table(["تاریخ", "شرح", "ورودی", "خروجی", "تراز بازه"], 1); v.addWidget(self.cash_table)
        self.tabs.addTab(w, "گردش وجوه")

    def cash_rows(self):
        f, t = self.rng(); q = self.db.q; ev = []
        for x in q("SELECT * FROM invoices WHERE paid>0 AND date BETWEEN ? AND ?", (f, t)):
            ev.append((x["date"], 0, x["id"], f"فروش — فاکتور {fa(x['number'])}" + (f" ({x['customer_name']})" if x["customer_name"] else ""), x["paid"], 0))
        for x in q("SELECT p.*, c.name FROM payments p LEFT JOIN customers c ON c.id=p.customer_id WHERE p.date BETWEEN ? AND ?", (f, t)):
            ev.append((x["date"], 1, x["id"], f"دریافتی از {x['name'] or 'مشتری'}" + (f" — {x['note']}" if x["note"] else ""), x["amount"], 0))
        for x in q("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (f, t)):
            ev.append((x["date"], 2, x["id"], f"هزینه — {x['category']}" + (f" ({x['note']})" if x["note"] else ""), 0, x["amount"]))
        for x in q("SELECT t.*, s.name FROM supplier_tx t LEFT JOIN suppliers s ON s.id=t.supplier_id WHERE t.kind='payment' AND t.date BETWEEN ? AND ?", (f, t)):
            ev.append((x["date"], 3, x["id"], f"پرداخت به {x['name'] or 'تأمین‌کننده'}" + (f" — {x['note']}" if x["note"] else ""), 0, x["amount"]))
        return sorted(ev)

    def fill_cash(self):
        ev = self.cash_rows(); self.cash_table.setRowCount(len(ev)); run = 0; tin = tout = 0
        for r, (d, _, _, desc, i, o) in enumerate(ev):
            run += i - o; tin += i; tout += o
            self.cash_table.setItem(r, 0, cell(fa(d))); self.cash_table.setItem(r, 1, cell(desc, Qt.AlignRight))
            self.cash_table.setItem(r, 2, cell(money(i) if i else "—", color="#3E7A4F" if i else None, bold=bool(i)))
            self.cash_table.setItem(r, 3, cell(money(o) if o else "—", color="#B3402F" if o else None, bold=bool(o)))
            self.cash_table.setItem(r, 4, cell(money(run), color="#3E7A4F" if run >= 0 else "#B3402F", bold=True))
        self.cash_total.setText(f"ورودی {money(tin)}   •   خروجی {money(tout)}   •   خالص {money(tin - tout)} {self.win.cur}")

    def cash_export(self):
        pth = pick_save_csv(self, "cashflow.csv")
        if pth:
            run = 0; rows = []
            for d, _, _, desc, i, o in self.cash_rows(): run += i - o; rows.append([d, desc, int(i), int(o), int(run)])
            write_csv(pth, ["تاریخ", "شرح", "ورودی", "خروجی", "تراز بازه"], rows); self.win.toast("فایل اکسل ذخیره شد.")

    # ---- refresh all
    def refresh(self):
        f, t = self.rng()
        ok = bool(f and t)
        self.range_lbl.setText(f"بازه: از {fa(f)} تا {fa(t)}" if ok else "بازه‌ی دلخواه را به شکل ۱۴۰۵/۰۱/۰۱ وارد کنید.")
        st = self.db.finance(f or "9999/99/99", t or "0000/00/00") if ok else self.db.finance("9999/99/99", "0000/00/00")
        cur = self.win.cur
        recv = sum(v for v in self.db.balances().values() if v > 0); pay = sum(v for v in self.db.supplier_balances().values() if v > 0)
        vals = dict(sales=st["sales"], received=st["received"], expenses=st["expenses"], cash_net=st["cash_net"], gross=st["gross"], net=st["net"], recv=recv, pay=pay)
        for key, (lab, unit) in self.cards.items():
            v = vals[key]; lab.setText(money(v)); unit.setText(cur)
            if key in ("cash_net", "net", "gross"):
                lab.setStyleSheet(f"font-size:22px;font-weight:bold;background:transparent;color:{'#3E7A4F' if v >= 0 else '#B3402F'}")
        if st["nocost"] > 0:
            self.warn.setText(f"توجه: برای کالاهایی به ارزش {money(st['nocost'])} {cur} از فروش این بازه «قیمت خرید» ثبت نشده، پس سود واقعی‌تر از عدد بالاست. "
                              "در بخش «کالاها» قیمت خرید را وارد کنید تا سود دقیق‌تر شود."); self.warn.show()
        else: self.warn.hide()
        d = jdatetime.date.today(); y, m = d.year, d.month; keys = []
        for _ in range(6):
            keys.append((y, m)); m -= 1
            if m == 0: m, y = 12, y - 1
        keys.reverse()
        sales = {r["m"]: r["s"] for r in self.db.q("SELECT substr(date,1,7) m, SUM(total) s FROM invoices GROUP BY m")}
        exps = {r["m"]: r["s"] for r in self.db.q("SELECT substr(date,1,7) m, SUM(amount) s FROM expenses GROUP BY m")}
        ks = [f"{y:04d}/{m:02d}" for y, m in keys]
        self.chart.set_data([MONTHS[m - 1] for y, m in keys], [sales.get(k, 0) for k in ks], [exps.get(k, 0) for k in ks])
        self.fill_expenses(); self.fill_suppliers(); self.fill_cash()


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.setObjectName("page"); self.win, self.db = win, win.db
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 26, 30, 26); lay.setSpacing(16)
        lay.addWidget(h1("تنظیمات"))
        cols = QHBoxLayout(); cols.setSpacing(20)
        c1 = card(); f1 = QFormLayout(c1); f1.setContentsMargins(22, 20, 22, 20); f1.setSpacing(12)
        self.f = {k: QLineEdit() for k in ("shop_name", "shop_sub", "phone", "address", "footer", "currency")}
        for label, k in [("نام فروشگاه", "shop_name"), ("زیرعنوان", "shop_sub"), ("تلفن", "phone"), ("آدرس", "address"),
                         ("متن پایین فاکتور", "footer"), ("واحد پول", "currency")]: f1.addRow(label, self.f[k])
        self.printer = QComboBox(); self.printer.addItem("چاپگر پیش‌فرض ویندوز", "")
        for n in QPrinterInfo.availablePrinterNames(): self.printer.addItem(n, n)
        self.pw = NumEdit(72, dec=True); self.copies = NumEdit(1); self.dx = NumEdit(0, dec=True)
        f1.addRow("چاپگر", self.printer); f1.addRow("عرض قابل چاپ (mm)", self.pw)
        f1.addRow("جابه‌جایی افقی (mm)", self.dx); f1.addRow("", cap("منفی = محتوا به چپ می‌رود، مثبت = به راست. مثلاً ‎-۴"))
        f1.addRow("تعداد نسخه‌ی چاپ", self.copies)
        cols.addWidget(c1, 3)
        c2 = card(); f2 = QVBoxLayout(c2); f2.setContentsMargins(22, 20, 22, 20); f2.setSpacing(12)
        t = QLabel("امکانات فاکتور"); t.setObjectName("h2"); f2.addWidget(t)
        f2.addWidget(cap("هرکدام را خواستید روشن یا خاموش کنید؛ روی هر فاکتور هم می‌توانید جداگانه تیکش را بردارید."))
        self.tax_on, self.disc_on, self.ship_on = QCheckBox("مالیات"), QCheckBox("تخفیف"), QCheckBox("هزینه ارسال")
        self.tax_pct = NumEdit(10, dec=True); self.tax_pct.setFixedWidth(80)
        r = QHBoxLayout(); r.addWidget(self.tax_on); r.addStretch(); r.addWidget(cap("درصد مالیات")); r.addWidget(self.tax_pct)
        f2.addLayout(r); f2.addWidget(self.disc_on); f2.addWidget(self.ship_on)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color:#E3E5DF"); f2.addWidget(line)
        t2 = QLabel("شماره‌گذاری فاکتور"); t2.setObjectName("h2"); f2.addWidget(t2)
        self.next_no = NumEdit(1); f2.addWidget(cap("شماره‌ی فاکتور بعدی (برای شروع دوباره، هر عددی بگذارید)")); f2.addWidget(self.next_no)
        f2.addStretch(); cols.addWidget(c2, 2); lay.addLayout(cols)
        bar = QHBoxLayout()
        for text, kind, ic, fn in [("ذخیره تنظیمات", "primary", "save", self.save), ("چاپ آزمایشی", "", "printer", self.test_print), ("چاپ تست تراز", "", "sliders", self.test_align),
                                   ("پشتیبان‌گیری", "", "download", self.backup), ("بازیابی از پشتیبان", "", "upload", self.restore)]:
            b = btn(text, kind, ic); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(); lay.addLayout(bar)
        self.path = cap(f"محل ذخیره‌ی اطلاعات: {DATA}   (پشتیبان خودکار روزانه در پوشه‌ی backups)"); self.path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.path); lay.addStretch()

    def refresh(self):
        s = self.db.settings()
        for k, w in self.f.items(): w.setText(s[k])
        self.printer.setCurrentIndex(max(self.printer.findData(s["printer"]), 0)); self.pw.setValue(float(s["print_w"])); self.dx.setValue(float(s["print_dx"])); self.copies.setValue(int(s["copies"]))
        self.tax_on.setChecked(s["tax_on"] == "1"); self.disc_on.setChecked(s["disc_on"] == "1"); self.ship_on.setChecked(s["ship_on"] == "1")
        self.tax_pct.setValue(float(s["tax_pct"])); self.next_no.setValue(int(s["next_no"]))

    def save(self):
        for k, w in self.f.items(): self.db.set(k, w.text().strip())
        self.db.set("printer", self.printer.currentData() or ""); self.db.set("print_w", self.pw.value() or 72); self.db.set("print_dx", self.dx.value())
        self.db.set("copies", min(max(int(self.copies.value()), 1), 5))
        for k, w in (("tax_on", self.tax_on), ("disc_on", self.disc_on), ("ship_on", self.ship_on)): self.db.set(k, "1" if w.isChecked() else "0")
        self.db.set("tax_pct", self.tax_pct.value()); self.db.set("next_no", max(int(self.next_no.value()), 1))
        self.win.apply_settings(); self.win.toast("تنظیمات ذخیره شد.")

    def test_print(self):
        self.save(); s = self.db.settings()
        inv = dict(number=int(s["next_no"]), date=today(), time=now_time(), customer_id=None, customer_name="چاپ آزمایشی", subtotal=250000,
                   discount=0, shipping=0, tax=0, tax_pct=0, total=250000, paid=250000, prev_balance=0, note="")
        self.win.print_img(render_receipt(s, inv, [dict(name="قهوه اسپرسو", unit="بسته", qty=2, price=125000, total=250000)]), copies=1)

    def test_align(self):
        self.save(); self.win.print_img(calibration_image(self.db.settings()), copies=1)

    def backup(self):
        d = QFileDialog.getExistingDirectory(self, "پوشه‌ی پشتیبان را انتخاب کنید")
        if d: self.db.backup(Path(d)); self.win.toast("پشتیبان ذخیره شد.")

    def restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "فایل پشتیبان را انتخاب کنید", "", "Database (*.db)")
        if p and ask(self, "اطلاعات فعلی با این پشتیبان جایگزین می‌شود (قبلش از اطلاعات فعلی هم پشتیبان گرفته می‌شود). ادامه؟"):
            try: self.db.restore(Path(p))
            except Exception: return msg(self, "این فایل، پشتیبان معتبر این برنامه نیست.")
            self.win.apply_settings(); self.refresh(); self.win.toast("اطلاعات بازیابی شد.")

# ---------------------------------------------------------------- main window
QSS = """
* { font-family: "Vazirmatn","Tahoma"; font-size: 13px; color: #1B1F1C; }
QMainWindow, QDialog, QWidget#page { background: #F2F3EF; }
QToolTip { background: #1E2420; color: #fff; border: none; padding: 6px 10px; }
QFrame#side { background: #1E2420; }
QLabel#brand { color: #F3E9D2; font-size: 20px; font-weight: bold; }
QLabel#brandsub { color: #8D968F; font-size: 12px; }
QLabel#hint { color: #6F7871; font-size: 11px; }
QPushButton#nav { background: transparent; color: #B7BFB8; border: none; border-radius: 0; text-align: right; padding: 13px 24px; font-size: 14px; }
QPushButton#nav:hover { background: #272E29; color: #FFFFFF; }
QPushButton#nav:checked { background: #2E3631; color: #FFFFFF; font-weight: bold; border-right: 4px solid #D9A441; }
QLabel#h1 { font-size: 24px; font-weight: bold; }
QLabel#h2 { font-size: 16px; font-weight: bold; }
QLabel#cap { color: #6B726C; font-size: 12px; }
QLabel#big { font-size: 26px; font-weight: bold; color: #8A5A12; }
QLabel#total { font-size: 30px; font-weight: bold; color: #1E2420; padding: 6px 0 10px 0; }
QLabel#bold { font-weight: bold; font-size: 15px; }
QFrame#banner { background: #FBEFD2; border: 1px solid #E8CF94; border-radius: 10px; }
QLabel#bannerlbl { color: #6B4A0E; font-weight: bold; background: transparent; }
QFrame#card { background: #FFFFFF; border: 1px solid #E1E4DC; border-radius: 12px; }
QFrame#card QLabel { background: transparent; }
QFrame#card QTableWidget { border: none; border-radius: 0; }
QLineEdit, QComboBox { background: #FFFFFF; border: 1px solid #D3D7CE; border-radius: 8px; padding: 7px 10px; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border: 1.5px solid #B8791F; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: #fff; border: 1px solid #D3D7CE; selection-background-color: #F6EBD3; selection-color: #1B1F1C; outline: 0; }
QPushButton { background: #FFFFFF; border: 1px solid #CDD1C7; border-radius: 8px; padding: 9px 16px; }
QPushButton:hover { background: #F6F7F3; border-color: #BFC4B8; }
QPushButton:pressed { background: #ECEEE7; }
QPushButton#primary { background: #B8791F; color: #FFFFFF; border: none; font-weight: bold; }
QPushButton#primary:hover { background: #A56A17; }
QPushButton#danger { color: #B3402F; }
QPushButton#link { border: none; background: transparent; color: #8A5A12; padding: 0; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1.5px solid #BFC4B8; border-radius: 5px; background: #fff; }
QCheckBox::indicator:checked { background: #B8791F; border-color: #B8791F; image: none; }
QTableWidget { background: #FFFFFF; border: 1px solid #E1E4DC; border-radius: 12px; selection-background-color: #F6EBD3; selection-color: #1B1F1C; outline: 0; }
QTableWidget::item { border-bottom: 1px solid #EEF0EA; padding: 0 8px; }
QHeaderView::section { background: #F7F8F4; border: none; border-bottom: 1px solid #E1E4DC; padding: 10px; font-weight: bold; color: #5B625C; }
QStatusBar { background: #F2F3EF; } QStatusBar QLabel { color: #3E7A4F; font-weight: bold; }
QScrollBar:vertical { width: 10px; background: transparent; } QScrollBar::handle:vertical { background: #C8CCC2; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel#dev { color: #8D968F; font-size: 11px; }
QPushButton#sidelink { background: transparent; border: none; color: #8D968F; text-align: right; padding: 8px 24px; font-size: 12px; }
QPushButton#sidelink:hover { color: #FFFFFF; }
QPushButton#seg { background: #FFFFFF; border: 1px solid #CDD1C7; border-radius: 8px; padding: 8px 16px; margin-right: 6px; }
QPushButton#seg:checked { background: #1E2420; color: #FFFFFF; border-color: #1E2420; font-weight: bold; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; padding: 10px 22px; color: #5B625C; font-size: 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #8A5A12; font-weight: bold; border-bottom: 2px solid #B8791F; }
QTabBar::tab:hover { color: #1B1F1C; }
QLabel#warn { background: #FBEFD2; border: 1px solid #E8CF94; border-radius: 10px; color: #6B4A0E; padding: 10px 14px; }
"""

class Main(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("فاکتور فروش"); self.resize(1320, 820); self.setMinimumSize(1120, 700)
        root = QWidget(); lay = QHBoxLayout(root); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(228)
        sl = QVBoxLayout(side); sl.setContentsMargins(0, 28, 0, 18); sl.setSpacing(2)
        self.brand = QLabel(); self.brand.setObjectName("brand"); self.brand.setContentsMargins(24, 0, 24, 0); self.brand.setWordWrap(True)
        self.brandsub = QLabel(); self.brandsub.setObjectName("brandsub"); self.brandsub.setContentsMargins(24, 0, 24, 22)
        sl.addWidget(self.brand); sl.addWidget(self.brandsub)
        self.stack = QStackedWidget()
        self.pages = [DashboardPage(self), InvoicePage(self), InvoicesPage(self), CustomersPage(self), ProductsPage(self), FinancePage(self), SettingsPage(self)]
        self.navs = []
        for i, (t, ic, p) in enumerate(zip(["داشبورد", "فاکتور جدید", "فاکتورها", "مشتریان", "کالاها", "مدیریت مالی", "تنظیمات"],
                                           ["home", "plus", "file", "users", "box", "chart", "sliders"], self.pages)):
            b = QPushButton(t); b.setObjectName("nav"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.setIcon(nav_icon(ic)); b.setIconSize(QSize(20, 20)); b.setToolTip(f"Ctrl+{i + 1}")
            b.clicked.connect(lambda _, i=i: self.go(i)); sl.addWidget(b); self.navs.append(b); self.stack.addWidget(p)
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.go(i))
        sl.addStretch()
        hint = QLabel("Ctrl+S ذخیره\nCtrl+P ذخیره و چاپ\nF2 جستجوی کالا"); hint.setObjectName("hint"); hint.setContentsMargins(24, 0, 24, 0); sl.addWidget(hint)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#2E3631"); wrap = QVBoxLayout(); wrap.setContentsMargins(24, 12, 24, 8); wrap.addWidget(sep); sl.addLayout(wrap)
        dev = QLabel(f"طراحی و توسعه<br><span style='color:#E8DDC4;font-size:13px;font-weight:bold'>{DEVELOPER['name']}</span>")
        dev.setObjectName("dev"); dev.setContentsMargins(24, 0, 24, 0); sl.addWidget(dev)
        mail = QLabel(f"<a href='mailto:{DEVELOPER['email']}' style='color:#D9A441;text-decoration:none'>{DEVELOPER['email']}</a>")
        mail.setObjectName("dev"); mail.setOpenExternalLinks(True); mail.setContentsMargins(24, 2, 24, 0); mail.setTextInteractionFlags(Qt.TextBrowserInteraction); sl.addWidget(mail)
        about = QPushButton("درباره‌ی برنامه"); about.setObjectName("sidelink"); about.setCursor(Qt.PointingHandCursor); about.setIcon(ico("info", "#8D968F", 16))
        about.clicked.connect(lambda: AboutDialog(self).exec()); sl.addWidget(about)
        lay.addWidget(side); lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.status = QLabel(""); self.statusBar().addPermanentWidget(self.status, 1)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=lambda: self.on_invoice_page(lambda: self.pages[1].save(False)))
        QShortcut(QKeySequence("Ctrl+P"), self, activated=lambda: self.on_invoice_page(lambda: self.pages[1].save(True)))
        QShortcut(QKeySequence("F2"), self, activated=lambda: (self.go(1), self.pages[1].prod.setFocus()))
        self.apply_settings(); self.go(1)

    def on_invoice_page(self, fn):
        if self.stack.currentIndex() == 1: fn()

    def apply_settings(self):
        s = self.db.settings(); self.cur = s["currency"]
        self.brand.setText(s["shop_name"]); self.brandsub.setText(s["shop_sub"])

    def go(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.navs): b.setChecked(k == i)
        self.pages[i].refresh()

    def show_invoices(self, name):
        self.go(2); self.pages[2].search.setText(name)

    def edit_invoice(self, iid, copy=False):
        self.go(1); self.pages[1].load_invoice(iid, copy)

    def toast(self, text):
        self.status.setText(text); QTimer.singleShot(4500, lambda: self.status.setText(""))

    def invoice_image(self, iid):
        inv = dict(self.db.q("SELECT * FROM invoices WHERE id=?", (iid,))[0])
        items = [dict(r) for r in self.db.q("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (iid,))]
        return render_receipt(self.db.settings(), inv, items)

    def print_invoice(self, iid): self.print_img(self.invoice_image(iid))

    def print_img(self, img, copies=None):
        s = self.db.settings()
        n = copies or int(s["copies"] or 1)
        for _ in range(n):
            if not print_image(img, s["printer"], float(s["print_w"] or 72), float(s["print_dx"] or 0)):
                return msg(self, "چاپگر پیدا نشد یا در دسترس نیست.\nاتصال و روشن بودن پرینتر را بررسی کنید و در «تنظیمات» چاپگر را انتخاب کنید.", "خطا در چاپ")
        self.toast("فاکتور به چاپگر ارسال شد.")


def excepthook(t, v, tb):
    text = "".join(traceback.format_exception(t, v, tb))
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "error.log", "a", encoding="utf-8") as f: f.write(f"\n[{datetime.datetime.now()}]\n{text}")
    except Exception: pass
    try: msg(None, f"مشکلی پیش آمد:\n{v}\n\nجزئیات در این فایل ذخیره شد:\n{DATA / 'error.log'}", "خطا")
    except Exception: pass

def setup_app(app):
    app.setLayoutDirection(Qt.RightToLeft)
    load_fonts()
    qss = QSS
    try:   # تیک داخل چک‌باکس‌ها
        chk = DATA / "cache" / "check.png"; chk.parent.mkdir(parents=True, exist_ok=True)
        _pix("check", "#FFFFFF", 7, 3.4).save(str(chk))
        qss = QSS.replace("image: none;", f"image: url({chk.as_posix()});")
    except Exception: pass
    app.setFont(QFont(FONT, 10)); app.setStyleSheet(qss); app.setWindowIcon(app_icon())

def main():
    if "--version" in sys.argv:
        print(APP_VERSION); return
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    setup_app(app)
    db = DB(DATA / "shop.db")
    try: db.backup(DATA / "backups")
    except Exception: pass
    w = Main(db); w.show()
    if os.environ.get("SHOP_SMOKETEST"): QTimer.singleShot(1500, app.quit)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
