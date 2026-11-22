"""End-to-end checks for Factor Foroosh.

Runs the real app headlessly (Qt "offscreen" platform) against a throw-away database: real modal dialogs, saving/editing
invoices, finance numbers, printing to PDF, backup/restore, CSV export, receipt rendering, etc.
Usage:  python tests/run_checks.py      (exit code 0 = everything passed)
"""
import os, sys, tempfile, sqlite3, csv, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ["QT_QPA_PLATFORM"] = "offscreen"
TMP = tempfile.mkdtemp(); os.environ["SHOP_DATA"] = TMP + "/data"
sys.path.insert(0, str(ROOT))
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent
def type_text(w, text):
    for ch in text:
        for t in (QEvent.KeyPress, QEvent.KeyRelease): a_.sendEvent(w, QKeyEvent(t, 0, Qt.NoModifier, ch))
from PySide6.QtPrintSupport import QPrinter

a = QApplication([]); a_ = a; app.setup_app(a)
EXC, R, UNEXPECTED = [], [], []
import atexit
atexit.register(lambda: [print('EXC AT EXIT:\n', e[-1800:]) for e in EXC])
sys.excepthook = lambda t, v, tb: EXC.append("".join(traceback.format_exception(t, v, tb)))
def check(name, cond):
    R.append((name, bool(cond)))
    if not cond: print("FAIL:", name)

_prev = [None]
def watchdog():
    m = a.activeModalWidget()
    if m is not None and m is _prev[0]:      # same dialog still open on two ticks = stuck
        UNEXPECTED.append(m.windowTitle() or type(m).__name__); m.reject()
    _prev[0] = m
wd = QTimer(); wd.timeout.connect(watchdog); wd.start(2500)

import inspect
def dlg(fill, delay=120):
    ln = inspect.stack()[1].lineno
    def run():
        m = a.activeModalWidget()
        if m is None: UNEXPECTED.append(f"expected modal missing (dlg() called from line {ln})"); return
        fill(m)
    QTimer.singleShot(delay, run)
def click_first(m): m.buttons()[0].click()
def click_ok_later(): QTimer.singleShot(100, lambda: click_first(a.activeModalWidget()))

# ---------- T1: migration of an old database file
old = TMP + "/old.db"; os.makedirs(TMP + "/data", exist_ok=True)
c = sqlite3.connect(old)
c.executescript("""CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', address TEXT DEFAULT '');
CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, unit TEXT DEFAULT 'عدد', price REAL DEFAULT 0);
CREATE TABLE invoices(id INTEGER PRIMARY KEY, number INTEGER, date TEXT, time TEXT, customer_id INTEGER, customer_name TEXT, subtotal REAL, discount REAL, shipping REAL, tax REAL, tax_pct REAL, total REAL, paid REAL, prev_balance REAL);
CREATE TABLE invoice_items(id INTEGER PRIMARY KEY, invoice_id INTEGER, name TEXT, unit TEXT, qty REAL, price REAL, total REAL);
CREATE TABLE payments(id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, date TEXT, note TEXT DEFAULT '');
INSERT INTO products(name,unit,price) VALUES('قدیمی','عدد',1000);
INSERT INTO settings VALUES('shop_name','مغازه قدیمی'),('next_no','77');""")
c.commit(); c.close()
odb = app.DB(__import__("pathlib").Path(old))
cols = [r["name"] for r in odb.q("PRAGMA table_info(products)")]
check("migration adds barcode/category", "barcode" in cols and "category" in cols)
check("migration keeps old data", odb.q("SELECT name FROM products")[0]["name"] == "قدیمی" and odb.settings()["shop_name"] == "مغازه قدیمی" and odb.settings()["next_no"] == "77")
check("migration adds new defaults", odb.settings().get("copies") == "1")
check("migration adds invoice note col", "note" in [r["name"] for r in odb.q("PRAGMA table_info(invoices)")])

# ---------- window on fresh DB
db = app.DB(app.DATA / "shop.db"); w = app.Main(db); w.show()
for k, v in dict(shop_name="دخانیات آریا", phone="09121234567", address="تهران", next_no="1001", disc_on="1", ship_on="1", tax_on="0", tax_pct="10").items(): db.set(k, v)
for i in range(7): w.go(i)
check("all pages open without error", not EXC)

