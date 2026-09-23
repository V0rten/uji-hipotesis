# Dokumentasi Analisis `gr_result`

**Project:** Analisis Data Crash Game\
**Dataset:** `410_kalibrasi.md`\
**Dokumen sumber project:** `readme.txt`\
**Fokus dokumen:** Analisis nilai `gr_result` saja\
**Status:** Eksplorasi / hipotesis kerja

------------------------------------------------------------------------

## 1. Tujuan Analisis

Tahap ini sengaja membatasi ruang lingkup hanya pada nilai `gr_result`.

Tidak digunakan sebagai variabel utama:

-   `tag_ts`
-   `ts`
-   `startdealing_ts`
-   `gr_ts`
-   `game_id`
-   `status`

Tujuannya adalah mencari apakah **distribusi nilai multiplier itu
sendiri** memiliki struktur yang cukup jelas untuk dijadikan dasar
hipotesis.

Prinsip utama:

> Jika terlihat pola, pola tersebut dicatat sebagai **asumsi/hipotesis
> sementara** terlebih dahulu. Pola tidak langsung dianggap sebagai
> bukti prediktabilitas.

Analisis ini tidak berangkat dari asumsi bahwa PRNG memiliki memori.
Yang diuji adalah **data hasil yang diamati**.

------------------------------------------------------------------------

# 2. Dataset

Dataset `410_kalibrasi.md` berisi:

-   **5.491 round**
-   7 kolom:
    -   `tag_ts`
    -   `ts`
    -   `startdealing_ts`
    -   `gr_ts`
    -   `gr_result`
    -   `game_id`
    -   `status`

Untuk dokumen ini hanya `gr_result` yang dianalisis.

## 2.1 Validasi dasar

Jumlah observasi:

``` text
N = 5.491
```

Rentang `gr_result`:

``` text
minimum = 1.00
maximum = 5000.00
```

Statistik utama:

  Statistik                        Nilai
  --------------------------- ----------
  N                                5.491
  Minimum                           1,00
  Median                            1,87
  Mean                            8,0393
  P95                              19,17
  Maximum                       5.000,00
  `gr_result >= 2`                 2.582
  Proporsi `gr_result >= 2`       47,02%

Perbedaan mean dan median sangat besar:

``` text
mean   = 8,04
median = 1,87
```

Ini menunjukkan distribusi sangat miring ke kanan dan memiliki **right
tail** yang panjang.

------------------------------------------------------------------------

# 3. Bentuk Distribusi

Observasi paling penting dari analisis awal adalah bahwa survival
probability `gr_result` cukup dekat dengan bentuk:

\[ P(X `\ge `{=tex}x) `\approx `{=tex}`\frac{0,95}{x}`{=tex} \]

Untuk melihat kedekatannya, berikut perbandingan empirical survival
dengan model sederhana `0,95/x`.

    Threshold `x`   Observed `P(X >= x)`   Model `0,95/x`
  --------------- ---------------------- ----------------
             1,10                 86,74%           86,36%
             1,20                 79,84%           79,17%
             1,50                 63,83%           63,33%
             2,00                 47,02%           47,50%
             3,00                 31,21%           31,67%
             5,00                 19,01%           19,00%
            10,00                  9,58%            9,50%
            20,00                  4,77%            4,75%
            30,00                  3,22%            3,17%
            50,00                  1,84%            1,90%
           100,00                  0,82%            0,95%
           500,00                  0,13%            0,19%

Kedekatan ini terlihat di banyak threshold, bukan hanya pada satu titik.

------------------------------------------------------------------------

# 4. Hipotesis Distribusi Heavy-Tail

## 4.1 Hipotesis sementara

Berdasarkan hasil di atas, hipotesis kerja pertama adalah:

> **`gr_result` memiliki distribusi heavy-tail yang secara kasar
> mengikuti survival function sekitar `0,95/x`.**

Ini adalah **hipotesis distribusi**, bukan kesimpulan mengenai algoritma
internal.

