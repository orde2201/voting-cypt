-- ============================================================
-- INIT.SQL - Database Initialization Script
-- ============================================================
-- Script ini akan dijalankan otomatis saat container PostgreSQL pertama kali dibuat
-- Membuat 3 database: votedata, verify_vote, userdata
-- ============================================================

-- ============================================================
-- 1. CREATE DATABASES
-- ============================================================

-- Database untuk menyimpan vote terenkripsi
CREATE DATABASE votedata;

-- Database untuk menyimpan hash verifikasi
CREATE DATABASE verify_vote;

-- Database untuk menyimpan data user
CREATE DATABASE userdata;

-- ============================================================
-- 2. SETUP VOTEDATA DATABASE
-- ============================================================

\c votedata;

-- Tabel untuk menyimpan vote yang sudah dienkripsi
CREATE TABLE uservote (
    voter_id VARCHAR(50) PRIMARY KEY,     -- NIM sebagai unique identifier
    vote BYTEA NOT NULL,                   -- Data vote yang sudah dienkripsi (RSA-OAEP)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Waktu vote dibuat
);

-- Index untuk mempercepat query
CREATE INDEX idx_uservote_created_at ON uservote(created_at);

-- Komentar tabel dan kolom untuk dokumentasi
COMMENT ON TABLE uservote IS 'Menyimpan data vote yang sudah dienkripsi dengan RSA-OAEP';
COMMENT ON COLUMN uservote.voter_id IS 'NIM voter (unique identifier)';
COMMENT ON COLUMN uservote.vote IS 'Data vote yang sudah dienkripsi (format BYTEA)';
COMMENT ON COLUMN uservote.created_at IS 'Timestamp saat vote dibuat';

-- ============================================================
-- 3. SETUP VERIFY_VOTE DATABASE
-- ============================================================

\c verify_vote;

-- Tabel untuk menyimpan hash dari data vote ASLI (sebelum enkripsi)
CREATE TABLE hashing (
    vote_id VARCHAR(50) PRIMARY KEY,      -- NIM sebagai reference ke votedata
    hash TEXT NOT NULL,                    -- SHA-256 hash dari data asli
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Waktu hash dibuat
);

-- Index untuk mempercepat query
CREATE INDEX idx_hashing_created_at ON hashing(created_at);

-- Komentar tabel dan kolom
COMMENT ON TABLE hashing IS 'Menyimpan hash dari data vote asli untuk verifikasi integritas';
COMMENT ON COLUMN hashing.vote_id IS 'NIM voter (reference ke uservote.voter_id)';
COMMENT ON COLUMN hashing.hash IS 'SHA-256 hash dari data vote ASLI (sebelum enkripsi)';
COMMENT ON COLUMN hashing.created_at IS 'Timestamp saat hash dibuat';

-- ============================================================
-- 4. SETUP USERDATA DATABASE
-- ============================================================

\c userdata;

-- Tabel untuk menyimpan data user (autentikasi)
CREATE TABLE users (
    nim VARCHAR(50) PRIMARY KEY,          -- NIM sebagai primary key
    name VARCHAR(255) NOT NULL,            -- Nama lengkap user
    password VARCHAR(100) NOT NULL,        -- Password (plain text untuk demo)
    status VARCHAR(20) NOT NULL,           -- Role: 'admin' atau 'student'
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Waktu akun dibuat
);

-- Index untuk mempercepat query login
CREATE INDEX idx_users_nim ON users(nim);
CREATE INDEX idx_users_status ON users(status);

-- Komentar tabel dan kolom
COMMENT ON TABLE users IS 'Menyimpan data user untuk autentikasi login';
COMMENT ON COLUMN users.nim IS 'Nomor Induk Mahasiswa (unique identifier)';
COMMENT ON COLUMN users.name IS 'Nama lengkap user';
COMMENT ON COLUMN users.password IS 'Password user (plain text untuk demo - sebaiknya di-hash di production)';
COMMENT ON COLUMN users.status IS 'Role user: admin (akses recap) atau student (hanya vote)';
COMMENT ON COLUMN users.create_time IS 'Timestamp akun dibuat';

-- ============================================================
-- 5. INSERT DUMMY DATA FOR TESTING
-- ============================================================

-- Data dummy untuk login
-- nim 231010001-231010010
-- 1 admin + 9 student
INSERT INTO users (nim, name, password, status) VALUES
('231010001', 'Andi Pratama', 'admin123', 'admin'),
('231010002', 'Budi Santoso', 'pass123', 'student'),
('231010003', 'Citra Lestari', 'pass123', 'student'),
('231010004', 'Dewi Anggraini', 'pass123', 'student'),
('231010005', 'Eko Saputra', 'pass123', 'student'),
('231010006', 'Fajar Nugroho', 'pass123', 'student'),
('231010007', 'Gita Ramadhani', 'pass123', 'student'),
('231010008', 'Hendra Wijaya', 'pass123', 'student'),
('231010009', 'Intan Permata', 'pass123', 'student'),
('231010010', 'Joko Susilo', 'pass123', 'student');

-- ============================================================
-- 6. VERIFIKASI DATA (Optional - untuk debug)
-- ============================================================

\c userdata;
-- Tampilkan jumlah users yang berhasil di-insert
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    RAISE NOTICE '✅ Database initialized successfully!';
    RAISE NOTICE '📊 Total users inserted: %', user_count;
    RAISE NOTICE '👑 Admin: 1 (nim: 231010001)';
    RAISE NOTICE '🎓 Students: 9';
END $$;

-- ============================================================
-- 7. GRANT PERMISSIONS (Opsional untuk production)
-- ============================================================

-- Memberikan hak akses ke user postgres (default)
-- \c votedata;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;

-- \c verify_vote;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;

-- \c userdata;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;