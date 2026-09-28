import csv
import json
import os
import random
import time
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_CSV = os.path.join(BASE_DIR, "soal_blockchain.csv")
FILE_PENGATURAN = os.path.join(BASE_DIR, "pengaturan_kuis.json")
FONT = "Segoe UI"
INTERVAL_ISTIRAHAT = 25 * 60  # pengingat istirahat setiap 25 menit (detik)

# --- TEMA WARNA (semua dipilih agar kontras teks nyaman untuk belajar lama) ---
TEMA = {
    "Gelap": {   # Catppuccin Mocha
        "bg": "#1e1e2e", "card": "#181825", "opsi": "#1e1e2e", "hover": "#313244",
        "garis": "#45475a", "surface": "#313244", "teks": "#cdd6f4", "redup": "#a6adc8",
        "aksen": "#89b4fa", "benar": "#a6e3a1", "salah": "#f38ba8", "warn": "#f9e2af",
        "benar_bg": "#233329", "salah_bg": "#3a2430", "pilih_bg": "#26334d", "di_aksen": "#11111b",
    },
    "Terang": {  # Catppuccin Latte
        "bg": "#eff1f5", "card": "#ffffff", "opsi": "#f7f8fb", "hover": "#e6e9ef",
        "garis": "#ccd0da", "surface": "#dce0e8", "teks": "#4c4f69", "redup": "#6c6f85",
        "aksen": "#1e66f5", "benar": "#3a8f27", "salah": "#d20f39", "warn": "#b26a00",
        "benar_bg": "#ddf3d8", "salah_bg": "#fbdde3", "pilih_bg": "#dbe6fe", "di_aksen": "#ffffff",
    },
    "Sepia": {   # hangat, paling lembut untuk membaca lama
        "bg": "#f1e7d0", "card": "#faf3e3", "opsi": "#f6edd9", "hover": "#ebdfc3",
        "garis": "#d6c7a5", "surface": "#e3d5b5", "teks": "#3e3324", "redup": "#7b6a50",
        "aksen": "#9c5a1e", "benar": "#4a7a26", "salah": "#b0392f", "warn": "#8f5f00",
        "benar_bg": "#e2ebc9", "salah_bg": "#f2d6cb", "pilih_bg": "#e8d6ab", "di_aksen": "#faf3e3",
    },
}


