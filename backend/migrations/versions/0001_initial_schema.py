"""Начальная схема «Путника».

Revision ID: 0001_initial_schema
Revises: —
Create Date: 2026-10-28 (с правками ревью backend / security / scalability)

Принципы:
* PostgreSQL 16+ (Yandex Managed PostgreSQL). Никаких расширений: в Managed PG
  они включаются через консоль, а миграция должна проходить на «голом» кластере.
  gen_random_uuid() встроена с PG13, NULLS NOT DISTINCT есть с PG15.
* Перечисления — text + CHECK, а не ENUM: новое значение = одна строка в миграции.
* Время — timestamptz в UTC. «День шагов» — date по локальному поясу пользователя
  (D-08), пояс хранится в users.timezone и копируется в строку дня.
* 17 таблиц из ТЗ + служебные. Зачем каждая — docs/02-data-model.md.
* Гео-полей в пользовательских таблицах нет. Координаты — только у контента маршрутов.
* ПРАВИЛО БЛОКИРОВОК: любая транзакция, которая пишет данные пользователя
  (синк, бонус, старт маршрута, медали, лента), начинается с
  SELECT … FROM users WHERE id = $1 FOR NO KEY UPDATE. Не FOR UPDATE: он конфликтует
  с KEY SHARE, который берут внешние ключи при вставке в дочерние таблицы → deadlock.
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Месяцы, на которые партиции daily_steps создаются сразу. Дальше их создаёт
# ежедневный воркер: SELECT ensure_daily_steps_partitions(3).
PARTITIONS_FROM = "2026-01-01"
PARTITIONS_MONTHS = 24

UPGRADE_SQL = r"""
-- =====================================================================
-- Справочники контента (наполняются импортом из content/, не руками)
-- =====================================================================

CREATE TABLE meeples (
    id          smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE CHECK (code ~ '^[a-z0-9_]{2,40}$'),
    gender      text NOT NULL CHECK (gender IN ('m', 'f')),
    pose        text NOT NULL CHECK (pose IN ('walk', 'run', 'dog', 'stroller', 'backpack')),
    is_free     boolean NOT NULL DEFAULT false,
    name        jsonb NOT NULL CHECK (name ? 'ru'),          -- {"ru","en","zh"}
    sprite_key  text NOT NULL,                               -- ключ в Object Storage
    sort        smallint NOT NULL DEFAULT 0,
    is_active   boolean NOT NULL DEFAULT true
);

CREATE TABLE routes (
    id               integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug             text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{2,64}$'),
    scope            text NOT NULL CHECK (scope IN ('city', 'intercity', 'world')),
    country_code     char(2) NOT NULL,
    region_code      text,                                   -- ISO 3166-2, напр. RU-MOW
    title            jsonb NOT NULL CHECK (title ? 'ru'),
    description      jsonb NOT NULL DEFAULT '{}'::jsonb,
    distance_m       integer NOT NULL CHECK (distance_m > 0 AND distance_m <= 50000000),
    -- Длина шага фиксирована ТЗ: 75 см. Шаги = ceil(distance_m * 100 / 75).
    -- bigint-арифметика: мировые маршруты до 50 000 км не переполняют integer.
    -- Импортёр контента эту колонку НЕ пишет (GENERATED ALWAYS).
    total_steps      integer GENERATED ALWAYS AS (((distance_m::bigint * 100 + 74) / 75)::integer) STORED,
    is_loop          boolean NOT NULL DEFAULT false,
    tier             text NOT NULL CHECK (tier IN ('free', 'premium')),
    cover_key        text,                                   -- обложка в каталоге
    -- Линия маршрута лежит в Object Storage (GeoJSON LineString + накопленные
    -- расстояния по вершинам). Версия и хэш — для кэша на клиенте.
    geometry_key     text,
    geometry_version integer NOT NULL DEFAULT 0,
    geometry_sha256  char(64),
    status           text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    sort             smallint NOT NULL DEFAULT 0,
    content_version  integer NOT NULL DEFAULT 1,              -- растёт при любой правке точек/фактов
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CHECK (status <> 'published' OR geometry_key IS NOT NULL)
);

