"""
TANGKAP BOLA - Mini Game Grafik Komputer (pygame, dengan pilihan level + panel high score & riwayat)
Algoritma utama : Collision Detection Lingkaran vs AABB (Axis-Aligned Bounding Box)
Pendukung       : Translasi 2D (pergeseran posisi) berbasis delta time

Kontrol (INTERAKSI PENGGUNA):
  Menu      : tekan 1 / 2 / 3 atau klik kartu level
  Main      : panah kiri/kanan atau A/D atau gerakkan mouse = geser keranjang (translasi)
              H = mode debug    R = ulang level    M = kembali ke menu
  Menu      : C = hapus riwayat
  ESC       : keluar
"""
import json
import os
import random
import sys
from datetime import datetime

import pygame

GW, H = 600, 500            # area game
PW = 290                    # lebar panel kanan
W = GW + PW                 # lebar jendela
R_BOLA = 10
NYAWA_AWAL = 5

# nama, jeda munculnya bola (detik), rentang kecepatan jatuh (px/detik)
LEVELS = {
    pygame.K_1: ("CUNGPRET",    1.10, (80, 160)),
    pygame.K_2: ("LUMAYAN LAH", 0.75, (100, 170)),
    pygame.K_3: ("GOAT",        0.55, (220, 360)),
}
KET = {"CUNGPRET": "bola lambat, sedikit", "LUMAYAN LAH": "bola lambat, banyak", "GOAT": "bola banyak, kencang"}
WARNA = {"CUNGPRET": (120, 255, 160), "LUMAYAN LAH": (255, 220, 100), "GOAT": (255, 110, 120)}
TEKS, ABU, KUNING = (255, 255, 255), (151, 160, 204), (255, 210, 80)
KARTU = [pygame.Rect(150, 195 + i * 92, 300, 78) for i in range(3)]       # kartu menu


# ======================================================================
# ALGORITMA UTAMA: COLLISION DETECTION  LINGKARAN vs AABB
# ======================================================================
def circle_aabb(cx, cy, r, box):
    """Lingkaran (cx, cy, r) vs kotak box = (min_x, min_y, max_x, max_y).

    Langkah:
      1. CLAMP : cari titik pada kotak yang paling dekat dengan pusat lingkaran
                 nx = max(min_x, min(cx, max_x))
                 ny = max(min_y, min(cy, max_y))
      2. JARAK : dx = cx - nx ; dy = cy - ny ; d^2 = dx^2 + dy^2
      3. UJI   : tabrakan jika d^2 <= r^2   (tanpa akar kuadrat)
    Mengembalikan (tabrakan?, titik_terdekat, d2) supaya bisa ditampilkan.
    """
    min_x, min_y, max_x, max_y = box
    nx = max(min_x, min(cx, max_x))
    ny = max(min_y, min(cy, max_y))
    dx, dy = cx - nx, cy - ny
    d2 = dx * dx + dy * dy
    return d2 <= r * r, (nx, ny), d2


