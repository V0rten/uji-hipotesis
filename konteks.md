Saya sedang mengerjakan project analisis data empiris terhadap game crash multiplier. Fokus project ini bukan mengasumsikan game bisa diprediksi, melainkan menguji apakah data historis menunjukkan struktur statistik yang cukup stabil untuk membantu memperkirakan range hasil round berikutnya, terutama untuk mengidentifikasi/menghindari hasil rendah 1.00–1.99.

1. Tujuan project

Dataset berisi histori gr_result (multiplier) dan timestamp setiap round.

Tujuan utama saat ini:

> Mencari apakah informasi dari histori ribuan round dapat digunakan untuk memperkirakan range/kategori multiplier round berikutnya, bukan menebak angka multiplier secara exact.



Kategori yang digunakan:

Low: 1.00–1.99

Mid: 2.00–24.99

High: 25.00–99.99

Extra: >=100


Fokus praktisnya terutama mencari kondisi yang membuat probabilitas Low (<2) berbeda secara konsisten, karena saya ingin menguji apakah ada kondisi historis yang bisa digunakan sebagai filter.

2. Prinsip penting

Jangan mengasumsikan bahwa:

PRNG memiliki memory.

Hasil sebelumnya pasti memengaruhi hasil berikutnya.

Game pasti predictable.

Pola visual/deskriptif otomatis berarti hubungan kausal.


Semua harus dimulai dari data.

Pisahkan dengan jelas:

1. fakta dari dataset,


2. hasil perhitungan,


3. hipotesis,


4. interpretasi,


5. kesimpulan sementara.



Kalau suatu hipotesis tidak didukung data, jangan dipaksakan.

3. Dataset dasar

Dataset utama memiliki sekitar 5.491 round, dengan gr_result.

Statistik awal yang sudah ditemukan:

median ≈ 1.87

mean ≈ 8.04

max 5000

P95 ≈ 19.17

>=2 ≈ 47.02%


Distribusinya sangat heavy-tailed.

Secara kasar:

P(X >= x) ≈ 0.95 / x

di banyak threshold.

Contoh:

Threshold	Observed

>=2	47.02%
>=3	31.21%
>=5	19.01%
>=10	9.58%
>=20	4.77%
>=50	1.84%
>=100	0.82%


Tail exponent keseluruhan sekitar 1.

Jadi jangan menggunakan mean multiplier secara naif karena sangat dipengaruhi outlier.

4. Analisis dependency awal

Lag-1 correlation pada log(gr_result) sekitar:

-0.0132

dengan R² ≈ 0.00018.

Artinya dependency linear sederhana antar-round sangat kecil.

Transisi binary:

jika round sebelumnya <2, round berikutnya >=2 ≈ 48.13%

jika round sebelumnya >=2, round berikutnya >=2 ≈ 45.76%


Perbedaannya sekitar 2.37 percentage points.

Uji awal menghasilkan chi-square ≈ 2.987 dan p ≈ 0.084.

Jadi ada indikasi deskriptif, tetapi belum cukup untuk menyatakan adanya dependency yang kuat.

Base rate juga relatif stabil:

first half ≈ 47.07% >=2

second half ≈ 46.98% >=2


Streak:

LOW (<2) mean ≈ 2.08, max 12

HIGH (>=2) mean ≈ 1.84, max 16


Kesimpulan sementara: distribusi heavy-tail sangat jelas, sedangkan dependency sequential sederhana tampak lemah.

5. Data timestamp

Data juga memiliki:

tag_ts

ts

startdealing_ts

gr_ts

gr_result

game_id

status


Ada sekitar 50 row awal yang merupakan history tanpa timestamp lengkap, lalu sekitar 5.441 round timestamped/live.

Beberapa karakteristik timestamp yang pernah ditemukan:

tag_ts → ts sekitar 28.8 detik

ts → startdealing_ts median sekitar 7.09 detik

startdealing_ts → gr_ts median sekitar 8.20 detik

interval antar-round berdasarkan ts: median sekitar 17.64 detik, mean sekitar 21.50 detik

ada sebagian interval panjang, termasuk >30 detik dan beberapa >60 detik


Timestamp harus diperlakukan hati-hati karena bisa mengandung efek mekanisme game/collector, bukan hanya informasi statistik hasil.


---

6. Konsep utama yang sedang diuji: Sliding FIFO Window

Saya membuat analisis sliding FIFO window.

Misalnya window size N=30.

Window pertama:

round 1–30

window berikutnya:

round 2–31

berikutnya:

round 3–32

dan seterusnya.

Jadi window sangat overlap.

Untuk setiap window:

window_size

round awal

round akhir

first_tag_ts

last_gr_ts

window_duration

last_gr

mean/max/min GR

count_ge_X

since_ge_X


Window duration:

last_gr_ts - first_tag_ts

