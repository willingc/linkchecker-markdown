from pathlib import Path
import typing as T
import logging
import re
import asyncio

from .coro import check_urls

# http://www.useragentstring.com
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) Gecko/20100101 Firefox/64.0"


def check_links(
    path: Path,
    domain: str = None,
    *,
    ext: str,
    hdr: T.Dict[str, str] = None,
    method: str = "get",
    use_async: bool = True,
    local: bool = False,
) -> T.Iterable[tuple]:

    for bad in check_local(path, ext=ext):
        print(bad)

    bad = None
    if not local:
        bad = check_remotes(path, domain, ext=ext, hdr=hdr, method=method, use_async=use_async)

    return bad


def check_local(path: Path, ext: str) -> T.Iterable[T.Tuple[str, str]]:
    """check internal links of Markdown files
    this is a simple static analysis; only plain filename references are handled.
    """

    regex = r"\]\(([=a-zA-Z0-9\_\/\?\&\%\+\#\.\-]+)\)"
    glob = re.compile(regex)

    path = Path(path).resolve().expanduser()  # must have .resolve()

    for fn in get_files(path, ext):
        urls = glob.findall(fn.read_text(errors="ignore"))

        for url in urls:
            if url[0] == "#":
                continue

            if not url[0] == "/":
                if {"/", "."}.intersection(url.strip("/")):
                    continue
                yield fn.name, url
                continue

            if {"/", "."}.intersection(url.strip("/")):
                continue

            if not (path / (url.strip("/") + ext)).is_file():
                if not (path.parent / (url.strip("/") + ext)).is_file():
                    yield fn.name, url


def check_remotes(
    path: Path,
    domain: str,
    *,
    ext: str,
    hdr: T.Dict[str, str] = None,
    method: str = "get",
    use_async: bool = True,
) -> T.List[T.Tuple[str, str, T.Any]]:
    if domain:
        pat = "https?://" + domain + r"[=a-zA-Z0-9\_\/\?\&\%\+\#\.\-]*"
    else:
        pat = r"https?://[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[=a-zA-Z0-9\_\/\?\&\%\+\#\.\-]+"

    if ext == ".md":
        pat = r"\(" + pat + r"\)"

    logging.debug(f"regex {pat}")

    flist = get_files(path, ext)

    if not hdr:
        hdr = {"User-Agent": USER_AGENT}

    # %% session
    if use_async:
        urls = asyncio.run(check_urls(flist, pat, ext, hdr, method))
    else:
        from .sync import check_urls as sync_urls

        urls = sync_urls(flist, pat, ext, hdr)

    return urls


def get_files(path: Path, ext: str) -> T.Iterable[Path]:

    path = Path(path).expanduser().resolve()

    if path.is_dir():
        flist = iter(path.glob("*" + ext))
    elif path.is_file():
        flist = iter([path])
    else:
        raise FileNotFoundError(path)

    return flist
