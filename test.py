from bs4 import BeautifulSoup
soup = BeautifulSoup('<p class="foo bar">text</p>', 'xml')
print(repr(soup.p.get('class')))
