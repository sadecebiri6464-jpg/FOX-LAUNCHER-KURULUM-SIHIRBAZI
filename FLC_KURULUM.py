import importlib.util
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
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
        self.root.title("FOXLAUNCHER (FLC) — Kurulum Sihirbazı")
        self.root.geometry("620x460")
        self.root.resizable(False, False)

        self.bg_main = "#0f131a"
        self.bg_card = "#171c26"
        self.bg_input = "#222938"
        self.accent_fox = "#f97316"
        self.accent_green = "#16a34a"
        self.text_main = "#f8fafc"
        self.text_muted = "#94a3b8"
        self.root.configure(bg=self.bg_main)

        self.desktop_dir = self._get_desktop_path()
        # Klasör içine değil, doğrudan Masaüstüne kaydeder
        self.launcher_py_path = os.path.join(self.desktop_dir, "FoxLauncher.py")

        self._setup_styles()
        self._build_ui()

    def _get_desktop_path(self):
        userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        onedrive_desktop = os.path.join(userprofile, "OneDrive", "Desktop")
        std_desktop = os.path.join(userprofile, "Desktop")
        if os.path.isdir(std_desktop):
            return std_desktop
        if os.path.isdir(onedrive_desktop):
            return onedrive_desktop
        return userprofile

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
            thickness=14,
        )

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.bg_card, padx=22, pady=16)
        header.pack(fill="x")

        tk.Label(
            header, text="FOXLAUNCHER (FLC)", font=("Segoe UI", 16, "bold"),
            fg=self.accent_fox, bg=self.bg_card
        ).pack(anchor="w")
        tk.Label(
            header, text="Otomatik Gereksinim Kontrolü & GitHub Kurulum Sihirbazı",
            font=("Segoe UI", 9), fg=self.text_muted, bg=self.bg_card
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(self.root, bg=self.bg_main, padx=22, pady=16)
        body.pack(fill="both", expand=True)

        info_box = tk.Frame(body, bg=self.bg_card, padx=14, pady=12)
        info_box.pack(fill="x", pady=(0, 12))

        tk.Label(
            info_box, text="Kurulum Hedefi (Doğrudan Masaüstü):", font=("Segoe UI", 8, "bold"),
            fg=self.text_muted, bg=self.bg_card
        ).pack(anchor="w")
        tk.Label(
            info_box, text=self.launcher_py_path, font=("Consolas", 9, "bold"),
            fg="#fdba74", bg=self.bg_card
        ).pack(anchor="w", pady=(2, 6))

        tk.Label(
            info_box,
            text="1. Eksik Python kütüphaneleri denetlenir (yüklüyse atlanır).\n"
                 "2. GitHub deposundan en güncel FOXLAUNCHER kodu çekilir.\n"
                 "3. Doğrudan Masaüstüne tek başına FoxLauncher.py oluşturulur.",
            font=("Segoe UI", 8), fg="#cbd5e1", bg=self.bg_card, justify="left"
        ).pack(anchor="w")

        self.step_label = tk.Label(
            body, text="Kuruluma başlamak için aşağıdaki butona tıkla.",
            font=("Segoe UI", 9, "bold"), fg=self.text_main, bg=self.bg_main
        )
        self.step_label.pack(anchor="w", pady=(0, 6))

        self.progress = ttk.Progressbar(
            body, style="Fox.Horizontal.TProgressbar", mode="determinate", maximum=100
        )
        self.progress.pack(fill="x", pady=(0, 12))

        self.log_box = tk.Text(
            body, height=8, bg="#090c10", fg="#d1d5db", font=("Consolas", 8),
            relief="flat", bd=8, state="disabled", wrap="word"
        )
        self.log_box.pack(fill="both", expand=True, pady=(0, 12))

        btn_row = tk.Frame(body, bg=self.bg_main)
        btn_row.pack(fill="x")

        self.start_btn = tk.Button(
            btn_row, text="Kurulumu Başlat", command=self.start_install,
            bg=self.accent_fox, fg="#ffffff", activebackground="#ea580c",
            activeforeground="#ffffff", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=18, pady=8, cursor="hand2"
        )
        self.start_btn.pack(side="left", fill="x", expand=True)

        self.launch_now_btn = tk.Button(
            btn_row, text="FoxLauncher.py'yi Şimdi Aç", command=self.launch_installed_app,
            bg=self.accent_green, fg="#ffffff", activebackground="#15803d",
            activeforeground="#ffffff", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=18, pady=8, cursor="hand2", state="disabled"
        )
        self.launch_now_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))

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
        threading.Thread(target=self._run_wizard, daemon=True).start()

    def _is_package_installed(self, import_name):
        return importlib.util.find_spec(import_name) is not None

    def _fetch_code_from_github(self):
        headers = {"User-Agent": "FLC-SetupWizard/1.0"}
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
                        if item.get("type") == "blob" and not path.lower().endswith(".md"):
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
            self.set_step("Adım 1/3: Gereksinimler kontrol ediliyor...", 10)
            self.log("=== ADIM 1: GEREKSİNİM KONTROLÜ ===")

            total_pkgs = len(REQUIRED_PACKAGES)
            for idx, (import_name, pip_name) in enumerate(REQUIRED_PACKAGES, start=1):
                pct = 10 + int((idx / total_pkgs) * 35)
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
                    self.log(f"[KURULDU] '{pip_name}' başarıyla yüklendi.")

            # AŞAMA 2: GitHub'dan Kod Çekme
            self.set_step("Adım 2/3: GitHub deposundan güncel launcher kodu alınıyor...", 60)
            self.log("\n=== ADIM 2: GITHUB KAYNAK KODU İNDİRME ===")
            launcher_code = self._fetch_code_from_github()
            self.log(f"[BAŞARILI] Kaynak kod indirildi ({len(launcher_code)} karakter).")

            # AŞAMA 3: Doğrudan Masaüstüne FoxLauncher.py Oluşturma
            self.set_step("Adım 3/3: Masaüstüne doğrudan FoxLauncher.py oluşturuluyor...", 85)
            self.log("\n=== ADIM 3: MASAÜSTÜ KURULUMU ===")
            os.makedirs(self.desktop_dir, exist_ok=True)

            with open(self.launcher_py_path, "w", encoding="utf-8") as f:
                f.write(launcher_code)
            self.log(f"[OLUŞTURULDU] {self.launcher_py_path}")

            self.set_step("Kurulum başarıyla tamamlandı! Masaüstünde FoxLauncher.py hazır.", 100)
            self.log("\n=== KURULUM TAMAMLANDI ===")
            self.log("Doğrudan Masaüstündeki 'FoxLauncher.py' dosyasına çift tıklayarak açabilirsin.")

            self.root.after(0, lambda: (
                self.start_btn.config(text="Kurulum Tamamlandı ✓"),
                self.launch_now_btn.config(state="normal")
            ))

        except Exception as e:
            self.log(f"\n[HATA] {e}")
            self.set_step("Kurulum sırasında hata oluştu.", 0)
            self.root.after(0, lambda: (
                messagebox.showerror("Kurulum Hatası", str(e)),
                self.start_btn.config(state="normal", text="Tekrar Dene")
            ))

    def launch_installed_app(self):
        if not os.path.isfile(self.launcher_py_path):
            messagebox.showerror("Hata", "FoxLauncher.py dosyası bulunamadı.")
            return
        python_exe = sys.executable
        if sys.platform == "win32" and python_exe.lower().endswith("python.exe"):
            pythonw = python_exe[:-10] + "pythonw.exe"
            if os.path.isfile(pythonw):
                python_exe = pythonw
        subprocess.Popen([python_exe, self.launcher_py_path], cwd=self.desktop_dir)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FoxSetupWizard(root)
    root.mainloop()
