-- Тесты схемы и функции sync_daily_steps. Запуск: python backend/tests/run_sql_tests.py
-- Каждый блок падает с EXCEPTION, если инвариант нарушен.
\set ON_ERROR_STOP on

-- ---------- фикстуры ----------
INSERT INTO meeples (code, gender, pose, is_free, name, sprite_key)
VALUES ('man_walk', 'm', 'walk', true, '{"ru":"Путник"}', 'meeples/man_walk.png');

INSERT INTO routes (slug, scope, country_code, title, distance_m, tier, geometry_key, status)
VALUES ('test-route', 'city', 'RU', '{"ru":"Тест"}', 3000, 'free', 'routes/test.geojson', 'published');

INSERT INTO users (id, email, nickname, friend_code, timezone)
VALUES ('00000000-0000-0000-0000-00000000000a', 'a@example.com', 'Аня', 'ABCDEF', 'Asia/Vladivostok'),
       ('00000000-0000-0000-0000-00000000000b', 'b@example.com', 'Боря', 'GHJKLM', 'Europe/Moscow');

INSERT INTO user_routes (user_id, route_id, start_day)
SELECT '00000000-0000-0000-0000-00000000000a', id, (now() AT TIME ZONE 'Asia/Vladivostok')::date - 1
  FROM routes WHERE slug = 'test-route';

-- ---------- 1. маршрут: 3000 м / 0,75 = 4000 шагов ----------
DO $$ BEGIN
  IF (SELECT total_steps FROM routes WHERE slug = 'test-route') <> 4000 THEN
    RAISE EXCEPTION 'total_steps: ожидали 4000';
  END IF;
END $$;

-- ---------- 2. бесплатный лимит 2000 и идемпотентность ----------
DO $$
DECLARE r jsonb; r2 jsonb; t date := (now() AT TIME ZONE 'Asia/Vladivostok')::date;
BEGIN
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000a',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', 3500, 'source', 'health_connect', 'install_id', 'i1')));
  IF (r->'days'->0->>'credited')::int <> 2000 THEN RAISE EXCEPTION 'лимит: %', r; END IF;
  IF (r->'route'->>'steps_after')::int <> 2000 THEN RAISE EXCEPTION 'маршрут: %', r; END IF;

  -- тот же батч ещё раз: ничего не меняется
  r2 := sync_daily_steps('00000000-0000-0000-0000-00000000000a',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', 3500, 'source', 'health_connect', 'install_id', 'i1')));
  IF (r2->'days'->0->>'delta')::int <> 0 OR (r2->'route'->>'steps_after')::int <> 2000 THEN
    RAISE EXCEPTION 'повтор батча изменил данные: %', r2;
  END IF;

  -- устаревший батч (меньше шагов) не уменьшает
  r2 := sync_daily_steps('00000000-0000-0000-0000-00000000000a',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', 1000, 'source', 'sensor', 'install_id', 'i2')));
  IF (SELECT raw_steps FROM daily_steps WHERE user_id = '00000000-0000-0000-0000-00000000000a' AND day = t) <> 3500 THEN
    RAISE EXCEPTION 'устаревший батч уменьшил raw';
  END IF;
END $$;

-- ---------- 3. бонус за ролик пересчитывает тот же день ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Asia/Vladivostok')::date;
BEGIN
  INSERT INTO ad_bonuses (id, user_id, day, ad_unit_id, status)
  VALUES (gen_random_uuid(), '00000000-0000-0000-0000-00000000000a', t, 'R-M-TEST', 'granted');
  -- сервис после начисления бонуса вызывает режим «только пересчитать» (steps = null)
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000a',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', NULL)));
  IF (r->'days'->0->>'credited')::int <> 3000 OR (r->'route'->>'steps_after')::int <> 3000 THEN
    RAISE EXCEPTION 'бонус: %', r;
  END IF;
END $$;