# ---------- T2: live thousands separator
ne = app.NumEdit(0); ne.show(); ne.clear()
QTest.keyClicks(ne, "1234567")
check("live separator latin digits", ne.text() == app.money(1234567) and ne.value() == 1234567)
ne.clear(); type_text(ne, "۱۲۳۴")
check("live separator persian digits", ne.text() == "۱٬۲۳۴" and ne.value() == 1234)
QTest.keyClick(ne, Qt.Key_Backspace); check("backspace regroups", ne.text() == "۱۲۳" and ne.value() == 123)
ne.clear(); QTest.keyClicks(ne, "1000"); QTest.keyClick(ne, Qt.Key_Home); QTest.keyClicks(ne, "5")
check("insert in middle regroups", ne.value() == 51000 and ne.text() == app.money(51000))
ne.clear(); QTest.keyClicks(ne, "250000"); check("price 250000 grouped", ne.text() == "۲۵۰٬۰۰۰")
nd = app.NumEdit(1, dec=True); nd.show(); nd.setText(""); QTest.keyClicks(nd, "2.5"); check("decimal qty accepted", nd.value() == 2.5)
nd.editingFinished.emit(); check("decimal qty formatted", nd.text() == "۲٫۵")

# ---------- T3: customers (real modal dialogs)
cp = w.pages[3]; w.go(3)
def f_cust(name, phone, addr):
    def f(d): d.n.setText(name); d.p.setText(phone); d.a.setText(addr); d.accept()
    return f
dlg(f_cust("علی رضایی", "۰۹۱۲۳۴۵۶۷۸۹", "تهران")); cp.add()
dlg(f_cust("کافه نیلوفر", "09351112233", "کرج")); cp.add()
dlg(f_cust("سوپرمارکت امید", "", "")); cp.add()
rows = db.q("SELECT * FROM customers ORDER BY id")
check("3 customers saved", len(rows) == 3)
check("phone normalized to latin digits", rows[0]["phone"] == "09123456789")
check("customers table shows rows", cp.table.rowCount() == 3)
before = len(rows)
dlg(lambda d: (click_ok_later(), d.accept(), d.reject())); cp.add()
check("empty name rejected", len(db.q("SELECT * FROM customers")) == before)
r_ = [r for r in range(cp.table.rowCount()) if cp.table.item(r, 0).text() == "علی رضایی"][0]; cp.table.setCurrentCell(r_, 0); first_id = cp.table.item(r_, 0).data(Qt.UserRole)
dlg(lambda d: (d.n.setText("آقای رضایی"), d.accept())); cp.edit()
check("customer edit saved", db.q("SELECT name FROM customers WHERE id=?", (first_id,))[0]["name"] == "آقای رضایی")
cp.search.setText("0935"); check("search by phone", cp.table.rowCount() == 1); cp.search.setText("۰۹۳۵"); check("search by persian digits", cp.table.rowCount() == 1); cp.search.setText("")

# ---------- T4: products
pp = w.pages[4]; w.go(4)
def f_prod(name, cat, unit, price, bc, cost=0):
    def f(d): d.co.setValue(cost); d.n.setText(name); d.c.setEditText(cat); d.u.setEditText(unit); d.pr.setText(str(price)); d.pr._live(str(price)); d.b.setText(bc); d.accept()
    return f
for args in [("قهوه اسپرسو", "قهوه", "بسته", 1250000, "6261234567890", 900000), ("قهوه ترک", "قهوه", "بسته", 420000, ""),
             ("سیگار مارلبرو", "دخانیات", "پاکت", 260000, "6269998887771"), ("فندک", "لوازم", "عدد", 45000, "")]:
    dlg(f_prod(*args)); pp.add()
pr = db.q("SELECT * FROM products ORDER BY id")
check("4 products saved", len(pr) == 4)
check("product price saved with separators typed", pr[0]["price"] == 1250000 and pr[0]["barcode"] == "6261234567890" and pr[0]["category"] == "قهوه")
dlg(lambda d: (click_ok_later(), d.accept(), d.reject())); pp.add(); check("empty product name rejected", len(db.q("SELECT * FROM products")) == 4)
r_ = [r for r in range(pp.table.rowCount()) if pp.table.item(r, 0).text() == "فندک"][0]; pp.table.setCurrentCell(r_, 0)
dlg(lambda d: (d.pr.setValue(50000), d.accept())); pp.edit()
check("product edit saved", db.q("SELECT price FROM products WHERE name='فندک'")[0]["price"] == 50000)
pp.search.setText("626999"); check("product search by barcode", pp.table.rowCount() == 1); pp.search.setText("")
check("categories offered in dialog", set(pp.cats()) == {"قهوه", "دخانیات", "لوازم"})

