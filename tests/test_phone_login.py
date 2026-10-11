"""Phone login: Discord's signature must verify, or the interaction is refused."""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.phone_login import verify


def _keys():
    sk = Ed25519PrivateKey.generate()
    return sk, sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def test_signed_by_discord_passes():
    sk, pk = _keys()
    body, ts = b'{"type":1}', "1700000000"
    assert verify(sk.sign(ts.encode() + body).hex(), ts, body, pk)


def test_tampered_or_unsigned_is_refused():
    sk, pk = _keys()
    body, ts = b'{"type":1}', "1700000000"
    sig = sk.sign(ts.encode() + body).hex()
    assert not verify(sig, ts, b'{"type":2}', pk)          # body changed
    assert not verify(sig, "1700000001", body, pk)          # timestamp changed
    assert not verify("", ts, body, pk)                     # no signature
    assert not verify(sig, ts, body, "")                    # no key configured
    assert not verify("zz", ts, body, pk)                   # garbage
