# Quality Report Data Flow: Modul Instalasi

[English](module-en.md) | **Bahasa Indonesia**

Panduan ini memandu instalasi Quality Report Data Flow di PC Windows sampai laporan terkirim otomatis lewat email setiap hari.

Nama menu dan tombol di panduan ini ditulis sesuai tampilan bahasa Inggris di Windows dan Google Cloud Console.

**Prasyarat:**

- PC Windows dengan akses internet, karena laporan dikirim lewat Gmail.
- Akses ke database MySQL/MariaDB yang berisi tabel QID (`process_header`, `process_raw`, `member`): host, port, nama database, user, dan password.
- Akun Gmail atau Google Workspace yang akan mengirim laporan.
- Alamat email yang akan menerima laporan.

## Daftar Isi

- [Quality Report Data Flow: Modul Instalasi](#quality-report-data-flow-modul-instalasi)
  - [Daftar Isi](#daftar-isi)
  - [1. Instal perangkat lunak](#1-instal-perangkat-lunak)
  - [2. Instal paket Python](#2-instal-paket-python)
  - [3. Siapkan database](#3-siapkan-database)
  - [4. Isi file .env](#4-isi-file-env)
    - [4.1 Kunci enkripsi](#41-kunci-enkripsi)
    - [4.2 Database](#42-database)
    - [4.3 Nilai laporan](#43-nilai-laporan)
    - [4.4 Penerima email](#44-penerima-email)
  - [5. Siapkan pengiriman Gmail (Google Cloud Console)](#5-siapkan-pengiriman-gmail-google-cloud-console)
    - [5.1 Buat OAuth client](#51-buat-oauth-client)
    - [5.2 Masukkan client ke .env](#52-masukkan-client-ke-env)
    - [5.3 Login sekali untuk membuat refresh token](#53-login-sekali-untuk-membuat-refresh-token)
  - [6. Jalankan laporan](#6-jalankan-laporan)
  - [7. Jalankan otomatis setiap hari](#7-jalankan-otomatis-setiap-hari)
  - [8. Pemecahan masalah](#8-pemecahan-masalah)

> **Membuka Command Prompt di folder proyek.** Banyak langkah perlu menjalankan perintah. Buka folder proyek di File Explorer, klik address bar, ketik `cmd`, lalu tekan **Enter**. Command Prompt akan terbuka di folder tersebut. Jalankan semua perintah di panduan ini dari sana.

---

## 1. Instal perangkat lunak

1. **Instal Python 3.13.**
   [Unduh Python 3.13](https://www.python.org/downloads/release/python-31316/). Rilis 3.13.x apa pun dari [python.org/downloads/windows](https://www.python.org/downloads/windows/) bisa dipakai.
   Di layar pertama installer, centang **"Add python.exe to PATH"** sebelum klik **Install Now**. Jika langkah ini terlewat, perintah `python` di panduan ini tidak akan berfungsi.

2. **Instal text editor** untuk mengedit file `.env`:
   - [Sublime Text (disarankan)](https://www.sublimetext.com/download)
   - [VS Code](https://code.visualstudio.com/download)

3. **Unduh kode dari GitHub.**
   [Repo GitHub](https://github.com/ThePerfectJox/QualityReportDataFlow.git)
   Klik **Code → Download ZIP**, lalu ekstrak ke folder yang tidak akan dipindah, misalnya `C:\QualityReportDataFlow`. Jika Git sudah terinstal, Anda juga bisa menjalankan `git clone https://github.com/ThePerfectJox/QualityReportDataFlow.git`.

> **Jalan pintas:** `setup\environment.bat` menginstal Python 3.13, Git, dan Notepad++ melalui winget, lalu meng-clone repository ke `C:\`. Klik kanan file tersebut, pilih **Run as administrator**, lalu tempelkan URL repository saat diminta.

**Cek:** buka Command Prompt **baru** dan jalankan `python --version`. Hasilnya harus `Python 3.13.x`.

---

## 2. Instal paket Python

Klik dua kali **`setup\python-configurations.bat`**.

File ini menginstal paket yang tercantum di `requirements.txt` (`mysql-connector-python`, `pandas`, `numpy`, `openpyxl`, `python-dotenv`, dan `cryptography`). File ini juga membuat `.env` dari `.env.example` jika `.env` belum ada. Jika berhasil, bagian akhirnya seperti ini:

```text
[OK] Python packages
[OK] Created .env from .env.example
...
  Setup completed.
```

Lakukan langkah ini sebelum bagian 4, karena script di bagian 4 membutuhkan paket-paket ini.

---

## 3. Siapkan database

1. Pastikan server MySQL sedang berjalan. Di XAMPP, klik **Start** di samping *MySQL*.
2. Opsional: jalankan juga **Apache** agar bisa memakai phpMyAdmin di `http://localhost/phpmyadmin`. MySQL command line juga bisa dipakai.
3. Jalankan **`installation-module\sql-configuration.sql`** pada database yang berisi tabel QID:
   - **phpMyAdmin:** klik database di panel kiri, lalu **Import** → **Choose file** → pilih `sql-configuration.sql` → **Import**.
   - **MySQL command line:** `mysql -u <user> -p <database> < installation-module\sql-configuration.sql`

   Script ini membuat view `daily_report` yang dibaca oleh program, serta tiga index yang mempercepat view tersebut.
4. **Cek:** jalankan `SELECT * FROM daily_report LIMIT 5;`. Query ini harus menampilkan data.

Script ini aman dijalankan ulang. View akan diganti dengan yang baru. Error `Duplicate key name` hanya berarti index sudah ada.

---

## 4. Isi file .env

`.env` menyimpan semua pengaturan yang dipakai program. Data rahasia seperti password dan token disimpan dalam bentuk **terenkripsi**, dengan kunci yang juga tersimpan di file yang sama. Perlakukan `.env` seperti password: jangan dikirim lewat email, dibagikan, atau diunggah. File ini sudah dikecualikan dari Git.

Buka `.env` di text editor dan isi **sesuai urutan berikut**.

### 4.1 Kunci enkripsi

1. Jalankan:

   ```bat
   python script\create_key.py
   ```

2. Salin dua baris yang ditampilkan ke `.env`, menggantikan baris placeholder:

   ```text
   ENCRYPTION_ALGORITHM = aes-gcm
   ENCRYPTION_KEY = <kunci yang dihasilkan>
   ```

3. **Simpan `.env`.** Script enkripsi di langkah berikutnya membaca kunci dari file yang sudah disimpan.

Buat kunci sekali saja, sebelum mengenkripsi apa pun. Jika nanti Anda membuat kunci baru, semua nilai terenkripsi di `.env` harus dienkripsi ulang.

> **Cara mengenkripsi nilai.** Jalankan `python script\encrypt_value.py "<nilai asli>"`, lalu tempelkan token yang ditampilkan ke `.env`. Untuk mengecek token, jalankan `python script\decrypt_value.py "<token>"`, yang akan menampilkan nilai aslinya.

### 4.2 Database

| Key | Yang diisi |
| --- | --- |
| `MYSQL_HOST` | Alamat server MySQL. Isi `localhost` jika MySQL berjalan di PC ini. |
| `MYSQL_PORT` | Biasanya `3306`. |
| `MYSQL_DATABASE` | Database tempat Anda menjalankan `sql-configuration.sql`. |
| `MYSQL_USER` | Nama user MySQL. User ini cukup memiliki izin `SELECT` pada database tersebut. |
| `MYSQL_PASSWORD` | Password yang sudah **dienkripsi** dengan `encrypt_value.py`. Kosongkan jika user tidak memakai password, seperti user `root` bawaan XAMPP. |

### 4.3 Nilai laporan

Nilai-nilai ini ditulis ke setiap baris laporan.

| Key | Kolom laporan | Contoh |
| --- | --- | --- |
| `PLANT` | Plant/Reg | `RK1` |
| `LOCATION` | Location | `U6` |
| `GROUP` | Group/Cell | `99` |
| `BRAND` | Brand | `DUMMY` |
| `BAGIAN` | Bagian | `Rolling & Cutting` |
| `SET_SAMPLE` | Set Sample | `1` |

### 4.4 Penerima email

| Key | Yang diisi |
| --- | --- |
| `EMAIL_RECIPIENT` | Alamat penerima laporan, dipisahkan koma, misalnya `qa.lead@example.com, supervisor@example.com` |
| `EMAIL_SUBJECT` | *Opsional.* Menggantikan subjek bawaan `[QID] Quality Inspection Device - Rungkut 1 - Unit 1 - <tanggal hari ini>`. |

Setiap laporan juga dikirim sebagai CC ke alamat di `LIST_CC_EMAIL` di bagian atas `main.py`. Ubah daftar tersebut untuk menggantinya.

Key email `SMTP_USER` dan `OAUTH_*` diisi di bagian 5.

> **Memperbarui instalasi lama?** File `.env` versi lama berisi `SMTP_HOST`, `SMTP_PASSWORD`, dan `SMTP_AUTH`. Key tersebut sudah tidak dipakai dan boleh dihapus. Email sekarang selalu dikirim lewat Gmail dengan OAuth.

---

## 5. Siapkan pengiriman Gmail (Google Cloud Console)

Program login ke Gmail menggunakan **OAuth 2.0**, metode login standar Google untuk aplikasi. Program tidak memerlukan password Gmail maupun app password. Anda cukup membuat OAuth client sekali di Google Cloud Console dan login sekali di browser. Setelah itu, program mengirim email dengan sendirinya.

### 5.1 Buat OAuth client

1. Buka [Google Cloud Console](https://console.cloud.google.com/) dan login. Sebaiknya login dengan akun Gmail yang akan mengirim laporan, agar semuanya berada di satu akun.
2. **Buat project.** Klik pemilih project di bagian atas halaman, lalu **New project**. Isi nama, misalnya `Quality Report`, lalu klik **Create**. Pastikan project baru tersebut sudah terpilih.
3. Buka **☰ Menu → Google Auth platform** (atau ketik "Google Auth platform" di kolom pencarian), lalu klik **Get started**. Isi:
   - **App information:** App name `Quality Report`, dan email Anda sebagai User support email.
   - **Audience:** **External** untuk akun `@gmail.com` biasa. Pilih **Internal** jika akun pengirim adalah akun Google Workspace perusahaan dan project berada di bawah organisasi tersebut.
   - **Contact information:** email Anda.
   - Setujui kebijakan, lalu klik **Create**.
4. **Khusus External:** buka **Audience**, klik **Publish app**, lalu **Confirm**. Status harus **In production**. Selama status masih *Testing*, login dari Google berakhir setelah 7 hari dan program berhenti mengirim email.
5. Buka **Clients → Create client**:
   - **Application type:** `Desktop app`
   - **Name:** bebas, misalnya `Quality Report Desktop`
   - Klik **Create**.

   **Salin Client ID dan Client secret sekarang**, atau klik **Download JSON**. Google hanya menampilkan secret satu kali. Jika hilang, tambahkan secret baru pada client yang sama.

Gmail API tidak perlu diaktifkan.

### 5.2 Masukkan client ke .env

| Key | Yang diisi |
| --- | --- |
| `SMTP_USER` | Alamat Gmail yang mengirim laporan. |
| `OAUTH_CLIENT_ID` | Client ID, dalam teks biasa. Diakhiri dengan `.apps.googleusercontent.com`. |
| `OAUTH_CLIENT_SECRET` | Client secret yang sudah **dienkripsi**: `python script\encrypt_value.py "<client secret>"` |

Simpan `.env`.

### 5.3 Login sekali untuk membuat refresh token

1. Jalankan:

   ```bat
   python script\create_oauth_token.py
   ```

2. Browser akan membuka halaman login Google. Login dengan akun **`SMTP_USER`**.
3. Google menampilkan **"Google hasn't verified this app"**. Ini aplikasi milik Anda sendiri, jadi klik **Advanced → Go to Quality Report (unsafe)**.
4. Di layar akses, izinkan akses ke Gmail, lalu klik **Continue**. Jika ada checkbox, centang.
5. Browser menampilkan **"Access granted."** Kembali ke Command Prompt, script akan mengetes login Gmail dan menampilkan:

   ```text
   SMTP login OK.

   Add this to your .env:

   OAUTH_REFRESH_TOKEN = <token terenkripsi>
   ```

6. Salin baris `OAUTH_REFRESH_TOKEN` ke `.env`, lalu simpan.

Gmail hanya mengizinkan login SMTP dengan akses penuh ke email (`https://mail.google.com/`), sehingga layar persetujuan meminta akses tersebut. Program hanya memakainya untuk mengirim laporan. Untuk mencabut akses, hapus aplikasi di [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

**Jalankan ulang langkah 5.3** jika salah satu hal berikut terjadi: password Gmail diganti, akses dicabut, token tidak dipakai selama 6 bulan, atau program melaporkan bahwa Google menolak refresh token.

---

## 6. Jalankan laporan

```bat
python main.py
```

Jika berhasil, tampilannya seperti ini:

```text
1) Loading .env
2) Connecting to MySQL
3) Running query
4) Processing query results
   12 rows, 40 columns
   ...
5) Writing Excel
   Report: C:\QualityReportDataFlow\reports\2026\october\quality_report_20261020_070000.xlsx
6) Building email
   Recipients: ['qa.lead@example.com', ...]
7) Sending email
   Email sent.
8) Updating query cache
   Cache updated to: 2026-10-20T06:58:12
```

- Laporan Excel disimpan di `reports\<tahun>\<bulan>\`, dengan nama bulan dalam bahasa Inggris (misalnya `october`).
- `cache.json` menyimpan waktu `End` dari baris terbaru yang sudah dikirim. Saat program dijalankan berikutnya, hanya baris yang selesai setelah waktu tersebut yang dikirim. Pada instalasi baru, atur `last_end_timestamp` di `cache.json` ke titik awal laporan, misalnya `{"last_end_timestamp": "2026-10-20T00:00:00"}`.
- `Query returned no rows. Nothing to report.` berarti tidak ada baris baru sejak program terakhir dijalankan, sehingga tidak ada yang dikirim.
- Jika pengiriman gagal, cache tidak diperbarui, sehingga baris yang sama akan dikirim lagi saat program dijalankan berikutnya.

Untuk mengirim email tes saja, tanpa menyentuh database atau cache, jalankan `python test\TestEmailManager.py`.

---

## 7. Jalankan otomatis setiap hari

`setup\run-report.bat` menjalankan `main.py` satu kali dan menambahkan output-nya ke `report.log` di folder proyek. Gunakan Windows Task Scheduler untuk menjalankannya sesuai jadwal:

1. Buka menu Start, ketik **Task Scheduler**, lalu buka. Klik **Create Basic Task…**.
2. **Name:** `Quality Report`, lalu **Next**.
3. **Trigger:** **Daily**, pilih jamnya, lalu **Next**.
4. **Action:** **Start a program**. Di **Program/script**, klik **Browse…** dan pilih `setup\run-report.bat` di folder proyek. Klik **Next**, lalu **Finish**.
5. *Opsional:* buka **Properties** task tersebut dan pilih **Run whether user is logged on or not**, agar task tetap berjalan saat PC terkunci atau akun sudah sign out. Windows akan meminta password akun. Gunakan akun Windows yang sama dengan yang menjalankan bagian 2.
6. **Tes:** klik kanan task, pilih **Run**, lalu buka `report.log`.

PC harus menyala dan terhubung ke internet pada jam yang dijadwalkan.

---

## 8. Pemecahan masalah

| Pesan | Yang harus dilakukan |
| --- | --- |
| `'python' is not recognized` atau Microsoft Store terbuka | Python belum ada di PATH. Instal ulang Python dengan mencentang **"Add python.exe to PATH"**, atau gunakan `py -3` sebagai pengganti `python`. |
| `ModuleNotFoundError: No module named ...` | Jalankan ulang `setup\python-configurations.bat`. |
| `.env file not found` | Jalankan `setup\python-configurations.bat`, atau salin `.env.example` menjadi `.env`. |
| `X environment variable has not been configured` / `X is empty` | Tambahkan key `X` ke `.env`, atau isi nilainya. |
| `Key must be (16, 24, 32) bytes` / `ENCRYPTION_KEY is not valid base64` | `ENCRYPTION_KEY` masih berisi placeholder atau rusak. Ulangi bagian 4.1. |
| `InvalidTag` / `Token is not valid base64` | Nilai terenkripsi dibuat dengan kunci yang berbeda, atau tidak tersalin lengkap. Enkripsi ulang nilai tersebut. |
| `MYSQL_PASSWORD could not be decrypted` | `MYSQL_PASSWORD` masih berupa teks biasa. Enkripsi password tersebut (bagian 4.1), atau kosongkan jika tidak ada password. |
| `2003 Can't connect to MySQL server` | MySQL tidak berjalan, atau `MYSQL_HOST` / `MYSQL_PORT` salah. |
| `1045 Access denied for user` | `MYSQL_USER` atau `MYSQL_PASSWORD` salah. |
| `1146 Table '...daily_report' doesn't exist` | Jalankan `sql-configuration.sql` pada database yang tertulis di `MYSQL_DATABASE` (bagian 3). |
| `Google rejected the OAuth client` | Cek `OAUTH_CLIENT_ID` dan `OAUTH_CLIENT_SECRET`, dan pastikan client tersebut masih ada di Google Cloud Console. |
| `Google rejected the refresh token` | Jalankan ulang bagian 5.3. Jika terjadi setiap 7 hari, publish aplikasinya (bagian 5.1, langkah 4). |
| `Google did not return a refresh token` | Hapus aplikasi di [myaccount.google.com/permissions](https://myaccount.google.com/permissions), lalu jalankan ulang bagian 5.3. |
| `Gmail access was not granted` | Jalankan ulang bagian 5.3 dan izinkan akses Gmail di layar persetujuan. |
| `OAuth login for ... was rejected` | Anda login dengan akun yang berbeda dari `SMTP_USER`. Jalankan ulang bagian 5.3 dan login sebagai `SMTP_USER`. |
| Google menampilkan "Access blocked" atau "This app is blocked" | Aplikasi masih *Testing*: publish aplikasinya (bagian 5.1, langkah 4). Akun Workspace perusahaan: minta admin untuk mempercayai Client ID tersebut (Admin console → Security → API controls), atau gunakan aplikasi **Internal**. |
| `Could not reach https://oauth2.googleapis.com/token` | Tidak ada koneksi internet, atau proxy/firewall memblokir Google. |
| `TimeoutError` saat mengirim, atau `does not offer XOAUTH2 login` | Jaringan mungkin memblokir port 587. Tambahkan `SMTP_PORT = 465` dan `SMTP_SECURITY = ssl` ke `.env`. |
| `Query returned no rows. Nothing to report.` | Bukan error: tidak ada baris baru sejak waktu yang tersimpan di `cache.json` (bagian 6). |