Kita belum dapat menyatakan bahwa mekanisme pembangkit hasil secara
internal menggunakan formula tertentu.

------------------------------------------------------------------------

## 4.2 Estimasi exponent

Estimasi exponent tail dari analisis awal:

``` text
Seluruh data : ~0,997
First half   : ~1,004
Second half  : ~0,990
```

Nilai tersebut sangat dekat dengan:

``` text
alpha = 1
```

Sehingga bentuk sederhananya dapat ditulis:

\[ P(X `\ge `{=tex}x) `\propto `{=tex}x\^{-1} \]

atau secara informal:

\[ P(X `\ge `{=tex}x) `\sim `{=tex}`\frac{k}{x}`{=tex} \]

dengan `k` empiris sekitar `0,95`.

Konsistensi exponent antara separuh awal dan separuh akhir merupakan
observasi yang perlu dicatat.

------------------------------------------------------------------------

# 5. Contoh Threshold `>= 2`

Threshold `2.00` sangat berguna sebagai sanity check.

Jumlah:

``` text
gr_result >= 2 = 2.582
```

Dari total:

``` text
5.491
```

sehingga:

\[ P(X`\ge2`{=tex})=`\frac{2582}{5491}`{=tex} \]

hasilnya:

``` text
47,02%
```

Model sederhana:

\[ `\frac{0,95}{2}`{=tex}=47,50% \]

Perbedaannya kecil:

``` text
Observed = 47,02%
Model    = 47,50%
```

Hal ini menjadi salah satu alasan utama mengapa bentuk `0,95/x` layak
dipakai sebagai **baseline distribusi**.

------------------------------------------------------------------------

# 6. Threshold Lain

Beberapa threshold menunjukkan pola yang sama.

## `>= 5`

Observed:

``` text
19,01%
```

Model:

``` text
0,95 / 5 = 19,00%
```

Hampir identik.

## `>= 10`

Observed:

``` text
9,58%
```

Model:

``` text
0,95 / 10 = 9,50%
```

## `>= 20`

Observed:

``` text
4,77%
```

Model:

``` text
0,95 / 20 = 4,75%
```

## `>= 30`

Observed:

``` text
3,22%
```

Model:

``` text
0,95 / 30 = 3,17%
```

## `>= 50`

Observed:

``` text
1,84%
```

Model:

``` text
0,95 / 50 = 1,90%
```

Pola ini mendukung hipotesis bahwa ekor distribusi mempunyai struktur
yang cukup dekat dengan inverse relationship.

------------------------------------------------------------------------

# 7. Konsentrasi Nilai Rendah

Walaupun tail panjang, mayoritas observasi tetap berada di sekitar nilai
rendah.

Contoh:

  Range          Persentase
  ------------ ------------
  1,00--1,49         36,17%
  1,50--1,99         16,81%
  2,00--2,49          9,43%
  2,50--2,99          6,37%
  3,00--3,49          4,13%
  3,50--3,99          3,31%
  4,00--4,49          2,64%
  4,50--4,99          2,11%

Dengan demikian distribusi memiliki dua karakteristik yang berjalan
bersamaan:

1.  Konsentrasi besar di sekitar multiplier rendah.
2.  Tail yang panjang menuju multiplier ekstrem.

Ini adalah karakteristik yang harus diperhitungkan ketika menggunakan
mean atau metode statistik yang sensitif terhadap outlier.

------------------------------------------------------------------------

# 8. Nilai Exact yang Sering Muncul

Beberapa nilai `gr_result` exact memiliki frekuensi tinggi.

    `gr_result`   Frekuensi
  ------------- -----------
           1,00         324
           1,02          54
           1,07          53
           1,04          48
           1,06          47
           1,03          47
           1,14          47
           1,23          45
           1,22          45
           1,13          45

Nilai `1,00` muncul:

``` text
324 / 5.491 = 5,90%
```

Semua data juga direpresentasikan pada resolusi dua angka desimal.

## Interpretasi

