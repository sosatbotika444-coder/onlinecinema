from app.security import create_room_code, hash_password, verify_password


def test_room_code_shape() -> None:
    code = create_room_code()
    assert len(code) == 8
    assert code.isalnum()
    assert code.upper() == code


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("secret-room")
    assert verify_password("secret-room", password_hash)
    assert not verify_password("wrong", password_hash)
