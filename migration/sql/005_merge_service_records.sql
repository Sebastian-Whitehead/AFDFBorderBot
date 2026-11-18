-- Merge service record "from" (the Steam identity's, source of truth) into "to" (the Discord identity's).
-- "to" keeps its id but takes the "from" rank and status; events, attendance and leave move over.
-- On a clash the "from" side wins: same-session attendance, and the one active leave request. "from" is deleted.
-- Errors (P0001): record_not_found, same_record, different_organization.
CREATE OR REPLACE FUNCTION public.fab_merge_service_records(p_from_record_id bigint, p_to_record_id bigint)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  f military.service_records%ROWTYPE;
  t military.service_records%ROWTYPE;
  v_events int; v_att_moved int; v_att_replaced int; v_leave_moved int; v_leave_cancelled int;
BEGIN
  IF p_from_record_id = p_to_record_id THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'same_record';
  END IF;
  -- lock in id order so concurrent opposite merges cannot deadlock
  PERFORM 1 FROM military.service_records
    WHERE id IN (p_from_record_id, p_to_record_id) ORDER BY id FOR UPDATE;
  SELECT * INTO f FROM military.service_records WHERE id = p_from_record_id;
  SELECT * INTO t FROM military.service_records WHERE id = p_to_record_id;
  IF f.id IS NULL OR t.id IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'record_not_found';
  END IF;
  IF f.organization_id <> t.organization_id THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'different_organization';
  END IF;

  UPDATE military.service_events SET service_record_id = t.id WHERE service_record_id = f.id;
  GET DIAGNOSTICS v_events = ROW_COUNT;

  DELETE FROM military.attendance
   WHERE service_record_id = t.id
     AND session_id IN (SELECT session_id FROM military.attendance WHERE service_record_id = f.id);
  GET DIAGNOSTICS v_att_replaced = ROW_COUNT;
  UPDATE military.attendance SET service_record_id = t.id WHERE service_record_id = f.id;
  GET DIAGNOSTICS v_att_moved = ROW_COUNT;

  UPDATE military.leave_requests SET status = 'cancelled', updated_at = now()
   WHERE service_record_id = t.id AND status = 'active'
     AND EXISTS (SELECT 1 FROM military.leave_requests WHERE service_record_id = f.id AND status = 'active');
  GET DIAGNOSTICS v_leave_cancelled = ROW_COUNT;
  UPDATE military.leave_requests SET service_record_id = t.id WHERE service_record_id = f.id;
  GET DIAGNOSTICS v_leave_moved = ROW_COUNT;

  DELETE FROM military.service_records WHERE id = f.id;
  UPDATE military.service_records
     SET current_rank = f.current_rank, service_status = f.service_status, updated_at = now()
   WHERE id = t.id;

  RETURN jsonb_build_object(
    'result', 'merged', 'events_moved', v_events, 'attendance_moved', v_att_moved,
    'attendance_replaced', v_att_replaced, 'leave_moved', v_leave_moved, 'leave_cancelled', v_leave_cancelled,
    'removed', jsonb_build_object('id', f.id, 'current_rank', f.current_rank, 'service_status', f.service_status),
    'previous', jsonb_build_object('current_rank', t.current_rank, 'service_status', t.service_status));
END;
$$;

-- same as the other fab_* functions: only the service role (the bot) may call it, never anon/authenticated
REVOKE ALL ON FUNCTION public.fab_merge_service_records(bigint, bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fab_merge_service_records(bigint, bigint) TO service_role;