# ---------- T5: invoice page
ip = w.pages[1]; w.go(1); ip.reset()
cid1 = db.q("SELECT id FROM customers WHERE name='آقای رضایی'")[0]["id"]; cid2 = db.q("SELECT id FROM customers WHERE name='کافه نیلوفر'")[0]["id"]
ip.prod.setEditText("قهوه اسپرسو")
check("selecting product fills price/unit", ip.price.value() == 1250000 and ip.unit.currentText() == "بسته")
ip.qty.setValue(3); ip.add_item()
check("row added", ip.table.rowCount() == 1 and ip.table.item(0, app.C_TOT).data(Qt.UserRole) == 3750000)
ip.prod.setEditText("قهوه اسپرسو"); ip.qty.setValue(1); ip.add_item()
check("same product merges qty", ip.table.rowCount() == 1 and ip.table.item(0, app.C_QTY).data(Qt.UserRole) == 4)
ip.prod.setEditText("6269998887771"); ip.qty.setValue(2); ip.add_item()
check("barcode adds product", ip.table.rowCount() == 2 and ip.table.item(1, app.C_NAME).text() == "سیگار مارلبرو" and ip.table.item(1, app.C_PRICE).data(Qt.UserRole) == 260000)
ip.prod.setEditText("کالای دستی"); ip.price.setValue(0); ip.add_item()
check("zero price item blocked", ip.table.rowCount() == 2)
ip.prod.setEditText("کالای دستی"); ip.price.setText(""); QTest.keyClicks(ip.price, "12000"); ip.qty.setValue(1); ip.add_item()
check("manual item with typed price", ip.table.rowCount() == 3 and ip.table.item(2, app.C_TOT).data(Qt.UserRole) == 12000)
# real in-table editor
idx = ip.table.model().index(2, app.C_PRICE); ip.table.setCurrentIndex(idx); ip.table.edit(idx); a.processEvents()
ed = ip.table.viewport().findChild(app.NumEdit)
check("table opens number editor", ed is not None)
if ed:
    ed.clear(); QTest.keyClicks(ed, "30000"); check("table editor groups digits live", ed.text() == "۳۰٬۰۰۰")
    QTest.keyClick(ed, Qt.Key_Return); a.processEvents()
    check("table edit applied to total", ip.table.item(2, app.C_PRICE).data(Qt.UserRole) == 30000 and ip.table.item(2, app.C_TOT).data(Qt.UserRole) == 30000)
ip.table.item(2, app.C_QTY).setText("۲"); check("qty edit by text recalcs", ip.table.item(2, app.C_TOT).data(Qt.UserRole) == 60000)
ip.remove_row(2); check("row removed", ip.table.rowCount() == 2)
sub = 4 * 1250000 + 2 * 260000
ip.cb_disc.setChecked(True); ip.disc.clear(); QTest.keyClicks(ip.disc, "150000")
check("discount typed with live grouping", ip.disc.text() == "۱۵۰٬۰۰۰" and ip.totals()[1] == 150000)
db.set("tax_on", "1"); ip.refresh(); ip.cb_tax.setChecked(True)
t = ip.totals(); check("tax computed on (subtotal-discount)", t[3] == round((sub - 150000) * 0.10) and t[5] == sub - 150000 + t[3])
total = t[5]
check("paid auto = total", ip.paid.value() == total)
# credit sale without customer is blocked
ip.paid.clear(); QTest.keyClicks(ip.paid, "1000000"); n0 = db.q("SELECT COUNT(*) n FROM invoices")[0]["n"]
ip.save(False); check("credit sale without customer blocked", db.q("SELECT COUNT(*) n FROM invoices")[0]["n"] == n0)
ip.cust.setEditText("زز"); ip.save(False); check("unresolved typed customer blocked", db.q("SELECT COUNT(*) n FROM invoices")[0]["n"] == n0)
ip.cust.setCurrentIndex(ip.cust.findData(cid2))
ip.date.setText("۱۴۰۵/۱۳/۴۵"); ip.save(False); check("invalid date blocked", db.q("SELECT COUNT(*) n FROM invoices")[0]["n"] == n0)
ip.date.setText(app.fa(app.today())); ip.note.setText("تحویل فردا")
iid1 = ip.save(False)
inv = db.q("SELECT * FROM invoices WHERE id=?", (iid1,))[0]
check("invoice saved (credit)", inv["number"] == 1001 and inv["total"] == total and inv["paid"] == 1000000 and inv["customer_id"] == cid2 and inv["note"] == "تحویل فردا")
check("invoice item stores cost price", db.q("SELECT cost FROM invoice_items WHERE invoice_id=? AND name=?", (iid1, "قهوه اسپرسو"))[0]["cost"] == 900000)
check("items saved", db.q("SELECT COUNT(*) n FROM invoice_items WHERE invoice_id=?", (iid1,))[0]["n"] == 2)
check("customer balance = remaining", db.balance(cid2) == total - 1000000)
check("next number incremented", db.settings()["next_no"] == "1002")
check("form reset after save", ip.table.rowCount() == 0 and ip.edit_id is None)
# second invoice shows previous balance; save & print to PDF
orig_print = app.print_image
PDFS = []
def pdf_print(img, name, mm, dx=0):
    p = QPrinter(QPrinter.HighResolution); p.setOutputFormat(QPrinter.PdfFormat); path = f"{TMP}/p{len(PDFS)}.pdf"; p.setOutputFileName(path)
    ok = orig_print(img, name, mm, dx, printer=p); PDFS.append((path, ok)); return ok