Frekuensi tinggi pada angka exact tidak boleh langsung diartikan sebagai
bukti adanya "angka yang sengaja dipilih".

Ada beberapa kemungkinan yang perlu dibedakan pada penelitian
berikutnya:

-   proses pembulatan,
-   mekanisme multiplier yang memang menghasilkan minimum 1,00,
-   discretization,
-   karakteristik formula distribusi,
-   atau kombinasi beberapa faktor.

Untuk saat ini, yang dapat dikatakan hanyalah:

> **Nilai 1,00 mempunyai frekuensi exact yang jauh terlihat sebagai
> salah satu titik paling sering.**

------------------------------------------------------------------------

# 9. Apakah Nilai Sebelumnya Mempengaruhi Nilai Berikutnya?

Tahap berikutnya tetap hanya menggunakan `gr_result`, tetapi sekarang
mempertahankan urutan round.

Target analisis:

\[ gr_t `\rightarrow `{=tex}gr\_{t+1} \]

## 9.1 Korelasi log

Karena distribusi sangat heavy-tail, analisis menggunakan:

\[ z_t=`\log`{=tex}(gr_t) \]

Korelasi lag-1:

``` text
corr(log(gr_t), log(gr_t+1))
≈ -0,0132
```

Nilainya sangat dekat dengan nol.

Interpretasi:

> Tidak terlihat hubungan linear yang berarti antara besar kecilnya
> `gr_result` sekarang dan `gr_result` berikutnya pada analisis lag-1
> sederhana.

------------------------------------------------------------------------

# 10. Analisis Binary `>= 2`

Untuk melihat transisi dengan cara yang lebih sederhana:

``` text
LOW  = gr_result < 2
HIGH = gr_result >= 2
```

Base rate HIGH:

``` text
47,02%
```

Conditional probability:

  Kondisi round sebelumnya     P(round berikutnya \>= 2)
  -------------------------- ---------------------------
  Previous `< 2`                                  48,13%
  Previous `>= 2`                                 45,76%

Perbedaannya:

``` text
48,13% - 45,76%
= 2,37 percentage points
```

Secara deskriptif terdapat perbedaan kecil.

Namun uji independensi menghasilkan:

``` text
chi-square ≈ 2,987
p ≈ 0,084
```

Dengan demikian, pada dataset ini, perbedaan tersebut belum cukup kuat
untuk dianggap sebagai bukti statistik pada ambang 5%.

------------------------------------------------------------------------

# 11. Interpretasi Sementara: Mean Reversion?

Ketika nilai sebelumnya dikelompokkan berdasarkan range, median nilai
berikutnya terlihat sedikit bergerak ke area tengah.

Contoh:

  Nilai sebelumnya         N   Median nilai berikutnya
  ------------------ ------- -------------------------
  `< 1,20`             1.107                      1,96
  1,20--1,49             879                      1,91
  1,50--1,99             923                      1,89
  2--2,99                868                     1,875
  3--4,99                670                      1,82
  5--9,99                518                      1,81
  10--19,99              264                     1,765
  20--49,99              161                      1,87
  \>= 50                 101                      1,97

Secara visual/deskriptif, ini dapat terlihat seperti:

``` text
nilai rendah
     ↓
bergerak menuju median

nilai tinggi
     ↓
bergerak menuju median
```

## Tetapi:

Korelasi log lag-1 hanya:

``` text
-0,0132
```

Artinya efek ini sangat kecil.

### Status

> **"Mean reversion" dicatat sebagai hipotesis eksploratif, bukan
> sebagai pola prediktif yang sudah terbukti.**

Alasan efek ini bisa muncul tanpa dependency yang berarti adalah
distribusi marginalnya sendiri sangat terkonsentrasi di sekitar nilai
rendah/median.

------------------------------------------------------------------------

# 12. Stability dari Waktu ke Waktu

Dataset dibagi menjadi dua bagian berdasarkan urutan observasi.

## First half

``` text
P(gr_result >= 2) = 47,07%
```

## Second half

``` text
P(gr_result >= 2) = 46,98%
```

