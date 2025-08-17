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

-- Create characters table
-- CREATE TABLE characters (
--     id SERIAL PRIMARY KEY,
--     user_character BOOLEAN,
--     first_name TEXT,
--     last_name TEXT,
--     date_of_birth DATE,
--     control_date DATE,
--     money DECIMAL(15,2),
--     family TEXT[],
--     notes TEXT,
--     additional JSONB
-- );

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