Setiap window dianggap sebagai satu observasi dengan target berupa hasil round terakhirnya.

Ini penting karena:

> Window bukan kumpulan round independen. Window N dan N+1 hampir seluruhnya berbagi data.



Contoh W30 #100 dan #101 berbagi 29 dari 30 round.

Jadi ribuan window tidak boleh dianggap sebagai ribuan eksperimen independen.

Validasi harus menggunakan pembagian waktu/chronological split dan memperhatikan overlap.


---

7. File analisis window

Saya sudah menghasilkan data window sampai:

window size 10–2000

Data raw per-window memiliki satu baris untuk setiap window.

Selain raw data, ada data agregat yang berisi distribusi duration window.

Untuk setiap window_size, duration dibagi menjadi 10 equal-width bins.

Setiap bin menyimpan:

jumlah round/window

persentase

mean

median

jumlah Low

jumlah Mid

jumlah High

jumlah Extra

pct_low

pct_mid

pct_high

pct_extra


Kategori:

Low   = 1.00–1.99
Mid   = 2.00–24.99
High  = 25.00–99.99
Extra = >=100

Data agregat ini bagus untuk eksplorasi hubungan:

window duration → distribusi result

tetapi tidak cukup untuk live prediction, karena informasi individual tentang masing-masing window hilang setelah agregasi.

Untuk modeling/prediction sebaiknya menggunakan raw per-window.


---

8. Ide utama yang sedang kita kembangkan

Saya awalnya berpikir:

> "Prediksi range round berikutnya berdasarkan sisa durasi window."



Misalnya suatu window biasanya berlangsung dalam range duration tertentu. Jika saat ini window sudah berjalan sekian menit dan masih belum mencapai endpoint, mungkin kondisi elapsed/remaining duration memiliki informasi tentang hasil endpoint berikutnya.

Tetapi saya belum tahu bagaimana memanfaatkan GR histori di dalam window secara optimal.

Ini adalah masalah utama yang ingin saya pecahkan.

Jangan langsung menganggap konsep "remaining duration" valid. Itu harus diuji.


---

9. Hipotesis yang ingin diuji

H1 — Window duration memiliki informasi

Apakah duration window berhubungan dengan kategori last_gr?

Misalnya:

duration → P(Low/Mid/High/Extra)


---

H2 — Relative duration lebih informatif

Absolute duration bisa berbeda karena window size.

Gunakan:

duration_ratio = actual_duration / median_duration_for_window_size

Kemudian uji apakah ratio lebih informatif dibanding absolute duration.


---

H3 — Recency extreme GR

Gunakan:

since_ge_X

Contoh:

since_ge_2

since_ge_5

since_ge_10

since_ge_20

since_ge_50

since_ge_100


Artinya berapa round sejak terakhir ada hasil >= X.


---

H4 — Frequency extreme GR

Gunakan:

count_ge_X

Contoh:

berapa kali >=10 terjadi dalam window.


---

H5 — Interaction recency + frequency

Contoh:

terakhir >=10 baru saja + frequency tinggi

terakhir >=10 sudah lama + frequency rendah


Mungkin kombinasi ini lebih informatif daripada salah satu saja.


---

H6 — Statistik GR dalam window

Gunakan:

mean

median

max

min


Tetapi hati-hati karena heavy-tail membuat mean/max sangat sensitif terhadap outlier.


---

H7 — State window

Buat state sederhana:

HOT

NORMAL

COLD


berdasarkan kombinasi recency/frequency.

Kemudian lihat distribusi target berikutnya.


---

H8 — Window size

Uji apakah informasi berbeda pada:

10–50

51–100

101–250

251–500

501–1000

1001–2000


Jangan mencari satu window size "terbaik" terlalu cepat.


---

H9 — Konsistensi antar-window size

Signal yang bagus seharusnya tidak hanya muncul pada satu window size.

Cari apakah efek yang sama muncul pada banyak ukuran window.


---

H10 — Ensemble antar-window

Daripada memilih satu window:

gunakan beberapa window size sekaligus.

Misalnya masing-masing menghasilkan estimasi probabilitas:

P(next >= 2)

kemudian digabungkan dengan:

majority vote

weighted vote

median probability



---

H11 — Consensus score

Untuk setiap window:

+1 jika mendukung non-low

0 netral

-1 mendukung low


Lalu hitung:

consensus = jumlah positive / jumlah active windows

Tujuannya melihat apakah banyak window independen-ish memberikan sinyal yang searah.

Tetap ingat: window overlap berat, jadi jangan menyebutnya independent votes.


---

H12 — Round density

Gunakan:

density = window_size / duration

Ini mengukur seberapa cepat N round terjadi dalam window.

Mungkin lebih stabil daripada duration mentah.


---

H13 — Normalisasi recency/frequency

Karena window size berbeda, gunakan:

count_ge_X / window_size

dan

since_ge_X / window_size


---

H14 — Duration × recency

Uji interaksi:

duration_ratio × normalized_recency


---

H15 — Duration × frequency

Uji:

duration_ratio × normalized_frequency


---

H16 — Duration × recency × frequency

Interaksi tiga arah.

Ini jangan dilakukan terlalu awal karena risiko overfitting tinggi.


---

H17 — Stability across time

Signal yang ditemukan harus dicek apakah tetap ada pada periode waktu berbeda.

Contoh:

awal dataset

tengah

akhir


Jika signal hanya muncul di satu periode, jangan dianggap robust.


---

H18 — Walk-forward validation

Jangan random train/test split.

Gunakan chronological split:

TRAIN → VALIDATION → TEST

atau walk-forward.

Tujuannya mencegah future information masuk ke training.


---

H19 — Jangan hanya target >=2

Selain binary:

>=2

uji juga:

>=5

>=10

>=20

>=50

>=100


Karena mungkin suatu fitur tidak berguna untuk memprediksi >=2, tetapi berguna untuk membedakan tail event.


---

H20 — Fokus pada LOW filtering

Accuracy bukan metric utama.

Yang lebih penting:

coverage

low rate

non-low rate

lift terhadap base rate

jumlah sample

stability out-of-sample


Contoh:

Base:

P(Low) = 53%

Jika sebuah kondisi menghasilkan:

P(Low | condition) = 40%

maka itu menarik secara statistik.

Tetapi harus diuji out-of-sample dan pada periode berbeda.


---

10. Masalah yang ingin saya pecahkan sekarang

Saya ingin mengembangkan metode seperti:

current state
    ↓
elapsed duration
    +
remaining/expected duration
    +
GR history inside window
    +
recency extreme
    +
frequency extreme
    +
density
    ↓
estimasi range probability
    ↓
Low / Mid / High / Extra

Tetapi jangan langsung membuat model kompleks.

Saya ingin menemukan terlebih dahulu fitur mana yang benar-benar memiliki informasi.

Urutan yang saya inginkan:

1. validasi data
2. baseline distribution
3. duration
4. relative duration
5. recency
6. frequency
7. duration + recency
8. duration + frequency
9. kombinasi sederhana
10. multi-window
11. walk-forward validation
12. baru modeling jika memang ada signal


---

11. Hal yang sangat penting

Jangan melakukan:

mencari pola hanya karena terlihat menarik

memilih window size berdasarkan hasil terbaik in-sample

menganggap korelasi kecil sebagai prediktabilitas

menganggap ribuan sliding windows sebagai ribuan sample independen

memakai future data secara tidak sengaja

menggunakan mean GR tanpa memperhatikan heavy-tail

membuat model ML kompleks sebelum tahu signal dasarnya

menyimpulkan "bisa diprediksi" hanya dari backtest satu periode


Jika signal hanya kecil tetapi stabil, itu lebih menarik daripada signal besar tetapi hanya muncul sekali.


---

12. Peran AI dalam project ini

Saya ingin AI bertindak sebagai research/data-analysis partner, bukan sebagai mesin yang selalu membenarkan hipotesis saya.

Kalau saya mengajukan ide:

> "mungkin fitur X bisa memprediksi Y"



AI harus membantu:

1. mendefinisikan hipotesis yang bisa diuji,


2. menentukan feature,


3. menentukan baseline,


4. menentukan eksperimen,


5. menentukan metric,


6. menghindari leakage,


7. menginterpretasikan hasil,


8. mencari counter-evidence,


9. menentukan apakah signal stabil atau kemungkinan artefact.



Kalau hasil tidak mendukung hipotesis saya, katakan secara langsung.

Jangan mengarang kolom atau struktur data yang tidak ada.

Saya sendiri akan menjalankan script/eksperimen pada dataset besar dan mengirimkan hasilnya ke AI untuk dievaluasi.


---

13. Kondisi project sekarang

Saya sudah memiliki raw window data untuk window size 10–2000.

Langkah berikutnya kemungkinan adalah membuat eksperimen yang memanfaatkan:

window duration
duration ratio
elapsed duration
remaining/expected duration
since_ge_X
count_ge_X
normalized recency
normalized frequency
density

dan menguji hubungannya dengan:

target = kategori gr_result round berikutnya

atau secara khusus:

target_low = 1 jika next gr_result < 2

Tujuan akhirnya bukan menghasilkan "angka multiplier berikutnya", tetapi jika memang terdapat signal yang stabil:

> memperkirakan distribusi/range hasil berikutnya dan terutama mengetahui kapan kondisi historis tertentu berkaitan dengan risiko Low yang lebih rendah/lebih tinggi.

Jika punya model kompleks untuk diuji bisa diajukan ke user tapi dengan syarat hipotesis yang kuat.