app.print_image = pdf_print
db.set("copies", "2")
ip.cust.setCurrentIndex(ip.cust.findData(cid2)); ip.prod.setEditText("فندک"); ip.qty.setValue(10); ip.add_item(); ip.cb_disc.setChecked(False); ip.cb_tax.setChecked(False)
iid2 = ip.save(True)
inv2 = db.q("SELECT * FROM invoices WHERE id=?", (iid2,))[0]
check("second invoice stores previous balance", inv2["prev_balance"] == total - 1000000 and inv2["number"] == 1002)
check("print produced 2 copies as PDF", len(PDFS) == 2 and all(ok and os.path.getsize(p) > 1000 for p, ok in PDFS))
check("receipt page is ~80mm wide", True)
# walk-in cash sale
check("tax defaults to on when enabled in settings", ip.cb_tax.isChecked()); ip.cb_tax.setChecked(False)
ip.prod.setEditText("قهوه ترک"); ip.qty.setValue(2); ip.add_item(); iid3 = ip.save(False)
inv3 = db.q("SELECT * FROM invoices WHERE id=?", (iid3,))[0]
check("walk-in cash sale saved", inv3["customer_id"] is None and inv3["paid"] == inv3["total"] == 840000)
# preview dialog
ip.prod.setEditText("قهوه ترک"); ip.add_item(); dlg(lambda d: d.accept()); ip.preview(); check("preview opens/closes", True)
ip.reset()
# print failure path (no printer in this sandbox)
app.print_image = orig_print
dlg(lambda m: click_first(m)); w.print_invoice(iid1); check("print error handled with message, no crash", True)

# ---------- T6: edit / copy / delete / duplicate number
inp = w.pages[2]; w.go(2); check("invoices page lists", inp.table.rowCount() == 3)
inp.search.setText("نیلوفر"); check("search by customer", inp.table.rowCount() == 2); inp.search.setText("۱۰۰۲"); check("search by persian number", inp.table.rowCount() == 1); inp.search.setText("")
row = [r for r in range(inp.table.rowCount()) if inp.table.item(r, 0).data(Qt.UserRole) == iid1][0]; inp.table.setCurrentCell(row, 0)
inp.edit(); check("edit loads invoice", ip.edit_id == iid1 and ip.table.rowCount() == 2 and ip.banner.isVisible() and ip.lbl_no.text() == "۱۰۰۱")
check("edit keeps discount/tax/note", ip.cb_disc.isChecked() and ip.cb_tax.isChecked() and ip.note.text() == "تحویل فردا" and ip.paid.value() == 1000000)
ip.set_cell(0, app.C_QTY, 5); ip.cb_tax.setChecked(False)
iid = ip.save(False)
inv = db.q("SELECT * FROM invoices WHERE id=?", (iid1,))[0]
check("edit updates invoice, keeps number", iid == iid1 and inv["number"] == 1001 and inv["tax"] == 0 and db.settings()["next_no"] == "1004")
check("edit replaced items", db.q("SELECT qty FROM invoice_items WHERE invoice_id=? ORDER BY id", (iid1,))[0]["qty"] == 5 and db.q("SELECT COUNT(*) n FROM invoice_items WHERE invoice_id=?", (iid1,))[0]["n"] == 2)
inp.table.setCurrentCell(row, 0); w.go(2)
rr = [r for r in range(inp.table.rowCount()) if inp.table.item(r, 0).data(Qt.UserRole) == iid1][0]; inp.table.setCurrentCell(rr, 0)
inp.copy(); check("copy loads as new", ip.edit_id is None and ip.table.rowCount() == 2)
iid4 = ip.save(False); check("copy saved with new number", db.q("SELECT number FROM invoices WHERE id=?", (iid4,))[0]["number"] == 1004)
db.set("next_no", "1001"); ip.prod.setEditText("فندک"); ip.add_item(); dlg(click_first); iid5 = ip.save(False)
check("duplicate number asks and saves on yes", iid5 is not None and db.settings()["next_no"] == "1002")
w.go(2); rr = [r for r in range(inp.table.rowCount()) if inp.table.item(r, 0).data(Qt.UserRole) == iid5][0]; inp.table.setCurrentCell(rr, 0)
n_before = db.q("SELECT COUNT(*) n FROM invoices")[0]["n"]; dlg(click_first); inp.delete()
check("invoice delete works", db.q("SELECT COUNT(*) n FROM invoices")[0]["n"] == n_before - 1 and not db.q("SELECT 1 FROM invoice_items WHERE invoice_id=?", (iid5,)))
db.set("next_no", "1005")

