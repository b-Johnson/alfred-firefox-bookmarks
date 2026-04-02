#!/usr/bin/env python3
# encoding: utf-8

"""Update the cache of Firefox bookmarks.

Reads bookmarks from Firefox's places.sqlite, building a full folder-path
breadcrumb for each bookmark entry, then stores the result in the workflow
cache for fast access by bookmarks.py.
"""

import glob
import os
import shutil
import sqlite3
import sys
import tempfile
from time import time

from workflow import Workflow

# Will be populated later
log = None

# Root folder IDs Firefox uses internally (these have no meaningful title)
FIREFOX_ROOT_IDS = {1, 2, 3, 4, 5}


def find_firefox_profile(profile_path=None):
    """Locate the Firefox profile directory containing places.sqlite.

    Args:
        profile_path (str|None): Explicit path from settings; ``None`` means
            auto-detect by preferring the ``default-release`` profile, then
            any other profile containing ``places.sqlite``.

    Returns:
        str: Absolute path to the selected Firefox profile directory.

    Raises:
        RuntimeError: If no suitable profile is found.
    """
    if profile_path:
        expanded = os.path.expanduser(profile_path)
        db = os.path.join(expanded, 'places.sqlite')
        if os.path.exists(db):
            return expanded
        raise RuntimeError(
            'No places.sqlite found at configured profile path: {}'.format(expanded)
        )

    profiles_root = os.path.expanduser(
        '~/Library/Application Support/Firefox/Profiles'
    )

    candidates = glob.glob(os.path.join(profiles_root, '*/places.sqlite'))
    if not candidates:
        raise RuntimeError(
            'No Firefox places.sqlite found under {}'.format(profiles_root)
        )

    # Prefer the default-release profile
    for path in candidates:
        if 'default-release' in path:
            return os.path.dirname(path)

    # Fall back to the first match
    return os.path.dirname(candidates[0])


def read_bookmarks(profile_dir):
    """Read all bookmarks from the Firefox profile, returning a list of dicts.

    Firefox locks ``places.sqlite`` while running, so the file is copied to a
    temporary location before querying.

    Args:
        profile_dir (str): Absolute path to the Firefox profile directory.

    Returns:
        list[dict]: Each dict has keys ``title``, ``url``, and ``folder``.
    """
    src_db = os.path.join(profile_dir, 'places.sqlite')

    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        shutil.copy2(src_db, tmp_path)
        bookmarks = _query_bookmarks(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return bookmarks


def _query_bookmarks(db_path):
    """Execute the SQLite query and return structured bookmark records.

    Args:
        db_path (str): Path to the (copied) places.sqlite file.

    Returns:
        list[dict]: Bookmark records with ``title``, ``url``, ``folder``.
    """
    sql = """
        SELECT
            b.id,
            COALESCE(NULLIF(b.title, ''), p.title, p.url) AS title,
            p.url,
            b.parent
        FROM moz_bookmarks b
        JOIN moz_places p ON b.fk = p.id
        WHERE b.type = 1
          AND p.url NOT LIKE 'place:%'
        ORDER BY b.lastModified DESC
    """

    folder_sql = """
        SELECT id, title, parent
        FROM moz_bookmarks
        WHERE type = 2
    """

    conn = sqlite3.connect('file:{}?mode=ro&immutable=1'.format(db_path),
                           uri=True)
    conn.row_factory = sqlite3.Row

    try:
        folders = {}
        for row in conn.execute(folder_sql):
            folders[row['id']] = {
                'title': row['title'] or '',
                'parent': row['parent'],
            }

        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    bookmarks = []
    for row in rows:
        folder_path = _build_folder_path(row['parent'], folders)
        bookmarks.append({
            'title': row['title'],
            'url': row['url'],
            'folder': folder_path,
        })

    return bookmarks


def _build_folder_path(folder_id, folders):
    """Walk the folder hierarchy upward to build a breadcrumb path string.

    Args:
        folder_id (int): The ``parent`` id of the bookmark entry.
        folders (dict): Mapping of id → {title, parent} for all folder rows.

    Returns:
        str: Human-readable breadcrumb, e.g. ``"Bookmarks Menu > Dev > Python"``.
    """
    parts = []
    current_id = folder_id

    while current_id and current_id not in FIREFOX_ROOT_IDS:
        folder = folders.get(current_id)
        if not folder:
            break
        title = folder['title']
        if title:
            parts.append(title)
        current_id = folder.get('parent')

    parts.reverse()
    return ' > '.join(parts) if parts else ''


def main(wf):
    """Run the bookmark cache update."""
    start = time()

    profile_path = wf.settings.get('firefox_profile')

    try:
        profile_dir = find_firefox_profile(profile_path)
    except RuntimeError as err:
        log.error('%s', err)
        return 1

    log.info('Reading bookmarks from: %s', profile_dir)

    try:
        bookmarks = read_bookmarks(profile_dir)
    except Exception as err:
        log.exception('Failed to read bookmarks: %s', err)
        return 1

    wf.cache_data('bookmarks', bookmarks)

    log.info('%d bookmark(s) cached in %0.2fs', len(bookmarks), time() - start)
    log.info('update finished')
    [h.flush() for h in log.handlers]

    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
