from __future__ import unicode_literals

import re

from .common import FileDownloader
from ..utils import (
    int_or_none,
    sanitized_Request
)


class DashSegmentsFD(FileDownloader):
    """
    Download segments in a DASH manifest
    """
    def real_download(self, filename, info_dict):
        self.report_destination(filename)
        tmpfilename = self.temp_name(filename)
        base_url = info_dict['url']
        try:
            segment_urls = info_dict['segment_urls']
        except KeyError:
            segment_urls = None

        try:
            incremental_byte_ranges = info_dict['incremental_byte_ranges']
        except KeyError:
            incremental_byte_ranges = False            

        if incremental_byte_ranges is True:
            remaining_bytes = info_dict['filesize'] - 1
            total_bytes = remaining_bytes
            start_bytes = int_or_none(info_dict['initialization_range'].split('-')[0])
            incremental_bytes = info_dict['incremental_bytes']
            end_bytes = remaining_bytes if remaining_bytes < incremental_bytes else incremental_bytes
        else:
            is_test = self.params.get('test', False)
            remaining_bytes = self._TEST_FILE_SIZE if is_test else None

        byte_counter = 0

        def append_url_to_file(outf, target_url, target_name, remaining_bytes=None):
            self.to_screen('[DashSegments] %s: Downloading %s' % (info_dict['id'], target_name))
            req = sanitized_Request(target_url)
            if remaining_bytes is not None:
                if incremental_byte_ranges is True:
                    req.add_header('Range', 'bytes=%d-%d' % (start_bytes, end_bytes))
                else:
                    req.add_header('Range', 'bytes=0-%d' % (remaining_bytes - 1))

            data = self.ydl.urlopen(req).read()

            if remaining_bytes is not None:
                data = data[:remaining_bytes]

            outf.write(data)
            return len(data)

        def combine_url(base_url, target_url):
            if re.match(r'^https?://', target_url):
                return target_url
            return '%s%s%s' % (base_url, '' if base_url.endswith('/') else '/', target_url)

        with open(tmpfilename, 'wb') as outf:
            if incremental_byte_ranges is True:
                while True:
                    print(True)
                    append_url_to_file(
                        outf, base_url,
                        ('bytes range: %d of %d' % (start_bytes, end_bytes)),
                        remaining_bytes)

                    remaining_bytes -= incremental_bytes

                    if remaining_bytes <= 0:
                        break;
                    else:
                        if start_bytes == 0:
                            start_bytes += 1 # NOTE To not clash with byte ranges
                        start_bytes += incremental_bytes
                        end_bytes += incremental_bytes
                        byte_counter += incremental_bytes

            else:
                append_url_to_file(
                    outf, combine_url(base_url, info_dict['initialization_url']),
                    'initialization segment')
                for i, segment_url in enumerate(segment_urls):
                    segment_len = append_url_to_file(
                        outf, combine_url(base_url, segment_url),
                        'segment %d / %d' % (i + 1, len(segment_urls)),
                        remaining_bytes)
                    byte_counter += segment_len
                    if remaining_bytes is not None:
                        remaining_bytes -= segment_len
                        if remaining_bytes <= 0:
                            break

        self.try_rename(tmpfilename, filename)

        self._hook_progress({
            'downloaded_bytes': byte_counter,
            'total_bytes': remaining_bytes if incremental_byte_ranges is True else byte_counter,
            'filename': filename,
            'status': 'finished',
        })

        return True
