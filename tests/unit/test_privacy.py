"""
Unit tests for encryption (UT-10, UT-11).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from surakshaedge.edge.privacy import decrypt_payload, encrypt_payload


# UT-10: AES-GCM round trip
def test_encrypt_decrypt_round_trip():
    data = b"Hello SurakshaEdge"
    aad = b"test-event-id"
    enc = encrypt_payload(data, aad)
    dec = decrypt_payload(enc, aad)
    assert dec == data


def test_tamper_detection():
    """Flip one bit in ciphertext → decryption should fail."""
    import base64
    data = b"sensitive payload"
    enc = encrypt_payload(data, b"")
    ct = bytearray(base64.b64decode(enc["ciphertext"]))
    ct[5] ^= 0xFF  # Flip byte
    enc["ciphertext"] = base64.b64encode(bytes(ct)).decode()
    with pytest.raises(Exception):
        decrypt_payload(enc, b"")


def test_nonce_uniqueness():
    """10,000 encryption calls should produce unique nonces."""
    nonces = set()
    for _ in range(10000):
        enc = encrypt_payload(b"data", b"")
        nonces.add(enc["nonce"])
    assert len(nonces) == 10000, "Nonce collision detected!"


# UT-11: Replay protection
def test_replay_protection_old_event():
    """Events older than 30s should be rejected by check_replay."""
    import datetime
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from surakshaedge.api.security import check_replay
    old_ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)).isoformat().replace("+00:00", "Z")
    assert check_replay(old_ts) is False


def test_replay_protection_fresh_event():
    """Recent events should pass replay check."""
    import datetime

    from surakshaedge.api.security import check_replay
    fresh_ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    assert check_replay(fresh_ts) is True
