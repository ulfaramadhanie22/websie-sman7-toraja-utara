# Website Terpadu SMAN 7 Toraja Utara — Versi Login

## Fitur
Profil sekolah, pengumuman, data siswa/guru, akun admin/guru/siswa, absensi, jadwal, nilai, e-learning, dan formulir minat PPDB. Password di-hash dan formulir POST dilindungi token CSRF. Akun siswa melihat nilai/absensi miliknya jika akun sudah ditautkan ke data siswa.

## Uji coba lokal
1. Instal Python 3.10+.
2. Buka terminal di folder aplikasi.
3. Jalankan `pip install -r requirements.txt`.
4. Buat akun admin awal dengan variabel lingkungan sebelum menjalankan:
   - Windows PowerShell:
     `$env:INITIAL_ADMIN_USERNAME="adminsekolah"`
     `$env:INITIAL_ADMIN_PASSWORD="GantiDenganKataSandiKuat12!"`
     `$env:SECRET_KEY="buat-kunci-random-panjang"`
   - macOS/Linux:
     `export INITIAL_ADMIN_USERNAME=adminsekolah`
     `export INITIAL_ADMIN_PASSWORD='GantiDenganKataSandiKuat12!'`
     `export SECRET_KEY='buat-kunci-random-panjang'`
5. Jalankan `python app.py`.
6. Buka `http://127.0.0.1:5000` lalu pilih Login.
7. Admin dapat menambahkan data siswa, lalu membuat akun siswa dan menautkannya ke data siswa tersebut.

## Publikasi online
File `render.yaml` dan `Procfile` disertakan sebagai konfigurasi awal hosting. Untuk mempublikasikan, unggah proyek ke repositori GitHub milik sekolah, hubungkan ke layanan hosting, dan isi variabel lingkungan rahasia pada dashboard hosting. SQLite memerlukan penyimpanan persisten. Aplikasi ini belum menggunakan PostgreSQL; untuk banyak pengguna dan produksi, sebaiknya migrasikan ke database PostgreSQL sebelum digunakan dengan data sekolah sungguhan.

## Batasan keamanan
Ini prototipe pengembangan, bukan sistem produksi yang sudah diaudit. Belum tersedia reset kata sandi, pembatasan percobaan login, audit log, dan pengaturan hak guru per kelas/mapel. Formulir PPDB hanya menyimpan minat awal. Visi/misi adalah contoh. Jangan masukkan data pribadi nyata atau publikasikan sebelum sekolah menetapkan akses, privasi, backup, HTTPS, dan pengujian keamanan.