Perbedaannya sangat kecil:

``` text
≈ 0,09 percentage points
```

Ini menunjukkan bahwa base rate threshold `2.00` relatif stabil antara
dua bagian dataset.

Namun stabilitas base rate tidak otomatis berarti independensi.

Ia hanya menunjukkan bahwa proporsi HIGH tidak mengalami perubahan besar
pada pembagian sederhana ini.

------------------------------------------------------------------------

# 13. Analisis Streak

Untuk state:

``` text
LOW  = gr_result < 2
HIGH = gr_result >= 2
```

hasil awal:

## LOW streak

``` text
mean ≈ 2,08 round
maximum = 12
P95 = 5
```

## HIGH streak

``` text
mean ≈ 1,84 round
maximum = 16
P95 = 4
```

Streak panjang memang terdapat dalam data.

Tetapi keberadaan streak **tidak dengan sendirinya membuktikan
dependency**.

Streak juga dapat muncul secara natural dari proses independen.

------------------------------------------------------------------------

# 14. Hal yang Sudah Bisa Dikatakan

Berdasarkan analisis `gr_result` saja, beberapa observasi cukup kuat:

### Observasi A --- Heavy tail

Distribusi `gr_result` sangat right-skewed.

Median:

``` text
1,87
```

Mean:

``` text
8,04
```

Maximum:

``` text
5000
```

------------------------------------------------------------------------

### Observasi B --- Tail mendekati inverse relationship

Survival probability pada banyak threshold cukup dekat dengan:

\[ S(x)`\approx`{=tex}`\frac{0,95}{x}`{=tex} \]

Ini merupakan temuan paling menonjol dari analisis distribusi.

------------------------------------------------------------------------

### Observasi C --- Exponent mendekati 1

Estimasi exponent:

``` text
~0,997
```

dan relatif stabil pada first-half dan second-half.

------------------------------------------------------------------------

### Observasi D --- Dependency lag-1 sangat kecil

Korelasi log:

``` text
≈ -0,0132
```

Sehingga belum ada indikasi kuat bahwa besar `gr_result` sebelumnya
secara langsung menentukan besar `gr_result` berikutnya.

------------------------------------------------------------------------

### Observasi E --- Binary transition berbeda sedikit

``` text
previous LOW  → 48,13% HIGH
previous HIGH → 45,76% HIGH
```

Namun:

``` text
p ≈ 0,084
```

sehingga perbedaan ini belum cukup kuat sebagai bukti dependency pada
ambang 5%.

------------------------------------------------------------------------

# 15. Hipotesis Kerja

Hipotesis yang sekarang disimpan untuk investigasi lanjutan:

## H1 --- Distribusi inverse-tail

\[ P(X`\ge `{=tex}x)`\approx`{=tex}`\frac{k}{x}`{=tex} \]

dengan:

``` text
k ≈ 0,95
```

dan exponent mendekati 1.

**Status:** didukung oleh observasi awal, perlu fitting formal.

------------------------------------------------------------------------

## H2 --- Parameter distribusi relatif stabil

Base rate dan estimasi exponent tidak banyak berubah antara bagian awal
dan akhir dataset.

**Status:** indikasi awal, perlu rolling-window analysis.

------------------------------------------------------------------------

## H3 --- Ada apparent mean reversion

Nilai berikutnya sedikit bergerak menuju area median setelah nilai
sebelumnya sangat rendah atau tinggi.

**Status:** lemah / belum terbukti sebagai dependency.

------------------------------------------------------------------------

## H4 --- Dependensi antar-round sangat kecil

Korelasi lag-1 dan binary transition menunjukkan dependency sederhana
yang sangat kecil.

**Status:** didukung oleh analisis awal.

------------------------------------------------------------------------

# 16. Yang Belum Boleh Disimpulkan

Analisis ini **belum membuktikan**:

