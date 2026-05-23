from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from RSA import RSAEncryptor
from hashing import hash_message
import psycopg2
from psycopg2 import Binary
from collections import Counter
import json
###JANGAN DIHAPUS, INI UNTUK GENERATE KEY RSA, JALANKAN SEKALI SAJA LALU HAPUS FILE PEMNYA
#import RSA_key_gen 


##SETUP FASTAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
##-----------------------------------------
##TAHP 1: Menerima data vote dari frontend lalu menyimpan ke database
##-----------------------------------------
@app.post("/login")
def login(data: LoginRequest):

    conn = get_conn_login()
    cur = conn.cursor()

    cur.execute(
        "SELECT passw, status FROM users WHERE nim = %s",
        (data.nim,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return {"success": False, "message": "User tidak ditemukan"}

    db_password, status = user

    if data.password == db_password:
        return {
            "success": True,
            "message": "Login berhasil",
            "status": status   # 👈 penting
        }

    return {"success": False, "message": "Password salah"}
    

@app.post("/vote")
def submit_vote(vote: Vote):
    #Melakukan enkripsi pada data vote yang diterima dari frontend + oeap
    encrypted_vote = RSAEncryptor().encrypt(
        vote.model_dump_json()
    )
    #Menghitung hash dari data vote yang sudah diencrypt, digunakan untuk verifikasi hasil vote
    vote_hash = hash_message(encrypted_vote)

    conn = get_conn_vote()
    conn1 = get_conn_verify()

    cur = conn.cursor()
    cur1 = conn1.cursor()

    try:
        # insert ke database uservote, menyimpan data vote yang sudah diencrypt beserta hashnya
        cur.execute(
            "INSERT INTO userVote (voter_id, vote, vote_hash) VALUES (%s, %s, %s)",
            (vote.nim, Binary(encrypted_vote), vote_hash)
        )

        # insert ke database hashing, menyimpan hash dari data vote yang sudah diencrypt, digunakan untuk verifikasi hasil vote
        cur1.execute(
            "INSERT INTO hashing (vote_id, hash) VALUES (%s, %s)",
            (vote.nim, vote_hash)
        )

        conn.commit()
        conn1.commit()

        return {"message": "success"}

    except Exception as e:
        conn.rollback()
        conn1.rollback()
        return {"error": str(e)}

    finally:
        cur.close()
        cur1.close()
        conn.close()
        conn1.close()


##-----------------------------------------
##TAHP 2: REKAP HASIL VOTE, MENGAMBIL DATA DARI DATABASE, DECRYPT, DAN MENGHITUNG HASILNYA
##-----------------------------------------
@app.get("/recap")
def recap_vote():

    conn = get_conn_vote()
    cur = conn.cursor()

    try:
        cur.execute("SELECT vote FROM uservote")
        rows = cur.fetchall()

        decryptor = RSAEncryptor()
        kandidat_list = []

        for (encrypted_vote,) in rows:

            try:
                if isinstance(encrypted_vote, memoryview):
                    encrypted_vote = encrypted_vote.tobytes()

                decrypted = decryptor.decrypt(encrypted_vote)

                data = json.loads(decrypted)
                kandidat_list.append(data["kandidat"])

            except Exception as e:
                print("decrypt error:", e)
                continue

        counter = Counter(kandidat_list)

        return {
            "total": sum(counter.values()),
            "hasil": dict(counter)
        }

    finally:
        cur.close()
        conn.close()