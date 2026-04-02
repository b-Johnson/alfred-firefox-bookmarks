#!/usr/bin/env python3
# encoding: utf-8

"""bookmarks.py [command] [options] [<query>] [<url>]

Search and open Firefox bookmarks from Alfred.

Usage:
    bookmarks.py search [<query>]
    bookmarks.py settings
    bookmarks.py update
    bookmarks.py open <appkey> <url>

Options:
    -h, --help      Show this message

"""

import os
import subprocess
import sys
import time

from workflow import Workflow, ICON_WARNING, ICON_INFO
from workflow.background import is_running, run_in_background


# How often to refresh the bookmark cache (minutes)
DEFAULT_UPDATE_INTERVAL = 60

# GitHub repo for self-updating
UPDATE_SETTINGS = {'github_slug': 'b-Johnson/alfred-firefox-bookmarks'}

# GitHub Issues URL
HELP_URL = 'https://github.com/b-Johnson/alfred-firefox-bookmarks/issues'

# Icon shown when a newer version is available
ICON_UPDATE = 'update-available.png'

DEFAULT_SETTINGS = {
    'firefox_profile': None,
    'app_default': 'Firefox',
    'app_cmd': 'Browser',
    'app_alt': None,
    'app_ctrl': None,
    'app_shift': None,
    'app_fn': None,
}

# Will be populated later
log = None


class AttrDict(dict):
    """Access dictionary keys as attributes."""

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def settings_updated():
    """Return ``True`` if ``settings.json`` is newer than the bookmarks cache."""
    cache_age = wf.cached_data_age('bookmarks')
    settings_age = time.time() - os.stat(wf.settings_path).st_mtime
    log.debug('cache_age=%0.2f, settings_age=%0.2f', cache_age, settings_age)
    return settings_age < cache_age


def join_english(items):
    """Join a list of strings with commas and/or 'and'."""
    if isinstance(items, str):
        return items
    if len(items) == 1:
        return str(items[0])
    if len(items) == 2:
        return u' and '.join(items)
    return u', '.join(items[:-1]) + u' and {}'.format(items[-1])


def get_apps():
    """Load the app configuration from settings.

    Returns:
        dict: Modifier key → app name (str) or list of app names.
    """
    apps = {}
    for key, app in wf.settings.items():
        if not key.startswith('app_'):
            continue
        apps[key[4:]] = app[:]  if isinstance(app, list) else app

    if not apps.get('default'):
        apps['default'] = 'Firefox'

    return apps


def get_bookmarks(opts):
    """Load bookmarks from cache, triggering a background update if stale.

    Args:
        opts (AttrDict): Parsed CLI options.

    Returns:
        list[dict]: Cached bookmark records.
    """
    if not wf.cached_data_fresh('bookmarks', max_age=opts.update_interval):
        do_update()

    bookmarks = wf.cached_data('bookmarks', max_age=0)

    if not bookmarks:
        do_update()
        return []

    return bookmarks


def do_open(opts):
    """Open the given URL in the configured application(s).

    Args:
        opts (AttrDict): Parsed CLI options; uses ``opts.appkey`` and
            ``opts.url``.

    Returns:
        int: Exit status.
    """
    all_apps = get_apps()
    apps = all_apps.get(opts.appkey)

    if apps is None:
        log.warning('App key "%s" not configured. Use `bmsettings`.', opts.appkey)
        return 0

    if not isinstance(apps, list):
        apps = [apps]

    for app in apps:
        if app == 'Browser':
            log.info('Opening %s with system default browser', opts.url)
            subprocess.call(['open', opts.url])
        else:
            log.info('Opening %s with %s', opts.url, app)
            subprocess.call(['open', '-a', app, opts.url])

    return 0


def do_settings():
    """Open ``settings.json`` in the default editor.

    Returns:
        int: Exit status.
    """
    subprocess.call(['open', wf.settings_path])
    return 0


def do_update():
    """Trigger a background refresh of the bookmark cache.

    Returns:
        int: Exit status.
    """
    run_in_background('update', [sys.executable, 'update.py'])
    return 0


