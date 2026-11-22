"""Regenerate docs/screenshots/*.png from the real app, using demo data (nothing is written to your real database).

Usage:  python scripts/make_screenshots.py
"""
import os
import random
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
os.environ["SHOP_DATA"] = tempfile.mkdtemp()          # throw-away database
sys.path.insert(0, str(ROOT))

import jdatetime  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import app  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
qt = QApplication([])
app.setup_app(qt)
db = app.DB(app.DATA / "shop.db")
random.seed(4)
today = app.today()

for k, v in dict(shop_name="دخانیات و قهوه آریا", shop_sub="پخش عمده و خرده", phone="09121234567",
                 address="تهران، خیابان ولیعصر، پلاک ۱۲", tax_on="1", ship_on="1", next_no="1048").items():
    db.set(k, v)

PRODUCTS = [("قهوه اسپرسو ۱ کیلویی", "قهوه", "بسته", 1250000, "6261234567890", 1000000), ("قهوه ترک", "قهوه", "بسته", 420000, "", 330000),
            ("نسکافه گلد", "قهوه", "کارتن", 3600000, "", 3000000), ("سیگار وینستون", "دخانیات", "کارتن", 5200000, "6269990001112", 4700000),
            ("سیگار مارلبرو", "دخانیات", "پاکت", 260000, "6269998887771", 225000), ("فندک", "لوازم", "عدد", 45000, "", 28000),
            ("توتون پیپ", "دخانیات", "بسته", 380000, "", 300000)]
for n, c, u, p, b, co in PRODUCTS:
    db.x("INSERT INTO products(name,category,unit,price,barcode,cost) VALUES(?,?,?,?,?,?)", (n, c, u, p, b, co))
for n, ph, ad in [("علی رضایی", "09123456789", "تهران، سعادت‌آباد"), ("کافه نیلوفر", "09351112233", "کرج، گوهردشت"),
                  ("سوپرمارکت امید", "09190001122", "ری، خیابان شهید رجایی"), ("محسن کریمی", "09371239876", "")]:
    db.x("INSERT INTO customers(name,phone,address) VALUES(?,?,?)", (n, ph, ad))


def invoice(cid, name, items, paid, date):
    sub = sum(i["total"] for i in items)
    db.save_invoice(dict(customer_id=cid, customer_name=name, date=date, subtotal=sub, discount=0, shipping=0, tax=0,
                         tax_pct=0, total=sub, paid=paid, note=""), items)


def item(name, unit, qty, price, cost=0):
    return dict(name=name, unit=unit, qty=qty, price=price, total=qty * price, cost=cost)


def month_day(back, day):
    d = jdatetime.date.today()
    y, m = d.year, d.month - back
    while m <= 0:
        m, y = m + 12, y - 1
    return f"{y:04d}/{m:02d}/{day:02d}"


invoice(1, "علی رضایی", [item("فندک", "عدد", 10, 45000, 28000)], 450000, today)
invoice(2, "کافه نیلوفر", [item("قهوه اسپرسو ۱ کیلویی", "بسته", 5, 1250000, 1000000)], 4000000, today)
invoice(3, "سوپرمارکت امید", [item("سیگار مارلبرو", "پاکت", 20, 260000, 225000)], 5200000, today)
invoice(2, "کافه نیلوفر", [item("قهوه ترک", "بسته", 6, 420000, 330000)], 2520000, today)
invoice(None, "", [item("سیگار وینستون", "کارتن", 5, 5200000, 4700000)], 26000000, today)
invoice(None, "", [item("نسکافه گلد", "کارتن", 4, 3600000, 3000000), item("قهوه ترک", "بسته", 10, 420000, 330000)], 18600000, today)
db.x("INSERT INTO payments(customer_id,amount,date,note) VALUES(2,500000,?,?)", (today, "نقد"))
for back in range(1, 6):                                         # history for the 6-month chart
    for k in range(3):
        invoice(None, "", [item("قهوه اسپرسو ۱ کیلویی", "بسته", random.randint(6, 12), 1250000, 1000000)], 10**12, month_day(back, 3 + k * 8))
    for cat, amt in (("اجاره", 6000000), ("حقوق و دستمزد", random.randint(4, 7) * 1000000), ("قبض (برق، آب، گاز، اینترنت)", 1200000)):
        db.x("INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)", (month_day(back, 5), cat, amt, ""))
db.x("UPDATE invoices SET paid=total WHERE paid>total")           # history invoices are fully paid cash sales
for cat, amt, note in (("اجاره", 6000000, "اجاره‌ی ماه جاری"), ("حمل و نقل", 650000, "کرایه‌ی بار"), ("تبلیغات", 900000, "بنر")):
    db.x("INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)", (today, cat, amt, note))
s1 = db.x("INSERT INTO suppliers(name,phone) VALUES('پخش دخانیات شرق','02133445566')")
s2 = db.x("INSERT INTO suppliers(name,phone) VALUES('قهوه‌ی برتر (وارد‌کننده)','02188776655')")
for sid, kind, amt, note in ((s1, "purchase", 42000000, "فاکتور ۳۲۱"), (s1, "payment", 12000000, "چک"),
                             (s2, "purchase", 18500000, ""), (s2, "payment", 18500000, "نقد")):
    db.x("INSERT INTO supplier_tx(supplier_id,kind,amount,date,note) VALUES(?,?,?,?,?)", (sid, kind, amt, today, note))

w = app.Main(db)
w.resize(1320, 820)
w.show()
ip = w.pages[1]
ip.cust.setCurrentIndex(ip.cust.findData(2))
for name, q in [("قهوه اسپرسو ۱ کیلویی", 3), ("قهوه ترک", 4), ("فندک", 12)]:
    ip.prod.setEditText(name)
    ip.qty.setValue(q)
    ip.add_item()
ip.cb_disc.setChecked(True)
ip.disc.setValue(150000)
ip.cb_tax.setChecked(True)
ip.note.setText("تحویل در محل")
ip.paid.setValue(3000000)
ip.paid_edited()


def snap(page, name, tab=None):
    w.go(page)
    if tab is not None:
        w.pages[page].tabs.setCurrentIndex(tab)
    qt.processEvents()
    w.grab().save(str(OUT / f"{name}.png"))


for page, name in ((0, "dashboard"), (1, "new-invoice"), (3, "customers"), (4, "products"), (6, "settings")):
    snap(page, name)
snap(5, "finance", 0)
snap(5, "finance-suppliers", 2)
w.go(1)
inv, items = ip.collect()
inv["date"] = today
app.render_receipt(db.settings(), inv, items).save(str(OUT / "receipt.png"))
about = app.AboutDialog(w)
about.show()
qt.processEvents()
about.grab().save(str(OUT / "about.png"))
print("screenshots written to", OUT)
os._exit(0)
