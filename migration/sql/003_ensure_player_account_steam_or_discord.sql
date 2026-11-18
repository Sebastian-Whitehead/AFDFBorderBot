-- fab_ensure_player_account now accepts a Steam ID, a Discord ID, or both (at least one).
-- Same signature and return shape, so the game engine (Steam ID only) keeps working unchanged.
-- Existing identity is reused; a missing Steam/Discord ID is filled in when the other one matches.
-- A conflicting link (the ID belongs to a different identity) raises instead of silently ignoring.
CREATE OR REPLACE FUNCTION public.fab_ensure_player_account(p_alias text, p_steam_id bigint, p_discord_id bigint)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  v_player_id bigint;
  v_row public.identities_player%ROWTYPE;
  v_other_id bigint;
  player_count bigint;
  v_accounts jsonb;
  account_count bigint;
BEGIN
  IF p_steam_id IS NULL AND p_discord_id IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'invalid_player_identifier';
  END IF;

  -- fixed lock order (steam, then discord) so concurrent callers cannot deadlock
  IF p_steam_id IS NOT NULL THEN
    PERFORM pg_advisory_xact_lock(hashtextextended('fab-player:' || p_steam_id::text, 0));
  END IF;
  IF p_discord_id IS NOT NULL THEN
    PERFORM pg_advisory_xact_lock(hashtextextended('fab-player-discord:' || p_discord_id::text, 0));
  END IF;

  -- the identity this call refers to: by Steam ID if given, else by Discord ID
  IF p_steam_id IS NOT NULL THEN
    SELECT count(*), min(id) INTO player_count, v_player_id
      FROM public.identities_player WHERE steam_id = p_steam_id;
    IF player_count > 1 THEN
      RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'duplicate_player_identity';
    END IF;
  ELSE
    SELECT count(*), min(id) INTO player_count, v_player_id
      FROM public.identities_player WHERE discord_id = p_discord_id;
  END IF;

  IF player_count = 1 THEN
    SELECT * INTO v_row FROM public.identities_player WHERE id = v_player_id;

    -- link the Discord ID to the Steam-matched identity
    IF p_steam_id IS NOT NULL AND p_discord_id IS NOT NULL AND v_row.discord_id IS DISTINCT FROM p_discord_id THEN
      IF v_row.discord_id IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'identity_conflict';
      END IF;
      SELECT id INTO v_other_id FROM public.identities_player WHERE discord_id = p_discord_id;
      IF v_other_id IS NOT NULL THEN  -- two separate identities: merging them is not our call
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'identity_conflict';
      END IF;
      UPDATE public.identities_player SET discord_id = p_discord_id WHERE id = v_player_id;
    END IF;
  ELSE
    -- no identity for the primary key yet. With both given, a Discord-only identity may already exist: attach the Steam ID to it
    IF p_steam_id IS NOT NULL AND p_discord_id IS NOT NULL THEN
      SELECT * INTO v_row FROM public.identities_player WHERE discord_id = p_discord_id;
      IF FOUND THEN
        IF v_row.steam_id IS NOT NULL THEN
          RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'identity_conflict';
        END IF;
        UPDATE public.identities_player SET steam_id = p_steam_id WHERE id = v_row.id;
        v_player_id := v_row.id;
      END IF;
    END IF;

    IF v_player_id IS NULL THEN
      INSERT INTO public.identities_player (alias, steam_id, discord_id)
      VALUES (nullif(p_alias, ''), p_steam_id, p_discord_id)
      RETURNING id INTO v_player_id;
    END IF;
  END IF;

  SELECT count(*) INTO account_count
    FROM economy.accounts
    WHERE player_identity_id = v_player_id AND account_type = 'player';

  IF account_count = 0 THEN
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'player_account_unavailable';
  END IF;

  SELECT jsonb_agg(
    jsonb_build_object(
      'account_number', account_number,
      'account_name', account_name,
      'account_type', account_type::text,
      'money', money
    )
    ORDER BY account_name, account_number
  )
  INTO v_accounts
  FROM economy.accounts
  WHERE player_identity_id = v_player_id AND account_type = 'player';

  RETURN jsonb_build_object('accounts', v_accounts);
END;
$$;