-   bahwa game dapat diprediksi,
-   bahwa PRNG memiliki memori,
-   bahwa `gr_result` berasal dari formula `0,95/x`,
-   bahwa nilai ekstrem menyebabkan nilai berikutnya menjadi rendah,
-   bahwa streak dapat digunakan sebagai sinyal,
-   bahwa "setelah multiplier tinggi pasti akan rendah",
-   bahwa distribusi tersebut merupakan bukti mekanisme internal
    tertentu.

Semua klaim tersebut membutuhkan pengujian tambahan.

------------------------------------------------------------------------

# 17. Baseline Matematis yang Perlu Dipertahankan

Untuk penelitian selanjutnya, model baseline berikut perlu disimpan:

\[ S(x)=P(X`\ge `{=tex}x)`\approx`{=tex}`\frac{0,95}{x}`{=tex} \]

Contoh:

``` text
threshold 2   → ~47,5%
threshold 5   → ~19,0%
threshold 10  → ~9,5%
threshold 20  → ~4,75%
threshold 50  → ~1,90%
threshold 100 → ~0,95%
```

Baseline ini berguna untuk membedakan:

``` text
"kelihatannya tidak biasa"
```

dengan:

``` text
"memang menyimpang dari distribusi yang diharapkan"
```

------------------------------------------------------------------------

# 18. Eksperimen Lanjutan

Tahap selanjutnya sebaiknya tetap berfokus pada `gr_result` sebelum
memasukkan timestamp.

## Eksperimen 1 --- Fit distribusi secara formal

Bandingkan:

1.  Pareto
2.  truncated Pareto
3.  log-normal
4.  Weibull
5.  model empiris `k/x`

Tujuan:

> Menentukan apakah bentuk `0,95/x` memang model yang paling sesuai atau
> hanya kebetulan visual.

------------------------------------------------------------------------

## Eksperimen 2 --- Residual terhadap model `0,95/x`

Hitung:

\[ R(x)=Observed(x)-Expected(x) \]

Cari apakah residual memiliki bentuk sistematis.

Contoh pertanyaan:

-   Apakah ada excess di sekitar 1,00?
-   Apakah ada kekurangan di range tertentu?
-   Apakah tail terlalu berat dibanding model?
-   Apakah tail terpotong pada nilai tertentu?

------------------------------------------------------------------------

## Eksperimen 3 --- Rolling distribution

Hitung parameter distribusi menggunakan window:

``` text
100 round
250 round
500 round
1000 round
```

Kemudian lihat apakah `k` dan exponent berubah.

Tujuan:

> Membedakan distribusi yang stabil dari distribusi yang berpindah
> regime.

------------------------------------------------------------------------

## Eksperimen 4 --- Conditional tail

Jangan hanya menguji:

``` text
P(X_t >= 2 | X_t-1)
```

Uji:

``` text
P(X_t >= x | X_t-1 >= y)
```

untuk berbagai kombinasi:

``` text
x = 2, 5, 10, 20, 50
y = 2, 5, 10, 20, 50
```

Tujuan:

> Melihat apakah extreme result mengubah distribusi round berikutnya.

------------------------------------------------------------------------

## Eksperimen 5 --- Multi-lag

Uji:

``` text
lag 1
lag 2
lag 3
...
lag 20
```

untuk:

-   raw `gr_result`
-   `log(gr_result)`
-   binary `>=2`
-   binary `>=5`
-   binary `>=10`

Tujuan:

> Memeriksa apakah dependency muncul pada lag tertentu dan bukan pada
> lag-1.

------------------------------------------------------------------------

## Eksperimen 6 --- Extreme-event response

Kelompokkan:

``` text
X >= 5
X >= 10
X >= 20
X >= 50
X >= 100
```

Kemudian lihat distribusi:

``` text
next 1 round
next 2 rounds
next 3 rounds
...
next 20 rounds
```

Bandingkan dengan baseline tanpa conditioning.

Ini merupakan cara yang lebih kuat untuk menguji hipotesis bahwa extreme
result mempunyai efek setelahnya.

------------------------------------------------------------------------

# 19. Kontrol False Discovery

