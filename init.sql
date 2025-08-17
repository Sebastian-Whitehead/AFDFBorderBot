-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    steam_id TEXT NOT NULL,
    discord_id TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enlisted_at TIMESTAMP,
    money DECIMAL(15,2) DEFAULT 0,
    rank INTEGER DEFAULT 0,
    notes TEXT,
    achievements TEXT[],
    last_death DATE,
    deaths INTEGER DEFAULT 0,
    reprimands JSONB,
    extra_data JSONB
);

-- Create bot_settings table for storing configuration
CREATE TABLE bot_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries on setting_key
CREATE INDEX idx_bot_settings_key ON bot_settings(setting_key);

-- Create LOA (Leave of Absence) table
CREATE TABLE loa_requests (
    id SERIAL PRIMARY KEY,
    discord_id TEXT NOT NULL,
    username TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries on discord_id and status
CREATE INDEX idx_loa_discord_id ON loa_requests(discord_id);
CREATE INDEX idx_loa_status ON loa_requests(status);
CREATE INDEX idx_loa_end_date ON loa_requests(end_date);


-- Create transaction_log table
CREATE TABLE transaction_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    from_user_id TEXT,  -- NULL for system transactions (earning money)
    to_user_id TEXT,    -- Can be discord_id or character name for in-universe transactions
    amount DECIMAL(15,2) NOT NULL,
    transaction_type TEXT NOT NULL,  -- 'payment', 'casino', 'stock_market', 'salary', 'fine', 'transfer', etc.
    description TEXT,   -- Optional description of the transaction
    processed BOOLEAN DEFAULT FALSE,  -- Whether the transaction has been processed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX idx_transaction_log_from_user ON transaction_log(from_user_id);
CREATE INDEX idx_transaction_log_to_user ON transaction_log(to_user_id);
CREATE INDEX idx_transaction_log_type ON transaction_log(transaction_type);
CREATE INDEX idx_transaction_log_timestamp ON transaction_log(timestamp);
CREATE INDEX idx_transaction_log_processed ON transaction_log(processed);

-- Insert sample data
INSERT INTO users (name, steam_id, discord_id, rank, notes, extra_data) 
VALUES 
    ('senwk', '76561198070202465', '805449866971971594', 9, 'President - Special rank', NULL),
    ('Parz1val', '76561198150696236', '142876809992601601', 3, 'Head of medical department', NULL);

-- Insert default bot settings
INSERT INTO bot_settings (setting_key, setting_value) 
VALUES 
    ('listen-for-join-leave', 'true'),
    ('listen-for-border-officer', 'true'),
    ('listen-for-event-start', 'false');
