-- Ranks: allow UO and PRES (decision D1)
ALTER TABLE military.service_records DROP CONSTRAINT IF EXISTS service_records_current_rank_check;
ALTER TABLE military.service_records ADD CONSTRAINT service_records_current_rank_check CHECK (
  current_rank IS NULL OR current_rank = ANY (ARRAY['EN0','EN1','EN2','EN3','EN4','EN5','EN6','EN7','EN8',
  'OF0','OF1','OF2','OF3','OF4','OF5','OF6','OF7','OF8','OF9','OF10','OF11','UO','PRES']));
ALTER TABLE military.service_events DROP CONSTRAINT IF EXISTS service_events_rank_check;
ALTER TABLE military.service_events ADD CONSTRAINT service_events_rank_check CHECK (
  rank IS NULL OR rank = ANY (ARRAY['EN0','EN1','EN2','EN3','EN4','EN5','EN6','EN7','EN8',
  'OF0','OF1','OF2','OF3','OF4','OF5','OF6','OF7','OF8','OF9','OF10','OF11','UO','PRES']));

-- The bot's organization (service_records.organization_id is required)
INSERT INTO public.identities_organizations (name, organization_type)
VALUES ('AFDF-FAS', 'military') ON CONFLICT (name) DO NOTHING;  -- already exists in production, so a no-op there

-- One identity per Discord / Steam account (the bot looks players up by these)
CREATE UNIQUE INDEX IF NOT EXISTS identities_player_discord_id_uniq
  ON public.identities_player (discord_id) WHERE discord_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS identities_player_steam_id_uniq
  ON public.identities_player (steam_id) WHERE steam_id IS NOT NULL;

-- Leave of absence: the bot uses the existing military.leave_requests (keyed by service_record_id); no DDL needed.
