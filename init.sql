-- Create bot_settings table for storing configuration
CREATE TABLE bot_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries on setting_key
CREATE INDEX idx_bot_settings_key ON bot_settings(setting_key);

-- Insert default bot settings
INSERT INTO bot_settings (setting_key, setting_value) 
VALUES 
    ('listen-for-join-leave', 'true'),
    ('new-citizen-welcome', 'true'),
    ('enlist-welcome', 'true'),
    ('listen-for-border-officer', 'true');
