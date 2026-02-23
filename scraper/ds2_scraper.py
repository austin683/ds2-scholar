import requests
import time
import os
import re
from bs4 import BeautifulSoup
import html2text

# Config
BASE_URL = "https://darksouls2.wiki.fextralife.com"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ds2_scholar/knowledge_base_ds2")
DELAY = 1.5
os.makedirs(OUTPUT_DIR, exist_ok=True)

# html2text converter settings — tables are handled via custom parser
converter = html2text.HTML2Text()
converter.ignore_links = False
converter.ignore_images = True
converter.body_width = 0
converter.ignore_tables = True  # We replace tables with custom blocks first

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

# ---------------------------------------------------------------------------
# Weapon upgrade table column schema
# Fextralife weapon pages always use this exact column order.
# Sub-header row uses icon images (come out as empty strings) so we inject
# the known labels instead.
# 20 cols total: Name + 5 attack + stability/dur + 6 scaling + 2 aux + 5 DR%
# ---------------------------------------------------------------------------
WEAPON_UPGRADE_COLUMNS = [
    "Name",
    "Phys Atk", "Mag Atk", "Fire Atk", "Lit Atk", "Dark Atk",
    "Stability / Durability",
    "STR Scaling", "DEX Scaling", "Mag Scaling", "Fire Scaling", "Lit Scaling", "Dark Scaling",
    "Bleed", "Poison",
    "Phys DR%", "Mag DR%", "Fire DR%", "Lit DR%", "Dark DR%",
]

# Requirement stat order in the quick-stats widget
STAT_REQ_LABELS = ["STR", "DEX", "INT", "FTH"]


# ---------------------------------------------------------------------------
# Grid builder — resolves rowspan/colspan into a 2-D list of strings
# ---------------------------------------------------------------------------

def _cell_text(cell):
    """Clean text from a td/th, collapsing inner <br> to ' / '."""
    for br in cell.find_all("br"):
        br.replace_with(" / ")
    return cell.get_text(" ", strip=True)


def _build_grid(table):
    """Convert an HTML <table> to a 2-D list, resolving rowspan/colspan."""
    grid = []
    pending_rowspans = {}  # col_index -> (remaining_rows, cell_text)

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        grid_row = []
        physical_col = 0
        cell_idx = 0

        while cell_idx < len(cells) or physical_col in pending_rowspans:
            if physical_col in pending_rowspans:
                rem, val = pending_rowspans[physical_col]
                grid_row.append(val)
                if rem - 1 == 0:
                    del pending_rowspans[physical_col]
                else:
                    pending_rowspans[physical_col] = (rem - 1, val)
                physical_col += 1
                continue

            if cell_idx >= len(cells):
                break

            cell = cells[cell_idx]
            cell_idx += 1
            text = _cell_text(cell)
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))

            for _ in range(colspan):
                grid_row.append(text)
                if rowspan > 1:
                    pending_rowspans[physical_col] = (rowspan - 1, text)
                physical_col += 1

        if grid_row:
            grid.append(grid_row)

    return grid


def _pad_grid(grid):
    if not grid:
        return grid
    max_cols = max(len(r) for r in grid)
    for r in grid:
        while len(r) < max_cols:
            r.append("")
    return grid


# ---------------------------------------------------------------------------
# Table type detection
# ---------------------------------------------------------------------------

def _is_weapon_upgrade_table(grid):
    """
    Fextralife upgrade table:
      row 0 — group headers (Attack Values Bonus, Parameter Bonus, …)
      row 1 — icon-only sub-headers: 'Name' in col 0, rest empty
    """
    if len(grid) < 3:
        return False
    header_text = " ".join(str(c) for c in grid[0])
    sub_row = grid[1]
    has_groups = "Attack Values" in header_text and "Parameter Bonus" in header_text
    name_in_sub = len(sub_row) > 0 and sub_row[0].strip().lower() == "name"
    mostly_empty = sum(1 for c in sub_row[1:] if c.strip() == "") >= len(sub_row) - 2
    return has_groups and name_in_sub and mostly_empty


def _is_stats_widget(grid):
    """
    Fextralife quick-stats widget at the top of weapon pages.
    Identified by having 'Weapon Type' and 'Enchantable' as cell values.
    """
    all_cells = " ".join(str(c) for row in grid for c in row)
    return "Weapon Type" in all_cells and "Enchantable" in all_cells