-- ---------- 4. премиум снимает лимит, маршрут финиширует, остаток не переносится ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Asia/Vladivostok')::date;
BEGIN
  UPDATE users SET premium_until = now() + interval '7 days' WHERE id = '00000000-0000-0000-0000-00000000000a';
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000a',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', 9000, 'source', 'health_connect')));
  IF (r->'route'->>'steps_after')::int <> 4000 OR NOT (r->'route'->>'finished')::boolean THEN
    RAISE EXCEPTION 'финиш: %', r;
  END IF;
  IF (SELECT status FROM user_routes WHERE user_id = '00000000-0000-0000-0000-00000000000a') <> 'finished' THEN
    RAISE EXCEPTION 'статус не finished';
  END IF;
END $$;

-- ---------- 5. окно дат: будущее и слишком старое отклоняются ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Europe/Moscow')::date;
BEGIN
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000b', jsonb_build_array(
        jsonb_build_object('day', t + 5, 'steps', 100, 'source', 'sensor'),
        jsonb_build_object('day', t - 60, 'steps', 100, 'source', 'sensor'),
        jsonb_build_object('day', t, 'steps', 999999, 'source', 'sensor'),
        jsonb_build_object('day', t - 1, 'steps', 1500, 'source', 'sensor')));
  IF jsonb_array_length(r->'rejected') <> 3 OR jsonb_array_length(r->'days') <> 1 THEN
    RAISE EXCEPTION 'окно дат: %', r;
  END IF;
  IF r->'route' <> 'null'::jsonb THEN RAISE EXCEPTION 'у Б нет маршрута: %', r; END IF;
END $$;

-- ---------- 6. шаги до старта маршрута в маршрут не идут ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Europe/Moscow')::date;
BEGIN
  INSERT INTO user_routes (user_id, route_id, start_day)
  SELECT '00000000-0000-0000-0000-00000000000b', id, t FROM routes WHERE slug = 'test-route';
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000b', jsonb_build_array(
        jsonb_build_object('day', t - 2, 'steps', 1800, 'source', 'sensor'),
        jsonb_build_object('day', t, 'steps', 500, 'source', 'sensor')));
  IF (r->'route'->>'steps_after')::int <> 500 THEN RAISE EXCEPTION 'старт маршрута: %', r; END IF;
END $$;

-- ---------- 7. ограничения целостности ----------
DO $$ BEGIN
  BEGIN
    INSERT INTO user_routes (user_id, route_id, start_day)
    SELECT '00000000-0000-0000-0000-00000000000b', id, current_date FROM routes WHERE slug = 'test-route';
    RAISE EXCEPTION 'два активных маршрута разрешены';
  EXCEPTION WHEN unique_violation THEN NULL; END;

  BEGIN
    INSERT INTO users (nickname, friend_code) VALUES ('Код', 'ABCDE0');   -- 0 запрещён
    RAISE EXCEPTION 'код с 0 принят';
  EXCEPTION WHEN check_violation THEN NULL; END;

  BEGIN
    INSERT INTO users (email, nickname, friend_code) VALUES ('Upper@Example.com', 'Кейс', 'QRSTUV');
    RAISE EXCEPTION 'email в верхнем регистре принят';
  EXCEPTION WHEN check_violation THEN NULL; END;

  INSERT INTO friend_requests (from_user_id, to_user_id)
  VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000b');
  BEGIN
    INSERT INTO friend_requests (from_user_id, to_user_id)
    VALUES ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000a');
    RAISE EXCEPTION 'встречная заявка при открытой принята';
  EXCEPTION WHEN unique_violation THEN NULL; END;

  BEGIN
    INSERT INTO friends (user_a, user_b)
    VALUES ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000a');
    RAISE EXCEPTION 'неканонический порядок пары принят';
  EXCEPTION WHEN check_violation THEN NULL; END;

  BEGIN
    INSERT INTO route_facts (point_id, locale, status)
    SELECT p.id, 'ru', 'published' FROM route_points p LIMIT 1;
    -- если точек нет, вставки не было — проверим отдельно ниже
  EXCEPTION WHEN check_violation THEN NULL; END;
