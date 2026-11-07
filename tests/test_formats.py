import formats


WORDS = [{"w": "hello", "s": 0.0, "e": 0.4}, {"w": " ", "s": 0.4, "e": 0.5},
         {"w": "world", "s": 0.5, "e": 0.5}]


def test_list_formats_has_four_with_layout():
    items = formats.list_formats()
    assert {i["id"] for i in items} == set(formats.FORMATS)
    assert all(i["layout"] for i in items)


def test_captions_skip_blank_and_fix_zero_length():
    caps = formats.captions_from_words(WORDS)
    assert [c["text"] for c in caps] == ["hello", "world"]
    assert caps[1]["endMs"] > caps[1]["startMs"]


def test_unknown_format_falls_back():
    assert formats.build_project("nope", WORDS, 20)["format"] == formats.DEFAULT_FORMAT


def test_no_hook_text_means_no_hook_layer():
    assert formats.build_project("podcast", WORDS, 20, "  ")["hook"] is None
    assert formats.build_project("podcast", WORDS, 20, "Wait")["hook"]["text"] == "Wait"


def test_punches_do_not_overlap_or_touch_first_second_or_end():
    segs = formats.build_project("storytelling", WORDS, 30)["effects"]["segments"]
    assert segs
    assert segs[0]["startSec"] >= 1.0
    assert all(a["endSec"] <= b["startSec"] for a, b in zip(segs, segs[1:]))
    assert segs[-1]["endSec"] <= 30 - 0.3


def test_split_screen_has_no_zooms():
    assert formats.build_project("split_screen", WORDS, 30)["effects"]["segments"] == []


def test_overrides_whitelist_and_style_merge():
    base = formats.build_project("talking_head", WORDS, 20, "Hi")
    out = formats.apply_overrides(base, {
        "subtitles": {"position": "top", "evil": 1,
                      "style": {"fontSize": 90, "hack": "x"}},
        "hook": {"text": "New", "captions": []},
    })
    assert out["subtitles"]["position"] == "top"
    assert out["subtitles"]["style"]["fontSize"] == 90
    assert "evil" not in out["subtitles"] and "hack" not in out["subtitles"]["style"]
    assert out["hook"]["text"] == "New" and "captions" not in out["hook"]
    assert base["subtitles"]["position"] == "bottom"  # input untouched