def do_search(bookmarks, opts):
    """Filter bookmarks and emit Alfred JSON results.

    Args:
        bookmarks (list[dict]): Cached bookmark records.
        opts (AttrDict): Parsed CLI options.

    Returns:
        int: Exit status.
    """
    apps = get_apps()
    subtitles = {}
    valid = {}

    for key, app in apps.items():
        if not app:
            subtitles[key] = (
                'App for {} not set. Use `bmsettings` to configure.'.format(key)
            )
            valid[key] = False
        else:
            subtitles[key] = u'Open in {}'.format(join_english(app))
            valid[key] = True

    if opts.query:
        bookmarks = wf.filter(
            opts.query,
            bookmarks,
            key=lambda b: u'{} {} {}'.format(
                b.get('title', ''), b.get('url', ''), b.get('folder', '')
            ),
            min_score=20,
        )
        log.info(u'%d bookmark(s) match "%s"', len(bookmarks), opts.query)

    if not bookmarks:
        wf.add_item('No matching bookmarks found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    for bm in bookmarks:
        title = bm.get('title') or bm.get('url', '')
        url = bm.get('url', '')
        folder = bm.get('folder', '')

        subtitle = url
        default_app_label = subtitles.get('default', '')
        if default_app_label:
            subtitle = u'{} — {}'.format(url, default_app_label)
        if folder:
            subtitle = u'[{}]  {}'.format(folder, subtitle)

        it = wf.add_item(
            title,
            subtitle,
            arg=url,
            uid=url,
            valid=valid.get('default', False),
            icon='icon.png',
        )
        it.setvar('appkey', 'default')

        for key in apps:
            if key == 'default':
                continue
            mod_subtitle = u'{}{} — {}'.format(
                u'[{}]  '.format(folder) if folder else '',
                url,
                subtitles[key],
            )
            mod = it.add_modifier(
                key.replace('_', '+'),
                mod_subtitle,
                arg=url,
                valid=valid[key],
            )
            mod.setvar('appkey', key)

    wf.send_feedback()
    return 0


def parse_args():
    """Parse CLI arguments into an AttrDict of options.

    Returns:
        AttrDict: Parsed options.
    """
    from docopt import docopt

    args = docopt(__doc__, wf.args)
    log.debug('args=%r', args)

    update_interval = int(
        os.getenv('UPDATE_EVERY_MINS', DEFAULT_UPDATE_INTERVAL)
    ) * 60

    opts = AttrDict(
        query=(args.get('<query>') or u'').strip(),
        url=args.get('<url>'),
        appkey=args.get('<appkey>') or 'default',
        update_interval=update_interval,
        do_search=args.get('search'),
        do_update=args.get('update'),
        do_settings=args.get('settings'),
        do_open=args.get('open'),
    )

    log.debug('opts=%r', opts)
    return opts


def main(wf):
    """Run the workflow."""
    opts = parse_args()

    if opts.do_open:
        return do_open(opts)

    if opts.do_settings:
        return do_settings()

    if opts.do_update:
        return do_update()

    # Notify user if a workflow update is available
    if wf.update_available:
        wf.add_item(
            u'Workflow Update Available',
            u'↩ or ⇥ to install',
            autocomplete='workflow:update',
            valid=False,
            icon=ICON_UPDATE,
        )

    # Refresh cache if settings were edited since last update
    if settings_updated():
        log.info('Settings updated — refreshing bookmark cache...')
        do_update()

    bookmarks = get_bookmarks(opts)

    if not bookmarks:
        if is_running('update'):
            wf.add_item(
                u'Loading bookmarks…',
                'Should be done in a few seconds',
                icon=ICON_INFO,
            )
            wf.rerun = 0.5
        else:
            wf.add_item(
                'No bookmarks found',
                'Check your settings with `bmsettings`',
                icon=ICON_WARNING,
            )
        wf.send_feedback()
        return 0

    if is_running('update'):
        wf.rerun = 0.5

    return do_search(bookmarks, opts)


if __name__ == '__main__':
    wf = Workflow(
        default_settings=DEFAULT_SETTINGS,
        update_settings=UPDATE_SETTINGS,
        help_url=HELP_URL,
    )
    log = wf.logger
    sys.exit(wf.run(main))
