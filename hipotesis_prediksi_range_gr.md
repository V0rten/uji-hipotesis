# Dokumen Hipotesis — Prediksi Range GR Berbasis Sliding Window

## 1. Tujuan

Menguji apakah informasi dari sliding window historis dapat membantu memprediksi **range** GR ronde berikutnya, bukan angka eksak.

Target:
- `GR >= 2`
- `GR >= 5`
- `GR >= 10`
- `GR >= 20`
- `GR >= 50`
- `GR >= 100`

Prioritas utama: memaksimalkan kemampuan memfilter kondisi `1.00–1.99` tanpa bergantung pada satu ukuran window yang kebetulan bagus.

Eksperimen utama: window **10–2000**.

---

## 2. Prinsip Eksperimen

Pertanyaan utama bukan “window mana yang paling bagus?”, tetapi:

> Informasi apa yang secara konsisten mengubah probabilitas ronde berikutnya di berbagai ukuran window dan periode waktu?

Setiap window `t-N+1 ... t` harus memakai ronde `t+1` sebagai target. Fitur harus tersedia sebelum hasil target diketahui untuk menghindari future leakage.

Baseline perlu dihitung untuk setiap threshold:
`P(GR >= 2)`, `P(GR >= 5)`, `P(GR >= 10)`, `P(GR >= 20)`, `P(GR >= 50)`, `P(GR >= 100)`.

---

# 3. Hipotesis

## H1 — Durasi Window Membawa Informasi

Fitur: `duration_min`.

Hipotesis: window dengan durasi relatif pendek/panjang mungkin memiliki distribusi GR ronde berikutnya yang berbeda.

Uji:
- `P(next >= X | duration bin)`
- equal-width bin
- percentile
- short / normal / long

---

## H2 — Relative Duration Lebih Informatif daripada Duration Absolut

Durasi absolut berbeda skala antar-window-size.

Kandidat:

```text
duration_ratio = actual_duration / median_duration_for_window_size
```

atau ukuran deviasi relatif lain.

Hipotesis: relative duration lebih konsisten daripada duration absolut dalam menjelaskan target.

---

## H3 — Recency Extreme GR

Fitur:
- `since_ge_2`
- `since_ge_5`
- `since_ge_10`
- `since_ge_20`
- `since_ge_50`
- `since_ge_100`

`since_ge_X` adalah jumlah ronde sejak terakhir kali `GR >= X`; nilai `0` berarti ronde terakhir sendiri memenuhi threshold.

Hipotesis: probabilitas target berubah menurut recency.

Jangan mengasumsikan “semakin lama tidak muncul extreme maka semakin mungkin muncul”. Itu harus diuji.

---

## H4 — Frequency Extreme dalam Window

Fitur:
- `count_ge_2`
- `count_ge_5`
- `count_ge_10`
- `count_ge_20`
- `count_ge_50`
- `count_ge_100`

Hipotesis: frekuensi extreme dalam window berhubungan dengan distribusi ronde berikutnya.

Uji kondisi frequency rendah/sedang/tinggi.

---

## H5 — Interaksi Recency + Frequency

Bandingkan kombinasi:
- frequency rendah + recency lama
- frequency rendah + recency baru
- frequency tinggi + recency lama
- frequency tinggi + recency baru

Hipotesis: state lokal sequence mungkin tidak cukup dijelaskan satu variabel.

---

## H6 — Statistik GR dalam Window

Fitur:
- `mean_gr`
- `max_gr`
- `min_gr`

Hipotesis: karakter distribusi GR dalam window dapat berhubungan dengan target.

Catatan: distribusi GR memiliki tail berat, sehingga mean dan max dapat sangat dipengaruhi outlier. Jangan menganggap keduanya otomatis berguna.

---

## H7 — State Window: HOT / NORMAL / COLD

Gabungkan recency dan frequency menjadi keadaan sederhana.

Contoh:
- HOT: extreme relatif sering dan/atau baru
- COLD: extreme relatif jarang dan/atau lama
- NORMAL: di antara keduanya

Hipotesis: distribusi target berbeda antar-state.

Jangan mengasumsikan COLD harus segera menjadi HOT.

---

## H8 — Window Size Membawa Informasi

