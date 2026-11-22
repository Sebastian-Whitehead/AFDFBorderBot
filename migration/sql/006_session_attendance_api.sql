-- API for external programs (service role only): create a session, then dump a whole session's attendance in one call.
-- Players are identified by Steam ID. Organization is AFDF-Para Raiders, same as the bot.

-- Create a session. Returns {"session_id": n}.
-- Errors (P0001): name_required.
CREATE OR REPLACE FUNCTION public.fab_create_session(
  p_name text,
  p_timeline text DEFAULT 'A',
  p_operation text DEFAULT NULL,
  p_description text DEFAULT NULL,
  p_start_at timestamptz DEFAULT NULL,
  p_external_event_id text DEFAULT NULL)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  v_id bigint;
BEGIN
  IF p_name IS NULL OR btrim(p_name) = '' THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'name_required';
  END IF;
  INSERT INTO military.sessions (session_name, timeline, operation, description, start_at, external_event_id)
  VALUES (btrim(p_name), COALESCE(p_timeline, 'A'), p_operation, p_description, COALESCE(p_start_at, now()), p_external_event_id)
  RETURNING id INTO v_id;
  RETURN jsonb_build_object('session_id', v_id);
END;
$$;

-- Log a session's attendance from a list of Steam IDs. Every ACTIVE service record gets exactly one row:
--   Steam ID in the list                         -> present (a note records an active LOA, as the bot does)
--   not in the list, active LOA on session date  -> on_leave
--   otherwise                                    -> absent
-- Safe to re-run for the same session: rows are upserted, so the last call wins.
-- Returns {"session_id", "present", "on_leave", "absent", "unknown_steam_ids": [...]}; unknown = in the list but no
-- active service record (not enlisted / not active), nothing is written for them.
-- Errors (P0001): session_not_found.
CREATE OR REPLACE FUNCTION public.fab_log_attendance(
  p_session_id bigint,
  p_steam_ids bigint[],
  p_recorded_by text DEFAULT 'external')
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  v_date date;
  v_present int; v_leave int; v_absent int;
  v_unknown jsonb;
BEGIN
  SELECT start_at::date INTO v_date FROM military.sessions WHERE id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'session_not_found';
  END IF;
  p_steam_ids := COALESCE(p_steam_ids, ARRAY[]::bigint[]);

  WITH active AS (
    SELECT sr.id AS rid, p.steam_id
    FROM military.service_records sr
    JOIN public.identities_player p ON p.id = sr.player_identity_id
    JOIN public.identities_organizations o ON o.id = sr.organization_id
    WHERE o.name = 'AFDF-Para Raiders' AND sr.service_status = 'active'
  ), calc AS (
    SELECT a.rid,
           CASE WHEN a.steam_id = ANY (p_steam_ids) THEN 'present'
                WHEN l.id IS NOT NULL THEN 'on_leave'
                ELSE 'absent' END AS st,
           CASE WHEN l.id IS NOT NULL
                THEN 'LOA until ' || l.end_date || COALESCE(': ' || l.reason, '') END AS note
    FROM active a
    LEFT JOIN LATERAL (
      SELECT id, end_date, reason FROM military.leave_requests
      WHERE service_record_id = a.rid AND status = 'active' AND v_date BETWEEN start_date AND end_date
      ORDER BY end_date DESC LIMIT 1) l ON true
  ), up AS (
    INSERT INTO military.attendance (service_record_id, session_id, attendance_status, notes, recorded_by)
    SELECT rid, p_session_id, st::military.attendance_status, note, p_recorded_by FROM calc
    ON CONFLICT (service_record_id, session_id) DO UPDATE
      SET attendance_status = EXCLUDED.attendance_status, notes = EXCLUDED.notes,
          recorded_at = now(), recorded_by = EXCLUDED.recorded_by
    RETURNING attendance_status
  )
  SELECT count(*) FILTER (WHERE attendance_status = 'present'),
         count(*) FILTER (WHERE attendance_status = 'on_leave'),
         count(*) FILTER (WHERE attendance_status = 'absent')
    INTO v_present, v_leave, v_absent FROM up;

  SELECT COALESCE(jsonb_agg(s ORDER BY s), '[]'::jsonb) INTO v_unknown
  FROM (SELECT DISTINCT s FROM unnest(p_steam_ids) s
        WHERE NOT EXISTS (
          SELECT 1 FROM military.service_records sr
          JOIN public.identities_player p ON p.id = sr.player_identity_id
          JOIN public.identities_organizations o ON o.id = sr.organization_id
          WHERE p.steam_id = s AND o.name = 'AFDF-Para Raiders' AND sr.service_status = 'active')) u;

  RETURN jsonb_build_object('session_id', p_session_id, 'present', v_present, 'on_leave', v_leave,
                            'absent', v_absent, 'unknown_steam_ids', v_unknown);
END;
$$;

-- same as the other fab_* functions: only the service role may call them, never anon/authenticated
REVOKE ALL ON FUNCTION public.fab_create_session(text, text, text, text, timestamptz, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fab_create_session(text, text, text, text, timestamptz, text) TO service_role;
REVOKE ALL ON FUNCTION public.fab_log_attendance(bigint, bigint[], text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fab_log_attendance(bigint, bigint[], text) TO service_role;
