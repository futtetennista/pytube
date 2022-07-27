import math
import os
import time
import xml.etree.ElementTree as ElementTree
from html import unescape
from typing import Dict, Literal, Optional, List, Union

from pytube import request
from pytube.helpers import safe_filename, target_directory


class Caption:
    """Container for caption tracks."""

    def __init__(self, caption_track: Dict):
        """Construct a :class:`Caption <Caption>`.

        :param dict caption_track:
            Caption track data extracted from ``watch_html``.
        """
        self.url = caption_track.get("baseUrl")

        # Certain videos have runs instead of simpleText
        #  this handles that edge case
        name_dict = caption_track['name']
        if 'simpleText' in name_dict:
            self.name = name_dict['simpleText']
        else:
            for el in name_dict['runs']:
                if 'text' in el:
                    self.name = el['text']

        # Use "vssId" instead of "languageCode", fix issue #779
        self.code: str = caption_track["vssId"]
        # Remove preceding '.' for backwards compatibility, e.g.:
        # English -> vssId: .en, languageCode: en
        # English (auto-generated) -> vssId: a.en, languageCode: en
        self.code = self.code.strip('.')

    @property
    def xml_captions(self) -> str:
        """Download the xml caption tracks."""
        return request.get(self.url)

    def generate_srt_captions(self) -> str:
        """Generate "SubRip Subtitle" captions.

        Takes the xml captions from :meth:`~pytube.Caption.xml_captions` and
        recompiles them into the "SubRip Subtitle" format.
        """
        return self.xml_caption_to_srt(self.xml_captions)

    @staticmethod
    def timestamp_to_srt_time_format(timestamp: float) -> str:
        """Convert milliseconds durations into proper srt format.

        :rtype: str
        :returns:
            SubRip Subtitle (str) formatted time duration.

        float_to_srt_time_format(3890) -> '00:00:03,890'
        """
        # ms, secs = math.modf(timestamp / 1000)
        # mins, secs_ = math.modf(secs / 60)
        # hours, mins_ = math.modf(mins / 60)
        # ms_ = f"{ms:.3f}".replace('0.', '')
        # return f"{hours:02.0f}:{mins_:02.0f}:{secs_ if mins != 0 else secs:02.0f},{ms_}"
        return Caption.float_to_srt_time_format(timestamp / 1000)

    @staticmethod
    def float_to_srt_time_format(d: float) -> str:
        """Convert decimal durations into proper srt format.

        :rtype: str
        :returns:
            SubRip Subtitle (str) formatted time duration.

        float_to_srt_time_format(3.89) -> '00:00:03,890'
        """
        fraction, whole = math.modf(d)
        time_fmt = time.strftime("%H:%M:%S,", time.gmtime(whole))
        ms = f"{fraction:.3f}".replace("0.", "")
        return time_fmt + ms

    def generate_transcript(self) -> str:
        """Generate textual captions.

        Takes the xml captions from :meth:`~pytube.Caption.xml_captions` and
        recompiles them into a plain text format.
        """
        return self.xml_caption_to_transcript(self.xml_captions)

    def xml_caption_to_transcript(self, xml_captions: str) -> str:
        """Convert xml caption tracks to a plain text file".

        :param str xml_captions:
            XML formatted caption tracks.
        """

        import traceback
        from functools import reduce

        segments: List[str] = []
        root = ElementTree.fromstring(xml_captions)

        try:
            child = root.find('body')
            if child is None:
                raise AssertionError("XML caption doesn't have a <body> tag")

            for p in child.findall('p'):
                text = reduce(lambda acc, s: acc + (s.text or ""), p.findall('s'), "")
                caption = unescape(text.replace("\n", " ").replace("  ", " "))
                if caption != "":
                    segments.append(caption)
        except:
            traceback.print_exc()

        return " ".join(segments).strip()

    def xml_caption_to_srt(self, xml_captions: str) -> str:
        """Convert xml caption tracks to "SubRip Subtitle (srt)".

        :param str xml_captions:
            XML formatted caption tracks.
        """

        import traceback
        from functools import reduce

        def append_segment(
            segments: List[str],
            caption: str,
            start: float,
            end: float,
            sequence_number: int
        ) -> None:

            line = "{seq}\n{start} --> {end}\n{text}\n".format(
                seq=sequence_number,
                start=Caption.timestamp_to_srt_time_format(start),
                end=Caption.timestamp_to_srt_time_format(end),
                text=caption,
            )
            segments.append(line)

        segments: List[str] = []
        root = ElementTree.fromstring(xml_captions)

        try:
            child = root.find('body')
            if child is None:
                raise AssertionError("XML caption doesn't have a <body> tag")

            ps = child.findall('p')
            for i in range(len(ps)):
                p = ps[i]
                start = float(p.attrib["t"])
                text = reduce(lambda acc, s: acc + (s.text or ""), p.findall('s'), "")
                caption = unescape(text.replace("\n", " ").replace("  ", " "))
                if i + 1 < len(ps):
                    end = float(ps[i + 1].attrib['t'])
                else:
                    end = float(p.attrib['d'])
                append_segment(segments, caption, start, end, i + 1)
        except:
            traceback.print_exc()

        return "\n".join(segments).strip()

    def download(
        self,
        title: str,
        srt: bool = True,
        format: Optional[Union[Literal['srt'], Literal['xml'], Literal['txt']]] = 'srt',
        output_path: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> str:
        """Write the media stream to disk.

        :param title:
            Output filename (stem only) for writing media file.
            If one is not specified, the default filename is used.
        :type title: str
        :param srt:
            (deprecated) Set to True to download srt, false to download xml. Defaults to True.
        :type srt: bool
        :type format str
            Download captions in srt, xml or txt format. Defaults to 'srt'.
        :type srt: 'srt' or 'xml' or 'txt'
        :param output_path:
            (optional) Output path for writing media file. If one is not
            specified, defaults to the current working directory.
        :type output_path: str or None
        :param filename_prefix:
            (optional) A string that will be prepended to the filename.
            For example a number in a playlist or the name of a series.
            If one is not specified, nothing will be prepended
            This is separate from filename so you can use the default
            filename but still add a prefix.
        :type filename_prefix: str or None

        :rtype: str
        """
        if title.endswith(".srt") or title.endswith(".xml"):
            filename = ".".join(title.split(".")[:-1])
        else:
            filename = title

        if filename_prefix:
            filename = f"{safe_filename(filename_prefix)}{filename}"

        filename = safe_filename(filename)

        filename += f" ({self.code})"

        if format == 'srt':
            filename += ".srt"
        elif format == 'xml':
            filename += ".xml"
        else:
            filename += ".txt"

        file_path = os.path.join(target_directory(output_path), filename)

        with open(file_path, "w", encoding="utf-8") as file_handle:
            if format == 'srt':
                file_handle.write(self.generate_srt_captions())
            elif format == 'xml':
                file_handle.write(self.xml_captions)
            else:
                file_handle.write(self.generate_transcript())

        return file_path

    def __repr__(self):
        """Printable object representation."""
        return '<Caption lang="{s.name}" code="{s.code}">'.format(s=self)
