"""Прогон миграций и SQL-тестов на чистой базе через psql.

Не требует SQLAlchemy/драйверов: SQL из миграций собирается подменой alembic.op.
Использует стандартные переменные PGHOST/PGPORT/PGUSER.

    PGHOST=/path/to/socket PGPORT=55432 PGUSER=postgres python backend/tests/run_sql_tests.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "migrations" / "versions"
TEST_DB = "putnik_test"


class _OpRecorder:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, sql: str) -> None:
        self.sql.append(sql)


def _load_migrations(direction: str) -> str:
    rec = _OpRecorder()
    alembic = types.ModuleType("alembic")
    alembic.op = rec  # type: ignore[attr-defined]
    sys.modules["alembic"] = alembic
    files = sorted(VERSIONS.glob("[0-9][0-9][0-9][0-9]_*.py"))
    if direction == "downgrade":
        files = list(reversed(files))
    for f in files:
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        getattr(mod, direction)()
    return "\n".join(rec.sql)


def psql(db: str, sql: str | None = None, file: Path | None = None, tuples: bool = False) -> str:
    cmd = ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", db] + (["-tA"] if tuples else [])
    cmd += ["-f", str(file)] if file else ["-c", sql or ""]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
        raise SystemExit(f"psql failed on {file or sql[:60]!r}")
    return res.stdout


def concurrency_test() -> None:
    """Регрессия на deadlock из ревью: «INSERT ad_bonuses → sync» в двух транзакциях одновременно.

    Вставка в ad_bonuses берёт KEY SHARE на строку users через внешний ключ; с FOR UPDATE
    в функции это давало deadlock, с FOR NO KEY UPDATE — нет. Плюс проверяем, что
    параллельные синки дают ровно тот зачёт, что и последовательные.
    """
    user = "00000000-0000-0000-0000-00000000000b"
    script = f"""
BEGIN;
INSERT INTO ad_bonuses (user_id, id, day, ad_unit_id, status)
VALUES ('{user}', gen_random_uuid(), (now() AT TIME ZONE 'Asia/Vladivostok')::date, 'R-M-TEST', 'granted');
SELECT pg_sleep(0.3);
SELECT sync_daily_steps('{user}', jsonb_build_array(jsonb_build_object(
    'day', (now() AT TIME ZONE 'Asia/Vladivostok')::date, 'steps', 9000, 'source', 'sensor')));
COMMIT;
"""
    procs = [
        subprocess.Popen(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", TEST_DB, "-c", script],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(4)
    ]
    errors = []
    for p in procs:
        out, err = p.communicate(timeout=60)
        if p.returncode != 0:
            errors.append(err.strip())
    if errors:
        raise SystemExit("параллельные синки упали:\n" + "\n".join(errors))
    # 4 бонуса по 1 000 → лимит 2 000 + 4 000 = 6 000 из 9 000 (если пользователь бесплатный)
    credited = psql(TEST_DB, f"""SELECT credited_steps FROM daily_steps
        WHERE user_id = '{user}' AND day = (now() AT TIME ZONE 'Asia/Vladivostok')::date""", tuples=True).strip()
    if credited != "6000":
        raise SystemExit(f"параллельный зачёт: ожидали 6000, получили {credited}")
    print("concurrency: ok (4 параллельных «бонус → синк», без deadlock, зачёт 6000)")


def main() -> None:
    psql("postgres", f"DROP DATABASE IF EXISTS {TEST_DB}")
    psql("postgres", f"CREATE DATABASE {TEST_DB}")

    up = ROOT / "tests" / ".upgrade.sql"
    up.write_text(_load_migrations("upgrade"), encoding="utf-8")
    psql(TEST_DB, file=up)
    print("upgrade: ok")

    print(psql(TEST_DB, file=ROOT / "tests" / "sql" / "test_steps_sync.sql").strip())
    concurrency_test()

    down = ROOT / "tests" / ".downgrade.sql"
    down.write_text(_load_migrations("downgrade"), encoding="utf-8")
    psql(TEST_DB, file=down)
    left = psql(TEST_DB, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'", tuples=True)
    if left.strip() != "0":
        raise SystemExit(f"downgrade оставил таблицы: {left!r}")
    print("downgrade: ok, таблиц не осталось")

    # повторный upgrade после downgrade — миграции обратимы
    psql(TEST_DB, file=up)
    print("re-upgrade: ok")
    up.unlink()
    down.unlink()


if __name__ == "__main__":
    main()