# ---------------- riwayat & high score (disimpan ke file) ----------------
def load_hist():
    try:
        with open(HIST_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_hist(hist):
    try:
        with open(HIST_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f)
    except Exception:
        pass


def best(hist, nama):
    return max([h["s"] for h in hist if h["l"] == nama], default=0)


# ---------------- helper tampilan ----------------
def gradient(w, h, atas, bawah):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        pygame.draw.line(s, tuple(int(atas[i] + (bawah[i] - atas[i]) * t) for i in range(3)), (0, y), (w, y))
    return s


def heart(surf, x, y, s, warna):
    pygame.draw.circle(surf, warna, (int(x + s * 0.27), int(y + s * 0.3)), int(s * 0.27))
    pygame.draw.circle(surf, warna, (int(x + s * 0.73), int(y + s * 0.3)), int(s * 0.27))
    pygame.draw.polygon(surf, warna, [(x + 1, y + s * 0.42), (x + s - 1, y + s * 0.42), (x + s / 2, y + s * 0.95)])


def tengah(surf, img, cx, cy):
    surf.blit(img, img.get_rect(center=(cx, cy)))


def main(frames=None, shot=None):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Tangkap Bola - Grafik Komputer")
    clock = pygame.time.Clock()
    fam = "segoeui,helvetica,arial"
    font = pygame.font.SysFont(fam, 20)
    small = pygame.font.SysFont(fam, 16)
    mono = pygame.font.SysFont("consolas,menlo,monospace", 14)
    bold = pygame.font.SysFont(fam, 22, bold=True)
    big = pygame.font.SysFont(fam, 52, bold=True)
    judul_f = pygame.font.SysFont(fam, 40, bold=True)

    latar = gradient(GW, H, (29, 35, 80), (18, 22, 43))
    gelap = pygame.Surface((GW, H), pygame.SRCALPHA)
    gelap.fill((0, 0, 0, 165))

    hist = load_hist()

    def reset():
        return [GW / 2 - 60, H - 36, 120, 22], [], 0, NYAWA_AWAL, 0.0, 0.0   # keranjang, bola, skor, nyawa, timer, durasi

    kr, bola, skor, nyawa, timer, durasi = reset()
    level = None       # None = sedang di menu
    debug = False
    log = "-"
    selesai = False    # supaya hasil game hanya dicatat sekali
    new_best = False
    n = 0

    def mulai(key):
        nonlocal level, kr, bola, skor, nyawa, timer, durasi, selesai, new_best
        level = LEVELS[key]
        kr, bola, skor, nyawa, timer, durasi = reset()
        selesai = new_best = False

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        n += 1

        # ---------------- INPUT ----------------
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if level is None:
                    if e.key in LEVELS:                      # pilih level di menu
                        mulai(e.key)
                    elif e.key == pygame.K_c:
                        hist = []; save_hist(hist)
                else:
                    if e.key == pygame.K_h:
                        debug = not debug
                    elif e.key == pygame.K_r:
                        mulai(next(k for k, v in LEVELS.items() if v is level))
                    elif e.key == pygame.K_m:
                        level = None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if level is None:
                    for i, k in enumerate(KARTU):
                        if k.collidepoint(e.pos):
                            mulai(list(LEVELS)[i])
                elif nyawa <= 0:
                    mulai(next(k for k, v in LEVELS.items() if v is level))
            elif e.type == pygame.MOUSEMOTION and level is not None and nyawa > 0 and e.pos[0] < GW:
                kr[0] = max(0, min(GW - kr[2], e.pos[0] - kr[2] / 2))    # keranjang ikut mouse
        keys = pygame.key.get_pressed()
        arah = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])

        # ---------------- PROSES ----------------
        if level is not None and nyawa > 0:
            nama, jeda, (v_min, v_max) = level

            kr[0] += arah * 550 * dt                       # TRANSLASI: x' = x + v*dt
            kr[0] = max(0, min(GW - kr[2], kr[0]))         # batas area game

            durasi += dt
            timer += dt
            if timer > jeda:                               # munculkan bola sesuai level
                bola.append([random.randint(20, GW - 20), 0.0, random.randint(v_min, v_max)])
                timer = 0

            box = (kr[0], kr[1], kr[0] + kr[2], kr[1] + kr[3])   # AABB keranjang
            for b in bola[:]:
                b[1] += b[2] * dt                          # TRANSLASI bola: y' = y + v*dt
                hit, near, d2 = circle_aabb(b[0], b[1], R_BOLA, box)   # COLLISION
                if debug and b[1] > H - 120:
                    log = f"d^2={d2:6.1f} r^2={R_BOLA ** 2} -> {'KENA' if hit else 'tidak'}"
                if hit:
                    bola.remove(b); skor += 1
                elif b[1] > H + R_BOLA:
                    bola.remove(b); nyawa -= 1

        if level is not None and nyawa <= 0 and not selesai:      # game over -> catat riwayat
            selesai = True
            new_best = skor > best(hist, level[0]) and skor > 0
            hist.append({"t": datetime.now().strftime("%d/%m %H:%M"),
                         "l": level[0], "s": skor, "d": round(durasi)})
            hist = hist[-100:]
            save_hist(hist)

        # ---------------- OUTPUT (RENDER) ----------------
        screen.blit(latar, (0, 0))
        mx, my = pygame.mouse.get_pos()
        if level is None:
            tengah(screen, big.render("TANGKAP BOLA", True, TEKS), GW // 2, 75)
            tengah(screen, small.render("Mini Game Grafik Komputer - Collision Lingkaran vs AABB", True, ABU), GW // 2, 125)
            for i, (k, rect) in enumerate(zip(LEVELS, KARTU)):
                nm = LEVELS[k][0]
                hover = rect.collidepoint(mx, my)
                pygame.draw.rect(screen, (50, 58, 108) if hover else (38, 44, 85), rect, border_radius=14)
                pygame.draw.rect(screen, WARNA[nm], rect, 2, border_radius=14)
                tengah(screen, bold.render(f"[{i + 1}] {nm}", True, WARNA[nm]), rect.centerx, rect.y + 26)
                tengah(screen, small.render(f"{KET[nm]}  -  best {best(hist, nm)}", True, ABU), rect.centerx, rect.y + 54)
            tengah(screen, small.render("Klik level atau tekan 1 / 2 / 3", True, TEKS), GW // 2, 478)
        else:
            # keranjang & bola
            pygame.draw.rect(screen, (90, 200, 255), kr, border_radius=6)
            pygame.draw.rect(screen, (170, 230, 255), (kr[0] + 4, kr[1] + 3, kr[2] - 8, 4), border_radius=2)
            for b in bola:
                pos = (int(b[0]), int(b[1]))
                pygame.draw.circle(screen, (255, 210, 80), pos, R_BOLA)
                pygame.draw.circle(screen, (255, 238, 170), (pos[0] - 3, pos[1] - 3), 3)
                if debug:
                    pygame.draw.circle(screen, (80, 255, 120), pos, R_BOLA, 1)
            if debug:
                pygame.draw.rect(screen, (255, 80, 80), kr, 1)       # AABB keranjang
                baris = ["INPUT  : kiri/kanan / mouse",
                         f"PROSES : x' = x + v*dt ; arah={arah:+d}",
                         "         clamp -> d^2 -> d^2 <= r^2",
                         "         " + log,
                         "OUTPUT : gambar keranjang & bola"]
                for i, t in enumerate(baris):
                    screen.blit(mono.render(t, True, (120, 255, 160)), (14, 60 + i * 18))
            # HUD
            screen.blit(bold.render(level[0], True, WARNA[level[0]]), (14, 10))
            screen.blit(small.render(f"Skor: {skor}   Best: {max(best(hist, level[0]), skor)}", True, TEKS), (14, 36))
            for i in range(max(nyawa, 0)):
                heart(screen, GW - 28 - i * 24, 12, 18, (255, 90, 110))
            screen.blit(small.render("[H] debug  [R] ulang  [M] menu", True, ABU),
                        (GW - 14 - small.size("[H] debug  [R] ulang  [M] menu")[0], 36))
            if nyawa <= 0:
                screen.blit(gelap, (0, 0))
                tengah(screen, big.render("GAME OVER", True, (255, 110, 120)), GW // 2, H // 2 - 50)
                tengah(screen, font.render(f"Skor {skor}", True, TEKS), GW // 2, H // 2 + 2)
                if new_best:
                    tengah(screen, bold.render("HIGH SCORE BARU!", True, KUNING), GW // 2, H // 2 + 36)
                tengah(screen, small.render("R / klik = ulang    M = menu", True, ABU), GW // 2, H // 2 + 76)

        # ---------------- PANEL HIGH SCORE & RIWAYAT ----------------
        pygame.draw.rect(screen, (28, 33, 66), (GW, 0, PW, H))
        x0, lebar = GW + 12, PW - 24
        screen.blit(bold.render("HIGH SCORE", True, KUNING), (x0 + 2, 12))
        for i, nm in enumerate(["CUNGPRET", "LUMAYAN LAH", "GOAT"]):
            r = pygame.Rect(x0, 46 + i * 34, lebar, 28)
            pygame.draw.rect(screen, (38, 44, 85), r, border_radius=8)
            screen.blit(small.render(nm, True, WARNA[nm]), (r.x + 10, r.y + 5))
            v = small.render(str(best(hist, nm)), True, TEKS)
            screen.blit(v, (r.right - 10 - v.get_width(), r.y + 5))
        screen.blit(bold.render("RIWAYAT", True, KUNING), (x0 + 2, 160))
        screen.blit(mono.render("Waktu       Level    Skor Durasi", True, ABU), (x0 + 6, 192))
        if not hist:
            screen.blit(small.render("Belum ada permainan.", True, ABU), (x0 + 6, 218))
        for i, h in enumerate(hist[-11:][::-1]):
            r = pygame.Rect(x0, 212 + i * 24, lebar, 22)
            if i % 2 == 0:
                pygame.draw.rect(screen, (34, 40, 78), r, border_radius=6)
            baris = f"{h['t']} {h['l'].split()[0]:<8} {h['s']:>3} {h['d']:>4}s"
            screen.blit(mono.render(baris, True, WARNA[h["l"]]), (r.x + 6, r.y + 3))
        screen.blit(mono.render("[C] hapus riwayat (di menu)", True, (110, 120, 160)), (x0 + 6, H - 22))
        pygame.display.flip()
if __name__ == "__main__":
    main()
