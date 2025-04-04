# USB-Monitor

🔌 A cross-platform USB monitoring system tray application that:
- Detects inserted USB devices
- Highlights trusted ones (green)
- Alerts on untrusted devices
- Works on macOS and Windows
- Built with Python, PyStray, SQLite

## 💻 Features

- Real-time USB detection
- Trusted device whitelist (SQLite-based)
- System tray with options: View Devices, Refresh, Clear
- Auto-start on boot (configurable)
- GUI + lightweight background mode

## 🚀 How to Run

```bash
pip install -r requirements.txt
python usb_tray_monitor.py
