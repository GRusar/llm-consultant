import pytest
import fakeredis.aioredis


# shared fixture: fake redis client
@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)
