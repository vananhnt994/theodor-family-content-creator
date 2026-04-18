import re
from bs4 import BeautifulSoup
import glob

for fp in glob.glob('html_dumps/*.html'):
    print(f"\n--- {fp} ---")
    html = open(fp, encoding='utf-8').read()
    soup = BeautifulSoup(html, 'html.parser')
    
    if "dantri" in fp:
        # find where the paragraphs are
        for p in soup.find_all('p')[:5]:
            if p.parent:
                print("Dantri parent class:", p.parent.get('class'))
    elif "lamchame" in fp:
        for p in soup.find_all('p')[:5]:
            if p.parent:
                print("Lamchame parent class:", p.parent.get('class'))
    elif "webtretho" in fp:
        # find headlines on the frontpage
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href.startswith('http') and len(a.text.strip()) > 30:
                print("Webtretho headline link class:", a.get('class'), "parent:", a.parent.get('class'))
    elif "spiegel" in fp:
        # find consent button
        buttons = soup.find_all('button')
        for b in buttons:
            print("Spiegel button:", b.get('title'), b.get('class'), b.get('id'), b.text.strip())