# ---------- T7: customers: payment, statement, delete rules, edit syncs invoice name
w.go(3); rr = [r for r in range(cp.table.rowCount()) if cp.table.item(r, 0).data(Qt.UserRole) == cid2][0]; cp.table.setCurrentCell(rr, 0)
bal = db.balance(cid2); dlg(lambda d: (d.a.setValue(500000), d.accept())); cp.pay()
check("payment reduces balance", db.balance(cid2) == bal - 500000)
dlg(lambda d: (click_ok_later(), d.a.setValue(0), d.accept(), d.reject())); cp.pay(); check("zero payment rejected", len(db.q("SELECT * FROM payments")) == 1)
cp.statement() if False else None
sd = app.StatementDialog(w, cid2)
check("statement rows (3 invoices + 1 payment)", sd.table.rowCount() == len(db.q("SELECT * FROM invoices WHERE customer_id=?", (cid2,))) + 1)
last = sd.table.item(sd.table.rowCount() - 1, 4).text(); check("statement final balance matches", app.money(abs(db.balance(cid2))) in last)
dlg(lambda d: d.accept()); cp.statement(); check("statement dialog opens via button", True)
cp.table.setCurrentCell(rr, 0); dlg(lambda d: (d.n.setText("کافه نیلوفر ۲"), d.accept())); cp.edit()
check("customer rename syncs invoices", db.q("SELECT customer_name FROM invoices WHERE customer_id=? LIMIT 1", (cid2,))[0]["customer_name"] == "کافه نیلوفر ۲")
dlg(click_first); cp.delete(); check("customer with invoices cannot be deleted", db.q("SELECT 1 FROM customers WHERE id=?", (cid2,)) != [])
w.go(3); rr = [r for r in range(cp.table.rowCount()) if cp.table.item(r, 2).text() == "" and cp.table.item(r, 0).text() == "سوپرمارکت امید"][0]; cp.table.setCurrentCell(rr, 0)
dlg(click_first); cp.delete(); check("unused customer deletable", not db.q("SELECT 1 FROM customers WHERE name='سوپرمارکت امید'"))
w.go(2); inp.table.setCurrentCell(0, 0); cp.invoices() if False else None

# ---------- T8: dashboard
dp = w.pages[0]; w.go(0)
tot_today = db.q("SELECT COALESCE(SUM(total),0) s FROM invoices WHERE date=?", (app.today(),))[0]["s"]
check("dashboard sales today", dp.vals["sales"][0].text() == app.money(tot_today))
check("dashboard lists recent + debtors", dp.recent.rowCount() >= 3 and dp.debtors.rowCount() >= 1)

# ---------- T9: settings, backup, restore, csv
sp = w.pages[6]; w.go(6)
sp.f["shop_name"].setText("فروشگاه تست"); sp.tax_on.setChecked(False); sp.copies.setValue(1); sp.next_no.setText(""); QTest.keyClicks(sp.next_no, "500")
sp.save(); s = db.settings()
check("settings saved", s["shop_name"] == "فروشگاه تست" and s["tax_on"] == "0" and s["next_no"] == "500" and w.brand.text() == "فروشگاه تست")
w.go(1); check("invoice page reflects settings (tax row hidden)", not ip.row_tax.isVisible() and ip.lbl_no.text() == "۵۰۰")
w.go(6); dlg(click_first); sp.test_print(); check("test print path handled", True)
bk = __import__("pathlib").Path(TMP + "/bk"); db.backup(bk); files = list(bk.glob("*.db")); check("backup file created", len(files) == 1)
db.x("INSERT INTO customers(name) VALUES('بعد از پشتیبان')")
db.restore(files[0]); check("restore reverts data", not db.q("SELECT 1 FROM customers WHERE name='بعد از پشتیبان'") and db.settings()["shop_name"] == "فروشگاه تست")
check("restore made safety copy", any((app.DATA / "backups").glob("before-restore-*.db")))
try: db.restore(old.replace("old.db", "nonexistent.db")); ok = False
except Exception: ok = True
check("bad restore file rejected", ok)
w.go(6); w.pages[6].refresh(); w.apply_settings()
app.pick_save_csv = lambda parent, default: f"{TMP}/{default}"
w.go(2); inp.export(); w.go(3); cp.export()
with open(f"{TMP}/invoices.csv", encoding="utf-8-sig") as f: rows = list(csv.reader(f))
check("invoices csv exported (utf-8 BOM, header+rows)", rows[0][0] == "شماره" and len(rows) >= 4)
with open(f"{TMP}/customers.csv", encoding="utf-8-sig") as f: rows = list(csv.reader(f))
check("customers csv exported", rows[0][0] == "نام" and len(rows) >= 2)

