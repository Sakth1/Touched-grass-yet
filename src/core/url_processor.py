import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from utils.net import extract_domain, is_trackable_url, normalize_url

logger = logging.getLogger(__name__)


@dataclass
class NormalizedUrl:
    url: str | None
    scheme: str | None
    host: str | None
    domain: str | None
    path: str | None
    is_trackable: bool
    extraction_method: str | None
    confidence: str


class UrlProcessor:
    def __init__(self):
        self._psl = None
        try:
            from publicsuffixlist import PublicSuffixList

            self._psl = PublicSuffixList()
            logger.debug("UrlProcessor using publicsuffixlist for domain extraction")
        except ImportError:
            logger.warning(
                "publicsuffixlist not available, using fallback domain extraction"
            )

    def normalize(
        self, url: str | None, method: str | None = None, confidence: str = "high"
    ) -> NormalizedUrl:
        if not url:
            return NormalizedUrl(
                url=None,
                scheme=None,
                host=None,
                domain=None,
                path=None,
                is_trackable=False,
                extraction_method=method,
                confidence=confidence,
            )

        raw = normalize_url(url)
        trackable = is_trackable_url(raw)

        scheme = None
        host = None
        domain = None
        path = None

        try:
            parsed = urlparse(raw)
            scheme = parsed.scheme or None
            host = parsed.hostname or None
            path = parsed.path or None
            if host:
                domain = extract_domain(host, self._psl)
        except Exception:
            logger.debug("Failed to parse URL: %s", raw, exc_info=True)

        return NormalizedUrl(
            url=raw,
            scheme=scheme,
            host=host,
            domain=domain,
            path=path,
            is_trackable=trackable,
            extraction_method=method,
            confidence=confidence,
        )
