from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from RSA import RSAEncryptor
from hashing import hash_message
import psycopg2
from psycopg2 import Binary
from collections import Counter
import json
import base64
from typing import Dict, List, Any, Optional

###JANGAN DIHAPUS, INI UNTUK GENERATE KEY RSA, JALANKAN SEKALI SAJA LALU HAPUS FILE PEMNYA
#import RSA_key_gen 

# ================================================================
# SETUP FASTAPI
# ================================================================

app = FastAPI(
    title="Voting System API",
    description="API untuk sistem voting dengan enkripsi RSA dan verifikasi hash",
    version="2.0.0"
)

# Konfigurasi CORS untuk mengizinkan akses dari frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Origin yang diizinkan
    allow_credentials=True,  # Izinkan pengiriman cookie/credentials
    allow_methods=["*"],     # Izinkan semua method HTTP (GET, POST, etc)
    allow_headers=["*"],     # Izinkan semua headers
)

# ================================================================
# DATABASE CONNECTIONS
# ================================================================

def get_conn_vote():
    """
    Membuat koneksi ke database votedata.
    Database ini menyimpan data vote yang sudah terenkripsi.
    
    Returns:
        psycopg2.connection: Koneksi ke database votedata
    """
    return psycopg2.connect(
        dbname="votedata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

def get_conn_verify():
    """
    Membuat koneksi ke database verify_vote.
    Database ini menyimpan hash dari data vote ASLI (sebelum enkripsi)
    untuk keperluan verifikasi integritas data.
    
    Returns:
        psycopg2.connection: Koneksi ke database verify_vote
    """
    return psycopg2.connect(
        dbname="verify_vote",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

def get_conn_login():
    """
    Membuat koneksi ke database userdata.
    Database ini menyimpan data user (NIM, password, role) untuk autentikasi.
    
    Returns:
        psycopg2.connection: Koneksi ke database userdata
    """
    return psycopg2.connect(
        dbname="userdata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

# ================================================================
# PYDANTIC MODELS (Data Validation)
# ================================================================

class Vote(BaseModel):
    """
    Model untuk data vote yang dikirim dari frontend.
    
    Attributes:
        nama (str): Nama lengkap voter
        nim (str): Nomor Induk Mahasiswa (unique identifier)
        kandidat (str): Pilihan kandidat (A, B, atau C)
    """
    nama: str
    nim: str
    kandidat: str

class LoginRequest(BaseModel):
    """
    Model untuk request login dari frontend.
    
    Attributes:
        nim (str): Nomor Induk Mahasiswa
        password (str): Password user
    """
    nim: str
    password: str

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def bytes_to_string(data):
    """
    Konversi data bytes/memoryview ke string untuk keperluan hashing.
    Fungsi ini memastikan format data konsisten sebelum di-hash.
    
    Args:
        data: Data dalam format bytes, memoryview, atau string
    
    Returns:
        str: Data dalam format string (base64 jika dari bytes)
    
    Note:
        Data bytes akan di-encode ke base64 untuk menghindari karakter yang tidak sesuai
    """
    if isinstance(data, memoryview):
        data = data.tobytes()
    if isinstance(data, bytes):
        # Encode bytes ke base64 untuk konsistensi hashing
        return base64.b64encode(data).decode('utf-8')
    if isinstance(data, str):
        return data
    return str(data)

# ================================================================
# ENDPOINT 1: LOGIN
# ================================================================

@app.post("/login")
def login(data: LoginRequest):
    """
    Endpoint untuk autentikasi user.
    
    Proses:
        1. Cek NIM di database userdata
        2. Validasi password
        3. Kembalikan role (admin/student) dan NIM
    
    Args:
        data (LoginRequest): NIM dan password dari frontend
    
    Returns:
        dict: {
            "success": bool,      # True jika login berhasil
            "message": str,       # Pesan keterangan
            "status": str,        # Role user (admin/student)
            "nim": str           # NIM user (kembali untuk konfirmasi)
        }
    
    Contoh Response:
        Success: {"success": True, "message": "Login berhasil", "status": "admin", "nim": "12345"}
        Failed: {"success": False, "message": "Password salah"}
    """
    conn = get_conn_login()
    cur = conn.cursor()

    try:
        # Query user berdasarkan NIM
        cur.execute(
            "SELECT passw, status FROM users WHERE nim = %s",
            (data.nim,)
        )

        user = cur.fetchone()

        if not user:
            return {"success": False, "message": "User tidak ditemukan"}

        db_password, status = user

        # Validasi password (plain text comparison - untuk demo)
        if data.password == db_password:
            return {
                "success": True,
                "message": "Login berhasil",
                "status": status,
                "nim": data.nim
            }

        return {"success": False, "message": "Password salah"}
    
    finally:
        cur.close()
        conn.close()

# ================================================================
# ENDPOINT 2: SUBMIT VOTE
# ================================================================

@app.post("/vote")
def submit_vote(vote: Vote):
    """
    Endpoint untuk menyimpan vote dengan arsitektur: Hash ASLI -> Encrypt.
    
    Alur Proses:
        1. Validasi NIM belum pernah vote
        2. Validasi NIM terdaftar di database user
        3. Hash data vote ASLI (JSON) -> simpan ke verify_vote.hashing
        4. Encrypt data vote ASLI -> simpan ke votedata.userVote
    
    Args:
        vote (Vote): Data vote (nama, nim, kandidat)
    
    Returns:
        dict: {
            "success": bool,     # True jika vote berhasil disimpan
            "message": str       # Pesan keterangan
        }
    
    Note:
        - Hash disimpan SEBELUM enkripsi untuk verifikasi integritas
        - Encrypted vote disimpan sebagai BYTEA di PostgreSQL
    """
    conn_vote = get_conn_vote()
    cur_vote = conn_vote.cursor()
    
    try:
        # ===== VALIDASI 1: Cek apakah NIM sudah pernah vote =====
        cur_vote.execute(
            "SELECT voter_id FROM userVote WHERE voter_id = %s",
            (vote.nim,)
        )
        existing_vote = cur_vote.fetchone()
        
        if existing_vote:
            return {
                "success": False, 
                "message": "Anda sudah melakukan vote sebelumnya!"
            }
        
        # ===== VALIDASI 2: Cek apakah NIM terdaftar di database user =====
        conn_login = get_conn_login()
        cur_login = conn_login.cursor()
        
        cur_login.execute(
            "SELECT nim, status FROM users WHERE nim = %s",
            (vote.nim,)
        )
        user_exists = cur_login.fetchone()
        
        cur_login.close()
        conn_login.close()
        
        if not user_exists:
            return {
                "success": False,
                "message": "NIM tidak terdaftar! Silahkan login terlebih dahulu."
            }
        
        # ===== PROSES VOTE =====
        # STEP 1: Konversi data vote ke JSON string
        vote_json = vote.model_dump_json()
        print(f"[DEBUG] Original vote JSON: {vote_json}")
        
        # STEP 2: Hash data ASLI (sebelum encrypt)
        # Hash ini akan digunakan untuk verifikasi saat recap
        original_hash = hash_message(vote_json)
        print(f"[DEBUG] Original hash: {original_hash}")
        
        # STEP 3: Enkripsi data vote asli menggunakan RSA
        rsa_encryptor = RSAEncryptor()
        encrypted_vote = rsa_encryptor.encrypt(vote_json)
        print(f"[DEBUG] Encrypted vote type: {type(encrypted_vote)}")

        # ===== SIMPAN KE DATABASE =====
        conn_verify = get_conn_verify()
        cur_verify = conn_verify.cursor()

        try:
            # Simpan encrypted vote ke votedata.userVote
            cur_vote.execute(
                "INSERT INTO userVote (voter_id, vote) VALUES (%s, %s)",
                (vote.nim, Binary(encrypted_vote))
            )

            # Simpan hash asli ke verify_vote.hashing
            cur_verify.execute(
                "INSERT INTO hashing (vote_id, hash) VALUES (%s, %s)",
                (vote.nim, original_hash)
            )

            conn_vote.commit()
            conn_verify.commit()

            return {
                "success": True, 
                "message": "Vote berhasil dikirim"
            }

        except Exception as e:
            # Rollback jika terjadi error
            conn_vote.rollback()
            conn_verify.rollback()
            print(f"[ERROR] Database error: {e}")
            return {"success": False, "error": str(e)}

        finally:
            cur_verify.close()
            conn_verify.close()

    except Exception as e:
        print(f"[ERROR] Vote error: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        cur_vote.close()
        conn_vote.close()

# ================================================================
# ENDPOINT 3: RECAP / HASIL VOTING (ADMIN ONLY)
# ================================================================

@app.get("/recap")
def recap_vote():
    """
    Endpoint untuk menghitung dan memverifikasi hasil voting.
    
    Alur Proses:
        1. Ambil semua encrypted vote dari votedata.userVote
        2. Ambil semua hash asli dari verify_vote.hashing
        3. Untuk setiap vote:
           a. Decrypt vote
           b. Hash hasil decrypt
           c. Bandingkan dengan hash yang tersimpan
           d. Jika cocok -> hitung suara
           e. Jika tidak cocok -> masukkan ke invalid/missing list
    
    Returns:
        dict: {
            "total_valid": int,        # Jumlah vote yang valid
            "total_invalid": int,      # Jumlah vote dengan hash mismatch
            "total_missing_hash": int, # Jumlah vote tanpa hash di verify_db
            "total_votes": int,        # Total vote di database
            "hasil": dict,             # Perolehan suara {"A": 10, "B": 5, ...}
            "valid_voters": list,      # Daftar NIM yang valid
            "invalid_votes": list,     # Detail vote yang invalid
            "missing_hash": list       # Detail vote yang hash-nya hilang
        }
    
    Note:
        - Endpoint ini sebaiknya hanya bisa diakses oleh ADMIN
        - Hash mismatch menandakan adanya manipulasi data
        - Missing hash menandakan data tidak lengkap di verify_db
    """
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()

    # Inisialisasi containers untuk hasil
    valid_votes: List[Dict[str, Any]] = []      # Vote yang valid
    invalid_votes: List[Dict[str, Any]] = []    # Vote dengan hash mismatch
    missing_hash: List[Dict[str, Any]] = []     # Vote tanpa hash di verify_db
    kandidat_list = []                           # List pilihan kandidat

    try:
        # Ambil semua data vote dari database votedata
        cur_vote.execute("SELECT voter_id, vote FROM uservote")
        rows = cur_vote.fetchall()

        # Ambil semua hash dari database verifikasi
        # Konversi ke dictionary untuk akses cepat: {vote_id: hash}
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        hash_records = {vote_id: hash_val for vote_id, hash_val in cur_verify.fetchall()}

        rsa_decryptor = RSAEncryptor()

        print(f"\n=== RECAP PROCESS START ===")
        print(f"[INFO] Total votes in DB: {len(rows)}")
        print(f"[INFO] Total hashes in verify DB: {len(hash_records)}")

        # Proses setiap vote
        for voter_id, encrypted_vote in rows:
            try:
                # Konversi memoryview ke bytes jika perlu
                if isinstance(encrypted_vote, memoryview):
                    encrypted_vote = encrypted_vote.tobytes()
                
                print(f"\n[PROCESSING] NIM: {voter_id}")
                
                # STEP 1: Decrypt vote menggunakan RSA
                decrypted_json = rsa_decryptor.decrypt(encrypted_vote)
                print(f"[DEBUG] Decrypted JSON: {decrypted_json}")
                
                # STEP 2: Hash hasil decrypt
                decrypted_hash = hash_message(decrypted_json)
                print(f"[DEBUG] Decrypted hash: {decrypted_hash}")
                
                # STEP 3: Ambil hash yang tersimpan di database
                stored_hash = hash_records.get(voter_id)
                print(f"[DEBUG] Stored hash: {stored_hash}")
                
                # Validasi 1: Cek apakah hash ada di database verify
                if stored_hash is None:
                    missing_hash.append({
                        "nim": voter_id,
                        "reason": "Hash tidak ditemukan di database verify_vote"
                    })
                    print(f"[WARNING] Hash not found for NIM {voter_id}")
                    continue
                
                # Validasi 2: Bandingkan hash hasil decrypt dengan yang tersimpan
                if decrypted_hash != stored_hash:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": "Hash mismatch - Data vote telah berubah",
                        "computed_hash": decrypted_hash,
                        "stored_hash": stored_hash
                    })
                    print(f"[ALERT] Hash mismatch for NIM {voter_id}")
                    continue
                
                # Validasi 3: Parse JSON dan cek konsistensi NIM
                vote_data = json.loads(decrypted_json)
                
                if vote_data.get("nim") != voter_id:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": f"NIM mismatch - Data untuk {vote_data.get('nim')}"
                    })
                    print(f"[ALERT] NIM mismatch for {voter_id}")
                    continue
                
                # Jika semua validasi lolos, vote dianggap valid
                valid_votes.append({
                    "nim": voter_id,
                    "kandidat": vote_data["kandidat"],
                    "nama": vote_data["nama"]
                })
                kandidat_list.append(vote_data["kandidat"])
                print(f"[VALID] ✅ {voter_id} -> Kandidat {vote_data['kandidat']}")

            except Exception as e:
                print(f"[ERROR] Failed to process {voter_id}: {e}")
                invalid_votes.append({
                    "nim": voter_id,
                    "reason": f"Error: {str(e)}"
                })

        # Hitung perolehan suara menggunakan Counter
        counter = Counter(kandidat_list)

        # Susun hasil akhir
        result = {
            "total_valid": len(valid_votes),
            "total_invalid": len(invalid_votes),
            "total_missing_hash": len(missing_hash),
            "total_votes": len(rows),
            "hasil": dict(counter),
            "valid_voters": [v["nim"] for v in valid_votes],
            "invalid_votes": invalid_votes,
            "missing_hash": missing_hash
        }

        # Logging summary untuk monitoring
        print(f"\n=== RECAP SUMMARY ===")
        print(f"[RESULT] Valid votes: {result['total_valid']}")
        print(f"[RESULT] Invalid votes: {result['total_invalid']}")
        print(f"[RESULT] Missing hash: {result['total_missing_hash']}")
        print(f"[RESULT] Total processed: {result['total_votes']}")
        print(f"[RESULT] Vote distribution: {dict(counter)}")

        return result

    except Exception as e:
        print(f"[CRITICAL] Recap error: {e}")
        return {
            "error": str(e), 
            "total_valid": 0, 
            "total_invalid": 0, 
            "total_missing_hash": 0, 
            "hasil": {}
        }

    finally:
        # Selalu tutup koneksi database
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()

