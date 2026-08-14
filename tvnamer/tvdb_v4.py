"""Minimal TheTVDB API v4 client used by tvnamer."""

import logging
from urllib.parse import parse_qs, urlparse

import requests


LOG = logging.getLogger(__name__)
BASE_URL = "https://api4.thetvdb.com/v4"
__version__ = "4"


class TvdbError(Exception):
    """The TVDB API could not complete a request."""


class ShowNotFound(TvdbError):
    """No matching TVDB series was found."""


class UserAbort(TvdbError):
    """The user declined to choose a series."""


class Series(object):
    def __init__(self, identifier, name, episodes):
        self.id = identifier
        self.name = name
        self.episodes = episodes


class Tvdb(object):
    """Fetch the subset of TVDB v4 data needed to name TV episodes."""

    def __init__(self, apikey, interactive=True, language="en", dvdorder=False,
                 search_all_languages=True, session=None, base_url=BASE_URL):
        self.apikey = apikey
        self.interactive = interactive
        
        # Map legacy 2-letter language codes to TVDB v4 3-letter codes
        lang_map = {
            "en": "eng", "fr": "fra", "es": "spa", "it": "ita", "de": "deu",
            "ru": "rus", "pt": "por", "nl": "nld", "da": "dan", "fi": "fin",
            "sv": "swe", "no": "nor", "cs": "ces", "pl": "pol", "hu": "hun",
            "el": "ell", "ja": "jpn", "zh": "zho", "ko": "kor"
        }
        self.language = lang_map.get(language.lower(), language)
        self.dvdorder = dvdorder
        self.search_all_languages = search_all_languages
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")
        self._series = {}
        self._login()

    def _login(self):
        try:
            response = self.session.post(self.base_url + "/login", json={"apikey": self.apikey}, timeout=30)
            payload = response.json()
        except requests.RequestException as error:
            raise TvdbError(str(error))
        except ValueError as error:
            raise TvdbError("Invalid response from TheTVDB login: %s" % error)
        token = payload.get("data", {}).get("token")
        if not response.ok or not token:
            raise TvdbError(payload.get("message", "TheTVDB login failed"))
        self.session.headers.update({"Authorization": "Bearer " + token})

    def _get(self, path, **params):
        params = {key: value for key, value in params.items() if value is not None}
        try:
            response = self.session.get(self.base_url + path, params=params, timeout=30)
            payload = response.json()
        except requests.RequestException as error:
            raise TvdbError(str(error))
        except ValueError as error:
            raise TvdbError("Invalid response from TheTVDB: %s" % error)
        if not response.ok or payload.get("status") == "failure":
            raise TvdbError(payload.get("message", "TheTVDB request failed"))
        return payload.get("data"), payload.get("links") or {}

    def _select_series(self, results, query):
        series = [item for item in results if item.get("type") in (None, "series")]
        if not series:
            raise ShowNotFound("Show %s not found" % query)
        if len(series) == 1 or not self.interactive:
            return series[0]
        print("TVDB Search Results:")
        for number, item in enumerate(series, 1):
            print("%d -> %s [%s] # https://thetvdb.com/series/%s" % (
                number, item.get("name", "Unknown"), item.get("primary_language", ""),
                item.get("tvdb_id", item.get("id")),
            ))
        print("Enter the number of the correct series (or anything else to skip):")
        try:
            selection = int(input().strip())
            return series[selection - 1]
        except (ValueError, IndexError, EOFError):
            raise UserAbort("Series selection cancelled")

    def _episodes(self, series_id):
        season_type = "dvd" if self.dvdorder else "default"
        page = 0
        episodes = []
        while page is not None:
            default_data, links = self._get("/series/%s/episodes/%s" % (series_id, season_type), page=page)
            default_eps = default_data.get("episodes", []) if isinstance(default_data, dict) else (default_data or [])
            
            translated_data, _ = self._get("/series/%s/episodes/%s/%s" % (series_id, season_type, self.language), page=page)
            translated_eps = translated_data.get("episodes", []) if isinstance(translated_data, dict) else (translated_data or [])
            
            trans_map = {ep["id"]: ep for ep in translated_eps if ep.get("id")}
            for default_ep in default_eps:
                trans_ep = trans_map.get(default_ep.get("id"))
                if trans_ep and trans_ep.get("name"):
                    default_ep["name"] = trans_ep["name"]
            
            episodes.extend(default_eps)
            next_page = links.get("next")
            if isinstance(next_page, int):
                page = next_page
            elif isinstance(next_page, str):
                # v4 deployments have returned both a numeric page and a URL.
                page_values = parse_qs(urlparse(next_page).query).get("page")
                page = int(page_values[0]) if page_values and page_values[0].isdigit() else None
            else:
                page = None
        return episodes

    def _series_name(self, series_id, fallback=None):
        try:
            translation, _ = self._get("/series/%s/translations/%s" % (series_id, self.language))
            if translation and translation.get("name"):
                return translation["name"]
        except TvdbError:
            LOG.debug("No %s translation for series %s", self.language, series_id)
        data, _ = self._get("/series/%s/extended" % series_id, short="true")
        return data.get("name") or fallback or str(series_id)

    def get_series(self, series_id, fallback_name=None):
        series_id = int(series_id)
        if series_id not in self._series:
            self._series[series_id] = Series(
                series_id, self._series_name(series_id, fallback_name), self._episodes(series_id)
            )
        return self._series[series_id]

    def search(self, query):
        # The v4 endpoint searches every language unless explicitly filtered.
        data, _ = self._get(
            "/search", query=query, type="series",
            language=None if self.search_all_languages else self.language,
        )
        selected = self._select_series(data or [], query)
        series_id = selected.get("tvdb_id") or selected.get("id")
        if series_id is None:
            raise ShowNotFound("Search result for %s did not include a series ID" % query)
        return self.get_series(series_id, selected.get("name"))