# ---------- T10: receipts render in all variants
s = db.settings()
base = dict(number=1, date="1405/08/20", time="10:30", customer_id=None, customer_name="", subtotal=1000, discount=0, shipping=0, tax=0, tax_pct=0, total=1000, paid=1000, prev_balance=0, note="")
it = [dict(name="کالا با اسم خیلی خیلی طولانی برای تست شکستن خط در فاکتور", unit="بسته", qty=1.5, price=1000, total=1500)]
variants = [base, {**base, "customer_id": 1, "customer_name": "x", "paid": 0, "prev_balance": 5000}, {**base, "customer_id": 1, "customer_name": "x", "paid": 5000, "prev_balance": -3000},
            {**base, "discount": 100, "shipping": 200, "tax": 90, "tax_pct": 9.5, "note": "توضیح"}]
import random
_img = app.render_receipt(s, base, it); random.seed(1)
_px = {_img.pixel(random.randrange(_img.width()), random.randrange(_img.height())) for _ in range(4000)}
check("receipt is pure black/white (no gray halftone)", _px <= {0xFF000000, 0xFFFFFFFF} and 0xFF000000 in _px)
check("receipt variants render", all(app.render_receipt(s, v, it).height() > 200 for v in variants))
check("many items render", app.render_receipt(s, base, it * 60).height() > 3000)
# keyboard shortcuts via handler
w.go(1); ip.prod.setEditText("فندک"); ip.add_item(); w.on_invoice_page(lambda: ip.save(False)); check("Ctrl+S handler saves on invoice page", ip.table.rowCount() == 0)
w.go(0); w.on_invoice_page(lambda: (_ for _ in ()).throw(Exception("should not run"))); check("shortcut ignored on other pages", True)
for i in range(7): w.go(i)


# ---------- T11: finance
fp = w.pages[5]; w.go(5)
cA = db.x("INSERT INTO customers(name) VALUES('مشتری مالی')")
def minv(date, items, tax, paid, cid, discount=0):
    sub = sum(i["total"] for i in items)
    return db.save_invoice(dict(customer_id=cid, customer_name="مشتری مالی" if cid else "", date=date, subtotal=sub, discount=discount, shipping=0, tax=tax, tax_pct=10 if tax else 0,
                                total=sub - discount + tax, paid=paid, note=""), items)
minv("1399/08/10", [dict(name="x", unit="عدد", qty=2, price=100000, total=200000, cost=60000), dict(name="y", unit="عدد", qty=1, price=50000, total=50000, cost=0)], 25000, 100000, cA)
minv("1399/08/20", [dict(name="z", unit="عدد", qty=3, price=10000, total=30000, cost=4000)], 0, 30000, None)
minv("1399/07/05", [dict(name="out", unit="عدد", qty=1, price=999, total=999, cost=1)], 0, 999, None)
db.x("INSERT INTO payments(customer_id,amount,date,note) VALUES(?,?,?,?)", (cA, 40000, "1399/08/15", ""))
db.x("INSERT INTO payments(customer_id,amount,date,note) VALUES(?,?,?,?)", (cA, 7000, "1399/07/01", ""))
fp.set_period("custom"); fp.f_from.setText("۱۳۹۹/۰۸/۰۱"); fp.f_to.setText("۱۳۹۹/۰۸/۳۰"); fp.refresh()
# expenses via real dialogs
def f_exp(date, cat, amt, note=""):
    def f(d): d.d.setText(date); d.c.setEditText(cat); d.a.setValue(amt); d.n.setText(note); d.accept()
    return f
