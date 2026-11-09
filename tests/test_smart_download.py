import smart_download as sd


def clip(s, e, **kw):
    return dict(start=s, end=e, **kw)


def test_plan_pads_clamps_and_merges():
    shorts = [clip(100, 160), clip(170, 200), clip(900, 950), clip(5, 20)]
    r = sd.plan_ranges(shorts, duration=1000, pad=30, merge_gap=30)
    # 5-20 -> 0-50, 100-160 -> 70-190, 170-200 -> 140-230: the first gap is 20s (< 30)
    # so all three merge; 900-950 -> 870-980 stays apart
    assert r == [(0.0, 230.0), (870.0, 980.0)]
    # with a tighter merge gap the 0-50 stretch stays separate
    r2 = sd.plan_ranges(shorts, duration=1000, pad=30, merge_gap=10)
    assert r2 == [(0.0, 50.0), (70.0, 230.0), (870.0, 980.0)]


def test_plan_clamps_to_video_end_and_skips_empty():
    r = sd.plan_ranges([clip(990, 1000), clip(50, 50)], duration=1000, pad=30)
    assert r == [(960.0, 1000.0)]


def test_is_worth_it():
    assert sd.is_worth_it([(0, 100), (500, 600)], 6000)
    assert not sd.is_worth_it([(0, 4000)], 6000)
    assert not sd.is_worth_it([], 6000)


def test_place_uses_actual_durations():
    p = sd.place([(100, 160), (300, 345)], [60.02, 45.0])
    assert p[0]["offset"] == 0.0 and p[1]["offset"] == 60.02
    assert p[0]["src_end"] == 160 and p[1]["src_start"] == 300


def test_remap_clips_moves_times_and_drops_unfit():
    placements = sd.place([(100, 160), (300, 345)], [60.0, 45.0])
    data = {"shorts": [clip(110, 150, proposed=[109.5, 151]),
                       clip(310, 340),
                       clip(500, 520)],       # in no stretch: dropped
            "cost_analysis": {"x": 1}}
    out = sd.remap_clips(data, placements)
    assert [(c["start"], c["end"]) for c in out["shorts"]] == [(10.0, 50.0), (70.0, 100.0)]
    assert out["shorts"][0]["proposed"] == [9.5, 51.0]
    assert out["cost_analysis"] == {"x": 1}
    assert data["shorts"][0]["start"] == 110   # input untouched


def test_remap_clip_straddling_stretches_is_dropped():
    placements = sd.place([(100, 160)], [60.0])
    assert sd.remap_clips({"shorts": [clip(150, 170)]}, placements)["shorts"] == []


def test_remap_transcript_filters_words_and_shifts():
    tr = {"language": "en", "segments": [
        {"start": 95, "end": 105, "text": "a b", "words": [
            {"word": "a", "start": 95, "end": 99}, {"word": "b", "start": 101, "end": 104}]},
        {"start": 400, "end": 410, "text": "far", "words": [
            {"word": "far", "start": 400, "end": 410}]},
    ]}
    placements = sd.place([(100, 160)], [60.0])
    out = sd.remap_transcript(tr, placements)
    assert out["language"] == "en" and len(out["segments"]) == 1
    seg = out["segments"][0]
    assert seg["text"] == "b" and seg["words"] == [{"word": "b", "start": 1.0, "end": 4.0}]
    assert seg["start"] == 0.0 and seg["end"] == 5.0