# ---------------------------------------------------------------------------
# Table converters
# ---------------------------------------------------------------------------

def _grid_to_markdown(headers, data_rows):
    """Render headers + data rows as a markdown table string."""
    def fmt(row):
        return "| " + " | ".join(str(c) for c in row) + " |"

    sep = "| " + " | ".join("---" for _ in headers) + " |"
    return "\n".join([fmt(headers), sep] + [fmt(r) for r in data_rows])


def _parse_upgrade_table(grid):
    """Inject known column headers and return markdown string."""
    n = len(grid[0])
    if n == len(WEAPON_UPGRADE_COLUMNS):
        headers = WEAPON_UPGRADE_COLUMNS
    else:
        headers = ["Name"] + [f"Col{i}" for i in range(1, n)]
    return _grid_to_markdown(headers, grid[2:])  # skip group-header + icon-sub-header rows


def _parse_stats_widget(grid):
    """
    Extract key metadata from the quick-stats widget as clean prose lines.
    Ignores the noisy attack-value stat rows (those are in the upgrade table)
    and extracts: requirements, weapon type, attack type, enchantable, special.
    Returns a plain text string, or None if nothing useful was found.
    """
    lines = []
    awaiting_req_row = False

    for row in grid:
        # Deduplicate colspan-expanded cells while preserving first-occurrence order
        seen = set()
        unique = []
        for v in (str(c).strip() for c in row):
            if v and v not in seen:
                seen.add(v)
                unique.append(v)

        if not unique:
            continue

        if len(unique) == 1:
            if unique[0] == "Requirements & Bonus":
                awaiting_req_row = True
            # Everything else (widget title like "Longsword+10 Stats", "*B" note) → skip

        elif awaiting_req_row:
            # Sample from known grid positions: each stat occupies colspan=4 in a 20-col grid
            # positions 0, 4, 8, 12 give STR, DEX, INT, FTH
            if len(row) >= 13:
                req_vals = [str(row[i]).strip() for i in (0, 4, 8, 12)]
            else:
                req_vals = unique + ["–"] * (4 - len(unique))

            parts = []
            for label, val in zip(STAT_REQ_LABELS, req_vals):
                if val and val != "–":
                    parts.append(f"{label} {val}")
            if parts:
                lines.append("Requirements: " + ", ".join(parts))
            awaiting_req_row = False  # Only the first row after the header

        elif len(unique) == 2:
            label, value = unique[0], unique[1]
            if label in ("Weapon Type", "Attack Type", "Enchantable", "Special"):
                lines.append(f"{label}: {value}")

    return "\n".join(lines).strip() if lines else None


# ---------------------------------------------------------------------------
# Main table dispatch — replaces tables in-place in the BeautifulSoup tree
# ---------------------------------------------------------------------------

def replace_tables_with_content(main_content):
    """
    Walk all <table> elements and replace each with either:
      - plain <div><p>…</p></div>  (stats widget → clean prose)
      - <pre> markdown block        (upgrade table + other tables)
    """
    for table in main_content.find_all("table"):
        grid = _pad_grid(_build_grid(table))

        if not grid:
            table.decompose()
            continue

        if _is_stats_widget(grid):
            text = _parse_stats_widget(grid)
            if text:
                inner = "".join(f"<p>{line}</p>" for line in text.splitlines() if line.strip())
                replacement = BeautifulSoup(f"<div>{inner}</div>", "html.parser")
                table.replace_with(replacement)
            else:
                table.decompose()

        elif _is_weapon_upgrade_table(grid):
            md = _parse_upgrade_table(grid)
            if md:
                replacement = BeautifulSoup(f"<pre>\n{md}\n</pre>", "html.parser")
                table.replace_with(replacement)
            else:
                table.decompose()

        else:
            # Generic table (table key, weapon category list, etc.)
            md = _grid_to_markdown(grid[0], grid[1:])
            if md:
                replacement = BeautifulSoup(f"<pre>\n{md}\n</pre>", "html.parser")
                table.replace_with(replacement)
            else:
                table.decompose()


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

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
    # Strip footer junk (comments, nav, etc.)
    for phrase in CUTOFF_PHRASES:
        if phrase in markdown:
            markdown = markdown[:markdown.index(phrase)].rstrip()
            break

    # Collapse 3+ blank lines to 2
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
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

        # Replace tables with clean text/markdown blocks before html2text
        replace_tables_with_content(main_content)

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