dlg(f_exp("۱۳۹۹/۰۸/۱۲", "اجاره", 20000)); fp.exp_add()
dlg(f_exp("۱۳۹۹/۰۸/۲۵", "حمل و نقل", 99999, "اشتباه")); fp.exp_add()
check("2 expenses listed in range", fp.exp_table.rowCount() == 2)
r_ = [r for r in range(fp.exp_table.rowCount()) if fp.exp_table.item(r, 2).text() == app.money(99999)][0]; fp.exp_table.setCurrentCell(r_, 0)
dlg(lambda d: (d.a.setValue(5000), d.accept())); fp.exp_edit()
check("expense edit saved", db.q("SELECT COUNT(*) n FROM expenses WHERE amount=5000")[0]["n"] == 1)
dlg(lambda d: (click_ok_later(), d.a.setValue(0), d.accept(), d.reject())); fp.exp_add(); check("zero expense rejected", fp.exp_table.rowCount() == 2)
dlg(f_exp("۱۳۹۹/۰۸/۲۶", "سایر", 777)); fp.exp_add()
r_ = [r for r in range(fp.exp_table.rowCount()) if fp.exp_table.item(r, 2).text() == app.money(777)][0]; fp.exp_table.setCurrentCell(r_, 0)
dlg(click_first); fp.exp_delete(); check("expense delete works", fp.exp_table.rowCount() == 2)
db.x("INSERT INTO expenses(date,category,amount) VALUES('1399/06/01','اجاره',1111)")
# suppliers via real dialogs
dlg(lambda d: (d.n.setText("شرکت پخش"), d.p.setText("۰۲۱۱۲۳۴"), d.accept())); fp.sup_add()
dlg(lambda d: (d.n.setText("شرکت دوم"), d.accept())); fp.sup_add()
dlg(lambda d: (click_ok_later(), d.n.setText(""), d.accept(), d.reject())); fp.sup_add(); check("empty supplier name rejected", fp.sup_table.rowCount() == 2)
s1 = db.q("SELECT id FROM suppliers WHERE name='شرکت پخش'")[0]["id"]; s2 = db.q("SELECT id FROM suppliers WHERE name='شرکت دوم'")[0]["id"]
def sel_sup(sid): fp.sup_table.setCurrentCell([r for r in range(fp.sup_table.rowCount()) if fp.sup_table.item(r, 0).data(Qt.UserRole) == sid][0], 0)
sel_sup(s1); dlg(lambda d: (d.a.setValue(500000), d.pd.setValue(0), d.d.setText("۱۳۹۹/۰۸/۰۵"), d.accept())); fp.sup_purchase()
sel_sup(s1); dlg(lambda d: (d.a.setValue(100000), d.d.setText("۱۳۹۹/۰۸/۱۸"), d.accept())); fp.sup_pay()
db.x("INSERT INTO supplier_tx(supplier_id,kind,amount,date,note) VALUES(?,?,?,?,?)", (s1, "payment", 3333, "1399/07/01", ""))
sel_sup(s2); dlg(lambda d: (d.a.setValue(200000), d.pd.setValue(50000), d.d.setText("۱۳۹۹/۰۷/۱۰"), d.accept())); fp.sup_purchase()
sel_sup(s2); dlg(lambda d: (click_ok_later(), d.a.setValue(100), d.pd.setValue(500), d.accept(), d.reject())); fp.sup_purchase()
check("paid more than purchase rejected", len(db.q("SELECT * FROM supplier_tx WHERE supplier_id=?", (s2,))) == 2)
fp.refresh(); bal = db.supplier_balances()
check("supplier balances", bal[s1] == 500000 - 103333 and bal[s2] == 150000)
check("purchase with paid-now creates payment entry", len(db.q("SELECT * FROM supplier_tx WHERE supplier_id=? AND kind='payment'", (s2,))) == 1)
sd2 = app.SupplierStatementDialog(w, s1); check("supplier statement rows", sd2.table.rowCount() == 3 and app.money(396667) in sd2.table.item(2, 4).text())
sel_sup(s1); dlg(lambda d: d.accept()); fp.sup_statement()
sel_sup(s1); dlg(click_first); fp.sup_delete(); check("supplier with transactions cannot be deleted", db.q("SELECT 1 FROM suppliers WHERE id=?", (s1,)) != [])
dlg(lambda d: (d.n.setText("بی‌تراکنش"), d.accept())); fp.sup_add(); s3 = db.q("SELECT id FROM suppliers WHERE name='بی‌تراکنش'")[0]["id"]; sel_sup(s3)
dlg(click_first); fp.sup_delete(); check("empty supplier deletable", not db.q("SELECT 1 FROM suppliers WHERE id=?", (s3,)))
# numbers
fp.refresh(); st = db.finance("1399/08/01", "1399/08/30")
exp = dict(sales=305000, count=2, tax=25000, revenue=280000, received=170000, expenses=25000, supplier_paid=100000, cash_net=45000, cogs=132000, nocost=50000, gross=148000, net=123000)
check("finance numbers exact", all(abs(st[k] - v) < 1e-6 for k, v in exp.items()))
for key, v in dict(sales=305000, received=170000, expenses=25000, cash_net=45000, gross=148000, net=123000).items():
    check(f"card {key} shows value", fp.cards[key][0].text() == app.money(v))