CREATE TABLE route_points (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_id    integer NOT NULL REFERENCES routes (id) ON DELETE CASCADE,
    seq         smallint NOT NULL CHECK (seq >= 0),
    code        text NOT NULL CHECK (code ~ '^[a-z0-9-]{2,64}$'),
    kind        text NOT NULL CHECK (kind IN ('start', 'checkpoint', 'finish')),
    card_type   text NOT NULL CHECK (card_type IN ('city', 'surroundings', 'region')),
    name        jsonb NOT NULL CHECK (name ? 'ru'),
    lat         numeric(9, 6) NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon         numeric(9, 6) NOT NULL CHECK (lon BETWEEN -180 AND 180),
    distance_m  integer NOT NULL CHECK (distance_m >= 0),     -- от старта по линии маршрута
    UNIQUE (route_id, seq),
    UNIQUE (route_id, code),
    UNIQUE (route_id, distance_m)
);

CREATE TABLE route_facts (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    point_id    integer NOT NULL REFERENCES route_points (id) ON DELETE CASCADE,
    locale      text NOT NULL CHECK (locale IN ('ru', 'en', 'zh')),
    sort        smallint NOT NULL DEFAULT 0,
    title       text NOT NULL DEFAULT '',
    body        text NOT NULL DEFAULT '',
    image_key   text,
    source_url  text,
    status      text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (point_id, locale, sort),
    -- опубликовать пустой шаблон нельзя
    CHECK (status = 'draft' OR (length(title) > 0 AND length(body) > 0))
);

CREATE TABLE npcs (
    id                  smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                text NOT NULL UNIQUE,
    name                jsonb NOT NULL CHECK (name ? 'ru'),
    base_pace_m_per_day integer NOT NULL CHECK (base_pace_m_per_day BETWEEN 500 AND 50000),
    sprite_key          text NOT NULL,
    is_active           boolean NOT NULL DEFAULT true
);

CREATE TABLE medals (
    id                 smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code               text NOT NULL UNIQUE,
    kind               text NOT NULL CHECK (kind IN ('route_finish', 'milestone', 'streak', 'distance')),
    -- milestone: 25/50/75 (%); streak: дни подряд; distance: метры суммарно
    threshold          integer CHECK (threshold > 0),
    route_id           integer REFERENCES routes (id) ON DELETE CASCADE,
    title              jsonb NOT NULL CHECK (title ? 'ru'),
    description        jsonb NOT NULL DEFAULT '{}'::jsonb,
    icon_key           text NOT NULL,
    is_premium_reward  boolean NOT NULL DEFAULT false,      -- «доп. награды» подписчиков
    sort               smallint NOT NULL DEFAULT 0,
    CHECK (kind = 'route_finish' OR threshold IS NOT NULL),
    CHECK (kind <> 'milestone' OR threshold IN (25, 50, 75))
);

-- =====================================================================
-- Пользователи и авторизация
-- =====================================================================

CREATE TABLE users (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email             text UNIQUE CHECK (email = lower(email) AND length(email) <= 254),
    email_verified_at timestamptz,
    password_hash     text,                                   -- argon2id; NULL у OAuth-only
    nickname          text NOT NULL CHECK (char_length(nickname) BETWEEN 2 AND 24),
    -- 6 символов без 0/O/1/I: 32^6 ≈ 1,07 млрд кодов
    friend_code       char(6) NOT NULL UNIQUE CHECK (friend_code ~ '^[2-9A-HJ-NP-Z]{6}$'),
    locale            text NOT NULL DEFAULT 'ru' CHECK (locale IN ('ru', 'en', 'zh')),
    timezone          text NOT NULL DEFAULT 'Europe/Moscow',  -- IANA, проверяет триггер
    meeple_id         smallint REFERENCES meeples (id),
    -- NULL = пользователь не вводил; калории считаются с 70 кг по умолчанию в коде
    weight_kg         numeric(4, 1) CHECK (weight_kg BETWEEN 30 AND 250),
    share_activity    boolean NOT NULL DEFAULT true,          -- маршрут и % видны друзьям (ТЗ); можно выключить
    trial_ends_at     timestamptz,                            -- 7 дней с регистрации, 1 раз на аккаунт
    -- Денормализованный кэш права на премиум: max(trial_ends_at, конец оплаченного периода).
    -- Обновляется в той же транзакции, что и subscriptions. Читается на каждом батче шагов.
    premium_until     timestamptz,
    -- Счётчики, которые обновляет sync_daily_steps: сводка и медали без чтения всей истории
    lifetime_steps    bigint NOT NULL DEFAULT 0 CHECK (lifetime_steps >= 0),
    streak_days       integer NOT NULL DEFAULT 0 CHECK (streak_days >= 0),
    streak_last_day   date,
    last_step_day     date,                                   -- для напоминания о простое
    -- Растёт при смене пароля, выходе отовсюду, удалении → access JWT с меньшей версией недействителен
    token_version     integer NOT NULL DEFAULT 0,
    push_enabled      boolean NOT NULL DEFAULT true,
    quiet_start       time NOT NULL DEFAULT '22:00',
    quiet_end         time NOT NULL DEFAULT '09:00',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    last_seen_at      timestamptz,
    -- Мягкое удаление: друзья и заявки удаляются сразу, код меняется; вход в течение
    -- 30 дней восстанавливает аккаунт, затем purge_deleted удаляет строку целиком.
    deleted_at        timestamptz
);
CREATE INDEX users_purge ON users (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX users_idle ON users (last_step_day) WHERE deleted_at IS NULL AND push_enabled;

CREATE FUNCTION users_check_timezone() RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = NEW.timezone) THEN
        RAISE EXCEPTION 'invalid_timezone: %', NEW.timezone USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END
