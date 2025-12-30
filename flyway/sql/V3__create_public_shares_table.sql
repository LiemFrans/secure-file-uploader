CREATE TABLE public_shares (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES html_files(id) ON DELETE CASCADE,
    share_token VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_public_shares_share_token ON public_shares(share_token);
CREATE INDEX idx_public_shares_file_id ON public_shares(file_id);
CREATE INDEX idx_public_shares_expires_at ON public_shares(expires_at);