Bandingkan kelompok:
- 10–50
- 51–100
- 101–250
- 251–500
- 501–1000
- 1001–2000

Hipotesis: hubungan fitur-target dapat berbeda menurut skala window.

Sinyal yang hanya muncul pada satu window-size lebih rentan dianggap noise/overfitting.

---

## H9 — Konsistensi Lintas Window

Jangan memilih window dengan probabilitas tertinggi.

Cari apakah arah hubungan yang sama muncul pada banyak window-size.

Contoh:
`W10 meningkat, W20 meningkat, W30 meningkat, ...`

Yang dicari adalah **konsistensi**, bukan angka tertinggi dari satu window.

---

## H10 — Ensemble Lintas Window

Beberapa cara:

### Majority Vote
Setiap window memberi positif/netral/negatif, lalu hitung proporsi.

### Weighted Vote
Bobot dapat diberikan setelah data menunjukkan ukuran window tertentu lebih stabil. Jangan menentukan bobot arbitrer sejak awal.

### Median Probability
Jika tiap window menghasilkan probabilitas, median dapat dipakai sebagai agregator yang lebih tahan terhadap outlier daripada mean.

---

## H11 — Consensus Score

Contoh:
- `+1` mendukung target
- `0` netral
- `-1` tidak mendukung

Lalu hitung proporsi sinyal positif.

Kelompokkan consensus, misalnya:
- 50–60%
- 60–70%
- 70–80%
- 80–90%
- 90–100%

Hipotesis: jika consensus berguna, probabilitas aktual target berubah secara konsisten saat consensus meningkat.

---

## H12 — Round Density

Kandidat:

```text
round_density = window_size / duration
```

Hipotesis: kepadatan ronde mungkin membawa informasi berbeda dari window size saja.

---

## H13 — Normalisasi Count dan Recency

Kandidat:

```text
count_rate_X = count_ge_X / window_size
since_ratio_X = since_ge_X / window_size
```

Hipotesis: pola yang bertahan setelah normalisasi lebih menarik karena tidak sekadar merupakan efek ukuran window.

---

## H14 — Interaksi Duration + Recency

Contoh:
- duration pendek + `since_ge_10` lama
- duration panjang + `since_ge_10` lama

Hipotesis: duration mungkin menjadi informatif ketika digabungkan dengan recency.

---

## H15 — Interaksi Duration + Frequency

Contoh:
- duration pendek + `count_ge_10` rendah
- duration panjang + `count_ge_10` tinggi

Hipotesis: duration dan frequency mungkin memberi informasi yang saling melengkapi.

---

## H16 — Interaksi Duration + Recency + Frequency

Level lanjutan.

Jangan langsung digunakan sebagai model utama karena risiko overfitting tinggi. Gunakan setelah fitur sederhana dipahami dan validasi out-of-sample tersedia.

---

## H17 — Stabilitas Antar-Periode

Bagi data secara kronologis menjadi beberapa periode.

Hipotesis: hubungan yang benar-benar berguna akan relatif stabil pada periode awal, tengah, dan akhir.

---

## H18 — Walk-Forward / Out-of-Sample

Pola yang ditemukan pada training diuji pada periode berikutnya yang belum digunakan untuk menemukan pola.

Hipotesis: pola yang valid tetap memberi informasi out-of-sample.

Ini adalah pemeriksaan penting sebelum strategi dianggap layak.

---

## H19 — Target Bertingkat

Gunakan seluruh target:
`>=2`, `>=5`, `>=10`, `>=20`, `>=50`, `>=100`.

Tujuannya membedakan:
- sinyal yang hanya membantu melewati 2
- sinyal yang juga meningkatkan peluang range lebih tinggi

---

## H20 — Fokus Metrik pada Filtering LOW

Accuracy bukan metrik utama.

Gunakan:
- **Coverage** — berapa banyak ronde yang lolos filter
- **Non-Low Rate** — proporsi `GR >= 2` dari ronde yang dipilih
- **Low Rate** — proporsi `1.00–1.99`
- **Lift** — perubahan terhadap baseline
- **Sample Size** — jumlah observasi kondisi

Rate tinggi dengan sample sangat kecil tidak boleh langsung dianggap bagus.

---

# 4. Masalah Penting: Sliding Window Overlap

