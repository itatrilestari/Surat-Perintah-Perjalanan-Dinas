# Surat-Perintah-Perjalanan-Dinas

Sistem pengelolaan perjalanan dinas yang mendukung proses pengajuan, persetujuan, penerbitan dokumen perjalanan dinas, hingga pertanggungjawaban biaya perjalanan.

## Tech Stack

- **Python:** 3.12
- **Django:** 6.1.3
- **Django REST Framework**
- **JWT Authentication:** Simple JWT 2.15.1
- **Database:** PostgreSQL

## Getting Started

Ikuti langkah-langkah berikut untuk menjalankan project di lingkungan lokal.

### 1. Clone Repository

```bash
git clone https://github.com/itatrilestari/Portal-Kinerja.git
cd Base-Code-Django
```

### 2. Install Dependencies

Pastikan Python 3.12 sudah terinstall, kemudian install seluruh dependency:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Sesuaikan konfigurasi database PostgreSQL dan environment project melalui file konfigurasi lokal yang tersedia.

Pastikan database PostgreSQL sudah dibuat dan dapat diakses oleh aplikasi.

### 4. Run Database Migrations

Jalankan perintah berikut untuk menerapkan database migrations:

```bash
make migrate
```

Atau menggunakan Django management command:

```bash
python manage.py migrate
```

### 6. Jalankan Data Initial

Terdapat data dummy pada `seed_data`. Untuk menjalankannya, jalankan:

```bash
./manage.py seed_data
```

### 5. Run Development Server

Jalankan aplikasi menggunakan:

```bash
make
```

Atau:

```bash
python manage.py runserver
```

Secara default, aplikasi dapat diakses melalui:

```text
http://127.0.0.1:8000/
```

## Authentication

Project ini menggunakan **JSON Web Token (JWT)** melalui `djangorestframework-simplejwt` sebagai mekanisme autentikasi API.

JWT menyediakan dua jenis token:

- **Access Token:** Digunakan untuk mengakses endpoint API yang membutuhkan autentikasi.
- **Refresh Token:** Digunakan untuk mendapatkan access token baru ketika access token kedaluwarsa.

## Dokumentasi API

Untuk mencoba dan menguji endpoint aplikasi, silakan unduh Postman Collection melalui file berikut:

`data/postman/SPPD.postman_collection.json`

### Cara Menggunakan

1. Buka Postman, kemudian import file Collection yang telah diunduh.
2. Atur variabel `base_url` dengan value berikut:

   ```text
   http://localhost:8000/api/
   ```

3. Buka folder **Auth**, kemudian jalankan endpoint **Register** untuk mendapatkan access token.
4. Salin access token yang diperoleh dari response API.
5. Masukkan access token pada header Authorization untuk mengakses endpoint yang memerlukan autentikasi dengan format berikut:

   ```http
   Authorization: Bearer <access_token>
   ```

6. Setelah berhasil melakukan autentikasi, endpoint API sudah dapat digunakan dan diuji melalui Postman.

## License

Repository ini dapat digunakan sebagai template dasar untuk pengembangan project backend berbasis Django REST Framework.
