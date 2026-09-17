from app.config import Settings


def test_groq_api_key_reads_from_roq_api_key_env_var(monkeypatch):
    monkeypatch.setenv("ROQ_API_KEY", "real-groq-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.groq_api_key == "real-groq-key"


def test_groq_api_key_defaults_to_none_without_roq_api_key(monkeypatch):
    monkeypatch.delenv("ROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.groq_api_key is None
