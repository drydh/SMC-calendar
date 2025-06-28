import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# supress bs warnings when unescaping html from url-looking strings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def unescape_html(string: str) -> str:
    if not string:
        return ""
    unescaped = BeautifulSoup(string, features="lxml").string
    if unescaped is None:
        raise ValueError(f"Failed to unescape: {string}")
    return unescaped
