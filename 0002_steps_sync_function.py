"""Функция идемпотентного приёма батча шагов.

Revision ID: 0002_steps_sync_function
Revises: 0001_initial_schema

Почему функция в БД, а не код в Python:
* Батч шагов — самый частый запрос (≈40 % трафика). Функция выполняется за один
  round-trip вместо 2 + 2N запросов, что важно при пулере в режиме транзакций.
* Вся логика зачёта атомарна под блокировкой строки пользователя: два параллельных
  синка одного пользователя (два телефона, ретрай) сериализуются.
* Медали, лента, пуши и NPC — в Python, НО В ТОЙ ЖЕ ТРАНЗАКЦИИ, что и вызов функции,
  и от абсолютного состояния (steps_done ≥ порог), а не от перехода «было → стало»:
  если сервер упадёт после зачёта, повторный синк всё равно выдаст недостающее.

Правила зачёта (docs/02-data-model.md, «Шаги»):
1. raw_steps = GREATEST(старое, новое). Два устройства не суммируются.
2. Бесплатно: зачтено ≤ free_limit + бонусы этого дня. Премиум — без лимита
   (право на момент синка).
3. credited_steps только растёт; дельта — в активный маршрут, если день ≥ дня старта.
4. «Сегодня» — по поясу пользователя на сервере. Окно: today − backfill … today + 1.
5. steps = null у дня → режим «только пересчитать» (после бонуса за ролик):
   строку не создаёт, если её нет.
6. p_timezone меняет пояс пользователя под той же блокировкой. Уже открытые дни
   сохраняют свой tz — клиент обязан считать день D в поясе, который вернул сервер
   для D, иначе вечерние часы попадут в два дня.
"""

from alembic import op

revision = "0002_steps_sync_function"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

