"""
TANGKAP BOLA - Mini Game Grafik Komputer (logika di Python, tampilan di HTML)
Algoritma utama : Collision Detection Lingkaran vs AABB (Axis-Aligned Bounding Box)
Pendukung       : Translasi 2D (pergeseran posisi) berbasis delta time

ARSITEKTUR
  Python (file ini) : PROSES -> game loop 60 FPS, translasi, collision, skor, nyawa, level, riwayat
  HTML              : INPUT & OUTPUT -> kirim tombol/mouse ke Python, gambar state dari Python

Jalankan : python GK_MiniGame.py     (lalu buka http://localhost:8000)
Butuh    : Python 3 saja (tanpa library tambahan). File TangkapBola.html harus satu folder.
"""
import json
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import random

W, H = 900, 600
R_BOLA = 12
NYAWA_AWAL = 5
KECEPATAN_KERANJANG = 550          # px/detik

# nama, jeda munculnya bola (detik), rentang kecepatan jatuh (px/detik), warna, keterangan
LEVELS = {
    "1": ("CUNGPRET",    1.10, (80, 160),  "#78ffa0", "bola lambat, sedikit"),
    "2": ("LUMAYAN LAH", 0.75, (100, 170), "#ffdc64", "bola lambat, banyak"),
    "3": ("GOAT",        0.55, (220, 360), "#ff6e78", "bola banyak, kencang"),
}

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE, "TangkapBola.html")
HIST_FILE = os.path.join(BASE, "riwayat.json")


# ======================================================================
# ALGORITMA UTAMA: COLLISION DETECTION  LINGKARAN vs AABB
# ======================================================================
def circle_aabb(cx, cy, r, box):
    """Lingkaran (cx, cy, r) vs kotak box = (min_x, min_y, max_x, max_y).

    1. CLAMP : titik pada kotak yang paling dekat dengan pusat lingkaran
               nx = max(min_x, min(cx, max_x)) ; ny = max(min_y, min(cy, max_y))
    2. JARAK : dx = cx - nx ; dy = cy - ny ; d^2 = dx^2 + dy^2
    3. UJI   : tabrakan jika d^2 <= r^2   (tanpa akar kuadrat)
    """
    min_x, min_y, max_x, max_y = box
    nx = max(min_x, min(cx, max_x))
    ny = max(min_y, min(cy, max_y))
    dx, dy = cx - nx, cy - ny
    d2 = dx * dx + dy * dy
    return d2 <= r * r, (nx, ny), d2


