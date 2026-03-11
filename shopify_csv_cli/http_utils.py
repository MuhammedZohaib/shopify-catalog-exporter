from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "shopify-products-to-csv/0.1 (+https://example.local)"


class ResponseLike(Protocol):
    text: str
    status_code: int
    encoding: str | None

    def raise_for_status(self) -> None: ...


class SessionLike(Protocol):
    headers: dict[str, str]

    def get(self, url: str, timeout: float) -> ResponseLike: ...


class HttpRequestError(Exception):
    pass


@dataclass(slots=True)
class _SimpleResponse:
    text: str
    status_code: int
    encoding: str | None = "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HttpRequestError(f"HTTP {self.status_code}")


class UrllibSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: float) -> _SimpleResponse:
        request = Request(url, headers=self.headers)
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                status_code = int(getattr(response, "status", 200))
                return _SimpleResponse(text=text, status_code=status_code, encoding=charset)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return _SimpleResponse(text=body, status_code=exc.code, encoding="utf-8")
        except URLError as exc:
            raise HttpRequestError(str(exc)) from exc


def create_session() -> SessionLike:
    try:
        import requests  # type: ignore
    except ModuleNotFoundError:
        return UrllibSession()
    return requests.Session()


def fetch_text(
    session: SessionLike,
    url: str,
    timeout: float,
    retries: int,
    verbose: bool = False,
) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            if response.encoding is None:
                response.encoding = "utf-8"
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            backoff = 0.5 * (2**attempt)
            if verbose:
                print(
                    f"Request failed ({attempt + 1}/{retries + 1}) for {url}; "
                    f"retrying in {backoff:.1f}s"
                )
            time.sleep(backoff)
    assert last_error is not None
    raise last_error
