CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(40) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL UNIQUE,
    file_path VARCHAR(500) NOT NULL,
    extracted_text TEXT,
    executive_summary TEXT,
    agreement_type VARCHAR(255),
    key_parties TEXT,
    business_purpose TEXT,
    effective_date VARCHAR(120),
    expiry_date VARCHAR(120),
    contract_value VARCHAR(255),
    risk_score INTEGER,
    risks JSON,
    alerts JSON,
    timeline JSON,
    compliance JSON,
    negotiation JSON,
    analysis_status VARCHAR(40) NOT NULL DEFAULT 'pending',
    analysis_error TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analyzed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_contracts_user_id ON contracts (user_id);
CREATE INDEX IF NOT EXISTS ix_contracts_created_at ON contracts (created_at);
