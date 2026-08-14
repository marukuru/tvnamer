from tvnamer.tvdb_v4 import Series, Tvdb
from tvnamer.data import EpisodeInfo


class Response(object):
    def __init__(self, payload, ok=True):
        self.payload = payload
        self.ok = ok

    def json(self):
        return self.payload


class Session(object):
    def __init__(self):
        self.headers = {}
        self.requests = []

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return Response({"data": {"token": "token"}})

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if url.endswith("/search"):
            return Response({"data": [{"type": "series", "tvdb_id": "42", "name": "Example"}]})
        if "/translations/" in url:
            return Response({"data": {"name": "Example Show"}})
        if "/episodes/dvd" in url:
            return Response({"data": {"episodes": [
                {"seasonNumber": 1, "number": 2, "name": "DVD episode"}
            ]}, "links": {}})
        raise AssertionError(url)


def test_v4_client_authenticates_searches_and_uses_dvd_episodes():
    session = Session()
    client = Tvdb("key", interactive=False, language="en", dvdorder=True, session=session)

    episode = EpisodeInfo("Example", 1, [2])
    episode.populate_from_tvdb(client)

    assert session.headers["Authorization"] == "Bearer token"
    assert episode.seriesname == "Example Show"
    assert episode.episodename == ["DVD episode"]
    assert any("/episodes/dvd" in request[1] for request in session.requests)


def test_absolute_number_fallback_uses_v4_episode_fields():
    class Client(object):
        def search(self, _name):
            return Series(1, "Example", [{"seasonNumber": 1, "number": 99, "absoluteNumber": 3, "name": "Third"}])

    episode = EpisodeInfo("Example", 1, [3])
    episode.populate_from_tvdb(Client())
    assert episode.episodename == ["Third"]
