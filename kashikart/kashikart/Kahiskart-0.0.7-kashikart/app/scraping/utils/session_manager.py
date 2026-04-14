import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict
import logging
import cloudscraper

from app.models.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:


    _sessions: Dict[int, requests.Session] = {}

    @classmethod
    def get_session(cls, source: Source) -> requests.Session:


        if source.id not in cls._sessions:
            cls._sessions[source.id] = cls.create_session()

        return cls._sessions[source.id]

    @classmethod
    def create_session(cls) -> requests.Session:
        """
        Build a hardened requests/CloudScraper session.

        Critical fix: disable system proxy inheritance (was pointing to 127.0.0.1:9),
        which was causing HTTPSConnectionPool/ProxyError before any fetch could start.
        """

        base_session = requests.Session()

        # Do not inherit OS/http_proxy/https_proxy env vars
        base_session.trust_env = False
        base_session.proxies.clear()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        base_session.mount("http://", adapter)
        base_session.mount("https://", adapter)

        # Wrap in cloudscraper to bypass anti-bot protections
        session = cloudscraper.create_scraper(sess=base_session)

        # Double‑ensure no proxies are used
        session.proxies = {}
        session.trust_env = False

        # Set headers
        session.headers.update({
            'User-Agent': settings.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        return session

    @classmethod
    def close_session(cls, source_id: int):


        if source_id in cls._sessions:
            cls._sessions[source_id].close()
            del cls._sessions[source_id]
            logger.info(f"Closed session for source {source_id}")

    @classmethod
    def close_all_sessions(cls):


        for source_id in list(cls._sessions.keys()):
            cls.close_session(source_id)

        logger.info("Closed all sessions")
