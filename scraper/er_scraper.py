import requests
import time
import os
import re
from collections import deque
from bs4 import BeautifulSoup
import html2text

# Config
BASE_URL = "https://eldenring.wiki.fextralife.com"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ds_scholar/knowledge_base_er")
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
    # Community build-link lists — navigational noise, no factual content.
    # Safe to cut: weapon pages don't use these headings; poise/upgrade data
    # always appears before any builds section on pages that have one.
    "Builds that use",
    "Builds with ",
    # Player-written test sections, explicitly flagged unreliable on-wiki.
    "Test Data for",
]

# ---------------------------------------------------------------------------
# Weapon upgrade table column schema
# Fextralife weapon pages use this column order for ER.
# Sub-header row uses icon images (come out as empty strings) so we inject
# the known labels instead.
# 18 cols total: Name + 5 attack + Stamina + 5 scaling + 6 guard negation
# ---------------------------------------------------------------------------
WEAPON_UPGRADE_COLUMNS = [
    "Name",
    "Phy Atk", "Mag Atk", "Fir Atk", "Lit Atk", "Hol Atk",
    "Stamina",
    "Str Scaling", "Dex Scaling", "Int Scaling", "Fai Scaling", "Arc Scaling",
    "Phy Guard%", "Mag Guard%", "Fir Guard%", "Lit Guard%", "Hol Guard%", "Guard Boost",
]