UPGRADE_SQL = r"""
CREATE FUNCTION sync_daily_steps(
    p_user_id       uuid,
    p_days          jsonb,            -- [{"day":"2026-10-28","steps":5400|null,"source":"health_connect"}]
    p_install_id    text    DEFAULT NULL,
    p_timezone      text    DEFAULT NULL,
    p_free_limit    integer DEFAULT 2000,
    p_backfill_days integer DEFAULT 30,
    p_streak_min    integer DEFAULT 1000   -- день засчитывается в серию с этого числа шагов
) RETURNS jsonb
LANGUAGE plpgsql
SET lock_timeout = '3s'               -- на уровне функции: безопасно для пулера, в отличие от сессионного SET
AS $fn$
DECLARE
    v_user        record;
    v_tz          text;
    v_today       date;
    v_premium     boolean;
    v_entry       record;
    v_old         record;
    v_raw         integer;
    v_bonus       integer;
    v_allow       integer;
    v_credited    integer;
    v_delta       integer;
    v_route       record;
    v_route_delta integer := 0;
    v_after       integer;
    v_life_delta  bigint  := 0;
    v_last_step   date;
    v_streak      integer;
    v_streak_last date;
    v_recompute   boolean := false;
    v_run         integer;
    v_days_out    jsonb := '[]'::jsonb;
    v_rejected    jsonb := '[]'::jsonb;
BEGIN
    -- Сериализация всех записей одного пользователя. NO KEY UPDATE совместим с KEY SHARE,
    -- который берут внешние ключи при вставке в дочерние таблицы, → нет deadlock.
    SELECT id, timezone, premium_until, streak_days, streak_last_day, last_step_day INTO v_user
      FROM users WHERE id = p_user_id AND deleted_at IS NULL
       FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'user_not_found' USING ERRCODE = 'P0002';
    END IF;

    v_tz := v_user.timezone;
    IF p_timezone IS NOT NULL AND p_timezone <> v_tz THEN
        UPDATE users SET timezone = p_timezone WHERE id = p_user_id;   -- триггер проверит имя пояса
        v_tz := p_timezone;
    END IF;

    v_today       := (now() AT TIME ZONE v_tz)::date;
    v_premium     := coalesce(v_user.premium_until > now(), false);
    v_streak      := v_user.streak_days;
    v_streak_last := v_user.streak_last_day;
    v_last_step   := v_user.last_step_day;

    SELECT ur.id, ur.route_id, ur.steps_done, ur.start_day, r.total_steps INTO v_route
      FROM user_routes ur JOIN routes r ON r.id = ur.route_id
     WHERE ur.user_id = p_user_id AND ur.status = 'active'
       FOR NO KEY UPDATE OF ur;

    -- Дубликаты дня внутри батча схлопываем максимумом; дни — по возрастанию (важно для серии)
    FOR v_entry IN
        SELECT (e->>'day')::date AS day,
               max((e->>'steps')::integer) AS steps,
               (array_agg(e->>'source' ORDER BY (e->>'steps')::integer DESC NULLS LAST))[1] AS source
          FROM jsonb_array_elements(p_days) e
         GROUP BY 1
         ORDER BY 1
    LOOP
        IF v_entry.day > v_today + 1 OR v_entry.day < v_today - p_backfill_days THEN
            v_rejected := v_rejected || jsonb_build_object('day', v_entry.day, 'reason', 'out_of_window');
            CONTINUE;
        END IF;
        IF v_entry.steps < 0 OR v_entry.steps > 150000 THEN
            v_rejected := v_rejected || jsonb_build_object('day', v_entry.day, 'reason', 'implausible');
            CONTINUE;
        END IF;

        SELECT raw_steps, credited_steps, tz INTO v_old
          FROM daily_steps WHERE user_id = p_user_id AND day = v_entry.day;

        IF v_entry.steps IS NULL AND v_old.raw_steps IS NULL THEN
            CONTINUE;                       -- пересчитывать нечего
        END IF;
        IF v_entry.steps IS NOT NULL AND v_entry.source IS NULL THEN
            v_rejected := v_rejected || jsonb_build_object('day', v_entry.day, 'reason', 'no_source');
            CONTINUE;
        END IF;

        v_raw := greatest(coalesce(v_old.raw_steps, 0), coalesce(v_entry.steps, 0));

        SELECT coalesce(sum(steps), 0) INTO v_bonus
          FROM ad_bonuses
         WHERE user_id = p_user_id AND day = v_entry.day AND status = 'granted';

        v_allow    := CASE WHEN v_premium THEN v_raw ELSE least(v_raw, p_free_limit + v_bonus) END;
        v_credited := greatest(coalesce(v_old.credited_steps, 0), v_allow);
        v_delta    := v_credited - coalesce(v_old.credited_steps, 0);

        INSERT INTO daily_steps AS d (user_id, day, raw_steps, credited_steps, source, install_id, tz)
        VALUES (p_user_id, v_entry.day, v_raw, v_credited,
                coalesce(v_entry.source, 'sensor'), p_install_id, v_tz)
        ON CONFLICT (user_id, day) DO UPDATE
           SET raw_steps      = EXCLUDED.raw_steps,
               credited_steps = EXCLUDED.credited_steps,
               source         = CASE WHEN EXCLUDED.raw_steps > d.raw_steps THEN EXCLUDED.source ELSE d.source END,
               install_id     = CASE WHEN EXCLUDED.raw_steps > d.raw_steps THEN EXCLUDED.install_id ELSE d.install_id END,
               updated_at     = now()
         WHERE d.raw_steps IS DISTINCT FROM EXCLUDED.raw_steps
            OR d.credited_steps IS DISTINCT FROM EXCLUDED.credited_steps;
        -- tz существующей строки не меняется: день живёт в поясе, в котором открылся

        v_life_delta := v_life_delta + (v_raw - coalesce(v_old.raw_steps, 0));
        IF v_raw > 0 AND (v_last_step IS NULL OR v_entry.day > v_last_step) THEN
            v_last_step := v_entry.day;
        END IF;

        -- Серия: день впервые перешёл порог
        IF v_raw >= p_streak_min AND coalesce(v_old.raw_steps, 0) < p_streak_min THEN
            IF v_streak_last IS NULL OR v_entry.day > v_streak_last + 1 THEN
                v_streak := 1; v_streak_last := v_entry.day;
            ELSIF v_entry.day = v_streak_last + 1 THEN
                v_streak := v_streak + 1; v_streak_last := v_entry.day;
            ELSE
                v_recompute := true;        -- дозаписан день в прошлом: пересчёт ниже
            END IF;
        END IF;

        IF v_route.id IS NOT NULL AND v_entry.day >= v_route.start_day THEN
            v_route_delta := v_route_delta + v_delta;
        END IF;

        v_days_out := v_days_out || jsonb_build_object(
            'day', v_entry.day, 'raw', v_raw, 'credited', v_credited, 'delta', v_delta,
            'tz', coalesce(v_old.tz, v_tz),
            'limited', NOT v_premium AND v_raw > v_credited);
    END LOOP;

    IF v_recompute THEN
        -- Длина серии, заканчивающейся на v_streak_last, в окне 400 дней
        -- (константная граница по дате → читаются только нужные партиции)
        SELECT count(*) INTO v_run FROM (
            SELECT day, row_number() OVER (ORDER BY day DESC) AS rn
              FROM daily_steps
             WHERE user_id = p_user_id AND raw_steps >= p_streak_min
               AND day <= v_streak_last AND day > v_streak_last - 400
        ) t WHERE t.day + t.rn::integer = v_streak_last + 1;
        v_streak := CASE WHEN v_run >= 400 THEN greatest(v_streak, v_run) ELSE v_run END;
    END IF;

    IF v_life_delta <> 0 OR v_last_step IS DISTINCT FROM v_user.last_step_day
       OR v_streak <> v_user.streak_days OR v_streak_last IS DISTINCT FROM v_user.streak_last_day THEN
        UPDATE users
           SET lifetime_steps  = lifetime_steps + v_life_delta,
               last_step_day   = v_last_step,
               streak_days     = v_streak,
               streak_last_day = v_streak_last
         WHERE id = p_user_id;
    END IF;

    IF v_route.id IS NOT NULL AND v_route_delta > 0 THEN
        v_after := least(v_route.total_steps, v_route.steps_done + v_route_delta);
        UPDATE user_routes
           SET steps_done  = v_after,
               status      = CASE WHEN v_after >= v_route.total_steps THEN 'finished' ELSE status END,
               finished_at = CASE WHEN v_after >= v_route.total_steps THEN now() ELSE finished_at END
         WHERE id = v_route.id;
    END IF;

    RETURN jsonb_build_object(
        'today', v_today,
        'timezone', v_tz,
        'premium', v_premium,
        'days', v_days_out,
        'rejected', v_rejected,
        'lifetime_steps', (SELECT lifetime_steps FROM users WHERE id = p_user_id),
        'streak_days', v_streak,
        'streak_last_day', v_streak_last,
        'route', CASE WHEN v_route.id IS NULL THEN NULL ELSE jsonb_build_object(
            'user_route_id', v_route.id,
            'route_id',      v_route.route_id,
            'steps_before',  v_route.steps_done,
            'steps_after',   coalesce(v_after, v_route.steps_done),
            'total_steps',   v_route.total_steps,
            'finished',      coalesce(v_after, v_route.steps_done) >= v_route.total_steps) END
    );
END
$fn$;
"""

DOWNGRADE_SQL = "DROP FUNCTION IF EXISTS sync_daily_steps(uuid, jsonb, text, text, integer, integer, integer);"


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
