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

##SETUP FASTAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

##SETUP DATABASE CONNECTION
def get_conn_vote():
    return psycopg2.connect(
        dbname="votedata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

def get_conn_verify():
    return psycopg2.connect(
        dbname="verify_vote",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

def get_conn_login():
    return psycopg2.connect(
        dbname="userdata",
        user="postgres",
        password="postgres",
        host="db1",
        port="5432"
    )

class Vote(BaseModel):
    nama: str
    nim: str
    kandidat: str

class LoginRequest(BaseModel):
    nim: str
    password: str

##-----------------------------------------
## HELPER FUNCTION UNTUK HANDLE BYTES KE STRING
##-----------------------------------------
def bytes_to_string(data):
    """Convert bytes/memoryview to string for hashing"""
    if isinstance(data, memoryview):
        data = data.tobytes()
    if isinstance(data, bytes):
        # Encode bytes to base64 string for consistent hashing
        return base64.b64encode(data).decode('utf-8')
    if isinstance(data, str):
        return data
    return str(data)

##-----------------------------------------
## TAHAP 1: LOGIN
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

##-----------------------------------------
## TAHAP 2: VOTE (Hash data asli, lalu encrypt)
##-----------------------------------------
@app.post("/vote")
def submit_vote(vote: Vote):
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
                "message": "Anda sudah melakukan vote sebelumnya!"
            }
        
        # Cek apakah NIM terdaftar
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
        
        # STEP 1: Buat JSON string dari data vote
        vote_json = vote.model_dump_json()
        print(f"Original vote JSON: {vote_json}")  # Debug
        
        # STEP 2: Hashing data ASLI (sebelum encrypt) - pastikan dalam bentuk string
        original_hash = hash_message(vote_json)  # vote_json sudah string
        print(f"Original hash: {original_hash}")  # Debug
        
        # STEP 3: Enkripsi data vote asli (hasilkan bytes)
        rsa_encryptor = RSAEncryptor()
        encrypted_vote = rsa_encryptor.encrypt(vote_json)
        print(f"Encrypted vote type: {type(encrypted_vote)}")  # Debug

        conn_verify = get_conn_verify()
        cur_verify = conn_verify.cursor()

        try:
            # STEP 4: Simpan encrypted vote ke database (sebagai bytes)
            cur_vote.execute(
                "INSERT INTO userVote (voter_id, vote) VALUES (%s, %s)",
                (vote.nim, Binary(encrypted_vote))
            )

            # STEP 5: Simpan hash asli ke database verify_vote
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
            conn_vote.rollback()
            conn_verify.rollback()
            print(f"Database error: {e}")
            return {"success": False, "error": str(e)}

        finally:
            cur_verify.close()
            conn_verify.close()

    except Exception as e:
        print(f"Vote error: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        cur_vote.close()
        conn_vote.close()

##-----------------------------------------
## TAHAP 3: RECAP (Decrypt, hash hasil decrypt, bandingkan)
##-----------------------------------------
@app.get("/recap")
def recap_vote():
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()

    valid_votes: List[Dict[str, Any]] = []
    invalid_votes: List[Dict[str, Any]] = []
    missing_hash: List[Dict[str, Any]] = []
    kandidat_list = []

    try:
        # Ambil semua data vote
        cur_vote.execute("SELECT voter_id, vote FROM uservote")
        rows = cur_vote.fetchall()

        # Ambil semua hash dari database verifikasi
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        hash_records = {vote_id: hash_val for vote_id, hash_val in cur_verify.fetchall()}

        rsa_decryptor = RSAEncryptor()

        print(f"\n=== RECAP PROCESS ===")
        print(f"Total votes in DB: {len(rows)}")
        print(f"Total hashes in verify DB: {len(hash_records)}")

        for voter_id, encrypted_vote in rows:
            try:
                # Convert memoryview to bytes if needed
                if isinstance(encrypted_vote, memoryview):
                    encrypted_vote = encrypted_vote.tobytes()
                
                print(f"\nProcessing NIM: {voter_id}")
                
                # STEP 1: Decrypt encrypted vote (hasil decrypt adalah string JSON)
                decrypted_json = rsa_decryptor.decrypt(encrypted_vote)
                print(f"Decrypted JSON: {decrypted_json}")
                
                # STEP 2: Hash hasil decrypt (string JSON)
                decrypted_hash = hash_message(decrypted_json)
                print(f"Decrypted hash: {decrypted_hash}")
                
                # STEP 3: Ambil hash yang tersimpan di database
                stored_hash = hash_records.get(voter_id)
                print(f"Stored hash: {stored_hash}")
                
                if stored_hash is None:
                    missing_hash.append({
                        "nim": voter_id,
                        "reason": "Hash tidak ditemukan di database verify_vote"
                    })
                    continue
                
                # STEP 4: Bandingkan hash
                if decrypted_hash != stored_hash:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": "Hash mismatch - Data vote telah berubah",
                        "computed_hash": decrypted_hash,
                        "stored_hash": stored_hash
                    })
                    continue
                
                # STEP 5: Parse JSON dan validasi
                vote_data = json.loads(decrypted_json)
                
                if vote_data.get("nim") != voter_id:
                    invalid_votes.append({
                        "nim": voter_id,
                        "reason": f"NIM mismatch - Data untuk {vote_data.get('nim')}"
                    })
                    continue
                
                # Vote valid
                valid_votes.append({
                    "nim": voter_id,
                    "kandidat": vote_data["kandidat"],
                    "nama": vote_data["nama"]
                })
                kandidat_list.append(vote_data["kandidat"])
                print(f"✅ VALID: {voter_id} -> {vote_data['kandidat']}")

            except Exception as e:
                print(f"❌ Error: {e}")
                invalid_votes.append({
                    "nim": voter_id,
                    "reason": f"Error: {str(e)}"
                })

        counter = Counter(kandidat_list)

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

        print(f"\n=== SUMMARY ===")
        print(f"Valid: {result['total_valid']}")
        print(f"Invalid: {result['total_invalid']}")
        print(f"Missing: {result['total_missing_hash']}")

        return result

    except Exception as e:
        print(f"Recap error: {e}")
        return {"error": str(e), "total_valid": 0, "total_invalid": 0, "total_missing_hash": 0, "hasil": {}}

    finally:
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()