class AplikasiUjian:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulasi UTS Blockchain")
        self.root.geometry("1080x820")
        self.root.minsize(780, 620)

        # Preferensi tersimpan (tema & ukuran huruf)
        self.pengaturan = self.muat_pengaturan()
        nama = self.pengaturan.get("tema", "Gelap")
        self.nama_tema = nama if nama in TEMA else "Gelap"
        try:
            self.skala = min(1.6, max(0.8, float(self.pengaturan.get("skala", 1.0))))
        except (TypeError, ValueError):
            self.skala = 1.0
        self.c = TEMA[self.nama_tema]

        self.filter_bab = "Semua Bab"
        self.info_after = None
        self.waktu_mulai = time.time()
        self.blok_istirahat = 0

        self.pastikan_file_csv_ada()
        try:
            self.semua_soal = self.baca_csv()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca data: {e}")
            self.root.destroy()
            raise SystemExit(1)

        self.daftar_bab = []
        for r in self.semua_soal:
            if r["Bab"] not in self.daftar_bab:
                self.daftar_bab.append(r["Bab"])

        self.mulai_sesi()
        self.bangun_ui()
        self.render()

        self.root.bind("<Key>", self.saat_tombol)
        self.root.bind_all("<MouseWheel>", self.saat_roda)
        self.root.bind_all("<Button-4>", self.saat_roda)
        self.root.bind_all("<Button-5>", self.saat_roda)
        self.root.protocol("WM_DELETE_WINDOW", self.tutup)
        self.tick()

    # ------------------------------------------------------------------
    # BANK SOAL
    # ------------------------------------------------------------------
    def pastikan_file_csv_ada(self):
        """Menulis ulang CSV dari bank_soal_mengecoh.py setiap script dijalankan."""
        from bank_soal_mengecoh import BANK
        with open(FILE_CSV, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Pertanyaan", "Opsi_A", "Opsi_B", "Opsi_C", "Opsi_D",
                             "Jawaban_Benar", "Penjelasan", "Bab"])
            for nama_bab, daftar in BANK:
                for baris in daftar:
                    writer.writerow(list(baris) + [nama_bab])

    def baca_csv(self):
        hasil = []
        with open(FILE_CSV, mode="r", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                row["Bab"] = row.get("Bab") or "Umum"
                hasil.append(row)
        if not hasil:
            raise ValueError("File soal kosong")
        return hasil

    def acak_opsi(self, row):
        """Mengacak urutan pilihan A-D agar posisi jawaban benar tidak bisa dihafal."""
        kunci = ["A", "B", "C", "D"]
        teks_benar = row["Opsi_" + row["Jawaban_Benar"].strip().upper()]
        daftar = [row["Opsi_" + k] for k in kunci]
        random.shuffle(daftar)
        for k, teks in zip(kunci, daftar):
            row["Opsi_" + k] = teks
        row["Jawaban_Benar"] = kunci[daftar.index(teks_benar)]

    # ------------------------------------------------------------------
    # PENGATURAN & SESI
    # ------------------------------------------------------------------
    def muat_pengaturan(self):
        try:
            with open(FILE_PENGATURAN, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def simpan_pengaturan(self):
        try:
            with open(FILE_PENGATURAN, "w", encoding="utf-8") as f:
                json.dump({"tema": self.nama_tema, "skala": self.skala}, f)
        except Exception:
            pass

    def mulai_sesi(self):
        if self.filter_bab == "Semua Bab":
            terpilih = self.semua_soal
        else:
            terpilih = [r for r in self.semua_soal if r["Bab"] == self.filter_bab]
        self.antrean_soal = []
        for r in terpilih:
            row = dict(r)
            self.acak_opsi(row)
            self.antrean_soal.append(row)
        random.shuffle(self.antrean_soal)

        self.total_awal = len(self.antrean_soal)
        self.benar = 0
        self.salah = 0
        self.percobaan_pertama = 0
        self.benar_pertama = 0
        self.sudah_pernah = set()
        self.pernah_salah = set()
        self.sudah_dijawab = False
        self.pilihan = None
        self.terakhir_benar = False

    def mulai_ulang(self):
        self.mulai_sesi()
        self.render()

    # ------------------------------------------------------------------
    # PEMBANGUN UI
    # ------------------------------------------------------------------
    def font(self, ukuran, tebal=False):
        ukuran = max(8, int(round(ukuran * self.skala)))
        return (FONT, ukuran, "bold") if tebal else (FONT, ukuran)

    def tombol_kecil(self, parent, teks, perintah):
        c = self.c
        return tk.Button(parent, text=teks, command=perintah, font=self.font(10, True),
                         bg=c["surface"], fg=c["teks"], activebackground=c["hover"],
                         activeforeground=c["teks"], relief="flat", bd=0, padx=12, pady=6,
                         cursor="hand2", takefocus=0)

    def chip(self, parent, caption, warna):
        c = self.c
        f = tk.Frame(parent, bg=c["card"], highlightthickness=1, highlightbackground=c["garis"])
        f.pack(side="left", padx=(0, 10))
        val = tk.Label(f, text="0", font=self.font(18, True), bg=c["card"], fg=warna, padx=16)
        val.pack(pady=(6, 0))
        tk.Label(f, text=caption, font=self.font(8, True), bg=c["card"], fg=c["redup"],
                 padx=16).pack(pady=(0, 6))
        return val

    def buat_menu_bab(self, parent):
        c = self.c
        nama = self.filter_bab if len(self.filter_bab) <= 26 else self.filter_bab[:25] + "…"
        mb = tk.Menubutton(parent, text=f"Bab: {nama}  ▾", font=self.font(10, True),
                           bg=c["surface"], fg=c["teks"], activebackground=c["hover"],
                           activeforeground=c["teks"], relief="flat", bd=0, padx=12, pady=6,
                           cursor="hand2", takefocus=0)
        menu = tk.Menu(mb, tearoff=0, bg=c["card"], fg=c["teks"], activebackground=c["aksen"],
                       activeforeground=c["di_aksen"], font=self.font(11), bd=0)
        for n in ["Semua Bab"] + self.daftar_bab:
            menu.add_command(label=n, command=lambda x=n: self.tunda(lambda: self.pilih_bab(x)))
        menu.add_separator()
        menu.add_command(label="Mulai ulang (acak ulang soal)",
                         command=lambda: self.tunda(self.mulai_ulang))
        mb.config(menu=menu)
        return mb

    def buat_kartu(self, parent):
        c = self.c
        return tk.Frame(parent, bg=c["card"], highlightthickness=1,
                        highlightbackground=c["garis"], highlightcolor=c["garis"])

    def buat_kartu_opsi(self, huruf):
        c = self.c
        kartu = tk.Frame(self.frame_opsi, bg=c["opsi"], highlightthickness=2,
                         highlightbackground=c["garis"], highlightcolor=c["garis"], cursor="hand2")
        kartu.pack(fill="x", pady=5)
        badge = tk.Label(kartu, text=huruf, width=3, font=self.font(12, True),
                         bg=c["surface"], fg=c["teks"])
        badge.pack(side="left", padx=(12, 12), pady=12)
        teks = tk.Label(kartu, text="", font=self.font(13), bg=c["opsi"], fg=c["teks"],
                        justify="left", anchor="w", cursor="hand2")
        teks.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=12)
        self.wrap_items.append((teks, 204))
        for w in (kartu, badge, teks):
            w.bind("<Button-1>", lambda e, h=huruf: self.pilih(h))
            w.bind("<Enter>", lambda e, h=huruf: self.hover(h, True))
            w.bind("<Leave>", lambda e, h=huruf: self.hover(h, False))
        self.kartu[huruf] = (kartu, badge, teks)

    def bangun_ui(self):
        c = self.c
        if self.info_after:
            try:
                self.root.after_cancel(self.info_after)
            except Exception:
                pass
            self.info_after = None
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=c["bg"])
        self.wrap_items = []
        self.kartu = {}

        # --- Toolbar
        bar = tk.Frame(self.root, bg=c["bg"])
        bar.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(bar, text="Simulasi UTS Blockchain", font=self.font(16, True),
                 bg=c["bg"], fg=c["teks"]).pack(side="left")
        self.tombol_kecil(bar, f"Tema: {self.nama_tema}",
                          lambda: self.tunda(self.ganti_tema)).pack(side="right", padx=(6, 0))
        self.tombol_kecil(bar, "A+", lambda: self.tunda(lambda: self.ubah_skala(0.1))
                          ).pack(side="right", padx=(6, 0))
        self.tombol_kecil(bar, "A-", lambda: self.tunda(lambda: self.ubah_skala(-0.1))
                          ).pack(side="right", padx=(6, 0))
        self.buat_menu_bab(bar).pack(side="right", padx=(6, 0))

        # --- Statistik
        baris = tk.Frame(self.root, bg=c["bg"])
        baris.pack(fill="x", padx=24, pady=(0, 6))
        self.lbl_sisa = self.chip(baris, "SISA", c["aksen"])
        self.lbl_benar = self.chip(baris, "BENAR", c["benar"])
        self.lbl_salah = self.chip(baris, "SALAH", c["salah"])
        self.lbl_akurasi = self.chip(baris, "AKURASI PERTAMA", c["warn"])
        self.lbl_timer = tk.Label(baris, text="", font=self.font(11), bg=c["bg"], fg=c["redup"])
        self.lbl_timer.pack(side="right")

        # --- Progress bar
        self.canvas_prog = tk.Canvas(self.root, height=8, bg=c["surface"],
                                     highlightthickness=0, bd=0)
        self.canvas_prog.pack(fill="x", padx=24, pady=(2, 6))
        self.canvas_prog.bind("<Configure>", lambda e: self.gambar_progres())

        # --- Baris info (pengingat istirahat / peringatan ringan)
        self.lbl_info = tk.Label(self.root, text="", font=self.font(11, True), bg=c["bg"],
                                 fg=c["warn"], anchor="w", justify="left")
        self.lbl_info.pack(fill="x", padx=24)

        # --- Tombol aksi (di bawah, selalu terlihat)
        bawah = tk.Frame(self.root, bg=c["bg"])
        bawah.pack(side="bottom", fill="x", padx=24, pady=(6, 16))
        self.btn_aksi = tk.Button(bawah, text="", font=self.font(13, True), bg=c["aksen"],
                                  fg=c["di_aksen"], activebackground=c["teks"],
                                  activeforeground=c["bg"], relief="flat", bd=0,
                                  cursor="hand2", takefocus=0, command=self.kunci_atau_lanjut)
        self.btn_aksi.pack(ipadx=36, ipady=8)
        tk.Label(bawah, text="Tombol cepat:  A-D atau 1-4 = pilih   •   Enter / Spasi = kunci jawaban / lanjut   •   Roda mouse = gulir",
                 font=self.font(9), bg=c["bg"], fg=c["redup"]).pack(pady=(8, 0))

        # --- Area konten yang bisa digulir
        area = tk.Frame(self.root, bg=c["bg"])
        area.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(area, bg=c["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.isi = tk.Frame(self.canvas, bg=c["bg"])
        self.win_id = self.canvas.create_window((0, 0), window=self.isi, anchor="nw")
        self.isi.bind("<Configure>",
                      lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.saat_resize)

        # --- Kartu soal
        self.frame_soal = self.buat_kartu(self.isi)
        self.lbl_bab = tk.Label(self.frame_soal, text="", font=self.font(10, True),
                                bg=c["card"], fg=c["aksen"], anchor="w", justify="left")
        self.lbl_bab.pack(fill="x", padx=28, pady=(22, 4))
        self.lbl_pertanyaan = tk.Label(self.frame_soal, text="", font=self.font(17, True),
                                       bg=c["card"], fg=c["teks"], anchor="w", justify="left")
        self.lbl_pertanyaan.pack(fill="x", padx=28, pady=(0, 18))
        self.wrap_items.append((self.lbl_pertanyaan, 104))
        self.frame_opsi = tk.Frame(self.frame_soal, bg=c["card"])
        self.frame_opsi.pack(fill="x", padx=28)
        for huruf in "ABCD":
            self.buat_kartu_opsi(huruf)

        # Panel umpan balik (muncul setelah menjawab)
        self.frame_feedback = tk.Frame(self.frame_soal, bd=0, highlightthickness=1)
        self.fb_judul = tk.Label(self.frame_feedback, text="", font=self.font(14, True),
                                 anchor="w", justify="left")
        self.fb_judul.pack(fill="x", padx=18, pady=(14, 4))
        self.fb_teks = tk.Label(self.frame_feedback, text="", font=self.font(13),
                                anchor="w", justify="left")
        self.fb_teks.pack(fill="x", padx=18)
        self.fb_catatan = tk.Label(self.frame_feedback, text="", font=self.font(11),
                                   anchor="w", justify="left")
        self.wrap_items.append((self.fb_judul, 140))
        self.wrap_items.append((self.fb_teks, 140))
        self.wrap_items.append((self.fb_catatan, 140))

        # --- Kartu selesai
        self.frame_selesai = self.buat_kartu(self.isi)
        self.sel_judul = tk.Label(self.frame_selesai, text="", font=self.font(24, True),
                                  bg=c["card"], fg=c["benar"])
        self.sel_judul.pack(pady=(36, 10))
        self.sel_detail = tk.Label(self.frame_selesai, text="", font=self.font(14),
                                   bg=c["card"], fg=c["teks"], justify="center")
        self.sel_detail.pack(padx=28, pady=(0, 36))
        self.wrap_items.append((self.sel_detail, 104))

        self.root.focus_set()

    # ------------------------------------------------------------------
    # RENDER
    # ------------------------------------------------------------------
    def kunci_saat_ini(self):
        return self.antrean_soal[0]["Jawaban_Benar"].strip().upper()

    def status(self, huruf):
        if self.sudah_dijawab:
            if huruf == self.kunci_saat_ini():
                return "benar"
            if huruf == self.pilihan:
                return "salah"
            return "mati"
        return "dipilih" if huruf == self.pilihan else "normal"

    def warnai(self, huruf, status):
        c = self.c
        peta = {
            "normal":  (c["opsi"], c["garis"], c["surface"], c["teks"], c["teks"]),
            "hover":   (c["hover"], c["aksen"], c["surface"], c["teks"], c["teks"]),
            "dipilih": (c["pilih_bg"], c["aksen"], c["aksen"], c["di_aksen"], c["teks"]),
            "benar":   (c["benar_bg"], c["benar"], c["benar"], c["di_aksen"], c["teks"]),
            "salah":   (c["salah_bg"], c["salah"], c["salah"], c["di_aksen"], c["teks"]),
            "mati":    (c["opsi"], c["garis"], c["surface"], c["redup"], c["redup"]),
        }
        bg, garis, bbg, bfg, tfg = peta[status]
        kartu, badge, teks = self.kartu[huruf]
        kartu.config(bg=bg, highlightbackground=garis, highlightcolor=garis)
        badge.config(bg=bbg, fg=bfg)
        teks.config(bg=bg, fg=tfg)

    def warnai_semua(self):
        for h in "ABCD":
            self.warnai(h, self.status(h))

    def hover(self, huruf, masuk):
        if self.sudah_dijawab or huruf == self.pilihan or not self.antrean_soal:
            return
        self.warnai(huruf, "hover" if masuk else "normal")

    def gambar_progres(self):
        c = self.c
        cv = self.canvas_prog
        cv.delete("all")
        w = cv.winfo_width()
        h = int(cv.cget("height"))
        cv.create_rectangle(0, 0, w, h, fill=c["surface"], width=0)
        lebar = int(w * self.benar / max(1, self.total_awal))
        if lebar > 0:
            cv.create_rectangle(0, 0, lebar, h, fill=c["benar"], width=0)

    def perbarui_stat(self):
        self.lbl_sisa.config(text=str(len(self.antrean_soal)))
        self.lbl_benar.config(text=str(self.benar))
        self.lbl_salah.config(text=str(self.salah))
        if self.percobaan_pertama:
            akurasi = round(100 * self.benar_pertama / self.percobaan_pertama)
            self.lbl_akurasi.config(text=f"{akurasi}%")
        else:
            self.lbl_akurasi.config(text="-")
        self.gambar_progres()

    def render(self):
        self.perbarui_stat()
        if not self.antrean_soal:
            self.render_selesai()
            return
        self.frame_selesai.pack_forget()
        self.frame_soal.pack(fill="x", padx=24, pady=8)

        s = self.antrean_soal[0]
        penanda = s["Bab"]
        if s["Pertanyaan"] in self.pernah_salah:
            penanda += "   •   PENGULANGAN (pernah salah)"
        self.lbl_bab.config(text=penanda.upper())
        self.lbl_pertanyaan.config(text=s["Pertanyaan"])
        for h in "ABCD":
            self.kartu[h][2].config(text=s["Opsi_" + h])
        self.warnai_semua()

        if self.sudah_dijawab:
            self.render_feedback(s)
            self.btn_aksi.config(text="Lanjut   [Enter]")
        else:
            self.frame_feedback.pack_forget()
            self.btn_aksi.config(text="Kunci Jawaban   [Enter]")
            self.canvas.yview_moveto(0)

    def render_feedback(self, s):
        c = self.c
        benar = self.terakhir_benar
        warna = c["benar"] if benar else c["salah"]
        bg = c["benar_bg"] if benar else c["salah_bg"]
        self.frame_feedback.config(bg=bg, highlightbackground=warna, highlightcolor=warna)
        judul = "Benar!" if benar else f"Belum tepat. Jawaban yang benar: {self.kunci_saat_ini()}"
        self.fb_judul.config(text=judul, bg=bg, fg=warna)
        self.fb_teks.config(text="Penjelasan:  " + s["Penjelasan"], bg=bg, fg=c["teks"])
        self.fb_catatan.pack_forget()
        if not benar:
            self.fb_catatan.config(
                text="Soal ini akan muncul lagi di antrean paling akhir sampai kamu menjawab benar.",
                bg=bg, fg=c["redup"])
            self.fb_catatan.pack(fill="x", padx=18, pady=(0, 14))
        self.fb_teks.pack_configure(pady=(0, 14) if benar else (0, 8))
        self.frame_feedback.pack(fill="x", padx=28, pady=(16, 26))
        self.root.after(40, lambda: self.canvas.yview_moveto(1.0))

    def render_selesai(self):
        self.frame_soal.pack_forget()
        self.frame_selesai.pack(fill="x", padx=24, pady=8)
        akurasi = round(100 * self.benar_pertama / self.percobaan_pertama) if self.percobaan_pertama else 0
        self.sel_judul.config(text="Selesai! Semua soal sudah dikuasai")
        self.sel_detail.config(text=(
            f"Kamu menuntaskan {self.total_awal} soal.\n\n"
            f"Akurasi percobaan pertama: {akurasi}%  ({self.benar_pertama} dari {self.percobaan_pertama})\n"
            f"Jawaban salah (dikerjakan ulang): {self.salah}\n"
            f"Waktu belajar: {self.format_waktu()}\n\n"
            "Tips: ulangi lagi besok. Pengulangan berjarak membuat ingatan bertahan lebih lama."))
        self.btn_aksi.config(text="Mulai Ulang   [Enter]")
        self.canvas.yview_moveto(0)

    # ------------------------------------------------------------------
    # INTERAKSI
    # ------------------------------------------------------------------
    def pilih(self, huruf):
        if self.sudah_dijawab or not self.antrean_soal:
            return
        self.pilihan = huruf
        self.warnai_semua()

    def kunci_atau_lanjut(self):
        if not self.antrean_soal:
            self.mulai_ulang()
        elif not self.sudah_dijawab:
            self.cek_jawaban()
        else:
            self.lanjut()

    def cek_jawaban(self):
        if self.pilihan is None:
            self.tampilkan_info("Pilih salah satu jawaban dulu (klik kartu atau tekan A-D / 1-4).",
                                self.c["warn"], 2500)
            return
        s = self.antrean_soal[0]
        id_soal = s["Pertanyaan"]
        benar = self.pilihan == self.kunci_saat_ini()
        pertama = id_soal not in self.sudah_pernah
        self.sudah_pernah.add(id_soal)
        if pertama:
            self.percobaan_pertama += 1
            if benar:
                self.benar_pertama += 1
        if benar:
            self.benar += 1
        else:
            self.salah += 1
            self.pernah_salah.add(id_soal)
        self.terakhir_benar = benar
        self.sudah_dijawab = True
        self.render()

    def lanjut(self):
        s = self.antrean_soal.pop(0)
        if not self.terakhir_benar:
            self.acak_opsi(s)              # posisi jawaban diacak lagi saat diulang
            self.antrean_soal.append(s)    # soal salah dilempar ke belakang
        self.sudah_dijawab = False
        self.pilihan = None
        self.render()

    def saat_tombol(self, e):
        k = e.keysym.lower()
        if k in ("return", "kp_enter", "space"):
            self.kunci_atau_lanjut()
            return
        if k.startswith("kp_"):
            k = k[3:]
        if k in ("a", "b", "c", "d"):
            self.pilih(k.upper())
        elif k in ("1", "2", "3", "4"):
            self.pilih("ABCD"[int(k) - 1])
        elif k == "up":
            self.canvas.yview_scroll(-1, "units")
        elif k == "down":
            self.canvas.yview_scroll(1, "units")
        elif k == "prior":
            self.canvas.yview_scroll(-1, "pages")
        elif k == "next":
            self.canvas.yview_scroll(1, "pages")

    def saat_roda(self, e):
        if getattr(e, "num", None) == 4:
            arah = -1
        elif getattr(e, "num", None) == 5:
            arah = 1
        else:
            arah = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(arah * 2, "units")

    def saat_resize(self, event):
        self.canvas.itemconfig(self.win_id, width=event.width)
        for lbl, kurang in self.wrap_items:
            lbl.config(wraplength=max(200, event.width - kurang))

    # ------------------------------------------------------------------
    # PENGATURAN TAMPILAN, FILTER, TIMER
    # ------------------------------------------------------------------
    def tunda(self, fungsi):
        """Jalankan setelah menu/tombol selesai, agar aman membangun ulang UI."""
        self.root.after(10, fungsi)

    def rebuild(self):
        self.bangun_ui()
        self.render()

    def ganti_tema(self):
        nama = list(TEMA)
        self.nama_tema = nama[(nama.index(self.nama_tema) + 1) % len(nama)]
        self.c = TEMA[self.nama_tema]
        self.simpan_pengaturan()
        self.rebuild()

    def ubah_skala(self, delta):
        self.skala = round(min(1.6, max(0.8, self.skala + delta)), 2)
        self.simpan_pengaturan()
        self.rebuild()

    def pilih_bab(self, nama):
        self.filter_bab = nama
        self.mulai_sesi()
        self.rebuild()

    def tampilkan_info(self, teks, warna=None, durasi=0):
        if self.info_after:
            try:
                self.root.after_cancel(self.info_after)
            except Exception:
                pass
            self.info_after = None
        try:
            self.lbl_info.config(text=teks, fg=warna or self.c["warn"])
        except tk.TclError:
            return
        if durasi:
            self.info_after = self.root.after(durasi, self.hapus_info)

    def hapus_info(self):
        self.info_after = None
        try:
            self.lbl_info.config(text="")
        except tk.TclError:
            pass

    def format_waktu(self):
        detik = int(time.time() - self.waktu_mulai)
        return f"{detik // 3600}:{(detik % 3600) // 60:02d}:{detik % 60:02d}"

    def tick(self):
        try:
            self.lbl_timer.config(text=f"Waktu belajar  {self.format_waktu()}")
        except tk.TclError:
            pass
        detik = int(time.time() - self.waktu_mulai)
        blok = detik // INTERVAL_ISTIRAHAT
        if blok > self.blok_istirahat:
            self.blok_istirahat = blok
            self.tampilkan_info(
                f"Sudah {blok * 25} menit belajar. Istirahat sebentar: berdiri, minum air, "
                "dan lihat objek yang jauh selama 20 detik.", self.c["warn"], 90000)
        self.root.after(1000, self.tick)

    def tutup(self):
        self.simpan_pengaturan()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AplikasiUjian(root)
    root.mainloop()