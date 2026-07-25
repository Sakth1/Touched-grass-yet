from browser_url_extractor.utils import is_trackable_url, normalize_url


def test_is_trackable_url_rejects_about_blank():
    assert is_trackable_url("about:blank") is False


def test_is_trackable_url_rejects_about_newtab():
    assert is_trackable_url("about:newtab") is False


def test_is_trackable_url_rejects_chrome_newtab():
    assert is_trackable_url("chrome://newtab/") is False


def test_is_trackable_url_rejects_chrome_newtab_no_slash():
    assert is_trackable_url("chrome://newtab") is False


def test_is_trackable_url_rejects_chrome_settings():
    assert is_trackable_url("chrome://settings/") is False


def test_is_trackable_url_rejects_edge_newtab():
    assert is_trackable_url("edge://newtab/") is False


def test_is_trackable_url_rejects_brave_newtab():
    assert is_trackable_url("brave://newtab/") is False


def test_is_trackable_url_rejects_opera_newtab():
    assert is_trackable_url("opera://newtab/") is False


def test_is_trackable_url_rejects_vivaldi_newtab():
    assert is_trackable_url("vivaldi://newtab/") is False


def test_is_trackable_url_accepts_http():
    assert is_trackable_url("http://example.com") is True


def test_is_trackable_url_accepts_https():
    assert is_trackable_url("https://github.com/Sakth1/Touched-grass-yet") is True


def test_is_trackable_url_accepts_www():
    assert is_trackable_url("www.example.com") is True


def test_is_trackable_url_rejects_none():
    assert is_trackable_url(None) is False


def test_is_trackable_url_rejects_empty():
    assert is_trackable_url("") is False


def test_is_trackable_url_rejects_whitespace():
    assert is_trackable_url("   ") is False


def test_is_trackable_url_rejects_chrome_extension():
    assert is_trackable_url("chrome-extension://abc123/popup.html") is False


def test_is_trackable_url_rejects_view_source():
    assert is_trackable_url("view-source:http://example.com") is False


def test_is_trackable_url_rejects_data_uri():
    assert is_trackable_url("data:text/html,hello") is False


def test_normalize_url_adds_http():
    assert normalize_url("example.com") == "http://example.com"


def test_normalize_url_keeps_https():
    assert normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_keeps_http():
    assert normalize_url("http://example.com") == "http://example.com"


def test_normalize_url_keeps_about():
    assert normalize_url("about:blank") == "about:blank"


def test_normalize_url_keeps_chrome():
    assert normalize_url("chrome://newtab/") == "chrome://newtab/"


def test_normalize_url_strips_whitespace():
    assert normalize_url("  example.com  ") == "http://example.com"
