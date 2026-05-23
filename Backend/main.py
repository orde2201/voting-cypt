from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from RSA import RSAEncryptor
from hashing import hash_message
import psycopg2
from psycopg2 import Binary
from collections import Counter
import json
from typing import Dict, List, Any

###JANGAN DIHAPUS, INI UNTUK GENERATE KEY RSA, JALANKAN SEKALI SAJA LALU HAPUS FILE PEMNYA
#import RSA_key_gen 

##SETUP FASTAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Tambahkan port Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

##SETUP DATABASE CONNECTION
##database untuk menampung vote yang sudah diencrypt dan hashnya
def get_conn_vote():
    return psycopg2.connect(
        dbname="votedata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

##database untuk menampung hash dari vote yang sudah diencrypt, digunakan untuk verifikasi hasil vote
def get_conn_verify():
    return psycopg2.connect(
        dbname="verify_vote",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

##database untuk menampung data user, digunakan untuk login
def get_conn_login():
    return psycopg2.connect(
        dbname="userdata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

##Tempat variabel yang digunakan untuk menyimpan data vote dari frontend
class Vote(BaseModel):
    nama: str
    nim: str
    kandidat: str

class LoginRequest(BaseModel):
    nim: str
    password: str

# Store login session (in production, use JWT token or Redis)
# Untuk demo sederhana, kita simpan sementara
active_sessions: Dict[str, str] = {}  # {nim: status}

##-----------------------------------------
## TAHAP 1: Menerima data vote dari frontend lalu menyimpan ke database
##-----------------------------------------
@app.post("/login")
def login(data: LoginRequest):
    conn = get_conn_login()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT passw, status FROM users WHERE nim = %s",
            (data.nim,)
        )

        user = cur.fetchone()

        if not user:
            return {"success": False, "message": "User tidak ditemukan"}

        db_password, status = user

        if data.password == db_password:
            # Simpan session (dalam production pake JWT)
            # Untuk sekarang, kita return nim dan status
            return {
                "success": True,
                "message": "Login berhasil",
                "status": status,
                "nim": data.nim  # Kirim nim kembali ke frontend
            }

        return {"success": False, "message": "Password salah"}
    
    finally:
        cur.close()
        conn.close()

@app.post("/vote")
def submit_vote(vote: Vote):
    # Validasi 1: Cek apakah NIM sudah pernah melakukan vote
    conn_vote = get_conn_vote()
    cur_vote = conn_vote.cursor()
    
    try:
        # Cek apakah NIM sudah pernah vote
        cur_vote.execute(
            "SELECT voter_id FROM userVote WHERE voter_id = %s",
            (vote.nim,)
        )
        existing_vote = cur_vote.fetchone()
        
        if existing_vote:
            return {
                "success": False, 
                "message": "Anda sudah melakukan vote sebelumnya! Tidak dapat vote lagi."
            }
        
        # Validasi 2: Cek apakah NIM terdaftar di database user
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
        
        # Proses vote jika validasi berhasil
        # Melakukan enkripsi pada data vote yang diterima dari frontend
        encrypted_vote = RSAEncryptor().encrypt(
            vote.model_dump_json()
        )
        
        # Menghitung hash dari data vote yang sudah diencrypt
        vote_hash = hash_message(encrypted_vote)

        conn_verify = get_conn_verify()
        cur_verify = conn_verify.cursor()

        try:
            # Insert ke database uservote, menyimpan data vote yang sudah diencrypt beserta hashnya
            cur_vote.execute(
                "INSERT INTO userVote (voter_id, vote, vote_hash) VALUES (%s, %s, %s)",
                (vote.nim, Binary(encrypted_vote), vote_hash)
            )

            # Insert ke database hashing, menyimpan hash dari data vote yang sudah diencrypt
            cur_verify.execute(
                "INSERT INTO hashing (vote_id, hash) VALUES (%s, %s)",
                (vote.nim, vote_hash)
            )

            conn_vote.commit()
            conn_verify.commit()

            return {
                "success": True, 
                "message": "Vote berhasil dikirim",
                "vote_hash": vote_hash
            }

        except Exception as e:
            conn_vote.rollback()
            conn_verify.rollback()
            return {"success": False, "error": str(e)}

        finally:
            cur_verify.close()
            conn_verify.close()

    except Exception as e:
        return {"success": False, "error": str(e)}
    
    finally:
        cur_vote.close()
        conn_vote.close()


##-----------------------------------------
## TAHAP 2: REKAP HASIL VOTE DENGAN VALIDASI HASH
##-----------------------------------------
@app.get("/recap")
def recap_vote():
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()

    # Untuk menyimpan hasil yang valid dan yang bermasalah
    valid_votes: List[str] = []
    invalid_votes: List[Dict[str, Any]] = []
    kandidat_list = []

    try:
        # Ambil semua data vote
        cur_vote.execute("SELECT voter_id, vote, vote_hash FROM uservote")
        rows = cur_vote.fetchall()

        # Ambil semua hash dari database verifikasi
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        hash_records = {vote_id: hash_val for vote_id, hash_val in cur_verify.fetchall()}

        decryptor = RSAEncryptor()

        for voter_id, encrypted_vote, stored_hash in rows:
            try:
                # Handle memoryview conversion
                if isinstance(encrypted_vote, memoryview):
                    encrypted_vote = encrypted_vote.tobytes()

                # Validasi hash: bandingkan hash yang tersimpan dengan hash dari database verifikasi
                expected_hash = hash_records.get(voter_id)
                
                if stored_hash != expected_hash:
                    # Hash tidak cocok - data telah dimanipulasi
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": "Hash mismatch - Data telah dimanipulasi",
                        "stored_hash": stored_hash,
                        "expected_hash": expected_hash
                    })
                    print(f"WARNING: Hash mismatch untuk NIM {voter_id}")
                    continue
                
                # Re-verify hash dari encrypted vote saat ini
                current_hash = hash_message(encrypted_vote)
                if current_hash != stored_hash:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": "Hash verification failed - Encrypted vote telah berubah",
                        "stored_hash": stored_hash,
                        "current_hash": current_hash
                    })
                    print(f"WARNING: Hash verification failed untuk NIM {voter_id}")
                    continue

                # Jika hash valid, decrypt dan hitung vote
                decrypted = decryptor.decrypt(encrypted_vote)
                data = json.loads(decrypted)
                
                # Validasi tambahan: cek apakah NIM dalam vote sama dengan voter_id
                if data.get("nim") != voter_id:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": f"NIM mismatch - Vote untuk NIM {data.get('nim')} tapi disimpan sebagai {voter_id}"
                    })
                    continue
                
                # Jika semua validasi lolos
                valid_votes.append(voter_id)
                kandidat_list.append(data["kandidat"])

            except Exception as e:
                invalid_votes.append({
                    "nim": voter_id,
                    "reason": f"Decryption/Parse error: {str(e)}"
                })
                print(f"Error processing vote for {voter_id}: {e}")
                continue

        # Hitung hasil dari vote yang valid
        counter = Counter(kandidat_list)

        result = {
            "total_valid": len(valid_votes),
            "total_invalid": len(invalid_votes),
            "total_votes": len(valid_votes) + len(invalid_votes),
            "hasil": dict(counter),
            "valid_voters": valid_votes,
            "invalid_votes": invalid_votes  # Informasi NIM yang bermasalah
        }

        # Jika ada vote yang tidak valid, tampilkan peringatan
        if invalid_votes:
            print(f"PERINGATAN: Ditemukan {len(invalid_votes)} vote yang tidak valid!")
            for inv in invalid_votes:
                print(f"  - NIM {inv['nim']}: {inv['reason']}")

        return result

    except Exception as e:
        return {"error": str(e), "total_valid": 0, "total_invalid": 0, "hasil": {}}

    finally:
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()

