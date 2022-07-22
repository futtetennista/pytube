import os
import pytest
from unittest import mock
from unittest.mock import MagicMock, mock_open, patch

from pytube import Caption, CaptionQuery, captions


def test_float_to_srt_time_format():
    caption1 = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    assert caption1.float_to_srt_time_format(3.89) == "00:00:03,890"


def test_caption_query_sequence():
    caption1 = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    caption2 = Caption(
        {"url": "url2", "name": {"simpleText": "name2"}, "languageCode": "fr", "vssId": ".fr"}
    )
    caption_query = CaptionQuery(captions=[caption1, caption2])
    assert len(caption_query) == 2
    assert caption_query["en"] == caption1
    assert caption_query["fr"] == caption2
    with pytest.raises(KeyError):
        assert caption_query["nada"] is not None


def test_caption_query_get_by_language_code_when_exists():
    caption1 = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    caption2 = Caption(
        {"url": "url2", "name": {"simpleText": "name2"}, "languageCode": "fr", "vssId": ".fr"}
    )
    caption_query = CaptionQuery(captions=[caption1, caption2])
    assert caption_query["en"] == caption1


def test_caption_query_get_by_language_code_when_not_exists():
    caption1 = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    caption2 = Caption(
        {"url": "url2", "name": {"simpleText": "name2"}, "languageCode": "fr", "vssId": ".fr"}
    )
    caption_query = CaptionQuery(captions=[caption1, caption2])
    with pytest.raises(KeyError):
        assert caption_query["hello"] is not None
        # assert not_found is not None  # should never reach here


@mock.patch("pytube.captions.Caption.generate_srt_captions")
def test_download(srt):
    open_mock = mock_open()
    with patch("builtins.open", open_mock):
        srt.return_value = ""
        caption = Caption(
            {
                "url": "url1",
                "name": {"simpleText": "name1"},
                "languageCode": "en",
                "vssId": ".en"
            }
        )
        caption.download("title")
        assert (
            open_mock.call_args_list[0][0][0].split(os.path.sep)[-1] == "title (en).srt"
        )


@mock.patch("pytube.captions.Caption.generate_srt_captions")
def test_download_with_prefix(srt):
    open_mock = mock_open()
    with patch("builtins.open", open_mock):
        srt.return_value = ""
        caption = Caption(
            {
                "url": "url1",
                "name": {"simpleText": "name1"},
                "languageCode": "en",
                "vssId": ".en"
            }
        )
        caption.download("title", filename_prefix="1 ")
        assert (
            open_mock.call_args_list[0][0][0].split(os.path.sep)[-1]
            == "1 title (en).srt"
        )


@mock.patch("pytube.captions.Caption.generate_srt_captions")
def test_download_with_output_path(srt):
    open_mock = mock_open()
    captions.target_directory = MagicMock(return_value="/target")
    with patch("builtins.open", open_mock):
        srt.return_value = ""
        caption = Caption(
            {
                "url": "url1",
                "name": {"simpleText": "name1"},
                "languageCode": "en",
                "vssId": ".en"
            }
        )
        file_path = caption.download("title", output_path="blah")
        assert file_path == os.path.join("/target","title (en).srt")
        captions.target_directory.assert_called_with("blah")


@mock.patch("pytube.captions.Caption.xml_captions")
def test_download_xml_and_trim_extension(xml):
    open_mock = mock_open()
    with patch("builtins.open", open_mock):
        xml.return_value = ""
        caption = Caption(
            {
                "url": "url1",
                "name": {"simpleText": "name1"},
                "languageCode": "en",
                "vssId": ".en"
            }
        )
        caption.download("title.xml", format='xml')
        assert (
            open_mock.call_args_list[0][0][0].split(os.path.sep)[-1] == "title (en).xml"
        )


def test_repr():
    caption = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    assert str(caption) == '<Caption lang="name1" code="en">'

    caption_query = CaptionQuery(captions=[caption])
    assert repr(caption_query) == '{\'en\': <Caption lang="name1" code="en">}'


@mock.patch("pytube.request.get")
def test_xml_captions(request_get):
    request_get.return_value = "test"
    caption = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    assert caption.xml_captions == "test"


@mock.patch("pytube.captions.request")
def test_generate_srt_captions(request):
    request.get.return_value = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<timedtext format="3">'
        '<body>'
        '<w t="0" />'
        '<p t="320" d="1.7">'
        '<s ac="255">[Herb, Software Engineer]\n本影片包含隱藏式字幕。</s>'
        '</p>'
        '<p t="1750" d="2410" w="1" a="1"> </p>'
        '<p t="1760" d="5119" w="1">'
        '<s ac="255">如要啓動字幕，請按一下這裡的圖示。</s>'
        '</p>'
        '</body>'
        '</timedtext>'
    )

    caption = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )

    assert caption.generate_srt_captions() == (
        "1\n"
        "00:00:00,320 --> 00:00:01,750\n"
        "[Herb, Software Engineer] 本影片包含隱藏式字幕。\n"
        "\n"
        "2\n"
        "00:00:01,750 --> 00:00:01,760\n"
        "\n" # empty text
        "\n"
        "3\n"
        "00:00:01,760 --> 00:00:05,119\n"
        "如要啓動字幕，請按一下這裡的圖示。"
    )

def test_timestamp_to_srt_time_format():
    assert Caption.timestamp_to_srt_time_format(3890) == '00:00:03,890'
    assert Caption.timestamp_to_srt_time_format(1_000) == "00:00:01,000"
    assert Caption.timestamp_to_srt_time_format(10_003) == "00:00:10,003"
    assert Caption.timestamp_to_srt_time_format(70_003) == "00:01:10,003"
    assert Caption.timestamp_to_srt_time_format(123_123) == "00:02:03,123"
    assert Caption.timestamp_to_srt_time_format(3_903_123) == "01:05:03,123"
