"""Generate assets/logo.png and assets/social-preview.png (1280x640, for GitHub's repository social preview).

Usage:  python scripts/make_social_preview.py     (run scripts/make_screenshots.py first)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import app  # noqa: E402

qt = QApplication([])
app.setup_app(qt)
app.app_icon().pixmap(256, 256).save(str(ROOT / "assets" / "logo.png"))

W, H = 1280, 640
img = QImage(W, H, QImage.Format_RGB32)
img.fill(QColor("#1E2420"))
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
p.setRenderHint(QPainter.SmoothPixmapTransform)
shot = QImage(str(ROOT / "docs" / "screenshots" / "dashboard.png")).scaledToWidth(700, Qt.SmoothTransformation)
path = QPainterPath()
path.addRoundedRect(QRectF(540, 150, shot.width(), shot.height()), 18, 18)
p.setClipPath(path)
p.drawImage(540, 150, shot)
p.setClipping(False)
p.drawPixmap(70, 70, app.app_icon().pixmap(96, 96))
p.setPen(QColor("#F3E9D2"))
p.setFont(QFont(app.FONT, 40, QFont.Bold))
p.drawText(QRectF(70, 190, 520, 70), Qt.AlignLeft | Qt.AlignVCenter, "Factor Foroosh")
p.setFont(QFont(app.FONT, 46, QFont.Bold))
p.drawText(QRectF(70, 262, 520, 80), Qt.AlignLeft | Qt.AlignVCenter, "فاکتور فروش")
p.setPen(QColor("#B7BFB8"))
p.setFont(QFont(app.FONT, 17))
p.drawText(QRectF(70, 360, 440, 150), Qt.AlignLeft | Qt.TextWordWrap,
           "Offline invoicing and finance for small shops.\nPersian/RTL · Shamsi dates · 80 mm thermal receipts")
p.setPen(QColor("#D9A441"))
p.setFont(QFont(app.FONT, 14))
p.drawText(QRectF(70, 560, 600, 40), Qt.AlignLeft | Qt.AlignVCenter, "Python · PySide6 · SQLite · MIT")
p.end()
img.save(str(ROOT / "assets" / "social-preview.png"))
print("wrote assets/logo.png and assets/social-preview.png")
os._exit(0)
