from backend.app.services.security import hash_password, verify_password


def test_hash_password_does_not_store_plaintext():
    stored_hash = hash_password("correct horse battery staple")

    assert stored_hash != "correct horse battery staple"
    assert "correct horse battery staple" not in stored_hash


def test_verify_password_accepts_matching_password():
    stored_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", stored_hash) is True


def test_verify_password_rejects_wrong_password():
    stored_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong password", stored_hash) is False


def test_hash_password_uses_a_unique_salt():
    first_hash = hash_password("correct horse battery staple")
    second_hash = hash_password("correct horse battery staple")

    assert first_hash != second_hash
