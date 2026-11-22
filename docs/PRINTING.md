# Printing guide · راهنمای چاپ

Factor Foroosh prints through the **normal Windows printer driver** — no special ESC/POS setup. Tested with a Meva TP-U1 (80 mm thermal, USB).

## 1. Setup

1. Install the printer's driver and confirm a test page prints from Windows.
2. *Printer preferences* → set the paper size to **80 mm** (roll / continuous, if the driver offers it).
3. In the app: **Settings → Printer** → pick your printer (or leave "Windows default printer") → **Save settings**.
4. Press **Test print**.

## 2. How a receipt is printed

The receipt is drawn as a **pure black-and-white bitmap** and sent to the driver as an image. This is deliberate:

- Persian letters join and change shape; sending plain text to thermal printers usually garbles them. A bitmap always looks like the preview.
- Thermal heads turn grey pixels into dot patterns, which makes thin anti-aliased text look faint. A pure black/white image avoids that.
- The image is rendered at **203 dpi** (8 dots/mm) at exactly the width you set, so one image pixel is one printer dot (no blurry rescaling).

The preview window in the app shows exactly what will be printed.

## 3. Alignment — if one side is empty or cut off

Most 80 mm printers only print ~72 mm of the 80 mm paper, and the driver may place that area slightly off-centre.

1. **Settings → Test alignment print.** You get a framed ruler sheet. Left/right are labelled on the paper.
2. Look at the printed sheet:
   - Frame line missing on one side → that side is **cut off** (printable area is narrower than your *Width*).
   - Extra blank space on one side → content is **shifted** away from that side.
3. Adjust, save, print the test again:
   - **Horizontal offset (mm)**: negative moves the content **left**, positive moves it **right**. Try steps of 1–2 mm.
   - **Printable width (mm)**: lower it (e.g. 72 → 68) if a side stays cut off after shifting.
4. Typical result for a TP-U1-class printer: width `67–72`, offset `-2…-5`.

## 4. Text looks faint

- Raise *Print density / darkness* in the Windows printer preferences (this is a printer setting the app cannot change).
- Use fresh thermal paper; old or cheap rolls print pale.
- Slower print speed gives darker output on many models.

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "Printer not found" message | Printer off, unplugged, or wrong printer selected | Check power/USB, choose the printer in Settings |
| Receipt is tiny or huge | Driver paper size is not 80 mm | Set 80 mm in Printer preferences |
| One side empty | Content off-centre | Use *Horizontal offset* (section 3) |
| One side cut off | Printable width too large | Lower *Width* |
| Receipt prints but is very long / blank paper at the end | Driver uses fixed page length | Choose a continuous-roll paper size in the driver |

---

## ‫راهنمای چاپ (فارسی)‬

<div dir="rtl" align="right">

فاکتور فروش با **درایور معمولی ویندوز** چاپ می‌کند و به تنظیم خاصی نیاز ندارد. روی Meva TP-U1 (حرارتی ۸۰ میلی‌متری، USB) تست شده است.

### ۱. راه‌اندازی
1. درایور پرینتر را نصب کنید و مطمئن شوید یک صفحه‌ی تست از ویندوز چاپ می‌شود.
2. در Printer preferences اندازه‌ی کاغذ را روی **۸۰ میلی‌متر** (رول/پیوسته) بگذارید.
3. در برنامه: **تنظیمات ← چاپگر** را انتخاب کنید و «ذخیره‌ی تنظیمات» را بزنید.
4. «چاپ آزمایشی» را بزنید.

### ۲. رسید چطور چاپ می‌شود؟
رسید به‌صورت **تصویر سیاه‌وسفید** ساخته و به درایور فرستاده می‌شود. دلیلش این است که حروف فارسی به‌هم می‌چسبند و ارسال متن ساده به پرینتر حرارتی معمولاً آن‌ها را خراب می‌کند، و پرینتر حرارتی نقاط خاکستری را نقطه‌چین می‌کند و نوشته‌ی ریز کمرنگ می‌شود. تصویر با رزولوشن ۲۰۳ نقطه در اینچ و دقیقاً به عرضی که تنظیم کرده‌اید ساخته می‌شود. پیش‌نمایش داخل برنامه همان چیزی است که چاپ می‌شود.

### ۳. اگر یک سمت رسید خالی یا بریده بود
بیشتر پرینترهای ۸۰ میلی‌متری فقط حدود ۷۲ میلی‌متر از کاغذ را چاپ می‌کنند و درایور ممکن است این ناحیه را کمی به یک سمت ببرد.

1. **تنظیمات ← چاپ تست تراز** را بزنید؛ یک برگه با قاب و خط‌کش چاپ می‌شود.
2. اگر خط قاب یک سمت دیده نمی‌شود، همان سمت **بریده** شده است. اگر یک سمت خالیِ اضافه دارد، محتوا از آن سمت **دور** شده است.
3. تنظیم کنید و دوباره تست بگیرید:
   - **جابه‌جایی افقی (mm):** عدد منفی محتوا را به **چپ** می‌برد و مثبت به **راست**. با قدم‌های ۱ تا ۲ میلی‌متر امتحان کنید.
   - **عرض قابل چاپ (mm):** اگر بعد از جابه‌جایی هنوز یک سمت بریده می‌شود، کمش کنید (مثلاً ۷۲ ← ۶۸).
4. نتیجه‌ی معمول برای پرینترهای شبیه TP-U1: عرض `۶۷ تا ۷۲` و جابه‌جایی `‎-۲ تا ‎-۵`.

### ۴. نوشته‌ها کمرنگ است
- گزینه‌ی Print density / Darkness را در تنظیمات پرینتر ویندوز بالاتر ببرید (این تنظیم پرینتر است و از داخل برنامه تغییر نمی‌کند).
- از کاغذ حرارتی تازه استفاده کنید؛ رول‌های قدیمی یا ارزان کم‌رنگ چاپ می‌کنند.
- در بعضی مدل‌ها سرعت چاپ کمتر، چاپ پررنگ‌تری می‌دهد.

</div>