class Game:
    def __init__(self):
        self.lock = threading.RLock()
        self.keys = set()
        self.level = None          # None = menu
        self.debug = False
        self.log = "-"
        self.arah = 0
        self.hist = self._load()
        self.reset()

    # ---------------- riwayat ----------------
    def _load(self):
        try:
            with open(HIST_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        try:
            with open(HIST_FILE, "w", encoding="utf-8") as f:
                json.dump(self.hist, f, ensure_ascii=False)
        except Exception:
            pass

    def best(self, nama):
        return max([h["s"] for h in self.hist if h["l"] == nama], default=0)

    # ---------------- state ----------------
    def reset(self):
        self.kr = [W / 2 - 60, H - 40, 120, 24]     # keranjang = [x, y, lebar, tinggi]
        self.bola = []                              # tiap bola = [x, y, kecepatan]
        self.skor = 0
        self.nyawa = NYAWA_AWAL
        self.timer = 0.0
        self.durasi = 0.0
        self.new_best = False
        self.over = False

    def end_game(self):
        self.over = True
        nama = self.level[0]
        self.new_best = self.skor > self.best(nama) and self.skor > 0
        self.hist.append({"t": datetime.now().strftime("%d/%m %H:%M"),
                          "l": nama, "s": self.skor, "d": round(self.durasi)})
        self.hist = self.hist[-100:]
        self._save()

    # ---------------- INPUT (dari HTML) ----------------
    def handle(self, ev):
        with self.lock:
            t = ev.get("t")
            if t == "key":
                k = str(ev.get("key", "")).lower()
                if ev.get("down"):
                    self.keys.add(k)
                    self._press(k)
                else:
                    self.keys.discard(k)
            elif t == "move":
                if self.level and not self.over:
                    self._set_x(float(ev["x"]))
            elif t == "click":
                x, y = float(ev["x"]), float(ev["y"])
                if self.level is None:
                    for i in range(3):
                        top = 230 + i * 95
                        if 250 < x < 650 and top < y < top + 80:
                            self._start(str(i + 1))
                elif self.over:
                    self.reset()
                else:
                    self._set_x(x)
            elif t == "clear":
                self.hist = []
                self._save()

    def _set_x(self, x):
        self.kr[0] = max(0, min(W - self.kr[2], x - self.kr[2] / 2))

    def _start(self, k):
        self.level = LEVELS[k]
        self.reset()

    def _press(self, k):
        if self.level is None:
            if k in LEVELS:
                self._start(k)
        elif k == "h":
            self.debug = not self.debug
        elif k == "r":
            self.reset()
        elif k == "m":
            self.level = None
            self.reset()

    # ---------------- PROSES ----------------
    def update(self, dt):
        with self.lock:
            if self.level is None or self.over:
                return
            nama, jeda, (v_min, v_max), _, _ = self.level
            kanan = "arrowright" in self.keys or "d" in self.keys
            kiri = "arrowleft" in self.keys or "a" in self.keys
            self.arah = int(kanan) - int(kiri)

            self.kr[0] += self.arah * KECEPATAN_KERANJANG * dt     # TRANSLASI: x' = x + v*dt
            self.kr[0] = max(0, min(W - self.kr[2], self.kr[0]))

            self.durasi += dt
            self.timer += dt
            if self.timer > jeda:                                  # munculkan bola sesuai level
                self.bola.append([random.randint(20, W - 20), 0.0, random.randint(v_min, v_max)])
                self.timer = 0

            kr = self.kr
            box = (kr[0], kr[1], kr[0] + kr[2], kr[1] + kr[3])     # AABB keranjang
            for b in self.bola[:]:
                b[1] += b[2] * dt                                  # TRANSLASI bola: y' = y + v*dt
                hit, near, d2 = circle_aabb(b[0], b[1], R_BOLA, box)   # COLLISION
                if self.debug and b[1] > H - 140:
                    self.log = f"d^2={d2:7.1f}  r^2={R_BOLA ** 2}  -> {'KENA' if hit else 'tidak'}"
                if hit:
                    self.bola.remove(b)
                    self.skor += 1
                elif b[1] > H + R_BOLA:
                    self.bola.remove(b)
                    self.nyawa -= 1
            if self.nyawa <= 0:
                self.end_game()

    # ---------------- OUTPUT (dikirim ke HTML) ----------------
    def snapshot(self):
        with self.lock:
            lv = self.level
            return {
                "W": W, "H": H, "r": R_BOLA,
                "menu": [{"key": k, "nama": v[0], "warna": v[3], "ket": v[4], "best": self.best(v[0])}
                         for k, v in LEVELS.items()],
                "level": None if lv is None else {"nama": lv[0], "warna": lv[3]},
                "kr": self.kr,
                "bola": [[round(b[0], 1), round(b[1], 1)] for b in self.bola],
                "skor": self.skor, "nyawa": self.nyawa,
                "over": self.over, "new_best": self.new_best, "debug": self.debug,
                "best": self.best(lv[0]) if lv else 0,
                "debug_lines": [
                    "INPUT  : kiri/kanan / mouse",
                    f"PROSES : x' = x + v*dt ; arah={self.arah:+d}",
                    "         clamp -> d^2 -> d^2 <= r^2",
                    "         " + self.log,
                    "OUTPUT : gambar keranjang & bola",
                ],
                "high": {v[0]: self.best(v[0]) for v in LEVELS.values()},
                "warna": {v[0]: v[3] for v in LEVELS.values()},
                "hist": self.hist[-10:][::-1],
            }


game = Game()


def game_loop():
    last = time.perf_counter()
    while True:
        now = time.perf_counter()
        dt = min(now - last, 0.05)
        last = now
        game.update(dt)
        time.sleep(1 / 60)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/stream":                      # Server-Sent Events: state Python -> HTML
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    data = json.dumps(game.snapshot())
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(1 / 60)
            except OSError:
                return
        elif self.path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "rb") as f:
                    body = f.read()
            except OSError:
                body = b"TangkapBola.html tidak ditemukan (harus satu folder dengan file ini)."
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):                                  # input HTML -> Python
        if self.path == "/input":
            n = int(self.headers.get("Content-Length", 0))
            try:
                game.handle(json.loads(self.rfile.read(n) or b"{}"))
            except Exception:
                pass
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


def main(port=8000):
    threading.Thread(target=game_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    url = f"http://localhost:{port}"
    print(f"Tangkap Bola jalan di {url}  (Ctrl+C untuk berhenti)")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
        sys.exit()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