Karena eksplorasi akan mencoba banyak threshold dan banyak lag, hasil
yang kebetulan terlihat signifikan sangat mungkin muncul.

Karena itu:

> Setiap pola yang ditemukan dari eksplorasi harus diuji ulang pada data
> yang belum digunakan untuk menemukan pola tersebut.

Struktur yang disarankan:

``` text
DATA
│
├── Discovery set
│     └── mencari pola
│
└── Confirmation set
      └── menguji pola yang sudah ditentukan
```

Untuk time-series, pembagian berdasarkan urutan waktu lebih sesuai
daripada random split.

------------------------------------------------------------------------

# 20. Kriteria Status Temuan

Gunakan label berikut agar dokumentasi tidak mencampur fakta dan
hipotesis.

### OBSERVED

Pola langsung terlihat dari data.

Contoh:

``` text
Median = 1,87
```

### CALCULATED

Hasil perhitungan statistik.

Contoh:

``` text
P(gr_result >= 2) = 47,02%
```

### HYPOTHESIS

Interpretasi yang masuk akal tetapi belum dibuktikan.

Contoh:

``` text
Distribusi mungkin mengikuti ~0,95/x
```

### TESTED

Hipotesis sudah diuji dengan metode statistik tertentu.

### CONFIRMED

Hanya digunakan jika hasil telah direplikasi dan bertahan pada data
out-of-sample atau dataset independen.

### REJECTED

Hipotesis gagal pada pengujian yang sesuai.

------------------------------------------------------------------------

# 21. Kesimpulan Sementara

Analisis `gr_result` menunjukkan satu struktur yang jauh lebih jelas
daripada dependency antar-round:

\[ `\boxed{
P(gr\_result\ge x)\approx\frac{0,95}{x}
}`{=tex} \]

dengan exponent empiris mendekati:

\[ `\boxed{\alpha\approx1}`{=tex} \]

Distribusi ini memiliki:

-   minimum 1,00,
-   median 1,87,
-   mean 8,04,
-   tail panjang sampai 5.000,
-   dan base rate `>=2` sekitar 47,02%.

Sebaliknya, hubungan langsung antara `gr_result_t` dan `gr_result_{t+1}`
sangat kecil:

``` text
corr(log GR_t, log GR_t+1) ≈ -0,0132
```

Binary transition juga hanya menunjukkan perbedaan kecil:

``` text
previous LOW  → 48,13% HIGH
previous HIGH → 45,76% HIGH
```

dengan:

``` text
p ≈ 0,084
```

Jadi pada tahap ini, **struktur distribusi `gr_result` merupakan temuan
utama**, sedangkan dependency antar-round belum menunjukkan bukti kuat.

------------------------------------------------------------------------

# 22. Status Penelitian

``` text
[✓] Validasi jumlah observasi
[✓] Descriptive statistics
[✓] Distribusi dasar
[✓] Heavy-tail inspection
[✓] Survival threshold inspection
[✓] Threshold >= 2 baseline
[✓] Lag-1 log correlation
[✓] Binary transition
[✓] Streak inspection
[✓] First-half vs second-half base rate

[ ] Formal distribution fitting
[ ] Formal tail exponent estimation dengan CI
[ ] Residual analysis terhadap 0,95/x
[ ] Rolling-window exponent
[ ] Conditional tail analysis
[ ] Multi-lag analysis
[ ] Extreme-event response
[ ] Out-of-sample confirmation
```

------------------------------------------------------------------------

# 23. Prinsip Untuk Analisis Berikutnya

Jangan mencari pola hanya agar ada pola.

Urutan penelitian:

``` text
observasi
   ↓
pola
   ↓
hipotesis
   ↓
uji
   ↓
replikasi
   ↓
out-of-sample
   ↓
kesimpulan
```

Khusus untuk `gr_result`, baseline distribusi `~0,95/x` harus
dipertahankan sebagai pembanding sebelum melakukan interpretasi terhadap
streak, extreme value, atau perubahan antar-round.
