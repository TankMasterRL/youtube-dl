# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_urllib_request,
)
from ..utils import (
    determine_ext,
    int_or_none,
    str_or_none,
)


class SVTBaseIE(InfoExtractor):
    # Based upon url_basename() in 'utils.py'
    def _url_basepath(self, url):
        parsed_url = compat_urllib_parse_urlparse(url)
        paths = parsed_url.path.strip('/').split('/')
        full_path = '%s://%s/' % (parsed_url.scheme, parsed_url.netloc)
        full_path += '/'.join(paths[0:-1])
        #print(full_path)

        return (full_path + '/')

    def _get_dash_filesize(self, dash_media_url):
        # TODO No proxy support

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:43.0) Gecko/20100101 Firefox/43.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': 1,
            'Range': 'bytes=0-719',
            'Origin': 'http://www.svtplay.se',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }
        request = compat_urllib_request.Request(dash_media_url, headers=headers)
        downloaded = compat_urllib_request.urlopen(request)
        media_headers = downloaded.info()
        #print(media_headers.get('Content-Range').split('/')[1])

        return media_headers.get('Content-Range').split('/')[1]

    # Based upon _parse_dash_manifest() in the 'youtube.py' extractor
    def _parse_dash_manifest(
        self, video_id, dash_manifest_url, fatal=True):
        #print(dash_manifest_url)
        dash_doc = self._download_xml(
            dash_manifest_url, video_id,
            note='Downloading DASH manifest',
            errnote='Could not download DASH manifest',
            fatal=fatal)
        #from xml.etree.ElementTree import tostring as tostringxml
        #print(tostringxml(dash_doc))
        #print(dash_doc.findall('.//{urn:mpeg:dash:schema:mpd:2011}Period/{urn:mpeg:dash:schema:mpd:2011}AdaptationSet'))

        if dash_doc is False:
            return []

        baseurl = self._url_basepath(dash_manifest_url)
        formats = []
        for a in dash_doc.findall('.//{urn:mpeg:dash:schema:mpd:2011}Period/{urn:mpeg:dash:schema:mpd:2011}AdaptationSet'):
        #for a in dash_doc.findall('.//{urn:mpeg:DASH:schema:MPD:2011}AdaptationSet'):
            #print(True)
            mime_type = a.attrib.get('mimeType')
            for r in a.findall('{urn:mpeg:dash:schema:mpd:2011}Representation'):
                url_el = r.find('{urn:mpeg:dash:schema:mpd:2011}BaseURL')
                if url_el is None:
                    continue
                if mime_type == 'text/vtt':
                    # TODO implement WebVTT downloading
                    pass
                elif mime_type.startswith('audio/') or mime_type.startswith('video/'):
                    segment_list = r.find('{urn:mpeg:dash:schema:mpd:2011}SegmentBase')
                    #print(segment_list)
                    #format_id = r.attrib['id'] # TODO Doesn't contain a valid media format tag
                    video_url = baseurl + url_el.text
                    #print(video_url)
                    file_size = self._get_dash_filesize(video_url)
                    f = {
                        #'format_id': format_id, # TODO Doesn't contain a valid media format tag
                        #'format_id': int_or_none(r.attrib.get('bandwidth'), 1000),
                        'url': video_url,
                        'tbr': int_or_none(r.attrib.get('bandwidth'), 1000),
                        'filesize': file_size,
                        'format_note': 'DASH video' if mime_type.startswith('video/') else 'DASH audio',
                        'width': int_or_none(r.attrib.get('width')),
                        'height': int_or_none(r.attrib.get('height')),
                        'fps': int_or_none(r.attrib.get('frameRate')),
                    }
                    if mime_type.startswith('video/'):
                        f.update({
                            'format-id': 'mp4-%d' % int_or_none(r.attrib.get('bandwidth'), 1000),
                            'ext': 'mp4',                           
                            'acodec': 'none',
                            'vcodec': str_or_none(r.attrib.get('codecs')),
                            'container': 'mp4',
                        })
                    else:
                        f.update({
                            'format-id': 'm4a-%d' % int_or_none(r.attrib.get('bandwidth'), 1000),
                            'ext': 'm4a',
                            'asr': int_or_none(r.attrib.get('audioSamplingRate')),
                            'acodec': str_or_none(r.attrib.get('codecs')),
                            'vcodec': 'none',
                            'container': 'm4a_dash',
                        })

                    #if segment_list is not None:
                    f.update({
                        'incremental_byte_ranges': True,
                        # NOTE will these be needed in the future?
                        'initialization_range': segment_list.find('{urn:mpeg:dash:schema:mpd:2011}Initialization').attrib.get('range'),
                        'segment_indexRange': segment_list.attrib.get('indexRange'),
                        #
                        'incremental_bytes': 3900,
                        'protocol': 'http_dash_segments',
                        #'http-headers': {
                        #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:43.0) Gecko/20100101 Firefox/43.0',
                        #    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        #    'Accept-Language': 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3',
                        #    'Accept-Encoding': 'gzip, deflate',
                        #    'DNT': 1,
                        #    'Origin': 'http://www.svtplay.se',
                        #    'Connection': 'keep-alive',
                        #},
                    })
                    print(f)
                    formats.append(f)
                    # try:
                    #     existing_format = next(
                    #         fo for fo in formats
                    #         if fo['format_id'] == format_id)
                    # except StopIteration:
                    #     full_info = self._formats.get(format_id, {}).copy()
                    #     full_info = {}
                    #     full_info.update(f)
                    #     codecs = r.attrib.get('codecs')
                    #     if codecs:
                    #         if full_info.get('acodec') == 'none' and 'vcodec' not in full_info:
                    #             full_info['vcodec'] = codecs
                    #         elif full_info.get('vcodec') == 'none' and 'acodec' not in full_info:
                    #             full_info['acodec'] = codecs
                    #     formats.append(full_info)
                    # else:
                    #     existing_format.update(f)
                else:
                    self.report_warning('Unknown MIME type %s in DASH manifest' % mime_type)
        return formats

    def _extract_video(self, url, video_id):
        extract_info = {}
        info = self._download_json(url, video_id)

        title = info['context']['title']
        thumbnail = info['context'].get('thumbnailImage')

        video_info = info['video']
        formats = []
        for vr in video_info['videoReferences']:
            vurl = vr['url']
            ext = determine_ext(vurl)
            #self.to_screen('%s' % ext)
            if ext == 'mpd':
                formats.extend(self._parse_dash_manifest(
                    video_id, vurl))
                extract_info.update({
                    'ext': 'mp4'
                })
            # elif ext == 'm3u8':
            #     formats.extend(self._extract_m3u8_formats(
            #         vurl, video_id,
            #         ext='mp4', entry_protocol='m3u8_native',
            #         m3u8_id=vr.get('playerType')))
            # elif ext == 'f4m':
            #     formats.extend(self._extract_f4m_formats(
            #         vurl + '?hdcore=3.7.0', video_id,
            #         f4m_id=vr.get('playerType')))            
            # else:
            #     formats.append({
            #         'format_id': vr.get('playerType'),
            #         'url': vurl,
            #     })
        self._sort_formats(formats)
        #self.to_screen('%s' % formats)

        duration = video_info.get('materialLength')
        age_limit = 18 if video_info.get('inappropriateForChildren') else 0

        extract_info.update({
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': age_limit,
        })

        return extract_info