Window berdekatan sangat overlap.

Contoh:
- W30 #100 = ronde 100–129
- W30 #101 = ronde 101–130

29 dari 30 ronde sama.

Jadi ribuan window **bukan ribuan observasi independen**.

Konsekuensi:
- jangan memperlakukan semua window sebagai eksperimen independen;
- jangan hanya memakai jumlah window yang menunjukkan sinyal;
- gunakan validasi kronologis;
- prioritaskan out-of-sample / walk-forward.

---

# 5. Remaining dan Volatility

## Remaining Duration

Belum perlu langsung dibuat.

Masalah utama: definisi target duration yang dipakai untuk menghitung remaining.

Jika remaining dihitung menggunakan durasi final yang sebenarnya belum diketahui saat prediksi live, terjadi future leakage.

Urutan yang lebih aman:
1. temukan fitur yang punya hubungan dengan target;
2. tentukan informasi apa yang tersedia secara real-time;
3. baru rancang estimasi remaining.

## Volatility

Belum perlu dipaksakan. Formula harus jelas dan harus terbukti memberi informasi tambahan.

---

# 6. Urutan Eksperimen

### Level 1 — Baseline
Hitung `P>=2`, `P>=5`, `P>=10`, `P>=20`, `P>=50`, `P>=100`.

### Level 2 — Single Feature
Uji:
- duration
- relative duration
- round density
- count
- since
- mean
- max
- min

### Level 3 — Two Feature
Uji:
- duration + since
- duration + count
- since + count
- duration + density

### Level 4 — Cross Window
Bandingkan kelompok window 10–2000.

### Level 5 — Consensus / Ensemble
Gabungkan sinyal lintas window.

### Level 6 — Walk-Forward
Uji pada data yang belum digunakan untuk menemukan pola.

---

# 7. Format Output Eksperimen

Single feature:

```text
window_size
feature
condition/bin
n
P>=2
P>=5
P>=10
P>=20
P>=50
P>=100
baseline_difference
```

Ensemble:

```text
window_group
consensus_score
n
P>=2
P>=5
P>=10
P>=20
P>=50
P>=100
```

Validasi waktu:

```text
period
window_group
condition
n
P>=2
P>=5
P>=10
P>=20
P>=50
P>=100
```

---

# 8. Kriteria Kandidat Sinyal

Sebuah pola belum dianggap sinyal hanya karena probabilitasnya tinggi.

Kandidat yang menarik sebaiknya memenuhi sebanyak mungkin:

1. Sample size memadai.
2. Ada perubahan terhadap baseline.
3. Arah hubungan relatif konsisten.
4. Muncul pada lebih dari satu window-size.
5. Tidak hanya muncul pada satu periode.
6. Tidak bergantung pada satu outlier.
7. Bertahan pada out-of-sample.
8. Tidak menggunakan informasi masa depan.
9. Coverage masih berguna untuk filtering LOW.

---

# 9. Prioritas Hipotesis

## Tier A — Prioritas tinggi
1. Relative duration → next GR
2. Round density → next GR
3. `since_ge_X` → next GR
4. `count_ge_X` → next GR
5. Duration × recency
6. Recency × frequency
7. Konsistensi lintas window-size

## Tier B — Prioritas menengah
8. `mean_gr`
9. `max_gr`
10. `min_gr`
11. Window size sebagai faktor
12. Normalisasi count
13. Normalisasi recency

## Tier C — Tahap lanjutan
14. Kombinasi tiga fitur
15. Consensus score
16. Ensemble probabilitas
17. Remaining duration
18. Volatility

---

# 10. Prinsip Akhir

Tujuan bukan menemukan “window ajaib” atau kondisi yang pernah menghasilkan rate tinggi.

Tujuan sebenarnya:

> Menemukan informasi historis yang konsisten, tersedia sebelum target terjadi, dan tetap terlihat ketika diuji pada banyak window serta periode waktu berbeda.

Jika tidak ditemukan, itu juga merupakan hasil yang valid.

Jika ditemukan, alurnya:

```text
raw features
    ↓
conditional probability
    ↓
cross-window consistency
    ↓
ensemble / consensus
    ↓
walk-forward validation
    ↓
simulasi filter LOW
    ↓
baru pertimbangkan predictor live
```
