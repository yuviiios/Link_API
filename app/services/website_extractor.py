import asyncio
import ipaddress
import socket
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

MAX_HTML_BYTES = 1_000_000
MAX_TEXT_CHARS = 18_000
REDIRECT_CODES = {301, 302, 303, 307, 308}


class WebsiteError(Exception):
    pass


class UnsafeWebsite(WebsiteError):
    pass


def public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        return address in ipaddress.IPv6Network("2000::/3") and not (
            address.sixtofour or address.teredo or address.ipv4_mapped
        )
    return True


def validate_destination(url: URL) -> None:
    host = url.raw_host
    if url.scheme not in ("http", "https") or not host or url.user is not None:
        raise UnsafeWebsite("Enter an HTTP or HTTPS website URL without credentials.")
    if url.port != (443 if url.scheme == "https" else 80):
        raise UnsafeWebsite("Only standard HTTP and HTTPS ports are supported.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if "." not in host.rstrip("."):
            raise UnsafeWebsite("Use a public website hostname.")
    else:
        if not public_address(host):
            raise UnsafeWebsite("The URL must resolve to a public address.")


class PublicResolver(aiohttp.abc.AbstractResolver):
    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        records = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=family, type=socket.SOCK_STREAM
        )
        # Feed the vetted numeric addresses directly to the connector.
        if any(not public_address(record[4][0]) for record in records):
            raise UnsafeWebsite("The URL must resolve to public addresses.")
        return [
            {
                "hostname": host,
                "host": record[4][0],
                "port": port,
                "family": record[0],
                "proto": record[2],
                "flags": socket.AI_NUMERICHOST,
            }
            for record in records
        ]

    async def close(self):
        pass


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    description: str
    text: str

    def evidence(self) -> dict[str, str]:
        return asdict(self)


def extract_page(html: bytes, url: str, encoding: str | None = None) -> Page:
    soup = BeautifulSoup(html, "html.parser", from_encoding=encoding)
    title = soup.title.get_text(" ", strip=True)[:300] if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    description = str(meta.get("content", ""))[:600] if meta else ""
    for element in soup(["script", "style", "noscript", "template", "nav", "footer", "aside"]):
        element.decompose()
    body = soup.find("main") or soup.body or soup
    lines = (" ".join(line.split()) for line in body.stripped_strings)
    content = "\n".join(dict.fromkeys(line for line in lines if line))[:MAX_TEXT_CHARS]
    if len(content) < 40:
        raise WebsiteError("The page has too little readable content for analysis.")
    return Page(url, title, description, content)


async def fetch_page(website: str) -> Page:
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
    try:
        async with asyncio.timeout(15), aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.DummyCookieJar(),
            headers={"User-Agent": "WebsiteLinkAnalysis/1.0", "Accept-Encoding": "identity"},
            auto_decompress=False,
        ) as session:
            url = URL(website).with_fragment(None)
            for _ in range(5):
                validate_destination(url)
                async with session.get(url, allow_redirects=False) as response:
                    if response.status in REDIRECT_CODES and response.headers.get("Location"):
                        url = URL(urljoin(str(url), response.headers["Location"])).with_fragment(None)
                        continue
                    if response.status != 200:
                        raise WebsiteError(f"The website returned HTTP {response.status}.")
                    if response.content_type not in ("text/html", "application/xhtml+xml"):
                        raise WebsiteError("The URL must return an HTML page.")
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        raise WebsiteError("The website did not return uncompressed HTML.")
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65_536):
                        data.extend(chunk)
                        if len(data) > MAX_HTML_BYTES:
                            raise WebsiteError("The HTML page exceeds the 1 MB limit.")
                    return extract_page(bytes(data), str(url), response.charset)
    except (aiohttp.ClientError, TimeoutError, UnicodeError, ValueError) as error:
        raise WebsiteError("The website could not be fetched.") from error
    raise WebsiteError("The website redirected too many times.")
