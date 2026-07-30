import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from core.collectors.windows.url_extractor import is_trackable_url, normalize_url

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
                domain = self._extract_domain(host)
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

    def _extract_domain(self, host: str) -> str | None:
        if not host:
            return None
        if self._psl is not None:
            try:
                result = self._psl.privatesuffix(host)
                if result:
                    return result
            except Exception:
                logger.debug("PSL lookup failed for %s", host, exc_info=True)
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host
