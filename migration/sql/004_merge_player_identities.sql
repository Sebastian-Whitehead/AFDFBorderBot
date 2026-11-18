-- Merge/link the identity that owns a Steam ID (A) with the one that owns a Discord ID (B).
-- Results: {result: 'linked'|'already_linked', identity_id} or {result: 'merged', identity_id, accounts_moved, removed}.
-- Errors (P0001): invalid_player_identifier, no_identity, steam_linked_to_other_discord, different_steam, service_record_conflict.
-- p_force lets a side overwrite an ID it already has. Both sides having a service record always fails:
-- run fab_merge_service_records first. The identity with an AFDF service record survives (B if neither has one).
-- Bank accounts move to the survivor; colliding names get " (merged from <id>)". Balances are not combined.
CREATE OR REPLACE FUNCTION public.fab_merge_player_identities(p_steam_id bigint, p_discord_id bigint, p_force boolean DEFAULT false)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  v_org constant text := 'AFDF-Para Raiders';
  a public.identities_player%ROWTYPE;
  b public.identities_player%ROWTYPE;
  s public.identities_player%ROWTYPE;
  l public.identities_player%ROWTYPE;
  v_moved int;
BEGIN
  IF p_steam_id IS NULL OR p_discord_id IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'invalid_player_identifier';
  END IF;

  -- same lock order as fab_ensure_player_account (steam, then discord)
  PERFORM pg_advisory_xact_lock(hashtextextended('fab-player:' || p_steam_id::text, 0));
  PERFORM pg_advisory_xact_lock(hashtextextended('fab-player-discord:' || p_discord_id::text, 0));

  SELECT * INTO a FROM public.identities_player WHERE steam_id = p_steam_id;
  SELECT * INTO b FROM public.identities_player WHERE discord_id = p_discord_id;

  IF a.id IS NULL AND b.id IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'no_identity';
  END IF;
  IF a.id = b.id THEN
    RETURN jsonb_build_object('result', 'already_linked', 'identity_id', a.id);
  END IF;

  IF a.id IS NULL THEN
    IF b.steam_id IS NOT NULL AND NOT p_force THEN
      RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'different_steam';
    END IF;
    UPDATE public.identities_player SET steam_id = p_steam_id WHERE id = b.id;
    RETURN jsonb_build_object('result', 'linked', 'identity_id', b.id);
  END IF;
  IF b.id IS NULL THEN
    IF a.discord_id IS NOT NULL AND NOT p_force THEN
      RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'steam_linked_to_other_discord';
    END IF;
    UPDATE public.identities_player SET discord_id = p_discord_id WHERE id = a.id;
    RETURN jsonb_build_object('result', 'linked', 'identity_id', a.id);
  END IF;

  -- two different identities
  IF a.discord_id IS NOT NULL AND NOT p_force THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'steam_linked_to_other_discord';
  END IF;
  IF b.steam_id IS NOT NULL AND NOT p_force THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'different_steam';
  END IF;
  IF EXISTS (
    SELECT 1 FROM military.service_records ra
    JOIN military.service_records rb ON rb.organization_id = ra.organization_id
    WHERE ra.player_identity_id = a.id AND rb.player_identity_id = b.id
  ) THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'service_record_conflict';
  END IF;

  -- survivor: the identity with an AFDF service record, else the Discord one
  IF EXISTS (
    SELECT 1 FROM military.service_records r
    JOIN public.identities_organizations o ON o.id = r.organization_id AND o.name = v_org
    WHERE r.player_identity_id = a.id
  ) THEN
    s := a; l := b;
  ELSE
    s := b; l := a;
  END IF;

  UPDATE economy.accounts x
     SET account_name = x.account_name || ' (merged from ' || l.id || ')'
   WHERE x.player_identity_id = l.id
     AND lower(x.account_name) IN (SELECT lower(y.account_name) FROM economy.accounts y WHERE y.player_identity_id = s.id);
  UPDATE economy.accounts SET player_identity_id = s.id WHERE player_identity_id = l.id;
  GET DIAGNOSTICS v_moved = ROW_COUNT;
  UPDATE military.service_records SET player_identity_id = s.id WHERE player_identity_id = l.id;
  DELETE FROM public.identities_player WHERE id = l.id;

  -- Steam identity's alias/details win; the Discord one only fills gaps
  UPDATE public.identities_player
     SET steam_id = p_steam_id,
         discord_id = p_discord_id,
         alias = coalesce(a.alias, b.alias),
         details = CASE WHEN a.details IS NULL AND b.details IS NULL THEN NULL
                        ELSE coalesce(b.details, '{}'::jsonb) || coalesce(a.details, '{}'::jsonb) END
   WHERE id = s.id;

  RETURN jsonb_build_object(
    'result', 'merged', 'identity_id', s.id, 'accounts_moved', v_moved,
    'removed', jsonb_build_object('id', l.id, 'alias', l.alias, 'steam_id', l.steam_id,
                                  'discord_id', l.discord_id, 'details', l.details));
END;
$$;

-- same as the other fab_* functions: only the service role (the bot) may call it, never anon/authenticated
REVOKE ALL ON FUNCTION public.fab_merge_player_identities(bigint, bigint, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fab_merge_player_identities(bigint, bigint, boolean) TO service_role;
