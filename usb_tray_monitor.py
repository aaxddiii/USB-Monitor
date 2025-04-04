import os
import platform
import sqlite3
import subprocess
import threading
import time
from tkinter import messagebox, Tk, simpledialog

import psutil
from PIL import Image, ImageDraw
import pystray

# -------------------- App Constants --------------------

OS_TYPE = platform.system()
DB_FILE = "trusted_devices.db"

# Hidden tkinter window for popups
root = Tk()
root.withdraw()

# -------------------- SQLite Whitelist --------------------

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS trusted_devices (
        name TEXT,
        vendor_id TEXT,
        product_id TEXT,
        serial_number TEXT PRIMARY KEY
    )
""")
conn.commit()

def is_trusted(serial):
    cursor.execute("SELECT * FROM trusted_devices WHERE serial_number=?", (serial,))
    return cursor.fetchone() is not None

def add_to_whitelist(device):
    try:
        cursor.execute("INSERT INTO trusted_devices VALUES (?, ?, ?, ?)", device)
        conn.commit()
        messagebox.showinfo("Whitelisted", f"{device[0]} has been added to the whitelist.")
    except sqlite3.IntegrityError:
        messagebox.showinfo("Exists", "Device is already in whitelist.")

def remove_from_whitelist(serial):
    cursor.execute("DELETE FROM trusted_devices WHERE serial_number=?", (serial,))
    conn.commit()
    messagebox.showinfo("Removed", "Device removed from whitelist.")

# -------------------- USB Detection --------------------

def get_connected_devices():
    devices = []

    if OS_TYPE == "Darwin":
        result = subprocess.run(["system_profiler", "SPUSBDataType"], stdout=subprocess.PIPE, text=True)
        output = result.stdout
        current = {}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Product ID:"):
                current['product_id'] = line.split(":")[1].strip().replace("0x", "")
            elif line.startswith("Vendor ID:"):
                parts = line.split()
                current['vendor_id'] = parts[2] if len(parts) > 2 else "Unknown"
                current['name'] = parts[-1].strip("()") if len(parts) > 3 else "Unknown"
            elif line.startswith("Serial Number:"):
                current['serial'] = line.split(":")[1].strip()
                if current.get('serial'):
                    devices.append(current.copy())

    elif OS_TYPE == "Windows":
        for part in psutil.disk_partitions(all=False):
            if 'removable' in part.opts.lower():
                name = os.path.basename(part.device)
                devices.append({
                    "name": f"Drive {name}",
                    "vendor_id": "Unknown",
                    "product_id": "Unknown",
                    "serial": name
                })

    return devices

# -------------------- Auto Eject (Optional) --------------------

def auto_eject(serial):
    try:
        if OS_TYPE == "Darwin":
            subprocess.run(["diskutil", "unmount", f"/Volumes/{serial}"], check=True)
    except Exception as e:
        print(f"Auto-eject failed: {e}")

# -------------------- Monitoring Logic --------------------

connected_serials = set()

def monitor_usb():
    while True:
        devices = get_connected_devices()
        current_serials = {d['serial'] for d in devices}

        for dev in devices:
            serial = dev['serial']
            if serial not in connected_serials:
                trusted = is_trusted(serial)
                status = "Trusted" if trusted else "Untrusted"

                msg = f"Name: {dev['name']}\nVendor: {dev['vendor_id']}\nProduct: {dev['product_id']}\nSerial: {serial}\nStatus: {status}"
                if trusted:
                    print(f"🔒 Trusted device connected: {serial}")
                else:
                    print(f"⚠️ Untrusted device connected: {serial}")
                    root.after(0, lambda d=dev: messagebox.showwarning("Untrusted USB Detected", msg))
                    # auto_eject(serial)  # Optional: eject on untrusted
                connected_serials.add(serial)

        disconnected = connected_serials - current_serials
        connected_serials.difference_update(disconnected)
        time.sleep(5)

# -------------------- Tray Menu Functions --------------------

def create_icon():
    # Optional: load icon from file
    if os.path.exists("icon.png"):
        return Image.open("icon.png")
    
    # Or draw default blue square
    icon_size = 64
    image = Image.new("RGB", (icon_size, icon_size), (100, 100, 255))
    d = ImageDraw.Draw(image)
    d.rectangle((10, 10, 54, 54), fill="white")
    return image

def on_exit(icon, item):
    icon.stop()
    root.quit()

def on_show_devices(icon, item):
    devices = get_connected_devices()
    if not devices:
        messagebox.showinfo("Connected Devices", "No USB devices connected.")
        return

    msg = ""
    for d in devices:
        status = "Trusted" if is_trusted(d['serial']) else "Untrusted"
        msg += f"{d['name']} - {d['serial']} ({status})\n"
    messagebox.showinfo("Connected Devices", msg)

def on_add_whitelist(icon, item):
    devices = get_connected_devices()
    for d in devices:
        if not is_trusted(d['serial']):
            add_to_whitelist((d['name'], d['vendor_id'], d['product_id'], d['serial']))

def on_remove_whitelist(icon, item):
    serial = simpledialog.askstring("Remove Device", "Enter serial number to remove from whitelist:")
    if serial:
        remove_from_whitelist(serial)

def setup_tray():
    icon = pystray.Icon("usb_tray")
    icon.icon = create_icon()
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show Devices", on_show_devices),
        pystray.MenuItem("Add All to Whitelist", on_add_whitelist),
        pystray.MenuItem("Remove from Whitelist", on_remove_whitelist),
        pystray.MenuItem("Quit", on_exit)
    )
    return icon

# -------------------- Run App --------------------

if __name__ == "__main__":
    tray_icon = setup_tray()
    threading.Thread(target=monitor_usb, daemon=True).start()
    tray_icon.run()