# Requirement stat order in the quick-stats widget (ER has 5: adds ARC, FTH → FAI)
STAT_REQ_LABELS = ["STR", "DEX", "INT", "FAI", "ARC"]


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
    Fextralife upgrade table detector — handles both DS2 and ER table layouts.

    DS2 layout:
      row 0 — group headers: "Attack Values", "Parameter Bonus", …
      row 1 — icon-only sub-headers: col 0 = "Name", rest are empty (icons)

    ER layout:
      row 0 — group headers: "Attack Power", "Stat Scaling", "Damage Reduction (%)"
      row 1 — sub-headers with short abbreviations: "Phy", "Mag", "Sta", "Str", …
               col 0 = weapon name (not "Name")
    """
    if len(grid) < 3:
        return False
    header_text = " ".join(str(c) for c in grid[0])
    sub_row = grid[1]

    # Group-header row must contain attack and scaling section labels.
    # "Scaling" alone catches: "Stat Scaling", "Attribute Scaling", "Parameter Bonus".
    has_groups = (
        ("Attack Power" in header_text or "Attack Values" in header_text)
        and ("Scaling" in header_text or "Parameter Bonus" in header_text)
    )
    if not has_groups:
        return False

    # DS2 style: sub-header row has "Name" in col 0, remaining cells mostly empty (icons)
    ds2_style = (
        len(sub_row) > 0
        and sub_row[0].strip().lower() == "name"
        and sum(1 for c in sub_row[1:] if c.strip() == "") >= len(sub_row) - 2
    )

    # ER style: sub-header row has short abbreviations (Phy, Mag, Sta, Str, Dex …)
    _ER_ABBREVS = {"Phy", "Mag", "Fir", "Lit", "Hol", "Sta", "Str", "Dex",
                   "Int", "Fai", "Arc", "Any", "Bst", "Rst"}
    er_style = (
        len(sub_row) > 4
        and all(len(c.strip()) <= 12 for c in sub_row)
        and len(_ER_ABBREVS & {c.strip() for c in sub_row}) >= 3
    )

    return ds2_style or er_style


def _is_stats_widget(grid):
    """
    Fextralife quick-stats widget detector — handles both DS2 and ER layouts.

    DS2 layout: wide colspan-expanded grid; cells contain literal labels
                "Weapon Type" and "Enchantable".

    ER layout:  2-column grid; label cells are icons (no text), so we detect
                by the presence of "Wgt." (weight) combined with attack or
                requirement data — both unique to weapon stat widgets.
    """
    if not grid:
        return False
    all_cells = " ".join(str(c) for row in grid for c in row)
    max_cols = max(len(r) for r in grid)

    # DS2: explicit text labels
    if "Weapon Type" in all_cells and ("Enchantable" in all_cells or "Skill" in all_cells):
        return True

    # ER: 2-column grid with weight + attack/requirement data
    return (
        max_cols <= 2
        and len(grid) <= 15
        and "Wgt." in all_cells
        and ("Attack" in all_cells or "Requires" in all_cells)
    )


# ---------------------------------------------------------------------------
# Entity info box detector/parser (bosses, talismans, spells, spirit ashes…)
# ---------------------------------------------------------------------------

def _is_entity_infobox(grid):
    """
    Detect a Fextralife entity info box: a 2-column table where at least one
    row has the same non-empty value in both cells (the entity-name header
    pattern). Used for bosses, talismans, spells, spirit ashes, locations, etc.

    Called only after _is_stats_widget() has already rejected the table, so
    weapon stat widgets (which share the 2-col layout) won't be re-caught here.
    """
    if not grid:
        return False
    max_cols = max(len(r) for r in grid)
    if max_cols != 2:
        return False
    for row in grid:
        if len(row) >= 2:
            a, b = str(row[0]).strip(), str(row[1]).strip()
            if a and a == b:
                return True
    return False


def _parse_entity_infobox(grid):
    """
    Extract key metadata from a 2-col entity info box as clean prose lines.

    Row patterns:
      - Both cells empty            → image placeholder, skip
      - Both cells same non-empty   → entity-name header (first time) or
                                      a repeated value; emit value once
      - Two different non-empty     → key: value pair
    """
    lines = []
    seen_header = False

    for row in grid:
        vals = [str(c).strip() for c in row]
        unique = list(dict.fromkeys(v for v in vals if v))  # unique, order preserved

        if not unique:
            continue  # image / empty row

        if len(unique) == 1:
            v = unique[0]
            if not seen_header:
                seen_header = True
                continue  # skip entity name (already in page title / URL)
            lines.append(v)
        elif len(unique) == 2:
            lines.append(f"{unique[0]}: {unique[1]}")
        else:
            lines.append(" | ".join(unique))

    return "\n".join(lines).strip() if lines else None


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
    """
    Return the upgrade table as a markdown string.

    DS2: sub-header row (row 1) is mostly empty icon cells → inject known column
         names from WEAPON_UPGRADE_COLUMNS (or fallback Col1, Col2 …).
    ER:  sub-header row already has readable abbreviations (Phy, Mag, Sta …) →
         use it directly as the header row.
    """
    sub_row = grid[1]
    mostly_empty = sum(1 for c in sub_row[1:] if c.strip() == "") >= len(sub_row) - 2

    if mostly_empty:
        # DS2-style: inject known column names
        n = len(grid[0])
        headers = WEAPON_UPGRADE_COLUMNS if n == len(WEAPON_UPGRADE_COLUMNS) \
                  else ["Name"] + [f"Col{i}" for i in range(1, n)]
        return _grid_to_markdown(headers, grid[2:])
    else:
        # ER-style: sub-header row is already the real column header
        return _grid_to_markdown(sub_row, grid[2:])


def _parse_stats_widget(grid):
    """
    Extract key metadata from the quick-stats widget as clean prose lines.

    DS2 layout: wide colspan-expanded grid. Explicit label cells trigger
                known key-value extraction + sampled requirement positions.

    ER layout:  2-column grid where label cells are icons (no text). Each row
                carries the full value in both cells (e.g. "Requires Str 10 /
                Dex 10"). We parse by content heuristics rather than labels.

    Returns a plain text string, or None if nothing useful was found.
    """
    max_cols = max(len(r) for r in grid)

    # ── ER-style: 2-column grid ───────────────────────────────────────────────
    if max_cols <= 2:
        lines = []
        for row in grid:
            seen = set()
            unique = []
            for v in (str(c).strip() for c in row):
                if v and v not in seen:
                    seen.add(v)
                    unique.append(v)
            if not unique:
                continue

            if len(unique) == 1:
                v = unique[0]
                if v.startswith("Wgt."):
                    lines.append(v)

            elif len(unique) == 2:
                a, b = unique[0], unique[1]
                # Requirements row: check before the skip — this row pairs
                # "Scaling Str D / Dex D" with "Requires Str 10 / Dex 10"
                if "Requires" in b:
                    lines.append(b)
                    continue
                elif "Requires" in a:
                    lines.append(a)
                    continue
                # Skip raw stat rows (attack values, guard values, scaling)
                if any(a.startswith(kw) for kw in ("Attack", "Guard", "Scaling")):
                    continue
                # Skill + FP row: second cell starts with "FP"
                elif b.startswith("FP"):
                    lines.append(f"Skill: {a}")
                    fp_val = re.sub(r"FP\s*-?\s*", "", b).strip()
                    if fp_val and fp_val != "-":
                        lines.append(f"FP: {fp_val}")
                # Weight row
                elif a.startswith("Wgt."):
                    lines.append(a)
                    # Strip any leading "Passive" word that the cell already
                    # contains, so we don't emit "Passive: Passive / (50)".
                    passive_val = re.sub(r'^Passive\s*[/\s-]*', '', b).strip()
                    if passive_val and passive_val != "-":
                        lines.append(f"Passive: {passive_val}")
                # Weapon type + attack type row (skip title row where a == b)
                elif a != b and b not in ("Passive -", "Passive"):
                    lines.append(f"Weapon Type: {a}")
                    lines.append(f"Attack Type: {b}")

        return "\n".join(lines).strip() if lines else None

    # ── DS2-style: wide colspan-expanded grid ─────────────────────────────────
    lines = []
    awaiting_req_row = False

    for row in grid:
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

        elif awaiting_req_row:
            # Each stat occupies colspan=4; sample positions 0, 4, 8, 12, 16
            if len(row) >= 17:
                req_vals = [str(row[i]).strip() for i in (0, 4, 8, 12, 16)]
            else:
                req_vals = unique + ["–"] * (5 - len(unique))
            parts = []
            for label, val in zip(STAT_REQ_LABELS, req_vals):
                if val and val != "–":
                    parts.append(f"{label} {val}")
            if parts:
                lines.append("Requirements: " + ", ".join(parts))
            awaiting_req_row = False

        elif len(unique) == 2:
            label, value = unique[0], unique[1]
            if label in ("Weapon Type", "Attack Type", "Enchantable", "Buffable",
                         "Skill", "FP", "Wgt.", "Passive"):
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

        all_text = " ".join(str(c) for row in grid for c in row)

        # Drop "See all <type>" reference tables — a cell full of ♦-separated
        # item names is pure noise for RAG.
        if all_text.count("♦") >= 5:
            table.decompose()
            continue

        # Drop single-column navigation boxes (location/region page nav headers).
        if max(len(r) for r in grid) == 1 and len(grid) <= 5:
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

        elif _is_entity_infobox(grid):
            text = _parse_entity_infobox(grid)
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
            # Generic table (talisman effects, spirit ash stats, etc.)
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

    # Remove empty headings (e.g. stray "###" with no text)
    markdown = re.sub(r'^#{1,6}\s*$', '', markdown, flags=re.MULTILINE)
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

def scrape_page(url, links_only=False):
    filename = url_to_filename(url)
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=15)

            # 404 = page genuinely doesn't exist, no point retrying
            if response.status_code == 404:
                print(f"  [404] Skipping permanently")
                return []

            # 5xx / other transient errors — retry with backoff
            if response.status_code != 200:
                if attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"  [FAIL] HTTP {response.status_code} — retrying in {wait}s ({attempt + 1}/2)")
                    time.sleep(wait)
                    continue
                print(f"  [FAIL] HTTP {response.status_code} — giving up")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Get links before stripping content
            links = get_wiki_links(soup)

            # Already scraped — return links so the crawl can find missed pages
            if links_only:
                return links

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

            # Sidecar: save all outgoing URLs (including those from tables,
            # which are lost in the markdown conversion) so resume runs can
            # recover them without HTTP requests.
            links_path = os.path.join(OUTPUT_DIR, f"{filename}.links")
            with open(links_path, "w", encoding="utf-8") as f:
                f.write("\n".join(links))

            return links

        except Exception as e:
            if attempt < 2:
                wait = 10 * (attempt + 1)
                print(f"  [ERROR] {e} — retrying in {wait}s ({attempt + 1}/2)")
                time.sleep(wait)
            else:
                print(f"  [ERROR] {e} — giving up")

    return []

def load_existing_knowledge_base():
    """
    Scan saved .md files on disk to recover visited URLs and outgoing wiki
    links without making any HTTP requests. Returns (visited_set, links_list).

    Outgoing links are extracted from markdown hyperlinks in the body. Note:
    links that were inside tables (converted to <pre> blocks) are not in the
    markdown and won't be recovered here — they're typically nav/category links
    and rarely the only path to a content page.
    """
    link_re = re.compile(
        r'\[.*?\]\((https://eldenring\.wiki\.fextralife\.com/[^)#?]+)\)'
    )
    visited_urls = set()
    outgoing = []

    try:
        md_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")]
    except FileNotFoundError:
        return visited_urls, outgoing

    for fname in md_files:
        fpath = os.path.join(OUTPUT_DIR, fname)
        links_path = fpath[:-3] + ".links"
        try:
            with open(fpath, encoding="utf-8") as f:
                first_line = f.readline().strip()
                body = f.read()
        except OSError:
            continue

        if first_line.startswith("# Source: "):
            visited_urls.add(first_line[len("# Source: "):])

        if os.path.exists(links_path):
            # Sidecar has full link set including links that were inside tables.
            try:
                with open(links_path, encoding="utf-8") as lf:
                    for line in lf:
                        url = line.strip()
                        if url and not should_skip(url):
                            outgoing.append(url)
            except OSError:
                pass
        else:
            # Fallback for files scraped before sidecar support: extract links
            # from markdown hyperlinks (misses any links that were in tables).
            for m in link_re.finditer(body):
                url = m.group(1)
                if not should_skip(url):
                    outgoing.append(url)

    return visited_urls, outgoing


def main():
    seed_pages = [
        "https://eldenring.wiki.fextralife.com/Weapons",
        "https://eldenring.wiki.fextralife.com/Spells",
        "https://eldenring.wiki.fextralife.com/Incantations",
        "https://eldenring.wiki.fextralife.com/Armor",
        "https://eldenring.wiki.fextralife.com/Talismans",
        "https://eldenring.wiki.fextralife.com/Items",
        "https://eldenring.wiki.fextralife.com/Bosses",
        "https://eldenring.wiki.fextralife.com/Locations",
        "https://eldenring.wiki.fextralife.com/NPCs",
        "https://eldenring.wiki.fextralife.com/Enemies",
        "https://eldenring.wiki.fextralife.com/Builds",
        "https://eldenring.wiki.fextralife.com/Stats",
        "https://eldenring.wiki.fextralife.com/Shields",
        "https://eldenring.wiki.fextralife.com/Spirit+Ashes",
        "https://eldenring.wiki.fextralife.com/Ashes+of+War",
        "https://eldenring.wiki.fextralife.com/Sites+of+Grace",
        "https://eldenring.wiki.fextralife.com/Game+Progress+Route",
        "https://eldenring.wiki.fextralife.com/Upgrades",
        "https://eldenring.wiki.fextralife.com/Multiplayer",
        # Questlines & lore (confirmed pages on Fextralife)
        "https://eldenring.wiki.fextralife.com/Side+Quests",
        "https://eldenring.wiki.fextralife.com/Lore",
    ]

    # Recover visited URLs and outgoing links from already-saved files on disk.
    # This lets us skip re-fetching those pages entirely while still queuing
    # any links they referenced that haven't been scraped yet.
    print("Scanning existing knowledge base for already-scraped pages...")
    disk_visited, disk_links = load_existing_knowledge_base()
    visited.update(disk_visited)
    skipped_count = len(disk_visited)
    print(f"  {skipped_count} pages already on disk — skipping HTTP requests for those.")

    queue = deque()
    queued = set()

    def enqueue(url):
        if url not in visited and url not in queued and url.startswith(BASE_URL) and not should_skip(url):
            queued.add(url)
            queue.append(url)

    for p in seed_pages:
        enqueue(p)
    for link in disk_links:
        enqueue(link)

    print(f"  {len(queue)} URLs queued (seed pages + links found in saved files).")
    print(f"Saving to: {OUTPUT_DIR}\n")

    scraped_count = 0

    while queue:
        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)

        if already_scraped(url):
            skipped_count += 1
            continue

        print(f"[{scraped_count + 1}] {url_to_filename(url)}")
        new_links = scrape_page(url)
        scraped_count += 1

        for link in new_links:
            enqueue(link)

        print(f"  [OK] Queue: {len(queue)} remaining")
        time.sleep(DELAY)

    print(f"\nDone!")
    print(f"Scraped: {scraped_count} | Skipped: {skipped_count}")
    print(f"Files in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