##-----------------------------------------
## ENDPOINT TAMBAHAN UNTUK CEK STATUS VOTE
##-----------------------------------------
@app.get("/check-vote-status/{nim}")
def check_vote_status(nim: str):
    """Cek apakah NIM sudah melakukan vote"""
    conn = get_conn_vote()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT voter_id FROM uservote WHERE voter_id = %s", (nim,))
        result = cur.fetchone()
        
        return {
            "has_voted": result is not None,
            "nim": nim
        }
    finally:
        cur.close()
        conn.close()

##-----------------------------------------
## ENDPOINT UNTUK VERIFIKASI MANUAL (ADMIN)
##-----------------------------------------
@app.get("/verify-all-hashes")
def verify_all_hashes():
    """Verifikasi semua hash untuk keperluan audit"""
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()
    
    verification_results = {
        "total_checked": 0,
        "valid": 0,
        "invalid": [],
        "missing_in_verify_db": []
    }
    
    try:
        cur_vote.execute("SELECT voter_id, vote, vote_hash FROM uservote")
        votes = cur_vote.fetchall()
        
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        verify_records = dict(cur_verify.fetchall())
        
        for voter_id, encrypted_vote, stored_hash in votes:
            verification_results["total_checked"] += 1
            
            if voter_id not in verify_records:
                verification_results["missing_in_verify_db"].append(voter_id)
                continue
            
            expected_hash = verify_records[voter_id]
            
            if stored_hash != expected_hash:
                verification_results["invalid"].append({
                    "nim": voter_id,
                    "stored": stored_hash,
                    "expected": expected_hash
                })
            else:
                # Re-verify current hash
                if isinstance(encrypted_vote, memoryview):
                    encrypted_vote = encrypted_vote.tobytes()
                current_hash = hash_message(encrypted_vote)
                
                if current_hash != stored_hash:
                    verification_results["invalid"].append({
                        "nim": voter_id,
                        "reason": "Current hash mismatch",
                        "stored": stored_hash,
                        "current": current_hash
                    })
                else:
                    verification_results["valid"] += 1
        
        return verification_results
        
    finally:
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()