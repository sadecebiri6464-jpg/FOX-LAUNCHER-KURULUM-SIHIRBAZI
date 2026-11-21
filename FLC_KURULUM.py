import ctypes
import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import urllib.request
import zipfile
import requests
import minecraft_launcher_lib

# Güncelleme Sistemi Ayarları
LAUNCHER_VERSION = "1.1.0"
GITHUB_OWNER = "sadecebiri6464-jpg"
GITHUB_REPO = "-E-YARAMAZ-SADECE-KAYNAK-KOD-SADECE-KURULUM-S-H-RBAZI-N"

# Windows görev çubuğu kimliğini Tkinter'dan ÖNCE ayarla
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FLC.FoxLauncher.Main.2")
    except Exception:
        pass

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://api.curseforge.com/v1"
HEADERS = {"User-Agent": "FLC-FoxLauncher/1.1"}


def _point_in_triangle(px, py, ax, ay, bx, by, cx, cy):
    d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
    d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
    d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def _render_fox_rgba_pixels(size):
    buf = bytearray(size * size * 4)
    s = float(size)
    cx = s * 0.5

    def set_px(x, y, r, g, b, a=255):
        if 0 <= x < size and 0 <= y < size:
            idx = (y * size + x) * 4
            buf[idx] = b
            buf[idx + 1] = g
            buf[idx + 2] = r
            buf[idx + 3] = a

    pad = s * 0.05
    rad = s * 0.24
    for y in range(size):
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            ix = max(pad + rad, min(s - pad - rad, px))
            iy = max(pad + rad, min(s - pad - rad, py))
            dist = ((px - ix) ** 2 + (py - iy) ** 2) ** 0.5
            if dist <= rad:
                if dist >= rad - max(1.2, s * 0.045):
                    set_px(x, y, 249, 115, 22, 255)
                else:
                    set_px(x, y, 26, 31, 43, 255)

            in_left_ear = _point_in_triangle(px, py, s * 0.20, s * 0.16, s * 0.43, s * 0.34, s * 0.19, s * 0.49)
            in_right_ear = _point_in_triangle(px, py, s * 0.80, s * 0.16, s * 0.57, s * 0.34, s * 0.81, s * 0.49)
            if in_left_ear or in_right_ear:
                set_px(x, y, 234, 88, 12, 255)

            in_face = (
                _point_in_triangle(px, py, s * 0.19, s * 0.44, cx, s * 0.31, s * 0.81, s * 0.44)
                or _point_in_triangle(px, py, s * 0.19, s * 0.44, s * 0.81, s * 0.44, s * 0.74, s * 0.67)
                or _point_in_triangle(px, py, s * 0.19, s * 0.44, s * 0.74, s * 0.67, s * 0.26, s * 0.67)
                or _point_in_triangle(px, py, s * 0.26, s * 0.67, s * 0.74, s * 0.67, cx, s * 0.85)
            )
            if in_face:
                set_px(x, y, 249, 115, 22, 255)

            in_l_cheek = (
                _point_in_triangle(px, py, s * 0.19, s * 0.48, s * 0.43, s * 0.62, cx, s * 0.85)
                or _point_in_triangle(px, py, s * 0.19, s * 0.48, cx, s * 0.85, s * 0.26, s * 0.67)
            )
            in_r_cheek = (
                _point_in_triangle(px, py, s * 0.81, s * 0.48, s * 0.57, s * 0.62, cx, s * 0.85)
                or _point_in_triangle(px, py, s * 0.81, s * 0.48, cx, s * 0.85, s * 0.74, s * 0.67)
            )
            if in_l_cheek or in_r_cheek:
                set_px(x, y, 248, 250, 252, 255)

            eye_r = max(1.1, s * 0.042)
            if ((px - s * 0.36) ** 2 + (py - s * 0.53) ** 2) ** 0.5 <= eye_r:
                set_px(x, y, 15, 23, 42, 255)
            if ((px - s * 0.64) ** 2 + (py - s * 0.53) ** 2) ** 0.5 <= eye_r:
                set_px(x, y, 15, 23, 42, 255)

            if _point_in_triangle(px, py, cx - s * 0.07, s * 0.75, cx + s * 0.07, s * 0.75, cx, s * 0.85):
                set_px(x, y, 15, 23, 42, 255)

    return bytes(buf)


