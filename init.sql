CREATE DATABASE votedata;
CREATE DATABASE verify_vote;

\c votedata;

CREATE TABLE uservote (
    voter_id VARCHAR(50) PRIMARY KEY,
    vote BYTEA,
    vote_hash TEXT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

\c verify_vote;

CREATE TABLE hashing (
    vote_id VARCHAR(50) PRIMARY KEY,
    hash TEXT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


##data login dari intansi
CREATE DATABASE userdata;
CREATE TABLE users (
    nim VARCHAR(50) PRIMARY KEY,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    name VARCHAR(255),
    status VARCHAR(50)
);
###Data dummy untuk login, nim 231010001-231010010, nama sesuai nim, status aktif untuk nim ganjil dan nonaktif untuk nim genap
INSERT INTO users (nim, name, status, password) VALUES
('231010001', 'Andi Pratama', 'admin', 'admin123'),
('231010002', 'Budi Santoso', 'student', 'pass123'),
('231010003', 'Citra Lestari', 'student', 'pass123'),
('231010004', 'Dewi Anggraini', 'student', 'pass123'),
('231010005', 'Eko Saputra', 'student', 'pass123'),
('231010006', 'Fajar Nugroho', 'student', 'pass123'),
('231010007', 'Gita Ramadhani', 'student', 'pass123'),
('231010008', 'Hendra Wijaya', 'student', 'pass123'),
('231010009', 'Intan Permata', 'student', 'pass123'),
('231010010', 'Joko Susilo', 'student', 'pass123');