$fn$;
CREATE TRIGGER users_timezone_check
    BEFORE INSERT OR UPDATE OF timezone ON users
    FOR EACH ROW EXECUTE FUNCTION users_check_timezone();

-- Согласия по 152-ФЗ: какую версию документа и когда принял пользователь.
-- Отдельная таблица, а не колонка: при новой версии политики согласие берётся заново,
-- история нужна как доказательство.
CREATE TABLE consents (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind            text NOT NULL CHECK (kind IN ('privacy_policy', 'terms', 'marketing_push')),
    policy_version  text NOT NULL CHECK (length(policy_version) BETWEEN 1 AND 32),
    accepted_at     timestamptz NOT NULL DEFAULT now(),
    withdrawn_at    timestamptz,
    ip              inet,                                     -- из заголовка API Gateway, не из X-Forwarded-For
    UNIQUE (user_id, kind, policy_version)
);

CREATE TABLE auth_providers (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider         text NOT NULL CHECK (provider IN ('email', 'yandex', 'vk', 'google')),
    provider_subject text NOT NULL,      -- id у провайдера; для email — сам email. Токены провайдера НЕ храним.
    created_at       timestamptz NOT NULL DEFAULT now(),
    last_login_at    timestamptz,
    UNIQUE (provider, provider_subject),
    UNIQUE (user_id, provider)
);

-- Ротируемые refresh-токены. Храним только SHA-256. Повторное использование
-- уже заменённого токена = кража → отзываем всю family.
CREATE TABLE refresh_sessions (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    family_id         uuid NOT NULL,
    family_expires_at timestamptz NOT NULL,                   -- абсолютный предел цепочки: 180 дней от первого входа
    token_hash        bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32),
    install_id        text CHECK (length(install_id) <= 64),
    created_at        timestamptz NOT NULL DEFAULT now(),
    expires_at        timestamptz NOT NULL,
    revoked_at        timestamptz,
    replaced_by       uuid REFERENCES refresh_sessions (id) ON DELETE SET NULL,
    CHECK (expires_at <= family_expires_at)
);
CREATE INDEX refresh_sessions_user_active ON refresh_sessions (user_id) WHERE revoked_at IS NULL;
CREATE INDEX refresh_sessions_family ON refresh_sessions (family_id);
CREATE INDEX refresh_sessions_expires ON refresh_sessions (expires_at);
CREATE INDEX refresh_sessions_replaced_by ON refresh_sessions (replaced_by) WHERE replaced_by IS NOT NULL;

-- Одноразовые токены: подтверждение email и сброс пароля. Только хэш.
CREATE TABLE auth_tokens (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    purpose     text NOT NULL CHECK (purpose IN ('verify_email', 'reset_password')),
    token_hash  bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32),
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz
);
CREATE INDEX auth_tokens_user ON auth_tokens (user_id, purpose);
CREATE INDEX auth_tokens_expires ON auth_tokens (expires_at);

CREATE TABLE devices (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    install_id    text NOT NULL CHECK (length(install_id) <= 64),  -- генерирует приложение, не IMEI/Android ID
    push_provider text NOT NULL DEFAULT 'rustore' CHECK (push_provider IN ('rustore', 'none')),
    push_token    text,
    app_version   text,
    os_version    text,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, install_id)
);
CREATE UNIQUE INDEX devices_push_token ON devices (push_token) WHERE push_token IS NOT NULL;

