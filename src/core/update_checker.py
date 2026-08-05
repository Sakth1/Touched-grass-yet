import hashlib
import json
import logging
import os
import platform
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from utils.constants import LATEST_RELEASE_REPO_URL, RELEASES_PAGE_URL
from utils.files import remove_file
from utils.platform import is_packaged
from utils.versions import compare_versions, get_current_version, normalize_version

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024

_API_VERSION_HEADER = "2022-11-28"


class UpdateCheckError(Exception):
    """Raised when the latest release cannot be fetched or parsed."""


class DownloadError(Exception):
    """Raised when a release asset cannot be downloaded."""


class DigestMismatchError(DownloadError):
    """Raised when a downloaded asset fails sha256 verification."""


class ApplyError(Exception):
    """Raised when a downloaded update cannot be applied."""


class ApplyResult(Enum):
    APPLIED = "applied"
    MANUAL_REQUIRED = "manual_required"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag_name: str
    release_notes: str
    published_at: str
    prerelease: bool
    html_url: str
    asset_name: str | None = None
    asset_url: str | None = None
    asset_size: int | None = None
    asset_digest: str | None = None

    @property
    def is_manual_only(self) -> bool:
        """True when the release has no asset this platform can auto-install."""
        return self.asset_url is None


def _parse_digest(digest: str | None) -> str | None:
    """Extract the hex sha256 from a GitHub asset digest (``sha256:...``)."""
    if not digest:
        return None
    if ":" in digest:
        digest = digest.rsplit(":", 1)[1]
    try:
        bytes.fromhex(digest)
    except ValueError:
        logger.warning("Unparseable asset digest: %r", digest)
        return None
    return digest


def _select_asset(release: dict) -> dict | None:
    """Pick the asset this platform can auto-install, if any."""
    assets = release.get("assets") or []
    system = platform.system()
    for asset in assets:
        name = asset.get("name", "")
        if system == "Windows" and name.endswith("-setup.exe"):
            return asset
        if system == "Android" and name.endswith(".apk"):
            return asset
    if system == "Windows":
        for asset in assets:
            if asset.get("name", "").endswith("-portable.zip"):
                return asset
    return None


