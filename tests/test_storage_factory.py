"""Database factory reuse and per-URL isolation tests."""
from sqlalchemy import select, text

from allsales import storage


def test_engine_factory_reused_for_same_database(tmp_path):
    first_url = "sqlite+pysqlite:///" + str(tmp_path / "first.sqlite")
    second_url = "sqlite+pysqlite:///" + str(tmp_path / "second.sqlite")
    storage._factory_for_url.cache_clear()
    first = storage.session_factory(first_url)
    assert first is storage.session_factory(first_url)
    second = storage.session_factory(second_url)
    assert first is not second

    with first.begin() as session:
        session.execute(text("CREATE TABLE isolated_test (entry TEXT)"))
        session.execute(text("INSERT INTO isolated_test (entry) VALUES ('first')"))
    with first() as session:
        assert session.execute(text("SELECT entry FROM isolated_test")).scalar_one() == "first"

    try:
        with second() as session:
            # The second DB must not inherit the first database's schema.
            assert session.execute(text("SELECT count(*) FROM sqlite_master WHERE name = 'isolated_test'")).scalar_one() == 0
    finally:
        first.kw["bind"].dispose()
        second.kw["bind"].dispose()
        storage._factory_for_url.cache_clear()


def test_factory_uses_current_environment_url(monkeypatch, tmp_path):
    url_a = "sqlite+pysqlite:///" + str(tmp_path / "a.sqlite")
    url_b = "sqlite+pysqlite:///" + str(tmp_path / "b.sqlite")
    storage._factory_for_url.cache_clear()
    monkeypatch.setenv("DATABASE_URL", url_a)
    first = storage.session_factory()
    monkeypatch.setenv("DATABASE_URL", url_b)
    second = storage.session_factory()
    try:
        assert first is not second
        assert storage.session_factory(url_a) is first
    finally:
        first.kw["bind"].dispose()
        second.kw["bind"].dispose()
        storage._factory_for_url.cache_clear()