-- Ответы на запросы с Idempotency-Key: повтор с тем же ключом получает сохранённый ответ.
-- Ключ уникален в паре с пользователем — чужой ключ не виден и не мешает. Хранение 24 ч.
CREATE TABLE idempotency_keys (
    user_id         uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key             uuid NOT NULL,
    request_sha256  bytea NOT NULL CHECK (octet_length(request_sha256) = 32),  -- тот же ключ + другое тело → 422
    status_code     smallint,
    response        jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)
);
CREATE INDEX idempotency_keys_created ON idempotency_keys (created_at);

-- =====================================================================
-- Путешествия
-- =====================================================================

CREATE TABLE user_routes (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    route_id          integer NOT NULL REFERENCES routes (id),
    status            text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'finished', 'abandoned')),
    -- Прогресс = зачтённые шаги, а не координаты. Позицию на линии считает клиент.
    steps_done        integer NOT NULL DEFAULT 0 CHECK (steps_done >= 0),
    start_day         date NOT NULL,                          -- локальный день старта
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    group_id          uuid,                                   -- совместный маршрут (этап 8)
    route_content_ver integer NOT NULL DEFAULT 1,
    CHECK ((status = 'finished') = (finished_at IS NOT NULL))
);
-- Ровно один активный маршрут у пользователя
CREATE UNIQUE INDEX user_routes_one_active ON user_routes (user_id) WHERE status = 'active';
CREATE INDEX user_routes_user ON user_routes (user_id, started_at DESC);
CREATE INDEX user_routes_group ON user_routes (group_id) WHERE group_id IS NOT NULL;

-- Шаги по локальным дням. Партиции по месяцам, ключ (user_id, day).
-- raw_steps — сколько насчитал телефон (максимум из присланного, GREATEST).
-- credited_steps — сколько зачтено в путешествие с учётом лимита 2 000 + бонусов.
-- Обе величины только растут, поэтому повтор батча ничего не меняет.
-- fillfactor=80 задаётся на каждой партиции (у родителя нельзя): строка дня
-- обновляется до ~12 раз в сутки, свободное место даёт HOT-обновления без раздувания индекса.
CREATE TABLE daily_steps (
    user_id         uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    day             date NOT NULL,
    raw_steps       integer NOT NULL CHECK (raw_steps BETWEEN 0 AND 150000),
    credited_steps  integer NOT NULL DEFAULT 0,
    source          text NOT NULL CHECK (source IN ('health_connect', 'sensor')),
    install_id      text,
    tz              text NOT NULL,                             -- пояс, в котором открыт день; клиент считает день в нём
    flags           smallint NOT NULL DEFAULT 0,               -- битовые флаги антифрода
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, day),
    CHECK (credited_steps BETWEEN 0 AND raw_steps)
) PARTITION BY RANGE (day);

CREATE TABLE goals (
    user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    period       text NOT NULL CHECK (period IN ('day', 'week', 'month')),
    target_steps integer NOT NULL CHECK (target_steps BETWEEN 500 AND 5000000),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, period)
);

-- Состояние попутчика в конкретном путешествии: снимок «на день as_of_day».
-- Сервис дошагивает его лениво до сегодняшнего дня (детерминированно от seed),
-- поэтому никакой фоновой симуляции нет.
CREATE TABLE user_route_npcs (
    user_route_id   uuid NOT NULL REFERENCES user_routes (id) ON DELETE CASCADE,
    npc_id          smallint NOT NULL REFERENCES npcs (id),
    position_m      integer NOT NULL DEFAULT 0 CHECK (position_m >= 0),
    pace_m_per_day  integer NOT NULL CHECK (pace_m_per_day > 0),
    seed            integer NOT NULL,
    as_of_day       date NOT NULL,
    PRIMARY KEY (user_route_id, npc_id)
);

CREATE TABLE npc_events (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_route_id  uuid NOT NULL REFERENCES user_routes (id) ON DELETE CASCADE,
    npc_id         smallint NOT NULL REFERENCES npcs (id),
    kind           text NOT NULL CHECK (kind IN ('camp', 'wrong_turn', 'rest', 'detour', 'sprint')),
    start_day      date NOT NULL,
    duration_days  smallint NOT NULL CHECK (duration_days BETWEEN 1 AND 7),
    payload        jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (user_route_id, npc_id, start_day)
);

