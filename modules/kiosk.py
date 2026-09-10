import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import sys
import subprocess
import threading
import json
import time
from modules.utils import ServiceUtils

class KioskView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.colors = controller.colors
        self.project_dir = Path(controller.project_dir)
        self.learn_win = None
        self.is_updating = False

        # Paths
        self.autostart_dir = Path.home() / ".config/autostart"
        self.ch_desktop = self.autostart_dir / "pommypc-chromium.desktop"

        self.killswitch_file = self.project_dir / "scripts/killswitch.py"
        self.ks_service_file = Path("/etc/systemd/system/pommypc-killswitch.service")
        self.config_file = Path.home() / ".pommypc_killswitch_config"

        # Camera stream URLs
        self.camera_urls = [
            "http://localhost:3180/api/streams/cams/0",
            "http://localhost:3180/api/streams/cams/1",
            "http://localhost:3180/api/streams/cams/2",
        ]

        # ===================== HEADER =====================
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", pady=(10, 20))

        self.btn_back = ctk.CTkButton(self.header, text="←", width=50, height=35,
                                      fg_color=self.colors["card"],
                                      border_color=self.colors["header"],
                                      border_width=1,
                                      text_color="white", command=controller.show_menu)
        self.btn_back.pack(side="left", padx=20)

        self.lbl_title = ctk.CTkLabel(self.header, text="Kiosk & Camera Setup",
                                      font=("Roboto", 28, "bold"), text_color="white")
        self.lbl_title.pack(side="left", padx=10)

        # ===================== INFO =====================
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.lbl_info = ctk.CTkLabel(info_frame,
                                     text="Configure the Autodarts kiosk browser, on-screen keyboard, kill-switch, and camera focus.",
                                     font=("Roboto", 14), text_color=self.colors["fg_dim"],
                                     wraplength=720, justify="left")
        self.lbl_info.pack(fill="x", padx=20)

        # ===================== URL ENTRY =====================
        url_container = ctk.CTkFrame(self, fg_color="transparent")
        url_container.pack(fill="x", pady=(5, 20), padx=40)
        ctk.CTkLabel(url_container, text="Kiosk URL", font=("Roboto", 13, "bold"),
                     text_color=self.colors["fg_dim"]).pack(anchor="w", padx=5)
        self.url_ent = ctk.CTkEntry(url_container, font=("Roboto", 16), height=50,
                                    corner_radius=10, border_color=self.colors["header"],
                                    fg_color=self.colors["bg"], text_color="white")
        self.url_ent.insert(0, "https://play.autodarts.io/")
        self.url_ent.pack(fill="x", pady=8)

        # ===================== BROWSER SECTION =====================
        browser_frame = ctk.CTkFrame(self, fg_color="transparent")
        browser_frame.pack(fill="x", padx=40)

        ch_box = ctk.CTkFrame(browser_frame, fg_color=self.colors["card"], corner_radius=12,
                              border_width=1, border_color=self.colors["header"])
        ch_box.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(ch_box, text="Chromium Kiosk", font=("Roboto", 15, "bold"),
                     text_color=self.colors["accent"]).pack(pady=(12, 5))

        ch_btn_frame = ctk.CTkFrame(ch_box, fg_color="transparent")
        ch_btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.btn_auto_ch = ctk.CTkButton(ch_btn_frame, text="", height=50, corner_radius=8,
                                         text_color="white", text_color_disabled="white",
                                         font=("Roboto", 14, "bold"),
                                         command=lambda: self.toggle_autostart("Chromium"))
        self.btn_auto_ch.pack(side="left", expand=True, fill="x", padx=5)

        self.btn_now_ch = ctk.CTkButton(ch_btn_frame, text="Launch Now", height=50, corner_radius=8,
                                        fg_color=self.colors["accent"],
                                        hover_color="#15803d",
                                        text_color="white", text_color_disabled="white",
                                        font=("Roboto", 14, "bold"),
                                        command=lambda: self.launch_now("Chromium"))
        self.btn_now_ch.pack(side="left", expand=True, fill="x", padx=5)

        # ===================== CAMERA FOCUS =====================
        cam_box = ctk.CTkFrame(self, fg_color=self.colors["card"], corner_radius=12,
                               border_width=1, border_color=self.colors["header"])
        cam_box.pack(fill="x", padx=40, pady=(0, 15))

        ctk.CTkLabel(cam_box, text="📷  Camera Focus", font=("Roboto", 15, "bold"),
                     text_color=self.colors["accent"]).pack(pady=(12, 5))

        ctk.CTkLabel(cam_box, text="Open a live preview for each camera to check and adjust focus.",
                     font=("Roboto", 12), text_color=self.colors["fg_dim"]).pack(pady=(0, 10))

        cam_btn_frame = ctk.CTkFrame(cam_box, fg_color="transparent")
        cam_btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        for i, url in enumerate(self.camera_urls):
            btn = ctk.CTkButton(cam_btn_frame, text=f"Camera {i + 1}", height=50, corner_radius=8,
                                fg_color=self.colors["header"],
                                hover_color=self.colors["accent"],
                                text_color="white", font=("Roboto", 14, "bold"),
                                command=lambda u=url: self.open_camera(u))
            btn.pack(side="left", expand=True, fill="x", padx=5)

        # ===================== ON-SCREEN KEYBOARD =====================
        osk_container = ctk.CTkFrame(self, fg_color=self.colors["card"], corner_radius=12,
                                     border_width=1, border_color=self.colors["header"])
        osk_container.pack(fill="x", padx=40, pady=(0, 12))

        ctk.CTkLabel(osk_container, text="On-Screen Keyboard", font=("Roboto", 14, "bold"),
                     text_color="white").pack(side="left", padx=20, pady=12)

        self.btn_toggle_osk = ctk.CTkButton(osk_container, text="", width=130, height=38,
                                            corner_radius=8,
                                            text_color="white", text_color_disabled="white",
                                            font=("Roboto", 13, "bold"),
                                            command=self.toggle_osk)
        self.btn_toggle_osk.pack(side="right", padx=15)

        # ===================== KILL-SWITCH =====================
        ks_container = ctk.CTkFrame(self, fg_color=self.colors["card"], corner_radius=12,
                                    border_width=1, border_color=self.colors["header"])
        ks_container.pack(fill="x", padx=40, pady=(0, 20))

        ctk.CTkLabel(ks_container, text="Kill-Switch", font=("Roboto", 14, "bold"),
                     text_color="white").pack(pady=(12, 5))

        ks_inner = ctk.CTkFrame(ks_container, fg_color="transparent")
        ks_inner.pack(fill="x", padx=15, pady=5)

        self.btn_learn = ctk.CTkButton(ks_inner, text="Learn Key", height=42, corner_radius=8,
                                       fg_color=self.colors["accent"],
                                       hover_color="#15803d",
                                       text_color="white", text_color_disabled="white",
                                       font=("Roboto", 13, "bold"),
                                       command=self.start_learning_wrapper)
        self.btn_learn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.info_box = ctk.CTkFrame(ks_inner, fg_color=self.colors["bg"], height=42,
                                     corner_radius=8, border_width=1,
                                     border_color=self.colors["header"])
        self.info_box.pack(side="left", expand=True, fill="both")

        self.key_label = ctk.CTkLabel(self.info_box, text="No key assigned",
                                      font=("Roboto", 12, "bold"),
                                      text_color=self.colors["fg_dim"])
        self.key_label.pack(expand=True)

        self.btn_toggle_ks = ctk.CTkButton(ks_container, text="", height=50, corner_radius=10,
                                           font=("Roboto", 15, "bold"),
                                           text_color="white", text_color_disabled="white",
                                           command=self.toggle_ks_service)
        self.btn_toggle_ks.pack(fill="x", padx=15, pady=(10, 15))

        self.update_status()

    # ===================== CAMERA =====================
    def open_camera(self, url):
        """Open a camera stream in a regular (non-kiosk) Chromium window."""
        cmd = f"chromium-browser --new-window '{url}' &"
        subprocess.Popen(cmd, shell=True)

    # ===================== BROWSER =====================
    def toggle_autostart(self, browser):
        if self.ch_desktop.exists():
            self.ch_desktop.unlink()
        else:
            if not self.autostart_dir.exists():
                self.autostart_dir.mkdir(parents=True, exist_ok=True)
            url = self.url_ent.get().strip()
            browser_cmd = f"chromium-browser --kiosk --password-store=basic {url}"
            cmd = f"bash -c 'sleep 3; {browser_cmd}'"
            with open(self.ch_desktop, "w") as f:
                f.write(f"[Desktop Entry]\nType=Application\nName=PommyPC-Kiosk\nExec={cmd}\n")
        self.update_status()

    def launch_now(self, browser):
        url = self.url_ent.get().strip()
        cmd = f"chromium-browser --kiosk --password-store=basic {url} &"
        subprocess.Popen(cmd, shell=True)

    # ===================== OSK =====================
    def toggle_osk(self):
        try:
            res = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.a11y.applications", "screen-keyboard-enabled"],
                text=True).strip()
            new_state = "false" if res == "true" else "true"
            subprocess.run(["gsettings", "set", "org.gnome.desktop.a11y.applications",
                            "screen-keyboard-enabled", new_state])
        except Exception as e:
            messagebox.showerror("Error", f"Could not toggle OSK: {e}")
        self.update_status()

    # ===================== KILL-SWITCH =====================
    def stop_ks_quietly(self):
        cmd = (f"systemctl stop pommypc-killswitch; systemctl disable pommypc-killswitch; "
               f"rm -f {self.ks_service_file}; systemctl daemon-reload")
        subprocess.run(ServiceUtils.sudo_cmd(cmd), shell=True, stderr=subprocess.DEVNULL)

    def start_learning_wrapper(self):
        self.stop_ks_quietly()
        self.update_status()
        self.start_learning()

    def start_learning(self):
        if hasattr(self, "learn_win") and self.learn_win is not None and self.learn_win.winfo_exists():
            self.learn_win.focus_set()
            return

        learn_script = self.project_dir / "scripts" / "tmp_learn.py"
        with open(learn_script, "w") as f:
            f.write(f"""
import evdev, time, json, sys, os
from select import select
try:
    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    last_k, count, last_t = None, 0, 0
    while True:
        r, w, x = select(devices, [], [], 0.5)
        for dev in r:
            try:
                for ev in dev.read():
                    if ev.type == 1 and ev.value == 1:
                        now = time.time()
                        if ev.code == last_k and now - last_t < 1.5: count += 1
                        else: count = 1
                        last_k, last_t = ev.code, now
                        print(f"FEEDBACK:{{count}}", flush=True)
                        if count >= 5:
                            kn = evdev.ecodes.KEY.get(ev.code, f"CODE:{{ev.code}}")
                            config_data = {{"device": dev.path, "key": ev.code, "key_name": kn, "ts": time.time()}}
                            with open("{self.config_file}", "w") as f_cfg:
                                json.dump(config_data, f_cfg)
                            os.chmod("{self.config_file}", 0o666)
                            print("SUCCESS", flush=True)
                            time.sleep(0.1)
                            sys.exit(0)
            except: continue
except Exception as e:
    print(f"ERROR:{{e}}", flush=True)
    sys.exit(1)
""")

        self.learn_win = ctk.CTkToplevel(self)
        self.learn_win.title("Learn Kill-Switch Key")
        self.learn_win.geometry("400x250")
        self.learn_win.transient(self)
        ctk.CTkLabel(self.learn_win,
                     text="Press your kill-switch key 5 times",
                     font=("Roboto", 14, "bold"), text_color="white").pack(pady=20)
        self.lbl_count = ctk.CTkLabel(self.learn_win, text="0 / 5",
                                      font=("Roboto", 40, "bold"),
                                      text_color=self.colors["accent"])
        self.lbl_count.pack(pady=10)
        threading.Thread(target=self.run_learn, args=(learn_script,), daemon=True).start()

    def run_learn(self, path):
        proc = subprocess.Popen(ServiceUtils.sudo_cmd(f"{sys.executable} {path}"),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, shell=True, bufsize=1)
        success = False
        old_ts = 0
        path = Path(path)
        if self.config_file.exists():
            old_ts = self.config_file.stat().st_mtime
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if "FEEDBACK:" in line:
                    try:
                        c = line.split(":")[1].strip()
                        self.after(0, lambda val=c: self.lbl_count.configure(text=f"{val} / 5"))
                    except:
                        pass
                if "SUCCESS" in line:
                    success = True
                    break
        except:
            pass

        def cleanup_window():
            if self.learn_win is not None:
                self.learn_win.destroy()
                self.learn_win = None

        self.after(0, cleanup_window)
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except:
            pass
        if proc.returncode == 0 or (self.config_file.exists() and
                                     self.config_file.stat().st_mtime > old_ts):
            success = True
        if path.exists():
            try:
                path.unlink()
            except:
                pass
        if success:
            self.after(100, self.auto_enable_ks)
        else:
            self.after(100, self.update_status)

    def auto_enable_ks(self):
        self.toggle_ks_service(force_enable=True)

    def toggle_ks_service(self, force_enable=False):
        status = ServiceUtils.check_status("pommypc-killswitch")
        is_installed = (status == "running" or status == "stopped")
        if force_enable or not is_installed:
            if not self.config_file.exists():
                messagebox.showwarning("Pommy PC", "Please learn a kill-switch key first.")
                return
            python_exe = sys.executable
            svc_content = (
                f"[Unit]\nDescription=Pommy PC Kill-Switch\nAfter=multi-user.target\n\n"
                f"[Service]\nType=simple\n"
                f"ExecStart={python_exe} {self.killswitch_file} {self.config_file}\n"
                f"Restart=always\nStandardOutput=journal\nStandardError=journal\n\n"
                f"[Install]\nWantedBy=multi-user.target\n"
            )
            temp_svc = Path.home() / "pommypc-killswitch.service"
            try:
                with open(temp_svc, "w") as f:
                    f.write(svc_content)
                cmd = ServiceUtils.sudo_cmd(
                    f"mv {temp_svc} {self.ks_service_file} && systemctl daemon-reload && "
                    f"systemctl enable pommypc-killswitch && systemctl start pommypc-killswitch"
                )
                ServiceUtils.run_bash_script(self, cmd, "Kill-Switch Activation",
                                             on_close=self.update_status)
            except Exception as e:
                messagebox.showerror("Error", f"Service could not be created: {e}")
        else:
            cmd = ServiceUtils.sudo_cmd(
                f"systemctl stop pommypc-killswitch; systemctl disable pommypc-killswitch; "
                f"rm -f {self.ks_service_file}; systemctl daemon-reload"
            )
            ServiceUtils.run_bash_script(self, cmd, "Kill-Switch Deactivation",
                                         on_close=self.update_status)
        self.update_status()

    # ===================== STATUS =====================
    def update_status(self):
        if self.is_updating:
            return
        self.is_updating = True
        threading.Thread(target=self._update_status_worker, daemon=True).start()

    def _update_status_worker(self):
        try:
            osk_active = False
            try:
                res = subprocess.check_output(
                    ["gsettings", "get", "org.gnome.desktop.a11y.applications",
                     "screen-keyboard-enabled"], text=True).strip()
                osk_active = (res == "true")
            except:
                pass

            ks_status = ServiceUtils.check_status("pommypc-killswitch")
            ch_active = self.ch_desktop.exists()

            self.after(0, lambda: self._update_ui(osk_active, ks_status, ch_active))
        except Exception as e:
            print(f"Kiosk update error: {e}")
        finally:
            self.is_updating = False

    def _update_ui(self, osk_active, ks_status, ch_active):
        grey = self.colors["header"]
        green = self.colors["success"]
        accent = self.colors["accent"]

        # OSK
        self.btn_toggle_osk.configure(
            text="OSK: ON" if osk_active else "OSK: OFF",
            fg_color=green if osk_active else grey,
            hover_color="#15803d" if osk_active else "#3f3f46"
        )

        # Kill-switch key label
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.key_label.configure(
                        text=f"Key: {data.get('key_name', '?')}",
                        text_color=green
                    )
            except:
                pass
        else:
            self.key_label.configure(text="No key assigned", text_color=self.colors["fg_dim"])

        # Kill-switch button
        if ks_status == "running":
            self.btn_toggle_ks.configure(text="Kill-Switch: ON ✓", fg_color=green,
                                         hover_color="#15803d")
        elif ks_status == "stopped":
            self.btn_toggle_ks.configure(text="Kill-Switch: Installed (stopped)", fg_color=grey,
                                         hover_color="#3f3f46")
        else:
            self.btn_toggle_ks.configure(text="Kill-Switch: OFF", fg_color=grey,
                                         hover_color="#3f3f46")

        # Autostart button
        self.btn_auto_ch.configure(
            text="Autostart: ON ✓" if ch_active else "Autostart: OFF",
            fg_color=green if ch_active else grey,
            hover_color="#15803d" if ch_active else "#3f3f46"
        )

    def update_texts(self):
        # Static English text — nothing to translate
        self.update_status()