def _api_request(url: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION_HEADER,
            "User-Agent": f"Unscreen-updater/{get_current_version()}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class UpdateChecker:
    def __init__(
        self,
        current_version: str | None = None,
        api_url: str = LATEST_RELEASE_REPO_URL,
        timeout: float = 10,
    ):
        self._current_version = normalize_version(
            current_version or get_current_version()
        )
        self._api_url = api_url
        self._timeout = timeout

    @property
    def current_version(self) -> str:
        return self._current_version

    def check_for_update(self) -> UpdateInfo | None:
        """Query the latest release and return it when it is newer than local.

        Returns ``None`` when the app is up to date or the repository has no
        releases yet. Raises :class:`UpdateCheckError` on network/API failure.
        """
        try:
            release = _api_request(self._api_url, self._timeout)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                logger.warning("No releases found at %s", self._api_url)
                return None
            raise UpdateCheckError(f"GitHub API returned HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise UpdateCheckError(f"Could not reach GitHub API: {error}") from error
        except json.JSONDecodeError as error:
            raise UpdateCheckError("GitHub API returned invalid JSON") from error

        update = self._build_update_info(release)
        if compare_versions(update.version, self._current_version) <= 0:
            logger.info("No update available (current %s)", self._current_version)
            return None
        logger.info("Update available: %s -> %s", self._current_version, update.version)
        return update

    def _build_update_info(self, release: dict) -> UpdateInfo:
        tag = release.get("tag_name", "")
        asset = _select_asset(release)
        return UpdateInfo(
            version=normalize_version(tag),
            tag_name=tag,
            release_notes=release.get("body") or "",
            published_at=release.get("published_at") or "",
            prerelease=bool(release.get("prerelease")),
            html_url=release.get("html_url") or RELEASES_PAGE_URL,
            asset_name=asset.get("name") if asset else None,
            asset_url=asset.get("browser_download_url") if asset else None,
            asset_size=asset.get("size") if asset else None,
            asset_digest=_parse_digest(asset.get("digest")) if asset else None,
        )

    def download(
        self,
        update: UpdateInfo,
        destination_dir: str | os.PathLike | None = None,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> Path:
        """Stream the update asset to disk and verify its sha256 digest.

        ``progress`` receives ``(downloaded_bytes, total_bytes)``; ``total`` is
        ``None`` when the server did not report a length. The partial file is
        removed on failure or digest mismatch.
        """
        if not update.asset_url or not update.asset_name:
            raise DownloadError(
                f"Release {update.version} has no downloadable asset for this platform"
            )
        destination_dir = destination_dir or tempfile.gettempdir()
        directory = Path(destination_dir)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / update.asset_name

        request = urllib.request.Request(
            update.asset_url,
            headers={"User-Agent": f"Unscreen-updater/{get_current_version()}"},
        )
        downloaded = 0
        total = update.asset_size
        try:
            with (
                urllib.request.urlopen(request, timeout=self._timeout) as response,
                destination.open("wb") as fp,
            ):
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    fp.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(downloaded, total)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            remove_file(destination)
            raise DownloadError(
                f"Failed to download {update.asset_name}: {error}"
            ) from error

        if total is not None and downloaded != total:
            remove_file(destination)
            raise DownloadError(f"Incomplete download: {downloaded} of {total} bytes")
        self._verify_digest(destination, update.asset_digest)
        return destination

    def _verify_digest(self, path: Path, expected: str | None) -> None:
        if not expected:
            logger.warning("No sha256 digest for %s; skipping verification", path.name)
            return
        hasher = hashlib.sha256()
        with path.open("rb") as fp:
            for chunk in iter(lambda: fp.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != expected:
            logger.error("sha256 mismatch for %s", path)
            remove_file(path)
            raise DigestMismatchError(
                f"Downloaded {path.name} failed sha256 verification"
            )
        logger.info("sha256 verified for %s", path.name)

    def apply(
        self, update: UpdateInfo, installer_path: str | os.PathLike
    ) -> ApplyResult:
        """Apply the downloaded update for the current platform.

        Windows spawns the Inno Setup installer silently; the caller is
        responsible for exiting the app afterwards. Android attempts an
        ``ACTION_VIEW`` install intent and falls back to manual install.
        """
        if not is_packaged():
            raise ApplyError(
                "Cannot apply an update when running from source; run the packaged app"
            )
        system = platform.system()
        if system == "Windows":
            return self._apply_windows(installer_path)
        if system == "Android":
            return self._apply_android(installer_path)
        logger.warning("No update apply path for platform %s", system)
        return ApplyResult.NOT_APPLICABLE

    def _apply_windows(self, installer_path: str | os.PathLike) -> ApplyResult:
        installer = Path(installer_path)
        if not installer.is_file():
            raise ApplyError(f"Installer not found: {installer}")
        try:
            subprocess.Popen(
                [
                    str(installer),
                    "/VERYSILENT",
                    "/SUPPRESSMSGBOXES",
                    "/NORESTART",
                ],
                cwd=str(installer.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as error:
            raise ApplyError(f"Failed to launch installer: {error}") from error
        logger.info("Launched installer %s", installer)
        return ApplyResult.APPLIED

    def _apply_android(self, installer_path: str | os.PathLike) -> ApplyResult:
        apk = Path(installer_path)
        if not apk.is_file():
            raise ApplyError(f"APK not found: {apk}")
        try:
            from jnius import autoclass  # type: ignore
        except ImportError:
            logger.warning("pyjnius not available; manual APK install required")
            return ApplyResult.MANUAL_REQUIRED
        try:
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            File = autoclass("java.io.File")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(
                Uri.fromFile(File(str(apk))), "application/vnd.android.package-archive"
            )
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            PythonActivity.mActivity.startActivity(intent)
        except Exception:
            logger.exception("APK install intent failed; manual install required")
            return ApplyResult.MANUAL_REQUIRED
        logger.info("Triggered APK install for %s", apk)
        return ApplyResult.APPLIED


if __name__ == "__main__":
    uc = UpdateChecker("0.4.0")
    info: UpdateInfo | None = uc.check_for_update()
    if info is None:
        print("Up to date.")
    else:
        print(f"Update available: {info.version}")
        print(info.release_notes)

        installer_path = uc.download(
            info,
            destination_dir=r"E:\Files",
            progress=lambda d, t: print(f"Downloaded {d}/{t}"),
        )

        print(uc.apply(info, installer_path))