-- =====================================================================
-- Друзья: только код, двустороннее подтверждение, никакой геолокации
-- =====================================================================

CREATE TABLE friend_requests (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id  uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    to_user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    status        text NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled', 'expired')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    responded_at  timestamptz,
    CHECK (from_user_id <> to_user_id)
);
-- Одна открытая заявка на пару, в какую сторону бы она ни шла
CREATE UNIQUE INDEX friend_requests_one_pending
    ON friend_requests (LEAST(from_user_id, to_user_id), GREATEST(from_user_id, to_user_id))
    WHERE status = 'pending';
CREATE INDEX friend_requests_inbox ON friend_requests (to_user_id, created_at DESC) WHERE status = 'pending';
CREATE INDEX friend_requests_outbox ON friend_requests (from_user_id) WHERE status = 'pending';
-- Для паузы 30 дней после отказа: сервис ищет последний declined от того же отправителя
CREATE INDEX friend_requests_declined ON friend_requests (from_user_id, to_user_id, responded_at DESC)
    WHERE status = 'declined';

-- Одна строка на пару, user_a < user_b — дружба симметрична по построению
CREATE TABLE friends (
    user_a      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    user_b      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_a, user_b),
    CHECK (user_a < user_b)
);
CREATE INDEX friends_b ON friends (user_b);

-- Лента друзей. Пишется в транзакции синка/старта маршрута.
-- Приватность: наружу отдаётся только локальная дата (без времени) и только после
-- visible_after = at + 6 ч, чтобы по ленте нельзя было восстановить распорядок дня.
-- Хранение 90 дней (воркер cleanup).
CREATE TABLE feed_events (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind           text NOT NULL CHECK (kind IN ('route_started', 'point_reached', 'milestone', 'route_finished', 'medal')),
    local_day      date NOT NULL,
    payload        jsonb NOT NULL DEFAULT '{}'::jsonb,         -- коды маршрута/точки/медали, без времени и мест пользователя
    at             timestamptz NOT NULL DEFAULT now(),
    visible_after  timestamptz NOT NULL DEFAULT now() + interval '6 hours',
    dedupe_key     text NOT NULL,
    UNIQUE (user_id, dedupe_key)
);
CREATE INDEX feed_events_user ON feed_events (user_id, visible_after DESC, id DESC);
CREATE INDEX feed_events_at ON feed_events (at);

-- =====================================================================
-- Медали
-- =====================================================================

CREATE TABLE user_medals (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    medal_id       smallint NOT NULL REFERENCES medals (id),
    -- CASCADE, а не SET NULL: иначе удаление двух прохождений с одной вехой упирается в UNIQUE
    user_route_id  uuid REFERENCES user_routes (id) ON DELETE CASCADE,
    awarded_at     timestamptz NOT NULL DEFAULT now(),
    -- Вехи и финиш — на каждое прохождение; серии и дистанция — один раз (user_route_id NULL)
    UNIQUE NULLS NOT DISTINCT (user_id, medal_id, user_route_id)
);
CREATE INDEX user_medals_user ON user_medals (user_id, awarded_at DESC);
CREATE INDEX user_medals_route ON user_medals (user_route_id) WHERE user_route_id IS NOT NULL;

-- =====================================================================
-- Монетизация
-- =====================================================================

CREATE TABLE subscriptions (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- SET NULL, а не CASCADE: финансовые записи хранятся по закону о бухучёте,
    -- после удаления аккаунта строка обезличивается, но возврат по ней ещё можно найти.
    user_id                  uuid REFERENCES users (id) ON DELETE SET NULL,
    provider                 text NOT NULL CHECK (provider IN ('rustore', 'yookassa')),
    provider_subscription_id text NOT NULL,
    -- Идентификатор аккаунта, переданный провайдеру при покупке (developerPayload и т.п.).
    -- Сервер сверяет его с user_id: чужую покупку к своему аккаунту не привязать.
    account_ref              text NOT NULL,
    product_id               text NOT NULL,
    plan                     text NOT NULL CHECK (plan IN ('monthly', 'yearly')),
    status                   text NOT NULL
                             CHECK (status IN ('pending', 'active', 'grace', 'on_hold', 'cancelled', 'expired', 'refunded')),
    current_period_start     timestamptz,
    current_period_end       timestamptz,
    auto_renew               boolean NOT NULL DEFAULT true,
    price_minor              integer CHECK (price_minor >= 0),   -- копейки
    currency                 char(3) NOT NULL DEFAULT 'RUB',
    last_verified_at         timestamptz,
    -- Только нужные поля ответа провайдера (статус, даты, id заказа). Данных карт нет и быть не должно.
    provider_payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_subscription_id),
    CHECK (current_period_end IS NULL OR current_period_start IS NULL OR current_period_end > current_period_start)
);
CREATE INDEX subscriptions_user ON subscriptions (user_id, current_period_end DESC);
CREATE INDEX subscriptions_to_recheck ON subscriptions (current_period_end) WHERE status IN ('active', 'grace', 'on_hold');