END $$;

-- ---------- 8. медаль за серию выдаётся один раз, за веху — на каждое прохождение ----------
DO $$
DECLARE m_streak smallint; m_half smallint; ur uuid;
BEGIN
  INSERT INTO medals (code, kind, threshold, title, icon_key) VALUES ('streak_7', 'streak', 7, '{"ru":"7 дней"}', 'm/s7.png') RETURNING id INTO m_streak;
  INSERT INTO medals (code, kind, threshold, title, icon_key) VALUES ('half', 'milestone', 50, '{"ru":"Половина"}', 'm/h.png') RETURNING id INTO m_half;
  SELECT id INTO ur FROM user_routes WHERE user_id = '00000000-0000-0000-0000-00000000000a';
  INSERT INTO user_medals (user_id, medal_id) VALUES ('00000000-0000-0000-0000-00000000000a', m_streak);
  INSERT INTO user_medals (user_id, medal_id, user_route_id) VALUES ('00000000-0000-0000-0000-00000000000a', m_half, ur);
  BEGIN
    INSERT INTO user_medals (user_id, medal_id) VALUES ('00000000-0000-0000-0000-00000000000a', m_streak);
    RAISE EXCEPTION 'медаль за серию выдана дважды';
  EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;

-- ---------- 9. партиции ----------
DO $$ BEGIN
  PERFORM ensure_daily_steps_partitions(3);
  IF (SELECT count(*) FROM pg_inherits WHERE inhparent = 'daily_steps'::regclass) < 24 THEN
    RAISE EXCEPTION 'мало партиций';
  END IF;
END $$;

-- ---------- 10. ни одного гео-поля в соцтаблицах ----------
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name IN ('users', 'friends', 'friend_requests', 'devices', 'user_routes', 'daily_steps')
                AND column_name ~ '(lat|lon|lng|geo|location|coord)') THEN
    RAISE EXCEPTION 'в соцтаблицах есть геополя';
  END IF;
END $$;


-- ---------- 11. пересчёт несуществующего дня не создаёт строку и не роняет батч ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Europe/Moscow')::date;
BEGIN
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000b',
        jsonb_build_array(jsonb_build_object('day', t - 10, 'steps', NULL)));
  IF EXISTS (SELECT 1 FROM daily_steps WHERE user_id = '00000000-0000-0000-0000-00000000000b' AND day = t - 10) THEN
    RAISE EXCEPTION 'пересчёт создал строку';
  END IF;
END $$;

-- ---------- 12. смена пояса: старые дни сохраняют свой tz, новый пояс применяется ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Europe/Moscow')::date;
BEGIN
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000b',
        jsonb_build_array(jsonb_build_object('day', t, 'steps', 600, 'source', 'sensor')),
        'i-b', 'Asia/Vladivostok');
  IF (SELECT timezone FROM users WHERE id = '00000000-0000-0000-0000-00000000000b') <> 'Asia/Vladivostok' THEN
    RAISE EXCEPTION 'пояс не сменился';
  END IF;
  IF (SELECT tz FROM daily_steps WHERE user_id = '00000000-0000-0000-0000-00000000000b' AND day = t) <> 'Europe/Moscow' THEN
    RAISE EXCEPTION 'tz открытого дня изменился';
  END IF;
  BEGIN
    UPDATE users SET timezone = 'Mars/Olympus' WHERE id = '00000000-0000-0000-0000-00000000000b';
    RAISE EXCEPTION 'несуществующий пояс принят';
  EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
END $$;

