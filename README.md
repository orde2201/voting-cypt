1. membuat key, hapus # pada /backend/main.py pada line 11
```
#import RSA_key_gen 
```

2. run
```
docker compose up
```

note :
Jika sudah muncul file private dan public key, hentikan docker compose lalu
tambahkan # lagi pada import RSA_key_gen agar tidak membuat ulang


3. Akses interface
User Interface 
```
http://localhost:3000/
```
api test 
```
http://localhost:8000/
```

## Tabel Users

Berikut adalah data dummy untuk testing:
note : login hanya bisa dilakukan dengan akun pada tabel ini
hal ini dibuat agar tidak ada yang menggunakan akun tidak resmi

| NIM | Nama Lengkap | Password | Status |
|-----|--------------|----------|--------|
| 231010001 | Andi Pratama | admin123 | **Admin** |
| 231010002 | Budi Santoso | pass123 | Student |
| 231010003 | Citra Lestari | pass123 | Student |
| 231010004 | Dewi Anggraini | pass123 | Student |
| 231010005 | Eko Saputra | pass123 | Student |
| 231010006 | Fajar Nugroho | pass123 | Student |
| 231010007 | Gita Ramadhani | pass123 | Student |
| 231010008 | Hendra Wijaya | pass123 | Student |
| 231010009 | Intan Permata | pass123 | Student |
| 231010010 | Joko Susilo | pass123 | Student |

> **Catatan:** 
> - Admin memiliki akses ke halaman Recap
> - Student hanya dapat mengakses halaman Vote
