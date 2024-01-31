import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# supress bs warnings when unescaping html from url-looking strings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def unescape_html(string):
    return BeautifulSoup(string, features="lxml").string
