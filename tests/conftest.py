import ecdsa
import pytest

# own
from main import Client


@pytest.fixture(scope="session")
def client():
    # TODO: set aliases to these keys rather than to hardcode the address.
    with open('keys/user_01.key') as f:
        # b1917dfe83c6fa47b53aee554347e2fae535c7b2e035191946272df19b31694d
        user_01_key = ecdsa.SigningKey.from_pem(f.read())
    with open('keys/user_02.key') as f:
        # b6285fe69a577b33773805c0e544cb19c7f1114faf2ae43322bebf8d3edcd225
        user_02_key = ecdsa.SigningKey.from_pem(f.read())
    with open('keys/user_03.key') as f:
        # 5803922ef28c4db7e6ca909cb35644400d9ec08cb3f1d7cfb29399afac149883
        user_03_key = ecdsa.SigningKey.from_pem(f.read())
    with open('keys/user_04.key') as f:
        # d79a2f79fb96a0e687094bc896251dae046e571e02d80d2c940f1a18a539f650
        user_04_key = ecdsa.SigningKey.from_pem(f.read())

    return Client([user_01_key, user_02_key, user_03_key, user_04_key])
