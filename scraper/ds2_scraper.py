import requests
import time
import os
import re
from bs4 import BeautifulSoup
import html2text

# Config
BASE_URL = "https://darksouls2.wiki.fextralife.com"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ds2_scholar/knowledge_base")
DELAY = 1.5
os.makedirs(OUTPUT_DIR, exist_ok=True)

# html2text converter settings
converter = html2text.HTML2Text()
converter.ignore_links = False
converter.ignore_images = True
converter.body_width = 0

# Track visited URLs
visited = set()

# Junk pages to skip
SKIP_PATTERNS = [
    "Media", "Gallery", "Stream", "Fan+Art", "Fan_Art", "Comedy",
    "Chatroom", "Player+ID", "Steam+Id", "Forum", "forum",
    "talk:", "Talk:", "user:", "User:", "file:", "File:",
    "image:", "Image:", "template:", "Template:",
    "category:", "Category:", "special:", "Special:",
    "widget:", "Widget:", "action=", "mailto:",
    ".jpg", ".png", ".gif", ".css", ".js",
    "News", "Review", "Article", "Podcast", "Video",
    "Shop", "Affiliate", "About+Fextralife",
    "Request+a+Wiki", "All+Wikis",
]

# Phrases that mark the start of junk at the bottom
CUTOFF_PHRASES = [
    "Join the page discussion",
    "Tired of anon posting?",
    "Load more",
    "Accept Terms and Save",
    "POPULAR MODS",
    "POPULAR WIKIS",
    "Submit  Submit Close",
]

def should_skip(url):
    for pattern in SKIP_PATTERNS:
        if pattern in url:
            return True
    return False

def url_to_filename(url):
    name = url.replace(BASE_URL, "").strip("/")
    name = re.sub(r'[^\w\-]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name[:120]

def already_scraped(url):
    filename = url_to_filename(url)
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")
    return os.path.exists(filepath)

def clean_markdown(markdown):
    # Strip everything before the first # heading (removes nav junk)
    lines = markdown.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            start_idx = i
            break
    markdown = "\n".join(lines[start_idx:])

    # Strip comments and footer junk
    for phrase in CUTOFF_PHRASES:
        if phrase in markdown:
            markdown = markdown[:markdown.index(phrase)].rstrip()
            break

    return markdown.strip()

def get_wiki_links(soup):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]

        if href.startswith("/") and not href.startswith("//"):
            full_url = BASE_URL + href
        elif href.startswith(BASE_URL):
            full_url = href
        else:
            continue

        if not full_url.startswith(BASE_URL):
            continue

        if "#" in full_url or "?" in full_url:
            continue

        if should_skip(full_url):
            continue

        if full_url not in visited:
            links.append(full_url)

    return links

def scrape_page(url):
    filename = url_to_filename(url)
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"  [FAIL] HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Get links before stripping content
        links = get_wiki_links(soup)

        # Extract main wiki content block only
        main_content = (
            soup.find("div", {"id": "wiki-content-block"}) or
            soup.find("div", {"class": "wiki-content"}) or
            soup.find("article") or
            soup.find("main")
        )

        if not main_content:
            print(f"  [NO CONTENT] Skipping")
            return links

        # Convert to markdown and clean
        markdown = converter.handle(str(main_content))
        markdown = clean_markdown(markdown)

        # Skip if barely any content remains
        if len(markdown.strip()) < 100:
            print(f"  [EMPTY] Skipping")
            return links

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Source: {url}\n\n")
            f.write(markdown)

        return links

    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

def main():
    seed_pages = [
        "https://darksouls2.wiki.fextralife.com/Weapons",
        "https://darksouls2.wiki.fextralife.com/Magic",
        "https://darksouls2.wiki.fextralife.com/Hexes",
        "https://darksouls2.wiki.fextralife.com/Armor",
        "https://darksouls2.wiki.fextralife.com/Rings",
        "https://darksouls2.wiki.fextralife.com/Items",
        "https://darksouls2.wiki.fextralife.com/Bosses",
        "https://darksouls2.wiki.fextralife.com/Locations",
        "https://darksouls2.wiki.fextralife.com/NPCs",
        "https://darksouls2.wiki.fextralife.com/Enemies",
        "https://darksouls2.wiki.fextralife.com/Builds",
        "https://darksouls2.wiki.fextralife.com/Stats",
        "https://darksouls2.wiki.fextralife.com/Shields",
        "https://darksouls2.wiki.fextralife.com/Covenants",
        "https://darksouls2.wiki.fextralife.com/Merchants",
        "https://darksouls2.wiki.fextralife.com/Bonfires",
        "https://darksouls2.wiki.fextralife.com/Game+Progress+Route",
        "https://darksouls2.wiki.fextralife.com/Upgrades",
    ]

    queue = [p for p in seed_pages if p not in visited]

    print(f"Starting full DS2 wiki crawl from {len(seed_pages)} seed pages...")
    print(f"Saving to: {OUTPUT_DIR}")
    print(f"Skipping already downloaded files.\n")

    scraped_count = 0
    skipped_count = 0

    while queue:
        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)

        if not url.startswith(BASE_URL):
            continue

        if should_skip(url):
            continue

        if already_scraped(url):
            skipped_count += 1
            print(f"[SKIP] {url_to_filename(url)}")
            continue

        print(f"[{scraped_count + 1}] {url_to_filename(url)}")
        new_links = scrape_page(url)
        scraped_count += 1

        for link in new_links:
            if link not in visited and link not in queue:
                queue.append(link)

        print(f"  [OK] Queue: {len(queue)} remaining")
        time.sleep(DELAY)

    print(f"\nDone!")
    print(f"Scraped: {scraped_count} | Skipped: {skipped_count}")
    print(f"Files in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()