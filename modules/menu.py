import tkinter as tk
import customtkinter as ctk

class MainMenu(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.colors = controller.colors

        # Grid — 2 columns, 2 tile rows + header + footer
        self.grid_columnconfigure((0, 1), weight=1, uniform="tiles")
        self.grid_rowconfigure((1, 2), weight=1, uniform="tiles")

        # ===================== HEADER =====================
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(20, 10))

        ctk.CTkLabel(header, text="🖨", font=("Roboto", 36), text_color=self.colors["accent"]).pack(side="left", padx=(40, 8))
        ctk.CTkLabel(header, text="Pommy PC", font=("Roboto", 36, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(header, text="Autodarts Setup", font=("Roboto", 18), text_color=self.colors["fg_dim"]).pack(side="left", padx=(12, 0), pady=(10, 0))

        # ===================== MENU TILES =====================
        # Row 1
        self._make_tile(self.controller.show_autodarts, "Autodarts", "🎯",
                        "Manage the Autodarts\nservice", 1, 0)
        self._make_tile(self.controller.show_autoglow, "AutoGlow", "💡",
                        "LED ring lighting\ncontrol", 1, 1)

        # Row 2
        self._make_tile(self.controller.show_kiosk, "Kiosk & Cameras", "🖥️",
                        "Browser kiosk, camera\nfocus & kill-switch", 2, 0)
        self._make_tile(self.controller.show_touch, "Screen & Touch", "📱",
                        "Display rotation &\ntouch mapping", 2, 1)

        # ===================== FOOTER =====================
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, columnspan=2, pady=(10, 20))
        ctk.CTkLabel(footer, text="pommyprints.com.au",
                     font=("Roboto", 12), text_color=self.colors["fg_dim"]).pack()

    def _make_tile(self, cmd, title, emoji, subtitle, row, col):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="nsew", padx=15, pady=15)

        btn = ctk.CTkFrame(frame, fg_color=self.colors["card"],
                           corner_radius=15,
                           border_width=1,
                           border_color=self.colors["header"],
                           cursor="hand2")
        btn.pack(expand=True, fill="both")
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(border_color=self.colors["accent"]))
        btn.bind("<Leave>", lambda e: btn.configure(border_color=self.colors["header"]))

        # Emoji
        ctk.CTkLabel(btn, text=emoji, font=("Roboto", 42),
                     text_color="white").pack(pady=(30, 5))

        # Title
        ctk.CTkLabel(btn, text=title, font=("Roboto", 18, "bold"),
                     text_color="white").pack()

        # Subtitle
        ctk.CTkLabel(btn, text=subtitle, font=("Roboto", 12),
                     text_color=self.colors["fg_dim"],
                     justify="center").pack(pady=(4, 25))

    def update_texts(self):
        # Static English — nothing to update dynamically
        pass