-- Уведомления провайдеров. Тело — только сигнал: состояние покупки сервер всегда
-- перечитывает по API провайдера. UNIQUE защищает от повтора.
CREATE TABLE billing_events (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider     text NOT NULL CHECK (provider IN ('rustore', 'yookassa')),
    event_id     text NOT NULL,
    received_at  timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    result       text CHECK (result IN ('applied', 'ignored', 'failed')),
    UNIQUE (provider, event_id)
);

-- Бонус за rewarded-ролик. id генерирует клиент (UUID на показ) → повторная
-- отправка того же показа не начислит дважды. Ключ — пара с пользователем,
-- чтобы чужой UUID нельзя было «занять». Потолок в день и интервал проверяет сервис
-- ПОСЛЕ блокировки строки пользователя.
CREATE TABLE ad_bonuses (
    user_id       uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    id            uuid NOT NULL,
    day           date NOT NULL,                               -- локальный день, ставит сервер
    steps         integer NOT NULL DEFAULT 1000 CHECK (steps BETWEEN 1 AND 10000),
    ad_unit_id    text NOT NULL,
    status        text NOT NULL CHECK (status IN ('granted', 'rejected')),
    reject_reason text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, id)
);
CREATE INDEX ad_bonuses_user_day ON ad_bonuses (user_id, day) WHERE status = 'granted';

-- =====================================================================
-- Исходящие очереди (outbox)
-- Воркер берёт пачку «арендой»: UPDATE … SET next_attempt_at/send_after = now() + 5 min
-- … RETURNING, COMMIT, затем HTTP-вызов, затем отметка результата. Транзакция
-- не держится открытой во время сетевого вызова (важно для пулера в режиме транзакций).
-- =====================================================================

-- Серверные события для AppMetrica (подписка продлена/отменена, медаль и т.п.).
-- Клиентские события шлёт SDK напрямую, сюда они не попадают. Отправленные старше 7 дней удаляются.
CREATE TABLE analytics_outbox (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         uuid REFERENCES users (id) ON DELETE CASCADE,
    event           text NOT NULL CHECK (event ~ '^[a-z0-9_]{2,64}$'),
    props           jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at     timestamptz NOT NULL,
    status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'dead')),
    attempts        smallint NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    sent_at         timestamptz
);
CREATE INDEX analytics_outbox_due ON analytics_outbox (next_attempt_at) WHERE status = 'pending';
CREATE INDEX analytics_outbox_user ON analytics_outbox (user_id) WHERE status = 'pending';

-- Пуши: очередь + журнал + дедупликация в одной таблице.
-- dedupe_key, напр. 'milestone:<user_route_id>:50' — одно событие не уйдёт дважды.
-- Лимит «не больше 2 в день» и тихие часы проверяет воркер; в пачку берётся не больше
-- одного пуша на пользователя (DISTINCT ON user_id), чтобы два воркера не обошли лимит.
-- Хранение 30 дней (воркер cleanup).
CREATE TABLE push_outbox (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind         text NOT NULL CHECK (kind IN ('quarter', 'half', 'three_quarters', 'near_city',
                                               'region_enter', 'arrival', 'pace_drop', 'idle', 'friend_request')),
    dedupe_key   text NOT NULL,
    local_day    date NOT NULL,
    priority     smallint NOT NULL DEFAULT 5,                 -- 1 — самый важный (прибытие)
    payload      jsonb NOT NULL DEFAULT '{}'::jsonb,           -- ключи локализации + параметры, не готовый текст
    send_after   timestamptz NOT NULL DEFAULT now(),
    status       text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'suppressed', 'failed')),
    attempts     smallint NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT now(),
    sent_at      timestamptz,
    UNIQUE (user_id, dedupe_key)
);
CREATE INDEX push_outbox_due ON push_outbox (send_after) WHERE status = 'queued';
CREATE INDEX push_outbox_user_day ON push_outbox (user_id, local_day) WHERE status = 'sent';
CREATE INDEX push_outbox_created ON push_outbox (created_at);

