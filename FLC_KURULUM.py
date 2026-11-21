import importlib.util
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import urllib.request

# GitHub Repo & Commit Bilgileri
REPO_OWNER = "sadecebiri6464-jpg"
REPO_NAME = "-E-YARAMAZ-SADECE-KAYNAK-KOD-SADECE-KURULUM-S-H-RBAZI-N"
TARGET_COMMIT = "059fe2925bd67df56f214e66a95819630967bded"

REQUIRED_PACKAGES = [
    ("minecraft_launcher_lib", "minecraft-launcher-lib"),
    ("requests", "requests"),
    ("PIL", "Pillow"),
]


class FoxSetupWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("FOXLAUNCHER (FLC) — Gelişmiş Kurulum Sihirbazı")

        # Pencereyi geniş ve yüksek yap, ekranın tam ortasında aç
        win_w, win_h = 860, 720
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(win_w, max(760, screen_w - 80))
        win_h = min(win_h, max(640, screen_h - 80))
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)

        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(740, 620)
        self.root.resizable(True, True)
        self.is_fullscreen = False

        self.bg_main = "#0f131a"
        self.bg_card = "#171c26"
        self.bg_input = "#222938"
        self.accent_fox = "#f97316"
        self.accent_blue = "#3b82f6"
        self.accent_green = "#16a34a"
        self.text_main = "#f8fafc"
        self.text_muted = "#94a3b8"
        self.root.configure(bg=self.bg_main)

        self.desktop_dir = self._get_desktop_path()
        self.mc_dir = self._get_minecraft_dir()

        # Kurulum Öncesi Ayar Değişkenleri
        self.install_dir_var = tk.StringVar(value=self.desktop_dir)
        self.default_user_var = tk.StringVar(value="Thefoxx20")
        self.default_ram_var = tk.StringVar(value="4096")
        self.default_loader_var = tk.StringVar(value="fabric")

        # Otomatik Güncelleme & Bildirim Tercihleri
        self.auto_update_check_var = tk.BooleanVar(value=True)
        self.auto_update_ask_var = tk.BooleanVar(value=True)
        self.notify_update_var = tk.BooleanVar(value=True)
        self.notify_mod_done_var = tk.BooleanVar(value=True)
        self.notify_game_state_var = tk.BooleanVar(value=False)

        # Başlangıç & Uygulama Ayarları
        self.win_startup_var = tk.BooleanVar(value=False)
        self.silent_launch_var = tk.BooleanVar(value=True)
        self.create_bat_var = tk.BooleanVar(value=False)
        self.auto_open_after_var = tk.BooleanVar(value=False)

        self._setup_styles()
        self._build_ui()

        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        self.fs_btn.config(text="Pencere Modu (F11)" if self.is_fullscreen else "Tam Ekran (F11)")

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.fs_btn.config(text="Tam Ekran (F11)")

    def _get_desktop_path(self):
        userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        onedrive_desktop = os.path.join(userprofile, "OneDrive", "Desktop")
        std_desktop = os.path.join(userprofile, "Desktop")
        if os.path.isdir(std_desktop):
            return std_desktop
        if os.path.isdir(onedrive_desktop):
            return onedrive_desktop
        return userprofile

    def _get_minecraft_dir(self):
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, ".minecraft")
        elif sys.platform == "darwin":
            return os.path.expanduser("~/Library/Application Support/minecraft")
        return os.path.expanduser("~/.minecraft")

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Fox.Horizontal.TProgressbar",
            troughcolor=self.bg_input,
            background=self.accent_fox,
            bordercolor=self.bg_input,
            lightcolor=self.accent_fox,
            darkcolor=self.accent_fox,
            thickness=15,
        )
        style.configure("TCombobox", fieldbackground=self.bg_input, background=self.bg_input,
                        foreground=self.text_main, arrowcolor=self.accent_fox, borderwidth=0)

    def _build_ui(self):
        # 1. ÜST BAŞLIK ÇUBUĞU (Sabit Üst)
        header = tk.Frame(self.root, bg=self.bg_card, padx=22, pady=12)
        header.pack(side="top", fill="x")

        title_row = tk.Frame(header, bg=self.bg_card)
        title_row.pack(fill="x")

        tk.Label(
            title_row, text="FOXLAUNCHER (FLC)", font=("Segoe UI", 16, "bold"),
            fg=self.accent_fox, bg=self.bg_card
        ).pack(side="left")

        self.fs_btn = tk.Button(
            title_row, text="Tam Ekran (F11)", command=self.toggle_fullscreen,
            bg=self.bg_input, fg=self.text_main, activebackground="#334155",
            activeforeground="#ffffff", font=("Segoe UI", 8, "bold"),
            relief="flat", padx=12, pady=4, cursor="hand2"
        )
        self.fs_btn.pack(side="right", padx=(10, 0))

        self.stage_badge = tk.Label(
            title_row, text="AŞAMA 1 / 2 — Kurulum Öncesi Ayarlar",
            font=("Segoe UI", 9, "bold"), fg="#fed7aa", bg="#431407", padx=12, pady=4
        )
        self.stage_badge.pack(side="right")

        tk.Label(
            header, text="Bildirim, otomatik güncelleme, başlangıç ve oyun tercihlerini yapılandır",
            font=("Segoe UI", 9), fg=self.text_muted, bg=self.bg_card
        ).pack(anchor="w", pady=(3, 0))

        # 2. ALT NAVİGASYON ÇUBUĞU (Doğrudan root'un en altına sabit — ASLA KAYBOLMAZ)
        self.bottom_nav = tk.Frame(self.root, bg=self.bg_card, padx=22, pady=12)
        self.bottom_nav.pack(side="bottom", fill="x")

        # Aşama 1 Alt Butonu
        self.stage1_nav_frame = tk.Frame(self.bottom_nav, bg=self.bg_card)
        self.stage1_nav_frame.pack(fill="x")

        self.next_btn = tk.Button(
            self.stage1_nav_frame, text="Sonraki: Kurulum Aşamasına Geç  →",
            command=self._go_to_install_stage,
            bg=self.accent_fox, fg="#ffffff", activebackground="#ea580c",
            activeforeground="#ffffff", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=22, pady=11, cursor="hand2"
        )
        self.next_btn.pack(fill="x")

        # Aşama 2 Alt Butonları
        self.stage2_nav_frame = tk.Frame(self.bottom_nav, bg=self.bg_card)

        self.back_btn = tk.Button(
            self.stage2_nav_frame, text="← Ayarlara Dön", command=self._go_back_to_settings,
            bg=self.bg_input, fg=self.text_main, activebackground="#334155",
            activeforeground="#ffffff", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=10, cursor="hand2"
        )
        self.back_btn.pack(side="left", padx=(0, 10))

        self.start_btn = tk.Button(
            self.stage2_nav_frame, text="Kurulumu Başlat", command=self.start_install,
            bg=self.accent_fox, fg="#ffffff", activebackground="#ea580c",
            activeforeground="#ffffff", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=20, pady=10, cursor="hand2"
        )
        self.start_btn.pack(side="left", fill="x", expand=True)

        self.launch_now_btn = tk.Button(
            self.stage2_nav_frame, text="FoxLauncher.py'yi Şimdi Aç", command=self.launch_installed_app,
            bg=self.accent_green, fg="#ffffff", activebackground="#15803d",
            activeforeground="#ffffff", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=20, pady=10, cursor="hand2", state="disabled"
        )
        self.launch_now_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 3. ORTA İÇERİK ALANI
        self.container = tk.Frame(self.root, bg=self.bg_main, padx=20, pady=12)
        self.container.pack(side="top", fill="both", expand=True)

        self.settings_page = tk.Frame(self.container, bg=self.bg_main)
        self.install_page = tk.Frame(self.container, bg=self.bg_main)

        self._build_settings_page()
        self._build_install_page()

        self.settings_page.pack(fill="both", expand=True)

    # --- AŞAMA 1: KURULUM ÖNCESİ AYARLAR SEKMESİ ---
    def _build_settings_page(self):
        grid = tk.Frame(self.settings_page, bg=self.bg_main)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)

        # SOL KOLON
        left_card = tk.Frame(grid, bg=self.bg_card, padx=14, pady=12)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))

        tk.Label(
            left_card, text="OTOMATİK GÜNCELLEME & BİLDİRİMLER",
            font=("Segoe UI", 9, "bold"), fg=self.accent_fox, bg=self.bg_card
        ).pack(anchor="w", pady=(0, 8))

        self._make_check(
            left_card, "Açılışta otomatik güncelleme kontrolü yap",
            self.auto_update_check_var, "İnternet açıksa GitHub'dan yeni sürümü denetler."
        )
        self._make_check(
            left_card, "Güncelleme varsa Evet / Hayır sor",
            self.auto_update_ask_var, "Kapalıysa sormadan güncelleyip yeniden başlatır."
        )
        self._make_check(
            left_card, "Güncelleme ve sistem bildirimleri",
            self.notify_update_var, "Yeni sürüm ve kurulum uyarılarını gösterir."
        )
        self._make_check(
            left_card, "Mod indirme tamamlanınca bildirim ver",
            self.notify_mod_done_var, "Bağımlılıklarla indirme bitince bilgi verir."
        )
        self._make_check(
            left_card, "Oyun açılınca / kapanınca bildirim ver",
            self.notify_game_state_var, "Minecraft süreci kapanınca uyarı verir."
        )

        # SAĞ KOLON
        right_card = tk.Frame(grid, bg=self.bg_card, padx=14, pady=12)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))

        tk.Label(
            right_card, text="BAŞLANGIÇ & UYGULAMA AYARLARI",
            font=("Segoe UI", 9, "bold"), fg="#60a5fa", bg=self.bg_card
        ).pack(anchor="w", pady=(0, 8))

        self._make_check(
            right_card, "Windows açıldığında otomatik başlat",
            self.win_startup_var, "Bilgisayar açılışında arka planda otomatik başlar."
        )
        self._make_check(
            right_card, "Siyah konsol olmadan başlat (Sessiz Mod)",
            self.silent_launch_var, "pythonw.exe ile doğrudan arayüzü açar."
        )
        self._make_check(
            right_card, "Masaüstüne hızlı başlatma (.bat) ekle",
            self.create_bat_var, "Tek tıkla başlatma için yardımcı dosya oluşturur."
        )
        self._make_check(
            right_card, "Kurulum bitince FoxLauncher'ı hemen aç",
            self.auto_open_after_var, "Kurulum tamamlanınca otomatik başlatır."
        )

        # ALT KART: Kurulum Konumu & Varsayılan Oyun Ayarları
        bottom_card = tk.Frame(self.settings_page, bg=self.bg_card, padx=14, pady=12)
        bottom_card.pack(fill="x")
        bottom_card.columnconfigure(0, weight=2)
        bottom_card.columnconfigure(1, weight=1)
        bottom_card.columnconfigure(2, weight=1)

        tk.Label(
            bottom_card, text="KURULUM KONUMU & VARSAYILAN OYUN AYARLARI",
            font=("Segoe UI", 9, "bold"), fg="#34d399", bg=self.bg_card
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        path_row = tk.Frame(bottom_card, bg=self.bg_card)
        path_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        tk.Label(path_row, text="Konum:", font=("Segoe UI", 8, "bold"),
                 fg=self.text_muted, bg=self.bg_card).pack(side="left", padx=(0, 8))

        path_entry = tk.Entry(
            path_row, textvariable=self.install_dir_var, bg=self.bg_input, fg="#fdba74",
            insertbackground=self.text_main, relief="flat", bd=5, font=("Consolas", 9)
        )
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = tk.Button(
            path_row, text="Gözat...", command=self._choose_install_dir,
            bg=self.bg_input, fg=self.text_main, activebackground="#334155",
            activeforeground="#ffffff", relief="flat", padx=12, pady=4,
            font=("Segoe UI", 8, "bold"), cursor="hand2"
        )
        browse_btn.pack(side="left")

        tk.Label(bottom_card, text="Varsayılan Oyuncu Adı", font=("Segoe UI", 8),
                 fg=self.text_muted, bg=self.bg_card).grid(row=2, column=0, sticky="w")
        tk.Label(bottom_card, text="Varsayılan RAM (MB)", font=("Segoe UI", 8),
                 fg=self.text_muted, bg=self.bg_card).grid(row=2, column=1, sticky="w", padx=(10, 0))
        tk.Label(bottom_card, text="Varsayılan Loader", font=("Segoe UI", 8),
                 fg=self.text_muted, bg=self.bg_card).grid(row=2, column=2, sticky="w", padx=(10, 0))

        tk.Entry(
            bottom_card, textvariable=self.default_user_var, bg=self.bg_input, fg=self.text_main,
            insertbackground=self.text_main, relief="flat", bd=5, font=("Segoe UI", 9)
        ).grid(row=3, column=0, sticky="ew", pady=(3, 0))

        ram_combo = ttk.Combobox(
            bottom_card, textvariable=self.default_ram_var, state="readonly",
            values=["2048", "4096", "6144", "8192", "12288"], font=("Segoe UI", 9)
        )
        ram_combo.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(3, 0))

        loader_combo = ttk.Combobox(
            bottom_card, textvariable=self.default_loader_var, state="readonly",
            values=["fabric", "forge", "neoforge", "quilt", "vanilla"], font=("Segoe UI", 9)
        )
        loader_combo.grid(row=3, column=2, sticky="ew", padx=(10, 0), pady=(3, 0))

    def _make_check(self, parent, title, var, subtitle):
        box = tk.Frame(parent, bg=self.bg_card)
        box.pack(fill="x", pady=(0, 6))
        cb = tk.Checkbutton(
            box, text=title, variable=var, bg=self.bg_card, fg=self.text_main,
            selectcolor=self.bg_input, activebackground=self.bg_card,
            activeforeground=self.text_main, font=("Segoe UI", 9, "bold"),
            anchor="w", cursor="hand2"
        )
        cb.pack(fill="x")
        tk.Label(
            box, text=subtitle, font=("Segoe UI", 7), fg=self.text_muted,
            bg=self.bg_card, anchor="w", justify="left"
        ).pack(fill="x", padx=(24, 0))

    def _choose_install_dir(self):
        chosen = filedialog.askdirectory(title="FoxLauncher.py Kurulum Klasörünü Seç")
        if chosen:
            self.install_dir_var.set(chosen)

    def _go_to_install_stage(self):
        target_dir = self.install_dir_var.get().strip() or self.desktop_dir
        self.launcher_py_path = os.path.join(target_dir, "FoxLauncher.py")
        self.target_summary_label.config(text=self.launcher_py_path)

        summary_items = [
            f"Otomatik Güncelleme: {'Açık' if self.auto_update_check_var.get() else 'Kapalı'}",
            f"Windows Başlangıcı: {'Açık' if self.win_startup_var.get() else 'Kapalı'}",
            f"Oyuncu: {self.default_user_var.get().strip() or 'Thefoxx20'}",
            f"RAM: {self.default_ram_var.get()} MB",
            f"Loader: {self.default_loader_var.get()}",
        ]
        self.chosen_settings_label.config(text=" • ".join(summary_items))

        self.settings_page.pack_forget()
        self.stage1_nav_frame.pack_forget()

        self.install_page.pack(fill="both", expand=True)
        self.stage2_nav_frame.pack(fill="x")
        self.stage_badge.config(text="AŞAMA 2 / 2 — Kurulum & Doğrulama", bg="#1e3a8a", fg="#bfdbfe")

    def _go_back_to_settings(self):
        self.install_page.pack_forget()
        self.stage2_nav_frame.pack_forget()

        self.settings_page.pack(fill="both", expand=True)
        self.stage1_nav_frame.pack(fill="x")
        self.stage_badge.config(text="AŞAMA 1 / 2 — Kurulum Öncesi Ayarlar", bg="#431407", fg="#fed7aa")

    # --- AŞAMA 2: KURULUM EKRANI ---
    def _build_install_page(self):
        info_box = tk.Frame(self.install_page, bg=self.bg_card, padx=16, pady=12)
        info_box.pack(fill="x", pady=(0, 12))

        tk.Label(
            info_box, text="Kurulum Hedefi:", font=("Segoe UI", 8, "bold"),
            fg=self.text_muted, bg=self.bg_card
        ).pack(anchor="w")

        self.launcher_py_path = os.path.join(self.desktop_dir, "FoxLauncher.py")
        self.target_summary_label = tk.Label(
            info_box, text=self.launcher_py_path, font=("Consolas", 10, "bold"),
            fg="#fdba74", bg=self.bg_card
        )
        self.target_summary_label.pack(anchor="w", pady=(2, 6))

        self.chosen_settings_label = tk.Label(
            info_box, text="", font=("Segoe UI", 8, "bold"),
            fg="#93c5fd", bg=self.bg_card, wraplength=760, justify="left"
        )
        self.chosen_settings_label.pack(anchor="w")

        self.step_label = tk.Label(
            self.install_page, text="Seçtiğin ayarlarla kuruluma başlamak için alttaki 'Kurulumu Başlat' butonuna bas.",
            font=("Segoe UI", 9, "bold"), fg=self.text_main, bg=self.bg_main
        )
        self.step_label.pack(anchor="w", pady=(0, 6))

        self.progress = ttk.Progressbar(
            self.install_page, style="Fox.Horizontal.TProgressbar", mode="determinate", maximum=100
        )
        self.progress.pack(fill="x", pady=(0, 12))

        self.log_box = tk.Text(
            self.install_page, height=12, bg="#090c10", fg="#d1d5db", font=("Consolas", 9),
            relief="flat", bd=8, state="disabled", wrap="word"
        )
        self.log_box.pack(fill="both", expand=True)

    def log(self, text):
        def _append():
            self.log_box.config(state="normal")
            self.log_box.insert(tk.END, text + "\n")
            self.log_box.see(tk.END)
            self.log_box.config(state="disabled")
        self.root.after(0, _append)

    def set_step(self, text, percent):
        def _update():
            self.step_label.config(text=text)
            self.progress["value"] = percent
        self.root.after(0, _update)

    def start_install(self):
        self.start_btn.config(state="disabled", text="Kurulum Devam Ediyor...")
        self.back_btn.config(state="disabled")
        threading.Thread(target=self._run_wizard, daemon=True).start()

    def _is_package_installed(self, import_name):
        return importlib.util.find_spec(import_name) is not None

    def _configure_windows_startup(self, enable, target_script):
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    py_exe = sys.executable
                    if self.silent_launch_var.get() and py_exe.lower().endswith("python.exe"):
                        pyw = py_exe[:-10] + "pythonw.exe"
                        if os.path.isfile(pyw):
                            py_exe = pyw
                    winreg.SetValueEx(key, "FOXLAUNCHER_FLC", 0, winreg.REG_SZ, f'"{py_exe}" "{target_script}"')
                    self.log("[BAŞLANGIÇ] Windows açılışında otomatik başlatma aktif edildi.")
                else:
                    try:
                        winreg.DeleteValue(key, "FOXLAUNCHER_FLC")
                        self.log("[BAŞLANGIÇ] Windows başlangıç kaydı temizlendi.")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            self.log(f"[UYARI] Başlangıç kaydı güncellenemedi: {e}")

    def _write_user_preferences(self):
        os.makedirs(self.mc_dir, exist_ok=True)
        config_path = os.path.join(self.mc_dir, "flc_config.json")
        existing = {}
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        user_name = self.default_user_var.get().strip() or "Thefoxx20"
        users = existing.get("users", [])
        if user_name not in users:
            users.insert(0, user_name)

        try:
            ram_val = int(self.default_ram_var.get())
        except ValueError:
            ram_val = 4096

        existing.update({
            "active": user_name,
            "users": users,
            "ram_mb": ram_val,
            "default_loader": self.default_loader_var.get(),
            "auto_update_check": self.auto_update_check_var.get(),
            "auto_update_ask": self.auto_update_ask_var.get(),
            "notify_update": self.notify_update_var.get(),
            "notify_mod_done": self.notify_mod_done_var.get(),
            "notify_game_state": self.notify_game_state_var.get(),
            "silent_launch": self.silent_launch_var.get(),
        })

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        self.log(f"[AYARLAR] Tercihler kaydedildi: {config_path}")

    def _fetch_code_from_github(self):
        headers = {"User-Agent": "FLC-SetupWizard/2.1"}
        api_urls = [
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{TARGET_COMMIT}",
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1",
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/master?recursive=1",
        ]

        raw_urls_to_try = []

        for api_url in api_urls:
            try:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if "files" in data:
                    for f in data["files"]:
                        if f.get("raw_url"):
                            raw_urls_to_try.append(f["raw_url"])
                        elif f.get("filename"):
                            raw_urls_to_try.append(
                                f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{TARGET_COMMIT}/{f['filename']}"
                            )
                if "tree" in data:
                    for item in data["tree"]:
                        path = item.get("path", "")
                        if item.get("type") == "blob" and path.lower().endswith(".py") and "kurulum" not in path.lower():
                            raw_urls_to_try.append(
                                f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
                            )
                if raw_urls_to_try:
                    break
            except Exception:
                continue

        for fallback_name in ("FoxLauncher.py", "launcher.py", "foxlauncher.py", "main.py", "flc.py"):
            raw_urls_to_try.append(
                f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{TARGET_COMMIT}/{fallback_name}"
            )
            raw_urls_to_try.append(
                f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{fallback_name}"
            )

        for raw_url in dict.fromkeys(raw_urls_to_try):
            try:
                self.log(f"[GITHUB] İndiriliyor: {raw_url}")
                req = urllib.request.Request(raw_url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    code_text = resp.read().decode("utf-8", errors="replace")
                if "FoxLauncher" in code_text or "tkinter" in code_text or len(code_text) > 500:
                    return code_text
            except Exception:
                continue

        raise RuntimeError(
            "GitHub deposundan launcher kodu indirilemedi. Deponun Public olduğundan ve internet bağlantından emin ol."
        )

    def _run_wizard(self):
        try:
            # AŞAMA 1: Gereksinim Kontrolü
            self.set_step("Adım 1/4: Python gereksinimleri kontrol ediliyor...", 10)
            self.log("=== ADIM 1: GEREKSİNİM KONTROLÜ ===")

            total_pkgs = len(REQUIRED_PACKAGES)
            for idx, (import_name, pip_name) in enumerate(REQUIRED_PACKAGES, start=1):
                pct = 10 + int((idx / total_pkgs) * 30)
                if self._is_package_installed(import_name):
                    self.log(f"[OK] '{pip_name}' zaten kurulu — bu aşama atlandı.")
                    self.set_step(f"'{pip_name}' zaten yüklü, geçiliyor...", pct)
                else:
                    self.log(f"[EKSİK] '{pip_name}' bulunamadı, otomatik indiriliyor...")
                    self.set_step(f"Eksik kütüphane kuruluyor: {pip_name}...", pct)
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    res = subprocess.run(
                        [sys.executable, "-m", "pip", "install", pip_name],
                        capture_output=True,
                        text=True,
                        creationflags=creation_flags,
                    )
                    if res.returncode != 0:
                        raise RuntimeError(f"'{pip_name}' kurulamadı:\n{res.stderr}")
                    self.log(f"[KURULDU] '{pip_name}' başarıyla yüklendi
