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
