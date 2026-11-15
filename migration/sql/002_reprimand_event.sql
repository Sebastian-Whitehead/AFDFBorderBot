-- /reprimand logs a 'reprimand' event on the service record
ALTER TABLE military.service_events DROP CONSTRAINT IF EXISTS service_events_type_check;
ALTER TABLE military.service_events ADD CONSTRAINT service_events_type_check CHECK (
  event_type = ANY (ARRAY['enlisted','rank_changed','discharged','reenlisted','retired','reprimand']));
