from app.config import Settings


def test_settings_safe_display_redacts_secrets():
    settings = Settings(
        tmdb_api_key="super-secret-tmdb",
        jwt_secret="super-secret-jwt",
        admin_api_key="admin-token",
    )
    display = settings.safe_display()

    assert display["tmdb_api_key"] == "***"
    assert display["jwt_secret"] == "***"
    assert display["admin_api_key"] == "***"
    assert "super-secret" not in repr(settings)
    assert "super-secret" not in str(settings)