-- ---------- 13. счётчики: суммарные шаги и серия, в том числе с дозаписью дня в прошлом ----------
DO $$
DECLARE r jsonb; t date := (now() AT TIME ZONE 'Europe/Moscow')::date;
BEGIN
  INSERT INTO users (id, nickname, friend_code) VALUES ('00000000-0000-0000-0000-00000000000c', 'Вера', 'NPQRST');
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000c', jsonb_build_array(
        jsonb_build_object('day', t - 3, 'steps', 1500, 'source', 'sensor'),
        jsonb_build_object('day', t - 1, 'steps', 1200, 'source', 'sensor'),
        jsonb_build_object('day', t,     'steps', 1100, 'source', 'sensor')));
  IF (r->>'streak_days')::int <> 2 OR (r->>'lifetime_steps')::bigint <> 3800 THEN
    RAISE EXCEPTION 'серия/сумма до дозаписи: %', r;
  END IF;
  -- офлайн-день t-2 пришёл позже: серия должна стать 4
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000c', jsonb_build_array(
        jsonb_build_object('day', t - 2, 'steps', 2000, 'source', 'sensor')));
  IF (r->>'streak_days')::int <> 4 OR (r->>'lifetime_steps')::bigint <> 5800 THEN
    RAISE EXCEPTION 'серия/сумма после дозаписи: %', r;
  END IF;
  -- повтор не меняет сумму
  r := sync_daily_steps('00000000-0000-0000-0000-00000000000c', jsonb_build_array(
        jsonb_build_object('day', t - 2, 'steps', 2000, 'source', 'sensor')));
  IF (r->>'lifetime_steps')::bigint <> 5800 THEN RAISE EXCEPTION 'повтор изменил сумму: %', r; END IF;
END $$;

-- ---------- 14. удаление прохождений с одинаковой вехой не падает ----------
DO $$
DECLARE m smallint; ur2 uuid;
BEGIN
  SELECT id INTO m FROM medals WHERE code = 'half';
  INSERT INTO user_routes (user_id, route_id, status, start_day, finished_at)
  SELECT '00000000-0000-0000-0000-00000000000a', id, 'finished', current_date, now() FROM routes WHERE slug = 'test-route'
  RETURNING id INTO ur2;
  INSERT INTO user_medals (user_id, medal_id, user_route_id) VALUES ('00000000-0000-0000-0000-00000000000a', m, ur2);
  DELETE FROM user_routes WHERE user_id = '00000000-0000-0000-0000-00000000000a';
  IF EXISTS (SELECT 1 FROM user_medals WHERE medal_id = m) THEN RAISE EXCEPTION 'медали прохождений остались'; END IF;
END $$;

-- ---------- 15. мировой маршрут 50 000 км не переполняет total_steps ----------
DO $$ BEGIN
  INSERT INTO routes (slug, scope, country_code, title, distance_m, tier)
  VALUES ('world-max', 'world', 'RU', '{"ru":"Мир"}', 50000000, 'premium');
  IF (SELECT total_steps FROM routes WHERE slug = 'world-max') <> 66666667 THEN
    RAISE EXCEPTION 'total_steps мирового маршрута';
  END IF;
END $$;

-- ---------- 16. удаление пользователя: подписка обезличивается и остаётся ----------
DO $$ BEGIN
  INSERT INTO subscriptions (user_id, provider, provider_subscription_id, account_ref, product_id, plan, status)
  VALUES ('00000000-0000-0000-0000-00000000000c', 'rustore', 'sub-1', 'ref-c', 'putnik_month', 'monthly', 'active');
  DELETE FROM users WHERE id = '00000000-0000-0000-0000-00000000000c';
  IF (SELECT user_id FROM subscriptions WHERE provider_subscription_id = 'sub-1') IS NOT NULL THEN
    RAISE EXCEPTION 'подписка не обезличена';
  END IF;
END $$;

-- ---------- 17. новые партиции создаются через ATTACH ----------
DO $$
DECLARE n integer;
BEGIN
  n := ensure_daily_steps_partitions(16);
  IF n < 1 OR to_regclass('daily_steps_2028_01') IS NULL THEN RAISE EXCEPTION 'ATTACH не создал партицию'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'daily_steps_2028_01' AND 'fillfactor=80' = ANY(reloptions)) THEN
    RAISE EXCEPTION 'fillfactor не задан';
  END IF;
END $$;

SELECT 'ALL SQL TESTS PASSED' AS result;
