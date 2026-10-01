"""Download the public CAMP University checkpoint; do not deserialize it."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar
import datetime
import hashlib
import json
import os

OUT = Path(__file__).resolve().parent / 'latest_author_checkpoints'
FILE_ID = '1qHjXr3VVQuJZ5kE5u7YrUB8id90Nv2GJ'
SOURCE = 'https://github.com/Mabel0403/CAMP/blob/b04a9c856711770ed7a72ebf851838329c5e5b8e/README.md'


class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}
        self.active = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form' and a.get('id') == 'download-form':
            self.action = a.get('action')
            self.active = True
        elif tag == 'input' and self.active and a.get('name'):
            self.fields[a['name']] = a.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.active = False


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    OUT.mkdir(exist_ok=True)
    target = OUT / 'CAMP_University_author_checkpoint.pth'
    partial = target.with_suffix('.part')
    receipt = OUT / 'CAMP_University_download.json'
    if target.exists() or partial.exists() or receipt.exists():
        raise RuntimeError('Existing download evidence requires inspection; no implicit replacement')
    state = {'status': 'requesting', 'created_utc': utc(), 'source_readme': SOURCE,
             'source_commit': 'b04a9c856711770ed7a72ebf851838329c5e5b8e', 'drive_file_id': FILE_ID,
             'source_kind': 'author-provided checkpoint, not independently trained',
             'checkpoint_loaded': False, 'compatibility_verified': False}
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    url = 'https://drive.google.com/uc?' + urlencode({'export': 'download', 'id': FILE_ID})
    try:
        for step in range(3):
            response = opener.open(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30)
            mime = response.headers.get('Content-Type', '')
            if 'text/html' not in mime:
                break
            body = response.read(2 * 1024 * 1024).decode('utf-8', errors='replace')
            response.close()
            parser = DownloadForm()
            parser.feed(body)
            if not parser.action or parser.fields.get('id') != FILE_ID:
                raise RuntimeError('Public download did not return a file or matching confirmation form')
            host = (urlparse(parser.action).hostname or '').lower()
            if host not in ('drive.google.com', 'drive.usercontent.google.com'):
                raise RuntimeError('Unexpected confirmation endpoint')
            url = parser.action + '?' + urlencode(parser.fields)
        else:
            raise RuntimeError('Download confirmation did not yield a file')
        if any(kind in mime.lower() for kind in ('html', 'json', 'text/')):
            raise RuntimeError('Unexpected nonbinary response: ' + mime)
        limit = 2 * 1024**3
        declared = response.headers.get('Content-Length')
        if declared and int(declared) > limit:
            raise RuntimeError('Checkpoint exceeds the registered two-GiB download limit')
        state.update(status='downloading', content_type=mime,
                     content_disposition=response.headers.get('Content-Disposition'), declared_bytes=declared)
        receipt.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        digest = hashlib.sha256()
        count = 0
        with partial.open('xb') as stream:
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > limit:
                    raise RuntimeError('Download exceeded the registered size limit')
                stream.write(block)
                digest.update(block)
        response.close()
        if count < 1024 * 1024 or (declared and count != int(declared)):
            raise RuntimeError('Truncated or unexpectedly small checkpoint')
        os.replace(partial, target)
        state.update(status='downloaded_pending_compatibility_review', completed_utc=utc(),
                     path=str(target), bytes=count, sha256=digest.hexdigest())
    except BaseException as error:
        state.update(status='download_failed', failed_utc=utc(), error=f'{type(error).__name__}: {error}')
        raise
    finally:
        receipt.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
