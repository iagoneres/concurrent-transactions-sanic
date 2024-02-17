-- Create tables
CREATE UNLOGGED TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    balance INTEGER NOT NULL,
    "limit" INTEGER NOT NULL
);

CREATE UNLOGGED TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) NOT NULL,
    value INTEGER NOT NULL,
    type CHAR(1) NOT NULL,
    description VARCHAR(10) NOT NULL,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_client_performed ON transactions (client_id, performed_at DESC);

-- Clean Tables
TRUNCATE clients CASCADE;
TRUNCATE transactions CASCADE;

-- Populate tables
INSERT INTO clients (id, "limit", balance)
VALUES
    (1, 100000, 0),
    (2, 80000, 0),
    (3, 1000000, 0),
    (4, 10000000, 0),
    (5, 500000, 0)
ON CONFLICT (id) DO NOTHING;
