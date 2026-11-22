# Third-party notices

Factor Foroosh is MIT-licensed (see `LICENSE`). It uses the following third-party components, each under its own license:

| Component | Use | License |
|---|---|---|
| [Qt for Python (PySide6)](https://doc.qt.io/qtforpython-6/) | GUI toolkit, printing, SVG icons | LGPL-3.0 (see The Qt Company's licensing page) |
| [jdatetime](https://pypi.org/project/jdatetime/) | Shamsi (Jalali) calendar | see its PyPI page |
| [Vazirmatn](https://github.com/rastikerdar/vazirmatn) | UI and receipt font (`fonts/`) | SIL Open Font License 1.1 (`fonts/OFL.txt`) |
| [Feather](https://feathericons.com/) | Icon shapes, embedded as inline SVG | MIT |
| [PyInstaller](https://pyinstaller.org/) | Builds the Windows `.exe` (build tool only) | GPL-2.0 with bootloader exception |

When you redistribute a PyInstaller-built `.exe`, the PySide6/Qt libraries inside it stay under their own (L)GPL terms.
