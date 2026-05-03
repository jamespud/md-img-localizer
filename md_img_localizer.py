#!/usr/bin/env python3
import os
import re
import json
import time
import hashlib
import argparse
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# -------------------------
# config
# -------------------------
ASSET_DIR_NAME = ".asset"
INDEX_FILE = "index.json"
DEFAULT_WORKERS = 8
TIMEOUT = 10
RETRY = 3

IMG_PATTERN = re.compile(r'!\[(.*?)\]\((\S+?)(?:\s+"(.*?)")?\)')


# -------------------------
# utils
# -------------------------
def is_remote(url):
    return url.startswith("http://") or url.startswith("https://")


def get_ext(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    return ext if ext else ".png"


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


# -------------------------
# asset index
# -------------------------
def load_index(asset_dir):
    path = os.path.join(asset_dir, INDEX_FILE)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(asset_dir, index):
    path = os.path.join(asset_dir, INDEX_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


# -------------------------
# download (with retry)
# -------------------------
def download(url, asset_dir, index):
    if url in index:
        return index[url]

    ext = get_ext(url)
    filename = f"{hash_url(url)}{ext}"
    filepath = os.path.join(asset_dir, filename)

    if os.path.exists(filepath):
        index[url] = filename
        return filename

    for i in range(RETRY):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(resp.content)

            index[url] = filename
            print(f"[OK] {url}")
            return filename

        except Exception as e:
            if i == RETRY - 1:
                print(f"[FAIL] {url} -> {e}")
                return None
            time.sleep(2 ** i)  # exponential backoff


# -------------------------
# process single md
# -------------------------
def process_md(md_path, workers):
    base_dir = os.path.dirname(os.path.abspath(md_path))
    asset_dir = os.path.join(base_dir, ASSET_DIR_NAME)
    os.makedirs(asset_dir, exist_ok=True)

    index = load_index(asset_dir)

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = list(IMG_PATTERN.finditer(content))

    # 收集需要下载的 URL
    urls = {
        m.group(2)
        for m in matches
        if is_remote(m.group(2)) and not m.group(2).startswith("data:")
    }

    # 并发下载
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(download, url, asset_dir, index): url
            for url in urls
        }
        for f in as_completed(futures):
            pass

    # 替换
    def replacer(match):
        alt, url, title = match.groups()

        if url not in index:
            return match.group(0)

        new_url = f"{ASSET_DIR_NAME}/{index[url]}"

        if title:
            return f'![{alt}]({new_url} "{title}")'
        return f'![{alt}]({new_url})'

    new_content = IMG_PATTERN.sub(replacer, content)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    save_index(asset_dir, index)

    print(f"[DONE] {md_path} ({len(urls)} images)")


# -------------------------
# batch
# -------------------------
def collect_md_files(path):
    if os.path.isfile(path):
        return [path]

    result = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(".md"):
                result.append(os.path.join(root, f))
    return result


# -------------------------
# main
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="markdown file or directory")
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS)

    args = parser.parse_args()

    md_files = collect_md_files(args.path)

    for md in md_files:
        process_md(md, args.workers)


if __name__ == "__main__":
    main()
