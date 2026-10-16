"""
TANGKAP BOLA - Mini Game Grafik Komputer (dengan pilihan level)
Algoritma utama : Collision Detection Lingkaran vs AABB (Axis-Aligned Bounding Box)
Pendukung       : Translasi 2D (pergeseran posisi) berbasis delta time

Kontrol (INTERAKSI PENGGUNA):
  Menu      : tekan 1 (Beginner), 2 (Medium), 3 (Hard)
  Main      : panah kiri/kanan atau A/D = geser keranjang (translasi)
              H = mode debug    R = ulang level    M = kembali ke menu
  ESC       : keluar
"""
import random
import sys

import pygame

W, H = 600, 500
R_BOLA = 10
NYAWA_AWAL = 5

# Pengaturan level: nama, jeda munculnya bola (detik), rentang kecepatan jatuh (px/detik)
#   jeda kecil  -> bola makin banyak
#   kecepatan   -> makin besar, bola makin kencang
LEVELS = {
    pygame.K_1: ("BEGINNER", 1.10, (80, 160)),   # lambat, sedikit
    pygame.K_2: ("MEDIUM",   0.75, (100, 170)),   # lambat, banyak
    pygame.K_3: ("HARD",     0.55, (220, 360)),   # banyak dan kencang
}


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


def main(frames=None, shot=None):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Tangkap Bola - Grafik Komputer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas,menlo,monospace", 18)
    big = pygame.font.SysFont("consolas,menlo,monospace", 30, bold=True)

    def reset():
        return [W / 2 - 50, H - 30, 100, 20], [], 0, NYAWA_AWAL, 0.0   # keranjang = [x, y, lebar, tinggi]

    kr, bola, skor, nyawa, timer = reset()
    level = None       # None = sedang di menu
    debug = False
    log = "-"          # hasil uji tabrakan terakhir (untuk panel debug)
    n = 0

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
                        level = LEVELS[e.key]
                        kr, bola, skor, nyawa, timer = reset()
                else:
                    if e.key == pygame.K_h:
                        debug = not debug
                    elif e.key == pygame.K_r:
                        kr, bola, skor, nyawa, timer = reset()
                    elif e.key == pygame.K_m:
                        level = None
        keys = pygame.key.get_pressed()
        arah = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])

        # ---------------- PROSES ----------------
        if level is not None and nyawa > 0:
            nama, jeda, (v_min, v_max) = level

            kr[0] += arah * 400 * dt                       # TRANSLASI: x' = x + v*dt
            kr[0] = max(0, min(W - kr[2], kr[0]))          # batas layar

            timer += dt
            if timer > jeda:                               # munculkan bola sesuai level
                bola.append([random.randint(20, W - 20), 0.0, random.randint(v_min, v_max)])
                timer = 0

            box = (kr[0], kr[1], kr[0] + kr[2], kr[1] + kr[3])   # AABB keranjang
            for b in bola[:]:
                b[1] += b[2] * dt                          # TRANSLASI bola: y' = y + v*dt
                hit, near, d2 = circle_aabb(b[0], b[1], R_BOLA, box)   # COLLISION
                if debug and b[1] > H - 120:
                    log = f"d^2={d2:7.1f}  r^2={R_BOLA ** 2}  -> {'KENA' if hit else 'tidak'}"
                if hit:
                    bola.remove(b); skor += 1
                elif b[1] > H + R_BOLA:
                    bola.remove(b); nyawa -= 1

        # ---------------- OUTPUT (RENDER) ----------------
        screen.fill((25, 30, 55))
        if level is None:
            judul = big.render("TANGKAP BOLA", True, (255, 255, 255))
            screen.blit(judul, judul.get_rect(center=(W // 2, 130)))
            menu = [("[1] BEGINNER", (120, 255, 160), "bola lambat, sedikit"),
                    ("[2] MEDIUM",   (255, 220, 100), "bola lambat, banyak"),
                    ("[3] HARD",     (255, 110, 120), "bola banyak, kencang")]
            for i, (t, warna, ket) in enumerate(menu):
                screen.blit(font.render(t, True, warna), (190, 220 + i * 55))
                screen.blit(font.render(ket, True, (150, 160, 190)), (190, 242 + i * 55))
            info = font.render("Pilih level dengan tombol 1 / 2 / 3", True, (255, 255, 255))
            screen.blit(info, info.get_rect(center=(W // 2, 430)))
        else:
            pygame.draw.rect(screen, (90, 200, 255), kr)
            for b in bola:
                pygame.draw.circle(screen, (255, 210, 80), (int(b[0]), int(b[1])), R_BOLA)
                if debug:
                    pygame.draw.circle(screen, (80, 255, 120), (int(b[0]), int(b[1])), R_BOLA, 1)
            if debug:
                pygame.draw.rect(screen, (255, 80, 80), kr, 1)       # AABB keranjang
                baris = ["INPUT  : tombol kiri/kanan",
                         f"PROSES : x' = x + v*dt ; arah={arah:+d}",
                         "         clamp -> d^2 -> d^2 <= r^2",
                         "         " + log,
                         "OUTPUT : gambar keranjang & bola"]
                for i, t in enumerate(baris):
                    screen.blit(font.render(t, True, (120, 255, 160)), (10, 40 + i * 20))
            screen.blit(font.render(f"{level[0]}  Skor: {skor}  Nyawa: {nyawa}  [H]debug [M]menu", True,
                                    (255, 255, 255)), (10, 10))
            if nyawa <= 0:
                t = big.render(f"GAME OVER - skor {skor}", True, (255, 100, 110))
                screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 15)))
                t2 = font.render("R = ulang level   M = menu", True, (255, 255, 255))
                screen.blit(t2, t2.get_rect(center=(W // 2, H // 2 + 25)))
        pygame.display.flip()

        if frames and n >= frames:                 # hanya untuk pengambilan screenshot
            if shot:
                pygame.image.save(screen, shot)
            pygame.quit(); return


if __name__ == "__main__":
    main()