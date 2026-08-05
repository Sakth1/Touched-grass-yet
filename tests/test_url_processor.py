from core.url_processor import UrlProcessor
from utils.net import extract_domain


class TestNormalize:
    def test_none_url(self):
        p = UrlProcessor()
        result = p.normalize(None)
        assert result.url is None
        assert result.is_trackable is False

    def test_empty_string(self):
        p = UrlProcessor()
        result = p.normalize("")
        assert result.url is None
        assert result.is_trackable is False

    def test_https_url(self):
        p = UrlProcessor()
        result = p.normalize("https://github.com/user/repo")
        assert result.url == "https://github.com/user/repo"
        assert result.scheme == "https"
        assert result.host == "github.com"
        assert result.domain == "github.com"
        assert result.path == "/user/repo"
        assert result.is_trackable is True
        assert result.extraction_method is None
        assert result.confidence == "high"

    def test_missing_scheme_added(self):
        p = UrlProcessor()
        result = p.normalize("github.com/user")
        assert result.url == "http://github.com/user"
        assert result.host == "github.com"
        assert result.domain == "github.com"

    def test_subdomain(self):
        p = UrlProcessor()
        result = p.normalize("https://news.ycombinator.com/item?id=123")
        assert result.host == "news.ycombinator.com"
        assert result.domain == "ycombinator.com"

    def test_internal_host_single_part(self):
        p = UrlProcessor()
        result = p.normalize("http://localhost:8080/path")
        assert result.host == "localhost"
        assert result.domain == "localhost"

    def test_trackable_normal(self):
        p = UrlProcessor()
        result = p.normalize("https://example.com/page")
        assert result.is_trackable is True

    def test_about_blank_not_trackable(self):
        p = UrlProcessor()
        result = p.normalize("about:blank")
        assert result.is_trackable is False

    def test_chrome_settings_not_trackable(self):
        p = UrlProcessor()
        result = p.normalize("chrome://settings/")
        assert result.is_trackable is False

    def test_data_url_not_trackable(self):
        p = UrlProcessor()
        result = p.normalize("data:text/html,hello")
        assert result.is_trackable is False

    def test_method_and_confidence_passed_through(self):
        p = UrlProcessor()
        result = p.normalize("https://x.com", method="uia", confidence="high")
        assert result.extraction_method == "uia"
        assert result.confidence == "high"

        result2 = p.normalize(None, method=None, confidence="low")
        assert result2.extraction_method is None
        assert result2.confidence == "low"

    def test_invalid_url_does_not_crash(self):
        p = UrlProcessor()
        result = p.normalize("http://[invalid-host")
        assert result.url is not None


class TestExtractDomain:
    def test_standard_domain(self):
        assert extract_domain("github.com") == "github.com"

    def test_subdomain(self):
        assert extract_domain("news.ycombinator.com") == "ycombinator.com"

    def test_co_uk(self):
        domain = extract_domain("example.co.uk")
        assert domain == "example.co.uk" or domain == "co.uk"

    def test_ip_address(self):
        result = extract_domain("192.168.1.1")
        assert result is not None

    def test_empty_host(self):
        assert extract_domain("") is None
        assert extract_domain(None) is None  # type: ignore

    def test_single_part(self):
        assert extract_domain("localhost") == "localhost"