##-----------------------------------------
## ENDPOINT CEK STATUS VOTE
##-----------------------------------------
@app.get("/check-vote-status/{nim}")
def check_vote_status(nim: str):
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
## ENDPOINT VERIFIKASI SEMUA HASH
##-----------------------------------------
@app.get("/verify-all-hashes")
def verify_all_hashes():
    conn_vote = get_conn_vote()
    conn_verify = get_conn_verify()
    
    cur_vote = conn_vote.cursor()
    cur_verify = conn_verify.cursor()
    
    results = {
        "total": 0,
        "valid": 0,
        "invalid": [],
        "missing": []
    }
    
    try:
        cur_vote.execute("SELECT voter_id, vote FROM uservote")
        votes = cur_vote.fetchall()
        
        cur_verify.execute("SELECT vote_id, hash FROM hashing")
        hashes = dict(cur_verify.fetchall())
        
        rsa_decryptor = RSAEncryptor()
        
        for voter_id, encrypted_vote in votes:
            results["total"] += 1
            
            if isinstance(encrypted_vote, memoryview):
                encrypted_vote = encrypted_vote.tobytes()
            
            try:
                decrypted = rsa_decryptor.decrypt(encrypted_vote)
                computed_hash = hash_message(decrypted)
                
                if voter_id not in hashes:
                    results["missing"].append(voter_id)
                elif computed_hash != hashes[voter_id]:
                    results["invalid"].append(voter_id)
                else:
                    results["valid"] += 1
            except Exception as e:
                results["invalid"].append(voter_id)
        
        return results
        
    finally:
        cur_vote.close()
        cur_verify.close()
        conn_vote.close()
        conn_verify.close()