class SVTIE(SVTBaseIE):
    _VALID_URL = r'https?://(?:www\.)?svt\.se/wd\?(?:.*?&)?widgetId=(?P<widget_id>\d+)&.*?\barticleId=(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.svt.se/wd?widgetId=23991&sectionId=3502&articleId=5767292&type=embed&contextSectionId=3502&autostart=false',
        #'md5': '9648197555fc1b49e3dc22db4af51d46',
        'info_dict': {
            'id': '5767292',
            'ext': 'mp4',
            'title': 'Solfilmen 2016-01-08',
            'duration': 52,
            'age_limit': 0,
        },
    }

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'(?:<iframe src|href)="(?P<url>%s[^"]*)"' % SVTIE._VALID_URL, webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        widget_id = mobj.group('widget_id')
        article_id = mobj.group('id')
        return self._extract_video(
            'http://www.svt.se/wd?widgetId=%s&articleId=%s&format=json&type=embed&output=json' % (widget_id, article_id),
            article_id)


class SVTPlayIE(SVTBaseIE):
    IE_DESC = 'SVT Play and Öppet arkiv'
    _VALID_URL = r'https?://(?:www\.)?(?P<host>svtplay|oppetarkiv)\.se/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.svtplay.se/video/5616500/radd-for-att-flyga/radd-for-att-flyga-avsnitt-1',
        #'md5': 'ade3def0643fa1c40587a422f98edfd9',
        'info_dict': {
            'id': '5616500',
            'ext': 'mp4',
            'title': 'Rädd för att flyga',
            'duration': 549,
            'thumbnail': 're:^https?://.*[\.-]jpg$',
            'age_limit': 0,
        },
    }, {
        'url': 'http://www.oppetarkiv.se/video/1297031/midsommar-midsommarvaka',
        #'md5': 'c3101a17ce9634f4c1f9800f0746c187',
        'info_dict': {
            'id': '1297031',
            'ext': 'mp4',
            'title': 'Midsommar',
            'duration': 687,
            'thumbnail': 're:^https?://.*[\.-]jpg$',
            'age_limit': 0,
        },
        'skip': 'Only works from Sweden',
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        host = mobj.group('host')
        return self._extract_video(
            'http://www.%s.se/video/%s?output=json' % (host, video_id),
            video_id)