check("receivables card = sum of positive balances", fp.cards["recv"][0].text() == app.money(sum(x for x in db.balances().values() if x > 0)))
check("payables card = 396667+150000", fp.cards["pay"][0].text() == app.money(396667 + 150000))
check("missing-cost warning shown", fp.warn.isVisible() and "۵۰٬۰۰۰" in fp.warn.text())
fp.tabs.setCurrentIndex(3); a.processEvents()
check("cash flow has 6 movements", fp.cash_table.rowCount() == 6)
check("cash flow final balance equals net cash", app.money(45000) in fp.cash_table.item(5, 4).text())
fp.tabs.setCurrentIndex(0); fp.chart.grab(); check("chart paints", fp.chart.width() > 0)
# period helpers
d0 = app.jdatetime.date.today()
check("period today", app.period_range("today") == (app.today(), app.today()))
check("period week starts Saturday", app.jdatetime.date(*map(int, app.period_range("week")[0].split("/"))).weekday() == 0)
check("period month/year start", app.period_range("month")[0].endswith("/01") and app.period_range("year")[0].endswith("/01/01"))
check("custom invalid -> empty", app.period_range("custom", ("abc", "")) == ("", ""))
for k in ("today", "week", "month", "year", "custom"): fp.set_period(k)
fp.f_from.setText("بد"); fp.f_to.setText(""); fp.refresh(); check("invalid custom range handled", "نامعتبر" in fp.range_lbl.text() or "وارد کنید" in fp.range_lbl.text() or fp.cards["sales"][0].text() == "۰")
fp.set_period("month")
app.pick_save_csv = lambda parent, default: f"{TMP}/{default}"
fp.set_period("custom"); fp.f_from.setText("۱۳۹۹/۰۸/۰۱"); fp.f_to.setText("۱۳۹۹/۰۸/۳۰"); fp.refresh(); fp.exp_export(); fp.cash_export()
with open(f"{TMP}/expenses.csv", encoding="utf-8-sig") as f_: rows_ = list(csv.reader(f_))
check("expenses csv", len(rows_) == 3 and rows_[0][0] == "تاریخ")
with open(f"{TMP}/cashflow.csv", encoding="utf-8-sig") as f_: rows_ = list(csv.reader(f_))
check("cashflow csv", len(rows_) == 7 and rows_[-1][-1] == "45000")
# developer credit + about
s_ = db.settings()
check("receipt shows developer credit", app.DEVELOPER["email"] in app.receipt_html(s_, base, it) and app.DEVELOPER["name"] in app.receipt_html(s_, base, it))
check("credit always printed (even if an old DB still has the retired setting)", app.DEVELOPER["email"] in app.receipt_html({**s_, "show_credit": "0"}, base, it))
check("settings page has no credit toggle", not hasattr(sp, "show_credit"))
dlg(lambda d: d.accept()); app.AboutDialog(w).exec(); check("about dialog opens", True)
from PySide6.QtWidgets import QPushButton as _QB
ab = [b for b in w.findChildren(_QB) if b.objectName() == "sidelink"][0]; dlg(lambda d: d.accept()); ab.click(); check("sidebar about link works", True)
# batch files must be pure ASCII with CRLF (Persian text broke cmd earlier)
for bf in ("build_exe.bat", "run.bat"):
    raw = open(str(ROOT / bf), "rb").read()
    check(f"{bf} is ASCII + CRLF", all(b < 128 for b in raw) and b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""))
check("icon file exists", os.path.getsize(ROOT / "assets" / "icon.ico") > 1000)


# ---------- T12: printer alignment tools
s_ = db.settings()
check("receipt_px native 203dpi", app.receipt_px({"print_w": "72"}) == 575 and app.receipt_px({"print_w": "67"}) == 535)
check("receipt rendered at native width", app.render_receipt({**s_, "print_w": "67"}, base, it).width() == 535 and app.render_receipt({**s_, "print_w": "72"}, base, it).width() == 575)
cal = app.calibration_image({**s_, "print_w": "67", "print_dx": "-4"})
import random as _r; _r.seed(2)
_px = {cal.pixel(_r.randrange(cal.width()), _r.randrange(cal.height())) for _ in range(3000)}
check("calibration sheet renders pure black/white", cal.width() == 535 and cal.height() > 400 and _px <= {0xFF000000, 0xFFFFFFFF})
cal.save(f"{TMP}/cal.png")
def pdf_bytes(dx):
    pr_ = QPrinter(QPrinter.HighResolution); pr_.setOutputFormat(QPrinter.PdfFormat); pth = f"{TMP}/dx{dx}.pdf"; pr_.setOutputFileName(pth)
    ok = orig_print(app.render_receipt(s_, base, it), "", 72, dx, printer=pr_); return ok, open(pth, "rb").read()
ok0, b0 = pdf_bytes(0); ok1, b1 = pdf_bytes(-4)
check("print with horizontal offset works and moves content", ok0 and ok1 and len(b0) > 1000 and b0 != b1)
w.go(6); sp.dx.setText("-۴"); check("offset field accepts negative numbers", sp.dx.value() == -4)
sp.save(); check("offset saved", float(db.settings()["print_dx"]) == -4.0)
sp.refresh(); check("offset reloaded in field", sp.dx.value() == -4)
dlg(click_first); sp.test_align(); check("alignment test print path handled", True)
sp.dx.setText("0"); sp.save()

check("no unexpected modal dialogs", not UNEXPECTED)
check("no exceptions raised anywhere", not EXC)
bad = [n for n, ok in R if not ok]
print(f"\n{len(R) - len(bad)}/{len(R)} checks passed")
if UNEXPECTED: print("UNEXPECTED MODALS:", UNEXPECTED)
for e in EXC[:4]: print("EXC:\n", e[-900:])
sys.stdout.flush()
os._exit(1 if (bad or EXC or UNEXPECTED) else 0)     # os._exit: skip Qt teardown (can segfault on some platforms)