def write_fox_ico_file(ico_path):
    sizes = [16, 32, 48, 64]
    images_data = []
    for sz in sizes:
        bgra = _render_fox_rgba_pixels(sz)
        rows = [bgra[y * sz * 4:(y + 1) * sz * 4] for y in range(sz - 1, -1, -1)]
        pixel_data = b"".join(rows)
        and_mask_row_bytes = ((sz + 31) // 32) * 4
        and_mask = b"\x00" * (and_mask_row_bytes * sz)
        bih = struct.pack(
            "<IIIHHIIIIII",
            40, sz, sz * 2, 1, 32, 0,
            len(pixel_data) + len(and_mask), 0, 0, 0, 0
        )
        images_data.append((sz, bih + pixel_data + and_mask))

    header = struct.pack("<HHH", 0, 1, len(images_data))
    offset = 6 + 16 * len(images_data)
    entries = []
    for sz, blob in images_data:
        w_byte = 0 if sz >= 256 else sz
        entries.append(struct.pack("<BBBBHHII", w_byte, w_byte, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)

    with open(ico_path, "wb") as f:
        f.write(header + b"".join(entries) + b"".join(b for _, b in images_data))
    return ico_path


def create_tk_fox_photo(size=38):
    bgra = _render_fox_rgba_pixels(size)
    photo = tk.PhotoImage(width=size, height=size)
    rows = []
    for y in range(size):
        row_colors = []
        for x in range(size):
            idx = (y * size + x) * 4
            b, g, r, a = bgra[idx], bgra[idx + 1], bgra[idx + 2], bgra[idx + 3]
            if a == 0:
                row_colors.append("#0f131a")
            else:
                row_colors.append(f"#{r:02x}{g:02x}{b:02x}")
        rows.append("{" + " ".join(row_colors) + "}")
    photo.put(" ".join(rows))
    return photo


class SoftButton(tk.Canvas):
    """Yumuşak yuvarlatılmış, animasyonlu ve asla kilitlenmeyen buton."""

    def __init__(self, parent, text, command, bg="#f97316", hover_bg="#fb923c",
                 active_bg="#ea580c", fg="#ffffff", height=36, radius=12, font=("Segoe UI", 9, "bold")):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.bg_color = bg
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        self.fg_color = fg
        self.radius = radius
        self.font = font
        self.enabled = True
        self._current_bg = bg
        self.text = text

        try:
            self.configure(bg=parent.cget("bg"))
        except Exception:
            self.configure(bg="#171c26")

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", lambda e: self._animate_color(self.hover_bg) if self.enabled else None)
        self.bind("<Leave>", lambda e: self._animate_color(self.bg_color) if self.enabled else None)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(c))) for c in rgb])

    def _animate_color(self, target_hex, step=0, steps=5):
        start = self._hex_to_rgb(self._current_bg)
        end = self._hex_to_rgb(target_hex)

        def _tick(i):
            if i > steps:
                return
            t = i / steps
            mixed = tuple(start[k] + (end[k] - start[k]) * t for k in range(3))
            self._current_bg = self._rgb_to_hex(mixed)
            self._redraw()
            self.after(15, lambda: _tick(i + 1))

        _tick(step)

    def _redraw(self, event=None):
        self.delete("all")
        w = max(self.winfo_width(), 36)
        h = max(self.winfo_height(), 24)
        r = min(self.radius, w // 2, h // 2)
        fill = self._current_bg if self.enabled else "#334155"

        self.create_rectangle(r, 0, w - r, h, fill=fill, outline="")
        self.create_rectangle(0, r, w, h - r, fill=fill, outline="")
        for cx, cy in [(0, 0), (w - 2 * r, 0), (0, h - 2 * r), (w - 2 * r, h - 2 * r)]:
            self.create_oval(cx, cy, cx + 2 * r, cy + 2 * r, fill=fill, outline="")

        self.create_text(w // 2, h // 2, text=self.text,
                         fill=self.fg_color if self.enabled else "#94a3b8", font=self.font)

    def set_text(self, text):
        self.text = text
        self._redraw()

    def set_colors(self, bg, hover_bg, active_bg):
        self.bg_color = bg
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        self._current_bg = bg if self.enabled else "#334155"
        self._redraw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._current_bg = self.bg_color if enabled else "#334155"
        self._redraw()

    def _on_press(self, event):
        if self.enabled:
            self._current_bg = self.active_bg
            self._redraw()

    def _on_release(self, event):
        if self.enabled:
            self._current_bg = self.hover_bg
            self._redraw()
            if self.command:
                self.command()


class FoxLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title(f"FOXLAUNCHER (FLC v{LAUNCHER_VERSION})")
        self.root.geometry("1150x750")
        self.root.minsize(920, 620)
        self.root.resizable(True, True)

        self.bg_main = "#0f131a"
        self.bg_card = "#171c26"
        self.bg_input = "#222938"
        self.accent_fox = "#f97316"
        self.accent_blue = "#3b82f6"
        self.accent_purple = "#8b5cf6"
        self.text_main = "#f1f5f9"
        self.text_muted = "#94a3b8"
        self.root.configure(bg=self.bg_main)

        self.default_mc_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.custom_profiles_root = os.path.join(self.default_mc_dir, "flc_profiles")
        os.makedirs(self.custom_profiles_root, exist_ok=True)
        os.makedirs(os.path.join(self.default_mc_dir, "mods"), exist_ok=True)

        self._apply_window_icons()

        self.active_game_dir = self.default_mc_dir
        self.active_profile_info = None
        self.game_process = None

        self.config_file = os.path.join(self.default_mc_dir, "flc_config.json")
        self.config = self._load_config()

        self.search_results = []
        self.all_profiles = []
        self.installed_mods_data = []
        self.mod_icon_cache = {}
        self.installed_icon_cache = {}
        self.current_mod_photo = None
        self.current_installed_photo = None
        self._pulse_index = 0
        self._is_busy = False

        self._setup_styles()
        self._show_splash_animation()

    def _apply_window_icons(self):
        self.header_logo = create_tk_fox_photo(38)
        self.win_icon_32 = create_tk_fox_photo(32)
        self.win_icon_64 = create_tk_fox_photo(64)

        try:
            self.root.iconphoto(True, self.win_icon_64, self.win_icon_32)
        except Exception:
            pass

        ico_path = os.path.join(self.default_mc_dir, "flc_fox_v2.ico")
        try:
            write_fox_ico_file(ico_path)
            self.root.iconbitmap(ico_path)
            self.root.iconbitmap(default=ico_path)
        except Exception:
            pass

        if sys.platform == "win32" and os.path.isfile(ico_path):
            def _win32_force_icon():
                try:
                    self.root.update_idletasks()
                    hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x0010
                    WM_SETICON = 0x0080
                    hicon_small = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    hicon_big = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                    if hicon_small:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)
                    if hicon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
                except Exception:
                    pass

            self.root.after(50, _win32_force_icon)
            self.root.after(400, _win32_force_icon)

    def _draw_splash_fox(self, canvas, cx, cy, scale_val):
        r = 42 * scale_val
        canvas.create_oval(cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35,
                           outline="#7c2d12", width=2)
        canvas.create_polygon(
            cx - r * 0.75, cy - r * 0.85,
            cx - r * 0.22, cy - r * 0.40,
            cx - r * 0.82, cy - r * 0.05,
            fill="#ea580c", outline=""
        )
        canvas.create_polygon(
            cx + r * 0.75, cy - r * 0.85,
            cx + r * 0.22, cy - r * 0.40,
            cx + r * 0.82, cy - r * 0.05,
            fill="#ea580c", outline=""
        )
        canvas.create_polygon(
            cx - r * 0.82, cy - r * 0.12,
            cx, cy - r * 0.46,
            cx + r * 0.82, cy - r * 0.12,
            cx + r * 0.65, cy + r * 0.45,
            cx, cy + r * 0.90,
            cx - r * 0.65, cy + r * 0.45,
            fill="#f97316", outline=""
        )
        canvas.create_polygon(
            cx - r * 0.82, cy - r * 0.02,
            cx - r * 0.18, cy + r * 0.34,
            cx, cy + r * 0.90,
            cx - r * 0.65, cy + r * 0.45,
            fill="#f8fafc", outline=""
        )
        canvas.create_polygon(
            cx + r * 0.82, cy - r * 0.02,
            cx + r * 0.18, cy + r * 0.34,
            cx, cy + r * 0.90,
            cx + r * 0.65, cy + r * 0.45,
            fill="#f1f5f9", outline=""
        )
        er = max(2, int(r * 0.09))
        canvas.create_oval(cx - r * 0.36 - er, cy + r * 0.08 - er, cx - r * 0.36 + er, cy + r * 0.08 + er, fill="#0f172a", outline="")
        canvas.create_oval(cx + r * 0.36 - er, cy + r * 0.08 - er, cx + r * 0.36 + er, cy + r * 0.08 + er, fill="#0f172a", outline="")
        canvas.create_polygon(
            cx - r * 0.15, cy + r * 0.68,
            cx + r * 0.15, cy + r * 0.68,
            cx, cy + r * 0.90,
            fill="#0f172a", outline=""
        )

    def _show_splash_animation(self):
        self.splash_frame = tk.Frame(self.root, bg=self.bg_main)
        self.splash_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        canvas = tk.Canvas(self.splash_frame, width=460, height=320, bg=self.bg_main, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.48, anchor="center")

        total_steps = 24

        def _animate(step=0):
            canvas.delete("all")
            t = step / total_steps
            ease = 1 - (1 - t) ** 3
            cx, cy = 230, 108 + int((1 - ease) * 18)

            self._draw_splash_fox(canvas, cx, cy, 0.74 + 0.26 * ease)

            canvas.create_text(230, 184, text="FOXLAUNCHER", fill="#f8fafc",
                               font=("Segoe UI", 20, "bold"))
            canvas.create_text(230, 210, text=f"FLC v{LAUNCHER_VERSION}  •  Hızlı & Modüler Minecraft Başlatıcı",
                               fill="#fb923c", font=("Segoe UI", 9, "bold"))

            bar_x1, bar_y1, bar_x2, bar_y2 = 85, 240, 375, 250
            canvas.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y2, fill="#1e2530", outline="")
            fill_w = int((bar_x2 - bar_x1) * ease)
            if fill_w > 2:
                canvas.create_rectangle(bar_x1, bar_y1, bar_x1 + fill_w, bar_y2, fill="#f97316", outline="")

            if step < total_steps:
                self.root.after(14, lambda: _animate(step + 1))
            else:
                self.root.after(60, self._finish_splash)

        _animate(0)

    def _finish_splash(self):
        self.splash_frame.destroy()
        self._build_ui()
        self._refresh_accounts_ui()
        self.refresh_all_profiles()
        self.refresh_installed_mods()
        self._animate_status_pulse()

        self.log(f"FLC v{LAUNCHER_VERSION} hazır. Oyun dizini: {self.default_mc_dir}")
        threading.Thread(target=self.load_versions, daemon=True).start()
        # İnternet açıksa arka planda otomatik güncelleme kontrolü başlat
        threading.Thread(target=self._check_for_updates_background, daemon=True).start()

    # --- OTOMATİK GÜNCELLEME SİSTEMİ ---
    def _parse_version_tuple(self, ver_str):
        nums = [int(x) for x in re.findall(r"\d+", ver_str or "0")]
        return tuple(nums) if nums else (0,)

    def _fetch_remote_launcher_code(self):
        req_headers = {"User-Agent": "FLC-AutoUpdater/1.0"}
        raw_urls = []

        for branch in ("main", "master"):
            tree_api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees/{branch}?recursive=1"
            try:
                req = urllib.request.Request(tree_api, headers=req_headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    tree_data = json.loads(resp.read().decode("utf-8"))
                for item in tree_data.get("tree", []):
                    path = item.get("path", "")
                    if item.get("type") == "blob" and path.lower().endswith(".py") and "kurulum" not in path.lower():
                        raw_urls.append(f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{branch}/{path}")
                if raw_urls:
                    break
            except Exception:
                continue

        for fallback in ("FoxLauncher.py", "launcher.py", "foxlauncher.py", "main.py"):
            raw_urls.append(f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{fallback}")
            raw_urls.append(f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/master/{fallback}")

        for url in dict.fromkeys(raw_urls):
            try:
                req = urllib.request.Request(url, headers=req_headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    code = resp.read().decode("utf-8", errors="replace")
                if "class FoxLauncher" in code and len(code) > 1000:
                    return code
            except Exception:
                continue
        return None

    def _check_for_updates_background(self):
        try:
            remote_code = self._fetch_remote_launcher_code()
            if not remote_code:
                return

            m_ver = re.search(r'LAUNCHER_VERSION\s*=\s*["\']([^"\']+)["\']', remote_code)
            remote_ver = m_ver.group(1) if m_ver else ""

            current_script = os.path.abspath(sys.argv[0])
            if not os.path.isfile(current_script):
                return

            with open(current_script, "r", encoding="utf-8", errors="replace") as f:
                local_code = f.read()

            local_norm = local_code.replace("\r\n", "\n").strip()
            remote_norm = remote_code.replace("\r\n", "\n").strip()

            has_update = False
            if remote_ver and self._parse_version_tuple(remote_ver) > self._parse_version_tuple(LAUNCHER_VERSION):
                has_update = True
            elif hashlib.sha256(local_norm.encode("utf-8")).hexdigest() != hashlib.sha256(remote_norm.encode("utf-8")).hexdigest():
                # GitHub'da daha eski bir sürüm etiketi yoksa kod değişikliğini güncelleme say
                if not remote_ver or self._parse_version_tuple(remote_ver) >= self._parse_version_tuple(LAUNCHER_VERSION):
                    has_update = True

            if has_update:
                ver_label = f" (v{remote_ver})" if remote_ver else ""
                self.log(f"[GÜNCELLEME] Yeni sürüm bulundu{ver_label}!")
                self.root.after(0, lambda: self._prompt_and_apply_update(remote_code, ver_label))
            else:
                self.log(f"[GÜNCELLEME] FOXLAUNCHER güncel (v{LAUNCHER_VERSION}).")
        except Exception:
            # İnternet kapalıysa veya erişilemiyorsa sessizce geç
            pass

    def _prompt_and_apply_update(self, new_code, ver_label=""):
        answer = messagebox.askyesno(
            "Güncelleme Mevcut — FOXLAUNCHER",
            f"FOXLAUNCHER için yeni bir güncelleme{ver_label} bulundu!\n\n"
            f"Mevcut Sürüm: v{LAUNCHER_VERSION}\n"
            "Şimdi güncellenip otomatik olarak yeniden başlatılsın mı?"
        )
        if not answer:
            self.log("[GÜNCELLEME] Kullanıcı güncellemeyi erteledi.")
            return

        try:
            target_file = os.path.abspath(sys.argv[0])
            backup_file = target_file + ".bak"
            if os.path.isfile(target_file):
                shutil.copy2(target_file, backup_file)

            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_code)

            if os.path.isfile(backup_file):
                try:
                    os.remove(backup_file)
                except Exception:
                    pass

            self.log("[GÜNCELLEME] Güncelleme uygulandı, yeniden başlatılıyor...")
            subprocess.Popen([sys.executable, target_file], cwd=os.path.dirname(target_file) or None)
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            messagebox.showerror("Güncelleme Hatası", f"Güncelleme uygulanamadı:\n{e}")

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "TCombobox",
            fieldbackground=self.bg_input,
            background=self.bg_input,
            foreground=self.text_main,
            arrowcolor=self.accent_fox,
            borderwidth=0,
            padding=5
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.bg_input)],
            foreground=[("readonly", self.text_main)]
        )
        style.configure("TNotebook", background=self.bg_card, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.bg_input, foreground=self.text_muted,
                        padding=[14, 7], font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", self.accent_fox)],
                  foreground=[("selected", "#ffffff")])

    def _load_config(self):
        default_data = {
            "active": "Thefoxx20",
            "users": ["Thefoxx20"],
            "polymc_instances_dir": "",
            "ram_mb": 4096,
        }
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                users = [u.strip() for u in data.get("users", []) if u.strip()] or ["Thefoxx20"]
                active = data.get("active", users[0])
                if active not in users:
                    active = users[0]
                return {
                    "active": active,
                    "users": users,
                    "polymc_instances_dir": data.get("polymc_instances_dir", ""),
                    "ram_mb": int(data.get("ram_mb", 4096)),
                }
            except Exception:
                pass
        return default_data

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Ayarlar kaydedilemedi: {e}")

    def get_current_mods_dir(self):
        mods = os.path.join(self.active_game_dir, "mods")
        os.makedirs(mods, exist_ok=True)
        return mods

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.bg_card, padx=18, pady=10)
        header.pack(fill="x", padx=12, pady=(10, 4))

        if self.header_logo:
            tk.Label(header, image=self.header_logo, bg=self.bg_card).pack(side="left", padx=(0, 10))

        tk.Label(header, text="FOXLAUNCHER", font=("Segoe UI", 16, "bold"),
                 fg=self.accent_fox, bg=self.bg_card).pack(side="left")
        tk.Label(header, text=f"  FLC v{LAUNCHER_VERSION}", font=("Segoe UI", 10, "bold"),
                 fg=self.text_muted, bg=self.bg_card).pack(side="left", pady=(4, 0))

        self.active_profile_badge = tk.Label(
            header, text="Aktif Profil: Standart (.minecraft)", font=("Segoe UI", 9, "bold"),
            fg="#fed7aa", bg="#431407", padx=12, pady=4
        )
        self.active_profile_badge.pack(side="left", padx=(18, 0))

        fs_btn = SoftButton(header, text="Tam Ekran (F11)", command=self.toggle_fullscreen,
                            bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b",
                            height=32, radius=12, font=("Segoe UI", 8, "bold"))
        fs_btn.configure(width=120)
        fs_btn.pack(side="right")
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())

        body = tk.Frame(self.root, bg=self.bg_main, padx=12, pady=6)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=6)
        body.rowconfigure(0, weight=1)

        # --- SOL PANEL ---
        left_panel = tk.Frame(body, bg=self.bg_main)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(3, weight=1)
        left_panel.columnconfigure(0, weight=1)

        # 1. Hesap Kartı
        acc_card = tk.Frame(left_panel, bg=self.bg_card, padx=14, pady=12)
        acc_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        tk.Label(acc_card, text="ÖZEL HESAPLAR", font=("Segoe UI", 9, "bold"),
                 fg=self.accent_fox, bg=self.bg_card).pack(anchor="w")

        acc_row = tk.Frame(acc_card, bg=self.bg_card)
        acc_row.pack(fill="x", pady=(6, 6))
        self.account_combo = ttk.Combobox(acc_row, state="readonly", font=("Segoe UI", 9))
        self.account_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.account_combo.bind("<<ComboboxSelected>>", self._on_account_selected)

        del_acc_btn = SoftButton(acc_row, text="Sil", command=self.delete_account,
                                 bg="#7f1d1d", hover_bg="#991b1b", active_bg="#450a0a",
                                 height=30, radius=10, font=("Segoe UI", 8, "bold"))
        del_acc_btn.configure(width=54)
        del_acc_btn.pack(side="left")

        new_acc_row = tk.Frame(acc_card, bg=self.bg_card)
        new_acc_row.pack(fill="x")
        self.new_account_entry = tk.Entry(new_acc_row, bg=self.bg_input, fg=self.text_main,
                                          insertbackground=self.text_main, relief="flat", bd=6, font=("Segoe UI", 9))
        self.new_account_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        add_acc_btn = SoftButton(new_acc_row, text="+ Hesap Ekle", command=self.add_account,
                                 bg=self.accent_blue, hover_bg="#60a5fa", active_bg="#2563eb",
                                 height=30, radius=10, font=("Segoe UI", 8, "bold"))
        add_acc_btn.configure(width=98)
        add_acc_btn.pack(side="left")

        # 2. Sürüm & Loader & RAM Kartı
        ver_card = tk.Frame(left_panel, bg=self.bg_card, padx=14, pady=12)
        ver_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ver_card.columnconfigure(0, weight=2)
        ver_card.columnconfigure(1, weight=2)
        ver_card.columnconfigure(2, weight=1)

        tk.Label(ver_card, text="Sürüm", font=("Segoe UI", 8, "bold"), fg=self.text_muted,
                 bg=self.bg_card).grid(row=0, column=0, sticky="w")
        tk.Label(ver_card, text="Loader", font=("Segoe UI", 8, "bold"), fg=self.text_muted,
                 bg=self.bg_card).grid(row=0, column=1, sticky="w", padx=(8, 0))
        tk.Label(ver_card, text="RAM (MB)", font=("Segoe UI", 8, "bold"), fg=self.text_muted,
                 bg=self.bg_card).grid(row=0, column=2, sticky="w", padx=(8, 0))

        self.version_combo = ttk.Combobox(ver_card, state="readonly", font=("Segoe UI", 9))
        self.version_combo.grid(row=1, column=0, sticky="ew", pady=(4, 8))

        self.loader_combo = ttk.Combobox(ver_card, state="readonly", font=("Segoe UI", 9),
                                         values=["fabric", "forge", "quilt", "neoforge", "vanilla"])
        self.loader_combo.current(0)
        self.loader_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 8))

        self.ram_entry = tk.Entry(ver_card, bg=self.bg_input, fg=self.text_main, width=7,
                                  insertbackground=self.text_main, relief="flat", bd=5, font=("Segoe UI", 9))
        self.ram_entry.insert(0, str(self.config.get("ram_mb", 4096)))
        self.ram_entry.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(4, 8))

        self.check_assets_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ver_card, text="Ses/Asset bütünlüğünü zorla kontrol et (yavaşlatır)",
                       variable=self.check_assets_var, bg=self.bg_card, fg=self.text_muted,
                       selectcolor=self.bg_input, activebackground=self.bg_card,
                       activeforeground=self.text_main, font=("Segoe UI", 8)).grid(row=2, column=0, columnspan=3, sticky="w")

        # 3. Başlat & Zorla Kapat Kartı
        launch_card = tk.Frame(left_panel, bg=self.bg_card, padx=14, pady=12)
        launch_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.status_label = tk.Label(launch_card, text="Sürümler yükleniyor...", font=("Segoe UI", 9, "bold"),
                                     fg="#fdba74", bg=self.bg_card, wraplength=360, justify="left")
        self.status_label.pack(anchor="w", pady=(0, 8))

        launch_btn_row = tk.Frame(launch_card, bg=self.bg_card)
        launch_btn_row.pack(fill="x")

        self.play_btn = SoftButton(
            launch_btn_row, text="OYNA (FLC BAŞLAT)", command=self.start_launch_thread,
            bg="#ea580c", hover_bg="#f97316", active_bg="#c2410c", height=42, radius=14,
            font=("Segoe UI", 10, "bold")
        )
        self.play_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.kill_btn = SoftButton(
            launch_btn_row, text="Zorla Kapat", command=self.force_close_game,
            bg="#991b1b", hover_bg="#dc2626", active_bg="#7f1d1d", height=42, radius=14,
            font=("Segoe UI", 9, "bold")
        )
        self.kill_btn.configure(width=105)
        self.kill_btn.set_enabled(False)
        self.kill_btn.pack(side="left")

        # 4. Canlı Log Kartı
        log_card = tk.Frame(left_panel, bg=self.bg_card, padx=14, pady=10)
        log_card.grid(row=3, column=0, sticky="nsew")
        log_card.rowconfigure(1, weight=1)
        log_card.columnconfigure(0, weight=1)

        log_top = tk.Frame(log_card, bg=self.bg_card)
        log_top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(log_top, text="CANLI LOGLAR", font=("Segoe UI", 9, "bold"),
                 fg="#5eead4", bg=self.bg_card).pack(side="left")

        clr_btn = SoftButton(log_top, text="Temizle", command=self.clear_logs,
                             bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b",
                             height=24, radius=9, font=("Segoe UI", 8))
        clr_btn.configure(width=64)
        clr_btn.pack(side="right")

        scroll = tk.Scrollbar(log_card)
        scroll.grid(row=1, column=1, sticky="ns")
        self.log_text = tk.Text(log_card, bg="#0b0e13", fg="#d4d4d4", font=("Consolas", 8),
                                state="disabled", wrap="word", yscrollcommand=scroll.set, relief="flat", bd=6)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        scroll.config(command=self.log_text.yview)

        # --- SAĞ PANEL ---
        right_panel = ttk.Notebook(body)
        right_panel.grid(row=0, column=1, sticky="nsew")

        # SEKME 1: Mod İndir & Detaylar
        search_tab = tk.Frame(right_panel, bg=self.bg_card, padx=14, pady=12)
        right_panel.add(search_tab, text=" Mod İndir & Detaylar ")

        row1 = tk.Frame(search_tab, bg=self.bg_card)
        row1.pack(fill="x", pady=(0, 8))

        self.source_combo = ttk.Combobox(row1, width=12, state="readonly", values=["Modrinth", "CurseForge"])
        self.source_combo.current(0)
        self.source_combo.pack(side="left", padx=(0, 8))

        self.mod_search_entry = tk.Entry(row1, bg=self.bg_input, fg=self.text_main,
                                         insertbackground=self.text_main, relief="flat", bd=6, font=("Segoe UI", 10))
        self.mod_search_entry.insert(0, "sodium")
        self.mod_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.mod_search_entry.bind("<Return>", lambda e: self.start_search_thread())

        search_btn = SoftButton(row1, text="Ara", command=self.start_search_thread,
                                bg=self.accent_blue, hover_bg="#60a5fa", active_bg="#2563eb",
                                height=32, radius=11, font=("Segoe UI", 9, "bold"))
        search_btn.configure(width=76)
        search_btn.pack(side="left")

        row2 = tk.Frame(search_tab, bg=self.bg_card)
        row2.pack(fill="x", pady=(0, 8))
        tk.Label(row2, text="CurseForge API Key (opsiyonel):", fg=self.text_muted,
                 bg=self.bg_card, font=("Segoe UI", 8)).pack(side="left")
        self.cf_key_entry = tk.Entry(row2, bg=self.bg_input, fg=self.text_main, show="*",
                                     relief="flat", bd=4, font=("Segoe UI", 8))
        self.cf_key_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.results_listbox = tk.Listbox(search_tab, height=8, bg=self.bg_input, fg=self.text_main,
                                          selectmode=tk.SINGLE, font=("Segoe UI", 9), relief="flat", bd=8,
                                          selectbackground=self.accent_fox, highlightthickness=0)
        self.results_listbox.pack(fill="both", expand=True, pady=(0, 10))
        self.results_listbox.bind("<<ListboxSelect>>", self.on_mod_result_select)

        detail_card = tk.Frame(search_tab, bg="#11161f", padx=12, pady=10)
        detail_card.pack(fill="x", pady=(0, 10))

        self.mod_logo_label = tk.Label(detail_card, text="MOD\nLOGOSU", width=10, height=5,
                                       bg="#1e2633", fg="#64748b", font=("Segoe UI", 8, "bold"))
        self.mod_logo_label.pack(side="left", padx=(0, 12))

        info_col = tk.Frame(detail_card, bg="#11161f")
        info_col.pack(side="left", fill="both", expand=True)

        self.mod_title_label = tk.Label(info_col, text="Bir mod seçerek logosunu ve bilgilerini görüntüle",
                                        font=("Segoe UI", 11, "bold"), fg="#f8fafc", bg="#11161f", anchor="w")
        self.mod_title_label.pack(fill="x")

        self.mod_meta_label = tk.Label(info_col, text="Durum: -  |  Yazar: -  |  İndirme: -",
                                       font=("Segoe UI", 8, "bold"), fg="#fb923c", bg="#11161f", anchor="w")
        self.mod_meta_label.pack(fill="x", pady=(2, 4))

        self.mod_desc_label = tk.Label(info_col, text="Arama listesinden herhangi bir moda tıkladığında açıklaması ve yüklü olup olmadığı burada görünür.",
                                       font=("Segoe UI", 9), fg="#cbd5e1", bg="#11161f",
                                       wraplength=430, justify="left", anchor="w")
        self.mod_desc_label.pack(fill="x")

        self.dl_mod_btn = SoftButton(
            search_tab, text="Seçili Modu + Gerekli Bağımlılıkları Aktif Profile İndir",
            command=self.start_mod_download_thread,
            bg="#16a34a", hover_bg="#22c55e", active_bg="#15803d", height=38, radius=13
        )
        self.dl_mod_btn.pack(fill="x")

        # SEKME 2: Tüm Profiller (Özel + PolyMC Karışık)
        profiles_tab = tk.Frame(right_panel, bg=self.bg_card, padx=14, pady=12)
        right_panel.add(profiles_tab, text=" Tüm Profiller (Özel + PolyMC) ")

        create_box = tk.Frame(profiles_tab, bg="#11161f", padx=12, pady=10)
        create_box.pack(fill="x", pady=(0, 10))
        create_box.columnconfigure(0, weight=2)
        create_box.columnconfigure(1, weight=1)
        create_box.columnconfigure(2, weight=1)
        create_box.columnconfigure(3, weight=1)

        tk.Label(create_box, text="Yeni Profil Adı", fg=self.text_muted, bg="#11161f", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(create_box, text="MC Sürümü", fg=self.text_muted, bg="#11161f", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w", padx=(8, 0))
        tk.Label(create_box, text="Loader", fg=self.text_muted, bg="#11161f", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="w", padx=(8, 0))
        tk.Label(create_box, text="RAM (MB)", fg=self.text_muted, bg="#11161f", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, sticky="w", padx=(8, 0))

        self.new_prof_name = tk.Entry(create_box, bg=self.bg_input, fg=self.text_main,
                                      insertbackground=self.text_main, relief="flat", bd=5, font=("Segoe UI", 9))
        self.new_prof_name.insert(0, "Survival Modlu")
        self.new_prof_name.grid(row=1, column=0, sticky="ew", pady=(3, 8))

        self.new_prof_ver = ttk.Combobox(create_box, state="readonly", font=("Segoe UI", 9), width=11)
        self.new_prof_ver.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(3, 8))

        self.new_prof_loader = ttk.Combobox(create_box, state="readonly", font=("Segoe UI", 9), width=10,
                                            values=["fabric", "forge", "neoforge", "quilt", "vanilla"])
        self.new_prof_loader.current(0)
        self.new_prof_loader.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(3, 8))

        self.new_prof_ram = tk.Entry(create_box, bg=self.bg_input, fg=self.text_main, width=7,
                                     insertbackground=self.text_main, relief="flat", bd=5, font=("Segoe UI", 9))
        self.new_prof_ram.insert(0, "4096")
        self.new_prof_ram.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(3, 8))

        create_btn = SoftButton(create_box, text="+ Yeni Profil Oluştur ve Aktif Yap", command=self.create_custom_profile,
                                bg=self.accent_fox, hover_bg="#fb923c", active_bg="#ea580c",
                                height=32, radius=11, font=("Segoe UI", 9, "bold"))
        create_btn.grid(row=2, column=0, columnspan=4, sticky="ew")

        prof_top_row = tk.Frame(profiles_tab, bg=self.bg_card)
        prof_top_row.pack(fill="x", pady=(0, 6))

        tk.Label(prof_top_row, text="Tüm Profiller (Özel & PolyMC Karışık)", font=("Segoe UI", 9, "bold"),
                 fg=self.text_main, bg=self.bg_card).pack(side="left")

        poly_folder_btn = SoftButton(prof_top_row, text="PolyMC Klasörü Seç...", command=self.choose_polymc_folder,
                                     bg=self.accent_purple, hover_bg="#a78bfa", active_bg="#7c3aed",
                                     height=26, radius=9, font=("Segoe UI", 8, "bold"))
        poly_folder_btn.configure(width=135)
        poly_folder_btn.pack(side="right")

        ref_all_p_btn = SoftButton(prof_top_row, text="Yenile", command=self.refresh_all_profiles,
                                   bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b",
                                   height=26, radius=9, font=("Segoe UI", 8, "bold"))
        ref_all_p_btn.configure(width=65)
        ref_all_p_btn.pack(side="right", padx=(0, 6))

        self.all_prof_listbox = tk.Listbox(profiles_tab, bg=self.bg_input, fg=self.text_main,
                                           selectmode=tk.SINGLE, font=("Segoe UI", 9), relief="flat", bd=8,
                                           selectbackground=self.accent_fox, highlightthickness=0)
        self.all_prof_listbox.pack(fill="both", expand=True, pady=(0, 8))
        self.all_prof_listbox.bind("<<ListboxSelect>>", self.on_unified_profile_select)

        self.prof_detail_label = tk.Label(
            profiles_tab, text="Listeden bir profil seçerek detaylarını görebilir, aktif edebilir veya silebilirsin.",
            font=("Segoe UI", 8), fg="#e2e8f0", bg="#11161f", padx=10, pady=6, justify="left", anchor="w"
        )
        self.prof_detail_label.pack(fill="x", pady=(0, 8))

        prof_btns = tk.Frame(profiles_tab, bg=self.bg_card)
        prof_btns.pack(fill="x")

        act_p_btn = SoftButton(prof_btns, text="Seçili Profili Aktif Yap", command=self.activate_selected_profile,
                               bg=self.accent_blue, hover_bg="#60a5fa", active_bg="#2563eb", height=34, radius=11)
        act_p_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        imp_p_btn = SoftButton(prof_btns, text="Modları .minecraft'a Aktar", command=self.import_selected_profile_mods,
                               bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b", height=34, radius=11,
                               font=("Segoe UI", 8, "bold"))
        imp_p_btn.configure(width=155)
        imp_p_btn.pack(side="left", padx=(0, 6))

        del_p_btn = SoftButton(prof_btns, text="Profili Sil", command=self.delete_selected_profile,
                               bg="#991b1b", hover_bg="#b91c1c", active_bg="#7f1d1d", height=34, radius=11)
        del_p_btn.configure(width=92)
        del_p_btn.pack(side="left")

        # SEKME 3: Kurulu Modlarım
        installed_tab = tk.Frame(right_panel, bg=self.bg_card, padx=14, pady=12)
        right_panel.add(installed_tab, text=" Kurulu Modlarım ")

        inst_top = tk.Frame(installed_tab, bg=self.bg_card)
        inst_top.pack(fill="x", pady=(0, 8))
        self.installed_count_label = tk.Label(inst_top, text="Kurulu Mod: 0", font=("Segoe UI", 10, "bold"),
                                              fg="#fb923c", bg=self.bg_card)
        self.installed_count_label.pack(side="left")

        ref_m_btn = SoftButton(inst_top, text="Listeyi Yenile", command=self.refresh_installed_mods,
                               bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b",
                               height=30, radius=10, font=("Segoe UI", 8, "bold"))
        ref_m_btn.configure(width=100)
        ref_m_btn.pack(side="right")

        open_m_btn = SoftButton(inst_top, text="Mods Klasörünü Aç", command=self.open_mods_folder,
                                bg=self.bg_input, hover_bg="#2d3748", active_bg="#1e293b",
                                height=30, radius=10, font=("Segoe UI", 8, "bold"))
        open_m_btn.configure(width=130)
        open_m_btn.pack(side="right", padx=(0, 8))

        self.installed_listbox = tk.Listbox(installed_tab, bg=self.bg_input, fg=self.text_main,
                                            selectmode=tk.SINGLE, font=("Segoe UI", 9), relief="flat", bd=8,
                                            selectbackground=self.accent_fox, highlightthickness=0)
        self.installed_listbox.pack(fill="both", expand=True, pady=(0, 10))
        self.installed_listbox.bind("<<ListboxSelect>>", self.on_installed_mod_select)

        inst_detail = tk.Frame(installed_tab, bg="#11161f", padx=12, pady=10)
        inst_detail.pack(fill="x", pady=(0, 10))

        self.inst_logo_label = tk.Label(inst_detail, text="MOD\nİKONU", width=9, height=4,
                                        bg="#1e2633", fg="#64748b", font=("Segoe UI", 8, "bold"))
        self.inst_logo_label.pack(side="left", padx=(0, 12))

        inst_info = tk.Frame(inst_detail, bg="#11161f")
        inst_info.pack(side="left", fill="both", expand=True)

        self.inst_title_label = tk.Label(inst_info, text="Bir mod seçerek logosunu ve durumunu gör",
                                         font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#11161f", anchor="w")
        self.inst_title_label.pack(fill="x")

        self.inst_state_label = tk.Label(inst_info, text="Durum: -  |  Dosya: -",
                                         font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#11161f", anchor="w")
        self.inst_state_label.pack(fill="x", pady=(2, 2))

        self.inst_desc_label = tk.Label(inst_info, text="Devre dışı bırakılan modlar '.jar.disabled' uzantısıyla saklanır ve oyuna girerken yüklenmez.",
                                        font=("Segoe UI", 8), fg="#cbd5e1", bg="#11161f",
                                        wraplength=420, justify="left", anchor="w")
        self.inst_desc_label.pack(fill="x")

        inst_btns = tk.Frame(installed_tab, bg=self.bg_card)
        inst_btns.pack(fill="x")

        self.toggle_mod_btn = SoftButton(
            inst_btns, text="Modu Devre Dışı Bırak / Aktif Et", command=self.toggle_selected_mod_state,
            bg="#d97706", hover_bg="#f59e0b", active_bg="#b45309", height=36, radius=12
        )
        self.toggle_mod_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        del_m_btn = SoftButton(inst_btns, text="Seçili Modu Sil", command=self.delete_selected_mod,
                               bg="#991b1b", hover_bg="#b91c1c", active_bg="#7f1d1d", height=36, radius=12)
        del_m_btn.configure(width=135)
        del_m_btn.pack(side="left")

    def _slugify(self, name):
        clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
        return clean or "profil"

    def _detect_polymc_instances_dirs(self):
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        userprofile = os.environ.get("USERPROFILE", "")
        candidates = [
            self.config.get("polymc_instances_dir", ""),
            os.path.join(appdata, "PolyMC", "instances"),
            os.path.join(appdata, "PrismLauncher", "instances"),
            os.path.join(appdata, "MultiMC", "instances"),
            os.path.join(localappdata, "PolyMC", "instances"),
            os.path.join(userprofile, "Desktop", "PolyMC", "instances"),
            r"C:\PolyMC\instances",
        ]
        return [c for c in dict.fromkeys(candidates) if c and os.path.isdir(c)]

    def choose_polymc_folder(self):
        chosen = filedialog.askdirectory(title="PolyMC 'instances' klasörünü seç")
        if not chosen:
            return
        if os.path.isfile(os.path.join(chosen, "mmc-pack.json")) or os.path.isfile(os.path.join(chosen, "instance.cfg")):
            instances_root = os.path.dirname(chosen)
        else:
            instances_root = chosen
        self.config["polymc_instances_dir"] = instances_root
        self._save_config()
        self.refresh_all_profiles()

    def _parse_polymc_instance(self, inst_path):
        folder_name = os.path.basename(inst_path)
        display_name = folder_name
        cfg_path = os.path.join(inst_path, "instance.cfg")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("name="):
                            val = line.split("=", 1)[1].strip()
                            if val:
                                display_name = val
                            break
            except Exception:
                pass

        mc_version, loader, loader_version = "", "vanilla", ""
        pack_path = os.path.join(inst_path, "mmc-pack.json")
        if os.path.isfile(pack_path):
            try:
                with open(pack_path, "r", encoding="utf-8") as f:
                    pack = json.load(f)
                for comp in pack.get("components", []):
                    uid = comp.get("uid", "")
                    ver = comp.get("version", "")
                    if uid == "net.minecraft":
                        mc_version = ver
                    elif uid == "net.fabricmc.fabric-loader":
                        loader, loader_version = "fabric", ver
                    elif uid == "net.minecraftforge":
                        loader, loader_version = "forge", ver
                    elif uid == "net.neoforged":
                        loader, loader_version = "neoforge", ver
                    elif uid == "org.quiltmc.quilt-loader":
                        loader, loader_version = "quilt", ver
            except Exception:
                pass

        game_dir = next((os.path.join(inst_path, s) for s in (".minecraft", "minecraft")
                         if os.path.isdir(os.path.join(inst_path, s))), None)
        if not game_dir:
            return None

        mods_folder = os.path.join(game_dir, "mods")
        mod_count = len([f for f in os.listdir(mods_folder) if f.lower().endswith((".jar", ".jar.disabled"))]) if os.path.isdir(mods_folder) else 0

        return {
            "type": "polymc",
            "name": display_name,
            "folder": folder_name,
            "inst_path": inst_path,
            "game_dir": game_dir,
            "mc_version": mc_version,
            "loader": loader,
            "loader_version": loader_version,
            "mod_count": mod_count,
            "ram_mb": self.config.get("ram_mb", 4096),
        }

    def refresh_all_profiles(self):
        self.all_profiles.clear()
        self.all_prof_listbox.delete(0, tk.END)

        std_mods = os.path.join(self.default_mc_dir, "mods")
        std_c = len([x for x in os.listdir(std_mods) if x.lower().endswith((".jar", ".jar.disabled"))]) if os.path.isdir(std_mods) else 0
        std_prof = {
            "type": "default",
            "name": "Standart (.minecraft)",
            "game_dir": self.default_mc_dir,
            "mc_version": self.version_combo.get().strip() if hasattr(self, "version_combo") else "",
            "loader": self.loader_combo.get().strip() if hasattr(self, "loader_combo") else "fabric",
            "ram_mb": self.config.get("ram_mb", 4096),
            "mod_count": std_c,
        }
        self.all_profiles.append(std_prof)

        for entry in sorted(os.listdir(self.custom_profiles_root)):
            p_dir = os.path.join(self.custom_profiles_root, entry)
            meta_file = os.path.join(p_dir, "profile.json")
            if os.path.isfile(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["type"] = "custom"
                    meta["game_dir"] = p_dir
                    mods_c = len([x for x in os.listdir(os.path.join(p_dir, "mods")) if x.lower().endswith((".jar", ".jar.disabled"))]) if os.path.isdir(os.path.join(p_dir, "mods")) else 0
                    meta["mod_count"] = mods_c
                    self.all_profiles.append(meta)
                except Exception:
                    pass

        for root_dir in self._detect_polymc_instances_dirs():
            for entry in sorted(os.listdir(root_dir)):
                full = os.path.join(root_dir, entry)
                if os.path.isdir(full) and not entry.startswith("_"):
                    parsed = self._parse_polymc_instance(full)
                    if parsed:
                        self.all_profiles.append(parsed)

        for idx, p in enumerate(self.all_profiles):
            if p["type"] == "default":
                tag = "[STANDART]"
            elif p["type"] == "custom":
                tag = "[ÖZEL]"
            else:
                tag = "[POLYMC]"

            active_mark = "  ★ AKTİF" if os.path.normpath(p["game_dir"]) == os.path.normpath(self.active_game_dir) else ""
            ver_txt = f"MC {p['mc_version']}" if p.get("mc_version") else "MC ?"
            self.all_prof_listbox.insert(
                tk.END,
                f"{tag}  {p['name']}  —  {ver_txt} ({p.get('loader', 'fabric')})  |  {p.get('mod_count', 0)} mod{active_mark}"
            )
            if p["type"] == "polymc":
                self.all_prof_listbox.itemconfig(idx, fg="#c4b5fd")
            elif p["type"] == "custom":
                self.all_prof_listbox.itemconfig(idx, fg="#fdba74")
            else:
                self.all_prof_listbox.itemconfig(idx, fg="#93c5fd")

    def on_unified_profile_select(self, event=None):
        sel = self.all_prof_listbox.curselection()
        if not sel:
            return
        p = self.all_profiles[sel[0]]
        kind = {"default": "Standart", "custom": "Özel Profil", "polymc": "PolyMC Profili"}.get(p["type"], "Profil")
        self.prof_detail_label.config(
            text=(
                f"Tür: {kind}  |  Ad: {p['name']}  |  Sürüm: {p.get('mc_version') or '?'} ({p.get('loader', '-')})\n"
                f"Klasör: {p['game_dir']}"
            )
        )

    def create_custom_profile(self):
        name = self.new_prof_name.get().strip()
        mc_ver = self.new_prof_ver.get().strip() or self.version_combo.get().strip()
        loader = self.new_prof_loader.get().strip()
        try:
            ram_mb = max(1024, int(self.new_prof_ram.get().strip()))
        except ValueError:
            ram_mb = 4096

        if not name or not mc_ver:
            messagebox.showwarning("Uyarı", "Profil adı ve Minecraft sürümü seçmelisin.")
            return

        folder_name = self._slugify(name)
        prof_dir = os.path.join(self.custom_profiles_root, folder_name)
        os.makedirs(os.path.join(prof_dir, "mods"), exist_ok=True)

        meta = {
            "type": "custom",
            "name": name,
            "folder": folder_name,
            "game_dir": prof_dir,
            "mc_version": mc_ver,
            "loader": loader,
            "ram_mb": ram_mb,
        }
        with open(os.path.join(prof_dir, "profile.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self._apply_profile(meta)
        self.log(f"Yeni profil oluşturuldu: {name} (MC {mc_ver} / {loader})")

    def activate_selected_profile(self):
        sel = self.all_prof_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Listeden bir profil seçmelisin.")
            return
        self._apply_profile(self.all_profiles[sel[0]])

    def delete_selected_profile(self):
        sel = self.all_prof_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Silmek için listeden bir profil seçmelisin.")
            return
        prof = self.all_profiles[sel[0]]
        if prof["type"] == "default":
            messagebox.showinfo("Bilgi", "Standart (.minecraft) ana dizini silinemez.")
            return

        target_dir = prof.get("inst_path") if prof["type"] == "polymc" else prof["game_dir"]
        if messagebox.askyesno("Profili Sil", f"'{prof['name']}' profilini ve içindeki dosyaları kalıcı olarak silmek istiyor musun?"):
            shutil.rmtree(target_dir, ignore_errors=True)
            if os.path.normpath(self.active_game_dir) == os.path.normpath(prof["game_dir"]):
                self.reset_to_default_mc_dir()
            self.refresh_all_profiles()
            self.log(f"Profil silindi: {prof['name']}")

    def import_selected_profile_mods(self):
        sel = self.all_prof_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Modlarını aktarmak için listeden bir profil seçmelisin.")
            return
        p = self.all_profiles[sel[0]]
        if p["type"] == "default":
            messagebox.showinfo("Bilgi", "Bu zaten standart .minecraft profili.")
            return
        src_mods = os.path.join(p["game_dir"], "mods")
        if not os.path.isdir(src_mods):
            messagebox.showinfo("Bilgi", "Bu profilde mods klasörü bulunamadı.")
            return
        dst_mods = os.path.join(self.default_mc_dir, "mods")
        os.makedirs(dst_mods, exist_ok=True)
        copied = 0
        for j in [f for f in os.listdir(src_mods) if f.lower().endswith((".jar", ".jar.disabled"))]:
            dst_file = os.path.join(dst_mods, j)
            if not os.path.exists(dst_file):
                shutil.copy2(os.path.join(src_mods, j), dst_file)
                copied += 1
        self.refresh_installed_mods()
        self.refresh_all_profiles()
        self.update_status(f"{copied} mod standart .minecraft/mods içine kopyalandı.", also_log=True)

    def _apply_profile(self, prof):
        if prof["type"] == "default":
            self.reset_to_default_mc_dir()
            return

        self.active_profile_info = prof
        self.active_game_dir = prof["game_dir"]
        if prof.get("mc_version") and prof["mc_version"] in self.version_combo["values"]:
            self.version_combo.set(prof["mc_version"])
        if prof.get("loader") in ("fabric", "forge", "quilt", "neoforge", "vanilla"):
            self.loader_combo.set(prof["loader"])
        if prof.get("ram_mb"):
            self.ram_entry.delete(0, tk.END)
            self.ram_entry.insert(0, str(prof["ram_mb"]))

        tag = "PolyMC" if prof.get("type") == "polymc" else "Özel Profil"
        self.active_profile_badge.config(
            text=f"{tag}: {prof['name']} ({prof.get('mc_version') or '?'})",
            bg="#431407" if tag == "Özel Profil" else "#3b0764",
            fg="#fed7aa"
        )
        self.refresh_all_profiles()
        self.refresh_installed_mods()
        if self.search_results:
            self.populate_results()
        self.update_status(f"Aktif profil: {prof['name']}", also_log=True)

    def reset_to_default_mc_dir(self):
        self.active_profile_info = None
        self.active_game_dir = self.default_mc_dir
        self.active_profile_badge.config(
            text="Aktif Profil: Standart (.minecraft)", bg="#431407", fg="#fed7aa"
        )
        self.refresh_all_profiles()
        self.refresh_installed_mods()
        if self.search_results:
            self.populate_results()
        self.update_status("Standart .minecraft profiline dönüldü.", also_log=True)

    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def _refresh_accounts_ui(self):
        self.account_combo["values"] = self.config["users"]
        self.account_combo.set(self.config["active"])

    def _on_account_selected(self, event=None):
        chosen = self.account_combo.get().strip()
        if chosen:
            self.config["active"] = chosen
            self._save_config()
            self.log(f"Aktif hesap: {chosen}")

    def add_account(self):
        name = self.new_account_entry.get().strip()
        if not name:
            return
        if name not in self.config["users"]:
            self.config["users"].append(name)
        self.config["active"] = name
        self.new_account_entry.delete(0, tk.END)
        self._save_config()
        self._refresh_accounts_ui()
        self.log(f"Hesap eklendi: {name}")

    def delete_account(self):
        name = self.account_combo.get().strip()
        if len(self.config["users"]) <= 1:
            messagebox.showwarning("Uyarı", "En az bir hesap kalmalıdır.")
            return
        if name in self.config["users"]:
            self.config["users"].remove(name)
            self.config["active"] = self.config["users"][0]
            self._save_config()
            self._refresh_accounts_ui()
            self.log(f"Hesap silindi: {name}")

    def _inspect_mod_jar(self, jar_path):
        filename = os.path.basename(jar_path)
        base_clean = re.sub(r"\.jar(\.disabled)?$", "", filename, flags=re.IGNORECASE)
        info = {
            "title": base_clean,
            "version": "",
            "description": "Yerel mod dosyası.",
            "icon_bytes": None,
        }
        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                names = zf.namelist()
                icon_candidate = None
                if "fabric.mod.json" in names:
                    raw = zf.read("fabric.mod.json").decode("utf-8", errors="ignore")
                    meta = json.loads(raw)
                    info["title"] = meta.get("name") or meta.get("id") or base_clean
                    info["version"] = meta.get("version", "")
                    info["description"] = (meta.get("description") or "Fabric modu.").strip()[:180]
                    icon_val = meta.get("icon")
                    if isinstance(icon_val, str):
                        icon_candidate = icon_val.lstrip("/")
                    elif isinstance(icon_val, dict) and icon_val:
                        icon_candidate = list(icon_val.values())[-1].lstrip("/")
                elif "quilt.mod.json" in names:
                    raw = zf.read("quilt.mod.json").decode("utf-8", errors="ignore")
                    meta = json.loads(raw).get("quilt_loader", {}).get("metadata", {})
                    info["title"] = meta.get("name") or base_clean
                    info["description"] = (meta.get("description") or "Quilt modu.").strip()[:180]
                    if isinstance(meta.get("icon"), str):
                        icon_candidate = meta["icon"].lstrip("/")
                elif "META-INF/mods.toml" in names or "META-INF/neoforge.mods.toml" in names:
                    toml_name = "META-INF/neoforge.mods.toml" if "META-INF/neoforge.mods.toml" in names else "META-INF/mods.toml"
                    txt = zf.read(toml_name).decode("utf-8", errors="ignore")
                    m_name = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', txt)
                    m_logo = re.search(r'logoFile\s*=\s*["\']([^"\']+)["\']', txt)
                    if m_name:
                        info["title"] = m_name.group(1)
                    if m_logo:
                        icon_candidate = m_logo.group(1).lstrip("/")

                if icon_candidate and icon_candidate in names:
                    info["icon_bytes"] = zf.read(icon_candidate)
                else:
                    pngs = [n for n in names if n.lower().endswith(".png") and "/" not in n]
                    if pngs:
                        info["icon_bytes"] = zf.read(pngs[0])
        except Exception:
            pass
        return info

    def _make_badge_photo(self, title_text, active=True):
        size = 64
        palette = ["#f97316", "#3b82f6", "#8b5cf6", "#10b981", "#ec4899", "#06b6d4"]
        bg_hex = palette[sum(ord(c) for c in title_text) % len(palette)] if active else "#334155"
        letter = (title_text.strip()[:1] or "M").upper()

        if HAS_PIL:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([2, 2, size - 3, size - 3], radius=14, fill=bg_hex)
            draw.text((size // 2 - 8, size // 2 - 12), letter, fill="#ffffff")
            return ImageTk.PhotoImage(img)

        photo = tk.PhotoImage(width=size, height=size)
        row = "{" + " ".join([bg_hex] * size) + "}"
        photo.put(" ".join([row] * size))
        return photo

    def refresh_installed_mods(self):
        mods_dir = self.get_current_mods_dir()
        files = sorted([f for f in os.listdir(mods_dir) if f.lower().endswith((".jar", ".jar.disabled"))])
        self.installed_mods_data.clear()
        self.installed_listbox.delete(0, tk.END)

        active_count = 0
        for idx, fn in enumerate(files):
            full_path = os.path.join(mods_dir, fn)
            is_enabled = fn.lower().endswith(".jar")
            if is_enabled:
                active_count += 1
            size_kb = os.path.getsize(full_path) / 1024
            meta = self._inspect_mod_jar(full_path)
            entry = {
                "filename": fn,
                "path": full_path,
                "enabled": is_enabled,
                "size_kb": size_kb,
                "title": meta["title"],
                "version": meta["version"],
                "description": meta["description"],
                "icon_bytes": meta["icon_bytes"],
            }
            self.installed_mods_data.append(entry)

            state_tag = "[AKTİF]" if is_enabled else "[PASİF]"
            ver_str = f" v{meta['version']}" if meta["version"] else ""
            self.installed_listbox.insert(
                tk.END,
                f"{state_tag}  {meta['title']}{ver_str}  ({fn} • {size_kb:.1f} KB)"
            )
            self.installed_listbox.itemconfig(idx, fg="#86efac" if is_enabled else "#94a3b8")

        prefix = self.active_profile_info["name"] if self.active_profile_info else ".minecraft"
        self.installed_count_label.config(
            text=f"[{prefix}] Toplam: {len(files)} Mod ({active_count} Aktif, {len(files) - active_count} Pasif)"
        )

    def on_installed_mod_select(self, event=None):
        sel = self.installed_listbox.curselection()
        if not sel:
            return
        mod = self.installed_mods_data[sel[0]]
        state_txt = "AKTİF (Oyunda yüklenecek)" if mod["enabled"] else "DEVRE DIŞI / PASİF (Oyunda yüklenmeyecek)"
        self.inst_title_label.config(text=f"{mod['title']} {('v' + mod['version']) if mod['version'] else ''}")
        self.inst_state_label.config(
            text=f"Durum: {state_txt}  |  Dosya: {mod['filename']}",
            fg="#4ade80" if mod["enabled"] else "#fbbf24"
        )
        self.inst_desc_label.config(text=mod["description"])

        if mod["enabled"]:
            self.toggle_mod_btn.set_text("Seçili Modu Devre Dışı Bırak (Pasif Yap)")
            self.toggle_mod_btn.set_colors("#d97706", "#f59e0b", "#b45309")
        else:
            self.toggle_mod_btn.set_text("Seçili Modu Aktif Et")
            self.toggle_mod_btn.set_colors("#16a34a", "#22c55e", "#15803d")

        cache_key = (mod["path"], mod["enabled"])
        if cache_key in self.installed_icon_cache:
            photo = self.installed_icon_cache[cache_key]
        else:
            photo = None
            if mod["icon_bytes"] and HAS_PIL:
                try:
                    pil_img = Image.open(io.BytesIO(mod["icon_bytes"])).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
                    if not mod["enabled"]:
                        pil_img = pil_img.convert("LA").convert("RGBA")
                    photo = ImageTk.PhotoImage(pil_img)
                except Exception:
                    photo = None
            if not photo:
                photo = self._make_badge_photo(mod["title"], active=mod["enabled"])
            self.installed_icon_cache[cache_key] = photo

        self.current_installed_photo = photo
        self.inst_logo_label.config(image=photo, text="", width=64, height=64)

    def toggle_selected_mod_state(self):
        sel = self.installed_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Aktif/Pasif yapmak için listeden bir mod seçmelisin.")
            return
        idx = sel[0]
        mod = self.installed_mods_data[idx]
        old_path = mod["path"]
        if mod["enabled"]:
            new_path = old_path + ".disabled"
            action_msg = f"Mod devre dışı bırakıldı: {mod['title']}"
        else:
            new_path = re.sub(r"\.disabled$", "", old_path, flags=re.IGNORECASE)
            action_msg = f"Mod aktif edildi: {mod['title']}"

        try:
            os.rename(old_path, new_path)
            self.log(action_msg)
            self.refresh_installed_mods()
            self.installed_listbox.selection_set(idx)
            self.on_installed_mod_select()
        except Exception as e:
            messagebox.showerror("Hata", f"Mod durumu değiştirilemedi: {e}")

    def open_mods_folder(self):
        os.startfile(self.get_current_mods_dir())

    def delete_selected_mod(self):
        sel = self.installed_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Silmek için listeden bir mod seçmelisin.")
            return
        mod = self.installed_mods_data[sel[0]]
        if messagebox.askyesno("Mod Sil", f"'{mod['filename']}' dosyasını kalıcı olarak silmek istiyor musun?"):
            os.remove(mod["path"])
            self.log(f"Mod silindi: {mod['filename']}")
            self.refresh_installed_mods()
            self.refresh_all_profiles()
            if self.search_results:
                self.populate_results()

    def _is_mod_already_installed(self, mod_title, mod_slug=""):
        mods_dir = self.get_current_mods_dir()
        files = [f.lower() for f in os.listdir(mods_dir) if f.lower().endswith((".jar", ".jar.disabled"))]
        tokens = [t for t in re.split(r"[^a-z0-9]+", (mod_slug or mod_title).lower()) if len(t) >= 3]
        if not tokens:
            return False
        primary = tokens[0]
        for fn in files:
            if primary in fn:
                return True
        return False

    def clear_logs(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def log(self, msg):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, msg.rstrip() + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def update_status(self, text, also_log=False):
        self.root.after(0, lambda: self.status_label.config(text=text[:115]))
        if also_log:
            self.log(text)

    def _animate_status_pulse(self):
        colors = ["#fdba74", "#fb923c", "#f97316", "#fb923c"]
        if self._is_busy:
            self.status_label.config(fg=colors[self._pulse_index % len(colors)])
            self._pulse_index += 1
        else:
            self.status_label.config(fg="#86efac")
        self.root.after(220, self._animate_status_pulse)

    def is_version_installed(self, version):
        ver_dir = os.path.join(self.default_mc_dir, "versions", version)
        return (
            os.path.isfile(os.path.join(ver_dir, f"{version}.json"))
            and os.path.isfile(os.path.join(ver_dir, f"{version}.jar"))
        )

    def find_installed_java(self, jvm_name):
        runtime_dir = os.path.join(self.default_mc_dir, "runtime", jvm_name)
        if os.path.isdir(runtime_dir):
            for root_dir, _, files in os.walk(runtime_dir):
                if "java.exe" in files:
                    return os.path.join(root_dir, "java.exe")
        for env_path in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(env_path, "java.exe")
            if os.path.isfile(candidate):
                return candidate
        return None

    def load_versions(self):
        try:
            self._is_busy = True
            self.log("Sürüm listesi çekiliyor...")
            versions = minecraft_launcher_lib.utils.get_version_list()
            releases = [v["id"] for v in versions if v["type"] == "release"]
            self.root.after(0, self.set_versions, releases)
        except Exception as e:
            self.update_status(f"Sürüm listesi alınamadı: {e}", also_log=True)
        finally:
            self._is_busy = False

    def set_versions(self, releases):
        self.version_combo["values"] = releases
        self.new_prof_ver["values"] = releases
        if releases:
            self.version_combo.current(0)
            self.new_prof_ver.current(0)
        self.update_status("Hazır. Profil veya sürüm seçip başlatabilirsin.", also_log=True)

    def _find_installed_loader_id(self, mc_version, loader):
        versions_root = os.path.join(self.default_mc_dir, "versions")
        if not os.path.isdir(versions_root):
            return None
        candidates = []
        for entry in os.listdir(versions_root):
            json_path = os.path.join(versions_root, entry, f"{entry}.json")
            if not os.path.isfile(json_path):
                continue
            low = entry.lower()
            if loader == "fabric" and "fabric-loader" in low and entry.endswith(f"-{mc_version}"):
                candidates.append(entry)
            elif loader == "quilt" and "quilt-loader" in low and entry.endswith(f"-{mc_version}"):
                candidates.append(entry)
            elif loader == "forge" and "forge" in low and "neoforge" not in low and mc_version in low:
                candidates.append(entry)
            elif loader == "neoforge" and "neoforge" in low and mc_version in low:
                candidates.append(entry)
        return sorted(candidates)[-1] if candidates else None

    def _install_and_resolve_launch_version(self, mc_version, loader, callback):
        if loader == "vanilla":
            return mc_version

        preferred_loader_ver = ""
        if self.active_profile_info and self.active_profile_info.get("loader") == loader:
            preferred_loader_ver = self.active_profile_info.get("loader_version", "")

        if loader == "fabric":
            if preferred_loader_ver:
                expected_id = f"fabric-loader-{preferred_loader_ver}-{mc_version}"
                if os.path.isfile(os.path.join(self.default_mc_dir, "versions", expected_id, f"{expected_id}.json")):
                    self.log(f"[LOADER] Kurulu Fabric bulundu: {expected_id}")
                    return expected_id
            existing = self._find_installed_loader_id(mc_version, "fabric")
            if existing and not preferred_loader_ver:
                self.log(f"[LOADER] Kurulu Fabric bulundu: {existing}")
                return existing

            self.update_status(f"Fabric Loader ({mc_version}) kuruluyor...", also_log=True)
            if preferred_loader_ver:
                minecraft_launcher_lib.fabric.install_fabric(
                    mc_version, self.default_mc_dir, loader_version=preferred_loader_ver, callback=callback
                )
            else:
                minecraft_launcher_lib.fabric.install_fabric(
                    mc_version, self.default_mc_dir, callback=callback
                )
            resolved = self._find_installed_loader_id(mc_version, "fabric")
            if resolved:
                self.log(f"[LOADER] Fabric hazır: {resolved}")
                return resolved
            raise RuntimeError(f"Fabric {mc_version} için kuruldu ama sürüm kimliği bulunamadı.")

        elif loader == "quilt":
            existing = self._find_installed_loader_id(mc_version, "quilt")
            if existing:
                self.log(f"[LOADER] Kurulu Quilt bulundu: {existing}")
                return existing
            self.update_status(f"Quilt Loader ({mc_version}) kuruluyor...", also_log=True)
            minecraft_launcher_lib.quilt.install_quilt(mc_version, self.default_mc_dir, callback=callback)
            resolved = self._find_installed_loader_id(mc_version, "quilt")
            if resolved:
                return resolved
            raise RuntimeError(f"Quilt {mc_version} için kuruldu ama sürüm kimliği bulunamadı.")

        elif loader == "forge":
            existing = self._find_installed_loader_id(mc_version, "forge")
            if existing:
                self.log(f"[LOADER] Kurulu Forge bulundu: {existing}")
                return existing
            self.update_status(f"Forge ({mc_version}) aranıyor ve kuruluyor...", also_log=True)
            forge_ver = minecraft_launcher_lib.forge.find_forge_version(mc_version)
            if not forge_ver:
                raise RuntimeError(f"Minecraft {mc_version} için uyumlu Forge sürümü bulunamadı.")
            minecraft_launcher_lib.forge.install_forge_version(forge_ver, self.default_mc_dir, callback=callback)
            resolved = self._find_installed_loader_id(mc_version, "forge")
            if resolved:
                self.log(f"[LOADER] Forge hazır: {resolved}")
                return resolved
            raise RuntimeError(f"Forge {mc_version} için kuruldu ama sürüm kimliği bulunamadı.")

        elif loader == "neoforge":
            existing = self._find_installed_loader_id(mc_version, "neoforge")
            if existing:
                self.log(f"[LOADER] Kurulu NeoForge bulundu: {existing}")
                return existing
            self.update_status(f"NeoForge ({mc_version}) kuruluyor...", also_log=True)
            if hasattr(minecraft_launcher_lib, "neoforge"):
                nf_versions = minecraft_launcher_lib.neoforge.get_neoforge_versions(mc_version)
                if not nf_versions:
                    raise RuntimeError(f"Minecraft {mc_version} için uyumlu NeoForge sürümü bulunamadı.")
                minecraft_launcher_lib.neoforge.install_neoforge_version(
                    nf_versions[0], self.default_mc_dir, callback=callback
                )
                resolved = self._find_installed_loader_id(mc_version, "neoforge")
                if resolved:
                    self.log(f"[LOADER] NeoForge hazır: {resolved}")
                    return resolved
            raise RuntimeError(f"NeoForge {mc_version} kurulumu başarısız oldu.")

        return mc_version

    def _watch_game_process(self, proc):
        try:
            proc.wait()
        except Exception:
            pass
        if self.game_process is proc:
            self.game_process = None
            self.root.after(0, lambda: self.kill_btn.set_enabled(False))
            self.update_status("Oyun kapatıldı.", also_log=True)

    def force_close_game(self):
        proc = self.game_process
        killed_any = False

        if proc and proc.poll() is None:
            pid = proc.pid
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    proc.kill()
                killed_any = True
                self.log(f"[SİSTEM] Oyun zorla kapatıldı (PID: {pid}).")
            except Exception as e:
                self.log(f"[SİSTEM] Süreç kapatma hatası: {e}")

        if not killed_any and sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", "javaw.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if res.returncode == 0:
                    killed_any = True
                    self.log("[SİSTEM] Arka plandaki Minecraft (javaw.exe) zorla kapatıldı.")
            except Exception:
                pass

        self.game_process = None
        self.kill_btn.set_enabled(False)
        if killed_any:
            self.update_status("Oyun zorla kapatıldı.", also_log=False)
        else:
            self.update_status("Açık bir Minecraft süreci bulunamadı.", also_log=True)

    def start_launch_thread(self):
        username = self.account_combo.get().strip() or "Thefoxx20"
        version = self.version_combo.get().strip()
        loader = self.loader_combo.get().strip() or "fabric"
        if not version:
            messagebox.showwarning("Uyarı", "Önce bir sürüm seçmelisin.")
            return
        try:
            ram_mb = max(1024, int(self.ram_entry.get().strip()))
        except ValueError:
            ram_mb = 4096
        self.config["ram_mb"] = ram_mb
        self._save_config()

        self._is_busy = True
        self.play_btn.set_enabled(False)
        self.play_btn.set_text("HAZIRLANIYOR...")
        threading.Thread(target=self.install_java_and_launch, args=(username, version, loader, ram_mb), daemon=True).start()

    def install_java_and_launch(self, username, version, loader, ram_mb):
        try:
            force_assets = self.check_assets_var.get()
            last_status = [""]

            def on_mc_status(text):
                if text.startswith("Download "):
                    if not force_assets:
                        return
                    if last_status[0] != "asset_dl":
                        last_status[0] = "asset_dl"
                        self.log("[MC] Ses/Asset dosyaları kontrol ediliyor...")
                    return
                if text != last_status[0]:
                    last_status[0] = text
                    self.log(f"[MC] {text}")

            callback = {
                "setStatus": on_mc_status,
                "setProgress": lambda value: None,
                "setMax": lambda value: None,
            }

            if self.is_version_installed(version) and not force_assets:
                self.update_status(f"{version} temel dosyaları hazır.", also_log=True)
            else:
                self.update_status(f"{version} temel dosyaları hazırlanıyor...", also_log=True)
                minecraft_launcher_lib.install.install_minecraft_version(version, self.default_mc_dir, callback=callback)

            launch_version_id = self._install_and_resolve_launch_version(version, loader, callback)

            jvm_name = "java-runtime-gamma"
            try:
                details = minecraft_launcher_lib.utils.get_version_details(launch_version_id, self.default_mc_dir)
                jvm_name = details.get("javaVersion", {}).get("component", "java-runtime-gamma")
            except Exception:
                pass

            existing_java = self.find_installed_java(jvm_name)
            if existing_java:
                self.update_status(f"Uygun Java hazır: {existing_java}", also_log=True)
            else:
                self.update_status(f"Java ({jvm_name}) indiriliyor...", also_log=True)
                minecraft_launcher_lib.install.install_jvm_runtime(jvm_name, self.default_mc_dir, callback=callback)

            options = {
                "username": username,
                "uuid": "",
                "token": "",
                "gameDirectory": self.active_game_dir,
                "jvmArguments": [f"-Xmx{ram_mb}M", f"-Xms1024M"],
            }
            command = minecraft_launcher_lib.command.get_minecraft_command(launch_version_id, self.default_mc_dir, options)

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            if sys.platform == "win32" and command and command[0].lower().endswith("java.exe"):
                javaw_candidate = command[0][:-8] + "javaw.exe"
                if os.path.isfile(javaw_candidate):
                    command[0] = javaw_candidate

            mods_dir = self.get_current_mods_dir()
            active_mods = [f for f in os.listdir(mods_dir) if f.lower().endswith(".jar")]
            env_label = self.active_profile_info["name"] if self.active_profile_info else "Standart .minecraft"
            self.log(f"[MOD] Klasör: {mods_dir} ({len(active_mods)} aktif mod yüklenecek)")
            self.update_status(f"Başlatılıyor ({launch_version_id} | {env_label} | {len(active_mods)} mod)...", also_log=True)

            proc = subprocess.Popen(command, cwd=self.active_game_dir, creationflags=creation_flags)
            self.game_process = proc
            self.root.after(0, lambda: self.kill_btn.set_enabled(True))
            threading.Thread(target=self._watch_game_process, args=(proc,), daemon=True).start()
            self.update_status(f"{launch_version_id} açıldı! (PID: {proc.pid})", also_log=True)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Başlatma Hatası", str(e)))
            self.update_status(f"Hata: {e}", also_log=True)
        finally:
            self._is_busy = False
            self.root.after(0, lambda: (
                self.play_btn.set_enabled(True),
                self.play_btn.set_text("OYNA (FLC BAŞLAT)")
            ))

    def start_search_thread(self):
        query = self.mod_search_entry.get().strip()
        source = self.source_combo.get()
        version = self.version_combo.get().strip()
        loader = self.loader_combo.get().strip()
        if not query:
            return
        self._is_busy = True
        self.update_status(f"{source} üzerinde '{query}' aranıyor...", also_log=True)
        threading.Thread(target=self.search_mods, args=(source, query, version, loader), daemon=True).start()

    def search_mods(self, source, query, version, loader):
        try:
            self.search_results.clear()
            if source == "Modrinth":
                facets_list = [[f"versions:{version}"], ["project_type:mod"]]
                if loader != "vanilla":
                    facets_list.append([f"categories:{loader}"])
                r = requests.get(
                    f"{MODRINTH_API}/search",
                    params={"query": query, "facets": json.dumps(facets_list), "limit": 25},
                    headers=HEADERS,
                    timeout=15
                )
                r.raise_for_status()
                for h in r.json().get("hits", []):
                    self.search_results.append({
                        "source": "Modrinth",
                        "id": h["project_id"],
                        "slug": h.get("slug", ""),
                        "title": h.get("title", "Bilinmeyen Mod"),
                        "author": h.get("author", "Bilinmiyor"),
                        "downloads": h.get("downloads", 0),
                        "description": h.get("description", "Açıklama yok."),
                        "categories": ", ".join(h.get("categories", [])[:5]),
                        "icon_url": h.get("icon_url") or "",
                        "versions": ", ".join(h.get("versions", [])[-5:]),
                    })
            else:
                api_key = self.cf_key_entry.get().strip()
                if not api_key:
                    raise RuntimeError("CurseForge araması için API Key girmen gerekiyor.")
                cf_headers = {**HEADERS, "x-api-key": api_key}
                r = requests.get(
                    f"{CURSEFORGE_API}/mods/search",
                    params={"gameId": 432, "searchFilter": query, "gameVersion": version, "pageSize": 25},
                    headers=cf_headers,
                    timeout=15
                )
                r.raise_for_status()
                for m in r.json().get("data", []):
                    authors = ", ".join([a.get("name", "") for a in m.get("authors", [])]) or "Bilinmiyor"
                    cats = ", ".join([c.get("name", "") for c in m.get("categories", [])[:5]])
                    logo_url = (m.get("logo") or {}).get("thumbnailUrl") or (m.get("logo") or {}).get("url") or ""
                    self.search_results.append({
                        "source": "CurseForge",
                        "id": m["id"],
                        "slug": m.get("slug", ""),
                        "title": m.get("name", "Bilinmeyen Mod"),
                        "author": authors,
                        "downloads": m.get("downloadCount", 0),
                        "description": m.get("summary", "Açıklama yok."),
                        "categories": cats,
                        "icon_url": logo_url,
                        "versions": version,
                    })

            self.root.after(0, self.populate_results)
            self.update_status(f"{len(self.search_results)} mod bulundu.", also_log=True)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Arama Hatası", str(e)))
            self.update_status(f"Arama hatası: {e}", also_log=True)
        finally:
            self._is_busy = False

    def populate_results(self):
        self.results_listbox.delete(0, tk.END)
        for idx, item in enumerate(self.search_results):
            installed = self._is_mod_already_installed(item["title"], item.get("slug", ""))
            item["is_installed"] = installed
            badge = "[✓ YÜKLÜ]" if installed else "[+ YÜKLÜ DEĞİL]"
            dl_fmt = f"{item['downloads']:,}".replace(",", ".")
            self.results_listbox.insert(
                tk.END,
                f"{badge}  {item['title']}  —  by {item['author']} ({dl_fmt} indirme)"
            )
            self.results_listbox.itemconfig(idx, fg="#86efac" if installed else "#f1f5f9")

    def on_mod_result_select(self, event=None):
        sel = self.results_listbox.curselection()
        if not sel:
            return
        mod = self.search_results[sel[0]]
        installed = self._is_mod_already_installed(mod["title"], mod.get("slug", ""))
        status_badge = "BU PROFİLDE YÜKLÜ ✓" if installed else "HENÜZ YÜKLÜ DEĞİL"
        dl_fmt = f"{mod['downloads']:,}".replace(",", ".")
        self.mod_title_label.config(text=f"{mod['title']}  [{mod['source']}]")
        self.mod_meta_label.config(
            text=f"Durum: {status_badge}  |  Yazar: {mod['author']}  |  İndirme: {dl_fmt}",
            fg="#4ade80" if installed else "#fb923c"
        )
        self.mod_desc_label.config(text=f"{mod['description']}\nKategoriler: {mod['categories'] or '-'}")

        icon_url = mod.get("icon_url", "")
        if not icon_url or not HAS_PIL:
            photo = self._make_badge_photo(mod["title"], active=True)
            self.current_mod_photo = photo
            self.mod_logo_label.config(image=photo, text="", width=64, height=64)
            return

        if icon_url in self.mod_icon_cache:
            self.current_mod_photo = self.mod_icon_cache[icon_url]
            self.mod_logo_label.config(image=self.current_mod_photo, text="", width=64, height=64)
            return

        self.mod_logo_label.config(image="", text="Yükleniyor...", width=10, height=5)
        threading.Thread(target=self._fetch_mod_logo, args=(icon_url, mod["title"]), daemon=True).start()

    def _fetch_mod_logo(self, url, title_fallback):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            pil_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            pil_img = pil_img.resize((64, 64), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            self.mod_icon_cache[url] = photo

            def _apply():
                self.current_mod_photo = photo
                self.mod_logo_label.config(image=photo, text="", width=64, height=64)

            self.root.after(0, _apply)
        except Exception:
            def _fallback():
                photo = self._make_badge_photo(title_fallback, active=True)
                self.current_mod_photo = photo
                self.mod_logo_label.config(image=photo, text="", width=64, height=64)
            self.root.after(0, _fallback)

    def start_mod_download_thread(self):
        sel = self.results_listbox.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Listeden bir mod seçmelisin.")
            return
        mod = self.search_results[sel[0]]
        version = self.version_combo.get().strip()
        loader = self.loader_combo.get().strip()
        self._is_busy = True
        self.dl_mod_btn.set_enabled(False)
        self.dl_mod_btn.set_text("MOD VE BAĞIMLILIKLAR İNDİRİLİYOR...")
        threading.Thread(target=self._run_mod_download, args=(mod, version, loader), daemon=True).start()

    def _run_mod_download(self, mod, version, loader):
        try:
            self.download_mod_with_deps(mod, version, loader, set())
            self.root.after(0, self.refresh_installed_mods)
            self.root.after(0, self.refresh_all_profiles)
            self.root.after(0, self.populate_results)
            self.root.after(0, self.on_mod_result_select)
            self.update_status("Mod kurulumu tamamlandı.", also_log=True)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Mod İndirme Hatası", str(e)))
            self.update_status(f"Mod hatası: {e}", also_log=True)
        finally:
            self._is_busy = False
            self.root.after(0, lambda: (
                self.dl_mod_btn.set_enabled(True),
                self.dl_mod_btn.set_text("Seçili Modu + Gerekli Bağımlılıkları Aktif Profile İndir")
            ))

    def download_mod_with_deps(self, mod, version, loader, visited):
        key = f"{mod['source']}:{mod['id']}"
        if key in visited:
            return
        visited.add(key)
        target_mods_dir = self.get_current_mods_dir()

        if mod["source"] == "Modrinth":
            project_id = mod["id"]
            self.update_status(f"Sürüm kontrol ediliyor: {mod['title']}...", also_log=True)
            r = requests.get(f"{MODRINTH_API}/project/{project_id}/version", headers=HEADERS, timeout=15)
            r.raise_for_status()
            versions = r.json()

            matched = None
            for v in versions:
                if version in v.get("game_versions", []) and (loader == "vanilla" or loader in v.get("loaders", [])):
                    matched = v
                    break
            if not matched and versions:
                matched = versions[0]
            if not matched:
                self.log(f"Uygun sürüm bulunamadı: {mod['title']}")
                return

            for dep in matched.get("dependencies", []):
                if dep.get("dependency_type") == "required" and dep.get("project_id"):
                    dep_id = dep["project_id"]
                    self.log(f"Gerekli alt mod işleniyor: {dep_id}")
                    self.download_mod_with_deps(
                        {"source": "Modrinth", "id": dep_id, "title": dep_id},
                        version, loader, visited
                    )

            files = matched.get("files", [])
            if files:
                f_info = files[0]
                out_path = os.path.join(target_mods_dir, f_info["filename"])
                if os.path.exists(out_path):
                    self.log(f"Zaten kurulu: {f_info['filename']}")
                    return
                self.update_status(f"İndiriliyor: {f_info['filename']}", also_log=True)
                content = requests.get(f_info["url"], headers=HEADERS, timeout=30).content
                with open(out_path, "wb") as f:
                    f.write(content)
                self.log(f"İndirildi: {f_info['filename']}")
        else:
            api_key = self.cf_key_entry.get().strip()
            if not api_key:
                raise RuntimeError("CurseForge indirmesi için API Key gerekli.")
            cf_headers = {**HEADERS, "x-api-key": api_key}
            r = requests.get(
                f"{CURSEFORGE_API}/mods/{mod['id']}/files",
                params={"gameVersion": version},
                headers=cf_headers,
                timeout=15
            )
            r.raise_for_status()
            files_data = r.json().get("data", [])
            if not files_data:
                self.log(f"Dosya bulunamadı: {mod['title']}")
                return
            file_obj = files_data[0]
            for dep in file_obj.get("dependencies", []):
                if dep.get("relationType") == 3 and dep.get("modId"):
                    self.download_mod_with_deps(
                        {"source": "CurseForge", "id": dep["modId"], "title": f"Mod {dep['modId']}"},
                        version, loader, visited
                    )
            dl_url = file_obj.get("downloadUrl")
            if dl_url:
                out_path = os.path.join(target_mods_dir, file_obj["fileName"])
                if os.path.exists(out_path):
                    self.log(f"Zaten kurulu: {file_obj['fileName']}")
                    return
                self.update_status(f"İndiriliyor: {file_obj['fileName']}", also_log=True)
                content = requests.get(dl_url, headers=HEADERS, timeout=30).content
                with open(out_path, "wb") as f:
                    f.write(content)
                self.log(f"İndirildi: {file_obj['fileName']}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FoxLauncher(root)
    root.mainloop()
