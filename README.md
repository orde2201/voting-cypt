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