-- Счётчики ограничения частоты: перебор кодов друзей (по пользователю, по IP и общий),
-- логины (по IP и по хэшу email), сброс пароля, регистрация. На /steps/days не применяется.
-- UNLOGGED: быстро, после сбоя БД просто обнуляется — для лимитов это нормально.
-- IP берётся только из заголовка, который выставляет API Gateway.
CREATE UNLOGGED TABLE rate_limits (
    bucket        text NOT NULL,                               -- 'friend_code:user:<id>', 'login:ip:<ip>', 'login:email:<sha256>'
    window_start  timestamptz NOT NULL,
    hits          integer NOT NULL DEFAULT 1,
    PRIMARY KEY (bucket, window_start)
);
CREATE INDEX rate_limits_window ON rate_limits (window_start);

-- =====================================================================
-- Партиции daily_steps
-- Создание через CREATE TABLE (LIKE …) + ATTACH PARTITION: ATTACH берёт на родителе
-- только SHARE UPDATE EXCLUSIVE и не останавливает синки (CREATE … PARTITION OF взял бы
-- ACCESS EXCLUSIVE). lock_timeout — чтобы воркер не встал в очередь за долгой транзакцией;
-- при таймауте воркер повторит позже, запас 3 месяца.
-- =====================================================================

CREATE FUNCTION ensure_daily_steps_partitions(months_ahead integer DEFAULT 3)
RETURNS integer
LANGUAGE plpgsql
SET lock_timeout = '2s'
AS $fn$
DECLARE
    m       date := (date_trunc('month', now() AT TIME ZONE 'UTC') - interval '1 month')::date;
    created integer := 0;
    pname   text;
BEGIN
    FOR i IN 0..months_ahead + 1 LOOP
        pname := format('daily_steps_%s', to_char(m, 'YYYY_MM'));
        IF to_regclass(pname) IS NULL THEN
            EXECUTE format(
                'CREATE TABLE %I (LIKE daily_steps INCLUDING DEFAULTS INCLUDING CONSTRAINTS) WITH (fillfactor = 80)',
                pname);
            -- CHECK по диапазону позволяет ATTACH не сканировать таблицу
            EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (day >= %L AND day < %L)',
                pname, pname || '_range', m, (m + interval '1 month')::date);
            EXECUTE format('ALTER TABLE daily_steps ATTACH PARTITION %I FOR VALUES FROM (%L) TO (%L)',
                pname, m, (m + interval '1 month')::date);
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', pname, pname || '_range');
            created := created + 1;
        END IF;
        m := (m + interval '1 month')::date;
    END LOOP;
    RETURN created;
END
$fn$;

-- =====================================================================
-- updated_at
-- =====================================================================

CREATE FUNCTION touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END
$fn$;

CREATE TRIGGER users_touch BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER routes_touch BEFORE UPDATE ON routes FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER subscriptions_touch BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
"""


def _initial_partitions_sql() -> str:
    """Партиции на PARTITIONS_MONTHS месяцев вперёд от PARTITIONS_FROM (на пустой таблице, блокировки не важны)."""
    from datetime import date

    y, m = map(int, PARTITIONS_FROM.split("-")[:2])
    out = []
    for _ in range(PARTITIONS_MONTHS):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append(
            f"CREATE TABLE IF NOT EXISTS daily_steps_{y:04d}_{m:02d} PARTITION OF daily_steps "
            f"FOR VALUES FROM ('{date(y, m, 1)}') TO ('{date(ny, nm, 1)}') WITH (fillfactor = 80);"
        )
        y, m = ny, nm
    return "\n".join(out)


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS rate_limits, push_outbox, analytics_outbox, ad_bonuses, billing_events,
    subscriptions, user_medals, feed_events, friends, friend_requests, npc_events, user_route_npcs,
    goals, daily_steps, user_routes, idempotency_keys, devices, auth_tokens, refresh_sessions,
    auth_providers, consents, users, medals, npcs, route_facts, route_points, routes, meeples CASCADE;
DROP FUNCTION IF EXISTS ensure_daily_steps_partitions(integer);
DROP FUNCTION IF EXISTS touch_updated_at();
DROP FUNCTION IF EXISTS users_check_timezone();
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)
    op.execute(_initial_partitions_sql())


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
