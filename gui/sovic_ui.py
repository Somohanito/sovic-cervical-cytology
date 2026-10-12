"""
INTERFAZ - SOVIC (Sistema Optomecatrónico de Citología Cervical)
VERSIÓN RASPBERRY PI 7" (1024x600 HORIZONTAL) - Touch & Control Mecatrónico
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
from pathlib import Path
import cv2
import serial
import threading
import queue
import time
import glob
import shutil
from datetime import datetime

# ======================================================
# CONFIGURACIÓN GENERAL DE LA INTERFAZ
# ======================================================

CLASES = ["HSIL", "LSIL", "NILM"]
IMG_SIZE = (224, 224)

COLORES = {
    "HSIL": "#e74c3c",
    "LSIL": "#f39c12",
    "NILM": "#27ae60"
}

NILM_NEG_THRESHOLD = 0.90


# ======================================================
# INTERFAZ RASPBERRY PI 1024x600 - TOUCH + CÁMARA + SERIAL ESP32
# ======================================================

class AplicacionClasificador:
    def __init__(self, root):
        self.root = root
        self.root.title("SOVIC - Citología Cervical")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")
        self.root.resizable(False, False)
        self.root.update_idletasks()
        self.root.attributes("-fullscreen", True)
        self.root.after(150, lambda: self.root.attributes("-fullscreen", True))

        self.app_container = tk.Frame(self.root)
        self.app_container.pack(fill="both", expand=True)
        self._ui_root = self.app_container

        # Paleta de colores de la interfaz
        self.BG = "#0f172a"
        self.PANEL = "#111827"
        self.PANEL2 = "#1f2937"
        self.DARK = "#020617"
        self.FG = "white"
        self.MUTED = "#94a3b8"
        self.BLUE = "#38bdf8"
        self.GREEN = "#22c55e"
        self.YELLOW = "#f59e0b"
        self.RED = "#ef4444"

        # Control de Cámara
        self.camera_index = 0
        self.cap = None
        self.last_frame_bgr = None
        self.camera_running = False

        self.base_capture_dir = Path("./capturas")
        for d in [self.base_capture_dir / "NILM", self.base_capture_dir / "LESION" / "LSIL", self.base_capture_dir / "LESION" / "HSIL"]:
            d.mkdir(parents=True, exist_ok=True)

        # Control de Escaneo Sincronizado
        self.base_scan_dir = Path("./escaneos")
        self.base_scan_dir.mkdir(parents=True, exist_ok=True)
        self.scan_manual_active = False
        self.current_sample_dir = None
        self.current_csv_path = None

        # Estado Platina / ESP32
        self.esp_x = 0
        self.esp_y = 0
        self.grid_w = 24
        self.grid_h = 9
        self.visited = set()
        self.suspect = set()

        # Comunicación Serial con ESP32-C3
        self.serial_queue = queue.Queue()
        self.esp_port = "/dev/ttyACM0"
        self.esp_baud = 115200
        self.ser = None
        self.serial_running = True
        self.closing = False

        self._build_layout()

        self._set_status("Iniciando cámara y sistemas...")
        self.root.update_idletasks()

        self._start_camera()
        self._start_serial_reader()
        self.root.after(100, self._process_serial_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_status(self, msg):
        self.lbl_status.configure(text=msg)

    def _build_layout(self):
        self.app_container.configure(bg=self.BG)

        header = tk.Frame(self.app_container, bg=self.BG, height=48)
        header.pack(fill="x", padx=12, pady=(6, 4))
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SOVIC · Citología Cervical",
            bg=self.BG,
            fg=self.FG,
            font=("Arial", 18, "bold")
        ).pack(side="left")

        btn_info = tk.Button(
            header,
            text="ⓘ",
            bg=self.BG,
            fg=self.BLUE,
            font=("Arial", 18, "bold"),
            bd=0,
            activebackground=self.BG,
            activeforeground="#7dd3fc",
            cursor="hand2",
            command=self._show_system_status
        )
        btn_info.pack(side="right", padx=(0, 4))

        btn_explorer = tk.Button(
            header,
            text="Muestras",
            bg=self.BG,
            fg=self.BLUE,
            font=("Arial", 11, "bold"),
            bd=0,
            activebackground=self.BG,
            activeforeground="#7dd3fc",
            cursor="hand2",
            command=self._show_sample_explorer
        )
        btn_explorer.pack(side="right", padx=(0, 8))

        self.lbl_status = tk.Label(header, text="—", bg=self.BG, fg=self.BG, font=("Arial", 10), anchor="e")
        self.lbl_status.pack(side="right", fill="x", expand=True)

        body = tk.Frame(self.app_container, bg=self.BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.pack_propagate(False)

        # Panel Izquierdo: Cámara en Vivo (40%)
        left = tk.Frame(body, bg=self.PANEL)
        left.place(relx=0, rely=0, relwidth=0.40, relheight=1.0)

        tk.Label(left, text="Cámara en vivo", bg=self.PANEL, fg=self.FG, font=("Arial", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 2))

        self.lbl_camera = tk.Label(left, bg=self.DARK, fg=self.MUTED, text="Cámara no iniciada", font=("Arial", 12, "bold"), justify="center")
        self.lbl_camera.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        camera_buttons = tk.Frame(left, bg=self.PANEL, height=52)
        camera_buttons.pack(fill="x", padx=8, pady=(0, 6))
        camera_buttons.pack_propagate(False)

        btn_main = {"font": ("Arial", 11, "bold"), "bg": self.BLUE, "fg": "black", "bd": 0, "height": 2}
        btn_dark = {"font": ("Arial", 10, "bold"), "bg": self.PANEL2, "fg": self.FG, "bd": 0, "height": 2}

        tk.Button(camera_buttons, text="Tomar foto y analizar", command=self.tomar_foto_y_analizar, **btn_main).pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Button(camera_buttons, text="Reiniciar cámara", command=self._restart_camera, **btn_dark).pack(side="left", fill="both", expand=True, padx=(4, 0))

        scan_buttons = tk.Frame(left, bg=self.PANEL, height=44)
        scan_buttons.pack(fill="x", padx=8, pady=(0, 6))
        scan_buttons.pack_propagate(False)

        tk.Button(scan_buttons, text="Iniciar escaneo", command=self.iniciar_escaneo_manual, **btn_dark).pack(side="left", fill="both", expand=True, padx=(0, 3))
        tk.Button(scan_buttons, text="Detener", command=self.detener_escaneo_manual, **btn_dark).pack(side="left", fill="both", expand=True, padx=3)
        tk.Button(scan_buttons, text="Inicio", command=lambda: self.enviar_comando_esp("HOME"), **btn_dark).pack(side="left", fill="both", expand=True, padx=(3, 0))

        origin_buttons = tk.Frame(left, bg=self.PANEL, height=40)
        origin_buttons.pack(fill="x", padx=8, pady=(0, 8))
        origin_buttons.pack_propagate(False)
        tk.Button(origin_buttons, text="Fijar este punto como inicio (0,0)", command=lambda: self.enviar_comando_esp("SET_ORIGIN"), **btn_dark).pack(side="left", fill="both", expand=True)

        # Panel Derecho: Grad-CAM + Resultados + Mapa (60%)
        right = tk.Frame(body, bg=self.BG)
        right.place(relx=0.41, rely=0, relwidth=0.59, relheight=1.0)
        right.pack_propagate(False)

        grad_panel = tk.Frame(right, bg=self.PANEL)
        grad_panel.pack(fill="both", expand=True, pady=(0, 8))
        grad_panel.pack_propagate(False)

        tk.Label(grad_panel, text="Grad-CAM (Explicabilidad)", bg=self.PANEL, fg=self.FG, font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(8, 3))
        self.lbl_gradcam = tk.Label(grad_panel, bg=self.DARK, fg=self.MUTED, text="Sin análisis", font=("Arial", 13, "bold"), justify="center")
        self.lbl_gradcam.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        result = tk.Frame(right, bg=self.PANEL, height=134)
        result.pack(fill="x", pady=(0, 8))
        result.pack_propagate(False)

        tk.Label(result, text="Resultado de Triaje", bg=self.PANEL, fg=self.FG, font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
        self.lbl_pred = tk.Label(result, text="Predicción: —", bg=self.PANEL, fg=self.FG, font=("Arial", 19, "bold"), anchor="w")
        self.lbl_pred.pack(fill="x", padx=12)
        self.lbl_probs = tk.Label(result, text="HSIL: —   LSIL: —   NILM: —", bg=self.PANEL, fg=self.MUTED, font=("Consolas", 10), anchor="w")
        self.lbl_probs.pack(fill="x", padx=12, pady=(2, 0))
        self.lbl_saved = tk.Label(result, text="Guardado: —", bg=self.PANEL, fg=self.MUTED, font=("Arial", 9, "bold"), anchor="w")
        self.lbl_saved.pack(fill="x", padx=12, pady=(2, 0))

        coord = tk.Frame(right, bg=self.PANEL, height=70)
        coord.pack(fill="x", pady=(0, 8))
        coord.pack_propagate(False)

        tk.Label(coord, text="Posición de laminilla", bg=self.PANEL, fg=self.FG, font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(7, 0))
        self.lbl_coord = tk.Label(coord, text="X=0   Y=0", bg=self.PANEL, fg=self.BLUE, font=("Arial", 22, "bold"))
        self.lbl_coord.pack(anchor="w", padx=12)

        tk.Label(
            coord,
            text="Desarrollado por Ing. Axel Daniel Somohano Maldonado",
            bg=self.PANEL, fg="#3d4f61", font=("Arial", 7), anchor="w"
        ).pack(anchor="w", padx=12, pady=(2, 0))

        map_panel = tk.Frame(right, bg=self.PANEL, height=190)
        map_panel.pack(fill="x", pady=(0, 8))
        map_panel.pack_propagate(False)

        tk.Label(map_panel, text="Mapa de recorrido 24 × 9", bg=self.PANEL, fg=self.FG, font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 3))
        self.canvas = tk.Canvas(map_panel, width=362, height=144, bg=self.DARK, highlightthickness=0)
        self.canvas.pack(padx=12, pady=(0, 8))
        self._draw_slide_map()

    def _draw_slide_map(self):
        self.canvas.delete("all")
        cw, ch, margin_x, margin_y = 362, 144, 12, 14
        grid_w_px, grid_h_px = cw - 2 * margin_x, ch - 2 * margin_y - 8
        cell_w, cell_h = grid_w_px / self.grid_w, grid_h_px / self.grid_h

        self.canvas.create_rectangle(margin_x - 5, margin_y - 5, margin_x + grid_w_px + 5, margin_y + grid_h_px + 5, outline="#475569", width=2, fill="#0f172a")

        for y in range(self.grid_h):
            for x in range(self.grid_w):
                x1 = margin_x + x * cell_w
                y1 = margin_y + y * cell_h
                fill = "#1e293b"
                if (x, y) in self.visited: fill = "#164e63"
                if (x, y) in self.suspect: fill = "#7f1d1d"
                if x == self.esp_x and y == self.esp_y: fill = self.BLUE
                self.canvas.create_rectangle(x1, y1, x1 + cell_w - 1, y1 + cell_h - 1, fill=fill, outline="#334155")

        self.canvas.create_text(cw // 2, ch - 7, text=f"Campo actual: X={self.esp_x}  Y={self.esp_y}", fill=self.MUTED, font=("Arial", 9, "bold"))

    def _start_camera(self):
        try:
            if self.cap is not None: self.cap.release()
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            if not self.cap.isOpened():
                self.camera_running = False
                self._set_status("Cámara no detectada.")
                return
            self.camera_running = True
            self._update_camera_frame()
        except Exception as e:
            self.camera_running = False
            self._set_status(f"Error cámara: {e}")

    def _restart_camera(self):
        self._start_camera()

    def _update_camera_frame(self):
        if not self.camera_running or self.cap is None: return
        ok, frame = self.cap.read()
        if ok:
            self.last_frame_bgr = frame.copy()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail((max(self.lbl_camera.winfo_width(), 100), max(self.lbl_camera.winfo_height(), 100)))
            foto = ImageTk.PhotoImage(img)
            self.lbl_camera.configure(image=foto, text="")
            self.lbl_camera.image = foto
        self.root.after(30, self._update_camera_frame)

    def tomar_foto_y_analizar(self):
        if self.last_frame_bgr is None:
            messagebox.showwarning("Cámara", "No hay imagen disponible.")
            return
        # Simulación de interfaz limpia sin pesos expuestos
        messagebox.showinfo("SOVIC - Modo Demostración", "Captura realizada. Módulo de inferencia protegido.")

    def iniciar_escaneo_manual(self):
        self.scan_manual_active = True
        self.enviar_comando_esp("START_SCAN")
        self._set_status("Escaneo manual iniciado.")

    def detener_escaneo_manual(self):
        self.scan_manual_active = False
        self.enviar_comando_esp("STOP_SCAN")
        self._set_status("Escaneo detenido.")

    def _start_serial_reader(self):
        def worker():
            while self.serial_running and not self.closing:
                if self.ser is None or not self.ser.is_open:
                    try:
                        self.ser = serial.Serial(self.esp_port, self.esp_baud, timeout=1)
                    except Exception:
                        time.sleep(1.0)
                        continue
                try:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    if line: self.serial_queue.put(("SERIAL", line))
                except Exception:
                    self.ser = None
                    time.sleep(1.0)
        threading.Thread(target=worker, daemon=True).start()

    def enviar_comando_esp(self, comando):
        try:
            if self.ser and self.ser.is_open:
                self.ser.write((comando + "\n").encode("utf-8"))
                self.ser.flush()
        except Exception:
            self.ser = None

    def _process_serial_queue(self):
        while not self.serial_queue.empty():
            tipo, data = self.serial_queue.get()
            if tipo == "SERIAL":
                parts = data.split(",")
                if parts[0] == "POS" and len(parts) >= 3:
                    self.esp_x, self.esp_y = int(parts[1]), int(parts[2])
                    self.lbl_coord.configure(text=f"X={self.esp_x}   Y={self.esp_y}")
                    self._draw_slide_map()
        if not self.closing:
            self.root.after(100, self._process_serial_queue)

    def _show_system_status(self):
        win = tk.Toplevel(self.root)
        win.title("Estado del Sistema")
        win.configure(bg="#111827")
        win.geometry("320x220")
        tk.Label(win, text="Estado del Sistema", bg="#111827", fg="white", font=("Arial", 15, "bold")).pack(pady=20)
        tk.Button(win, text="Cerrar", command=win.destroy, bg="#1f2937", fg="white").pack(pady=10)

    def _show_sample_explorer(self):
        messagebox.showinfo("Explorador", "Módulo de muestras guardadas.")

    def _on_close(self):
        self.closing = True
        self.serial_running = False
        if self.cap: self.cap.release()
        if self.ser and self.ser.is_open: self.ser.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    AplicacionClasificador(root)
    root.mainloop()

if __name__ == "__main__":
    main()