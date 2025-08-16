-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    steam_id TEXT NOT NULL,
    discord_id TEXT,
    money DECIMAL(15,2) DEFAULT 0,
    rank TEXT,
    notes TEXT,
    achievements TEXT[],
    last_death DATE,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    reprimands JSONB,
    extra_data JSONB
);

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
INSERT INTO users (name, steam_id, discord_id, rank, notes, extra_data, lore_character_id) 
VALUES 
    ('senwk', '76561198070202465', '805449866971971594', 'president', NULL, NULL, NULL),
    ('Parz1val', '76561198150696236', '142876809992601601', 'EN3', 'Head of medical department', NULL, NULL);
