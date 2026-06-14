# Tugas_akhir_Kapital_selekta
# Analisis Sentimen Publik Rupiah Rp18.000/USD

Program ini digunakan untuk:

* Scraping artikel berita online
* Ekstraksi kata kunci narasi media
* Analisis sentimen artikel menggunakan IndoBERT
* Scraping komentar Instagram
* Analisis sentimen publik menggunakan IndoBERT
* Menyimpan seluruh hasil dalam format CSV

---

# Langkah 1 - Clone Repository

Buka Terminal atau Command Prompt:

```bash
git clone https://github.com/USERNAME/NAMA-REPOSITORY.git
```

Masuk ke folder project:

```bash
cd NAMA-REPOSITORY
```

---

# Langkah 2 - Buat Virtual Environment

Windows:

```bash
python -m venv .venv
```

Aktifkan virtual environment:

```bash
.venv\Scripts\activate
```

Jika berhasil akan muncul:

```text
(.venv)
```

di awal terminal.

---

# Langkah 3 - Install Dependencies

Install seluruh library yang dibutuhkan:

```bash
pip install -r requirements.txt
```

Jika file `requirements.txt` belum tersedia:

```bash
pip install pandas
pip install requests
pip install beautifulsoup4
pip install selenium
pip install undetected-chromedriver
pip install transformers
pip install torch
pip install python-dotenv
```

---

# Langkah 4 - Buat File .env

Buat file baru bernama:

```text
.env
```

Isi dengan format berikut:

```env
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN

IG_USER=USERNAME_INSTAGRAM
IG_PASS=PASSWORD_INSTAGRAM
```

Contoh:

```env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx

IG_USER=akun_instagram
IG_PASS=password_instagram
```

---

# Langkah 5 - Dapatkan HuggingFace Token

1. Login ke https://huggingface.co
2. Buka:

```text
Settings
→ Access Tokens
→ Create New Token
```

3. Pilih:

```text
Read Access
```

4. Salin token ke file `.env`

---

# Langkah 6 - Konfigurasi Artikel Berita

Buka file Python utama.

Cari bagian berikut:

```python
NEWS_URLS = [
]
```

Masukkan URL artikel berita yang akan dianalisis:

```python
NEWS_URLS = [
    "https://contoh-artikel-1",
    "https://contoh-artikel-2"
]
```

---

# Langkah 7 - Konfigurasi Postingan Instagram

Cari bagian:

```python
IG_POST_URLS = [
]
```

Masukkan URL postingan Instagram:

```python
IG_POST_URLS = [
    "https://www.instagram.com/p/XXXXX/",
    "https://www.instagram.com/p/YYYYY/"
]
```

Contoh:

```python
IG_POST_URLS = [
    "https://www.instagram.com/p/DZJcFuDympN/",
    "https://www.instagram.com/p/DZHBpRBSpbX/"
]
```

---

# Langkah 8 - Jalankan Program

Jalankan file Python:

```bash
python main.py
```

atau sesuaikan dengan nama file yang digunakan:

```bash
python analisis_sentimen.py
```

---

# Langkah 9 - Tunggu Seluruh Proses Selesai

Program akan menjalankan proses berikut secara otomatis:

### 1. Scraping Artikel Berita

Output:

```text
artikel_berita_mentah.csv
```

### 2. Ekstraksi Kata Kunci Narasi Media

Output:

```text
kata_kunci_narasi_media.csv
```

### 3. Analisis Sentimen Artikel

Output:

```text
hasil_sentimen_artikel.csv
```

### 4. Scraping Komentar Instagram

Output:

```text
hasil_scraping_komentar_ig.csv
```

### 5. Analisis Sentimen Komentar Publik

Output:

```text
hasil_sentimen_publik.csv
```

---

# Struktur Output

Setelah program selesai, folder project akan berisi:

```text
artikel_berita_mentah.csv
kata_kunci_narasi_media.csv
hasil_sentimen_artikel.csv
hasil_scraping_komentar_ig.csv
hasil_sentimen_publik.csv
```

---

# Resume Otomatis

Program mendukung checkpoint otomatis.

Jika proses terhenti karena:

* Internet terputus
* Komputer restart
* Program tertutup

jalankan kembali:

```bash
python main.py
```

Program akan melanjutkan dari data terakhir yang sudah tersimpan.

---

# Troubleshooting

### Chrome Tidak Bisa Dibuka

Pastikan Google Chrome telah terinstall dan diperbarui ke versi terbaru.

### Login Instagram Gagal

Periksa:

* Username Instagram
* Password Instagram
* Verifikasi akun (2FA atau checkpoint Instagram)

### Error HuggingFace Token

Pastikan variabel berikut sudah terisi pada file `.env`:

```env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

### Error Module Not Found

Install ulang dependency:

```bash
pip install -r requirements.txt
```

---

# Catatan Penting

Jangan mengunggah file berikut ke GitHub:

```text
.env
hasil_*.csv
artikel_*.csv
.venv/
__pycache__/
```

Tambahkan ke file `.gitignore` untuk menjaga keamanan akun dan data hasil scraping.
