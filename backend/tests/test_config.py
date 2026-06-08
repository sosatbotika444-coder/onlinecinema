from app.config import Settings


def test_cors_origins_accept_plain_railway_string() -> None:
    settings = Settings(cors_origins="https://sex-party.netlify.app/")
    assert settings.cors_origin_list == ["https://sex-party.netlify.app"]


def test_cors_origins_accept_comma_separated_values() -> None:
    settings = Settings(cors_origins="https://a.example, https://b.example/")
    assert settings.cors_origin_list == ["https://a.example", "https://b.example"]