# ================================================================
# ENDPOINT 4: CEK STATUS VOTE
# ================================================================

@app.get("/check-vote-status/{nim}")
def check_vote_status(nim: str):
    """
    Endpoint untuk mengecek apakah seorang user sudah melakukan vote.
    Digunakan oleh frontend untuk menentukan apakah form vote ditampilkan.
    
    Args:
        nim (str): NIM user yang ingin dicek
    
    Returns:
        dict: {
            "has_voted": bool,  # True jika sudah vote
            "nim": str         # NIM yang dicek
        }
    
    Contoh:
        GET /check-vote-status/12345
        Response: {"has_voted": true, "nim": "12345"}
    """
    conn = get_conn_vote()
    cur = conn.cursor()
    
    try:
        # Query ke database votedata
        cur.execute("SELECT voter_id FROM uservote WHERE voter_id = %s", (nim,))
        result = cur.fetchone()
        
        return {
            "has_voted": result is not None,
            "nim": nim
        }
    finally:
        cur.close()
        conn.close()

# ================================================================
# ENDPOINT 5: VERIFIKASI SEMUA HASH (ADMIN AUDIT)
# ================================================================

@app.get("/verify-all-hashes")
def verify_all_hashes():
    """
    Endpoint untuk audit dan verifikasi semua hash yang tersimpan.
    Berguna untuk mendeteksi manipulasi data secara massal.
    
    Proses:
        1. Ambil semua vote dari votedata
        2. Decrypt dan hitung ulang hash setiap vote
        3. Bandingkan dengan hash di verify_vote.hashing
        4. Kategorikan hasil: valid, invalid, missing
    
    Returns:
        dict: {
            "total": int,        # Total vote yang diperiksa
            "valid": int,        # Jumlah hash yang cocok
            "invalid": list,     # Daftar NIM dengan hash mismatch
            "missing": list      # Daftar NIM tanpa hash di verify_db
        }
    
    Note:
        - Endpoint ini sebaiknya hanya bisa diakses oleh ADMIN
        - Digunakan untuk audit berkala atau troubleshooting
    """
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()
    
    results = {
        "total": 0,
        "valid": 0,
        "invalid": [],   # List NIM yang hash-nya tidak cocok
        "missing": []    # List NIM yang tidak punya hash di verify_db
    }
    
    try:
        # Ambil semua vote
        cur_vote.execute("SELECT voter_id, vote FROM uservote")
        votes = cur_vote.fetchall()
        
        # Ambil semua hash yang tersimpan
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        hashes = dict(cur_verify.fetchall())
        
        rsa_decryptor = RSAEncryptor()
        
        print(f"\n=== VERIFY ALL HASHES START ===")
        print(f"[INFO] Total votes to verify: {len(votes)}")
        print(f"[INFO] Total hashes in verify DB: {len(hashes)}")
        
        for voter_id, encrypted_vote in votes:
            results["total"] += 1
            
            # Konversi format jika perlu
            if isinstance(encrypted_vote, memoryview):
                encrypted_vote = encrypted_vote.tobytes()
            
            try:
                # Decrypt dan hitung hash ulang
                decrypted = rsa_decryptor.decrypt(encrypted_vote)
                computed_hash = hash_message(decrypted)
                
                # Verifikasi
                if voter_id not in hashes:
                    results["missing"].append(voter_id)
                    print(f"[MISSING] No hash for NIM {voter_id}")
                elif computed_hash != hashes[voter_id]:
                    results["invalid"].append(voter_id)
                    print(f"[INVALID] Hash mismatch for NIM {voter_id}")
                else:
                    results["valid"] += 1
                    print(f"[VALID] NIM {voter_id} verified")
                    
            except Exception as e:
                print(f"[ERROR] Failed to verify {voter_id}: {e}")
                results["invalid"].append(voter_id)
        
        print(f"\n=== VERIFICATION SUMMARY ===")
        print(f"[RESULT] Valid: {results['valid']}/{results['total']}")
        print(f"[RESULT] Invalid: {len(results['invalid'])}")
        print(f"[RESULT] Missing: {len(results['missing'])}")
        
        return results
        
    finally:
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()