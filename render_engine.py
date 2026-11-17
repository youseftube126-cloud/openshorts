import os
import subprocess

FORMATS = {
    "podcast_vertical": {"name": "Podcast Vertical", "font": "Montserrat", "font_size": 80, "primary_color": "#FFFFFF", "highlight_color": "#FFD700", "animation": "pop_up", "split_screen": False},
    "cinematic_kinetic": {"name": "Cinematic Kinetic", "font": "Montserrat", "font_size": 85, "primary_color": "#FFFFFF", "highlight_color": "#FFD700", "animation": "bounce", "split_screen": False},
    "minimalist_word": {"name": "Minimalist Word", "font": "Bebas Neue", "font_size": 100, "primary_color": "#FFFFFF", "highlight_color": "#FFFFFF", "animation": "hard_cut", "split_screen": False},
    "deep_quote": {"name": "Deep Quote", "font": "Playfair Display", "font_size": 80, "primary_color": "#FFFFFF", "highlight_color": "#87CEEB", "animation": "soft_fade", "split_screen": False},
    "raw_motivational": {"name": "Raw Motivational", "font": "Bebas Neue", "font_size": 90, "primary_color": "#FFFFFF", "highlight_color": "#FF3B30", "animation": "hard_pop", "split_screen": False},
    "two_speaker": {"name": "Two Speaker Switch", "font": "Montserrat", "font_size": 75, "primary_color": "#FFFFFF", "highlight_color": "#9A8CFF", "animation": "hard_cut", "split_screen": True}
}

def hex_to_ass(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return f"&H{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}&"
    return "&H00FFFFFF&"

def generate_ass(transcript, format_id, output_path):
    config = FORMATS.get(format_id, FORMATS["podcast_vertical"])
    font, size, anim = config["font"], config["font_size"], config["animation"]
    p_color, h_color = hex_to_ass(config["primary_color"]), hex_to_ass(config["highlight_color"])

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{p_color},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    words = transcript.get("words", [])
    if not words and "segments" in transcript:
        for seg in transcript["segments"]:
            if "words" in seg: words.extend(seg["words"])

    for w in words:
        start, end, word = w.get("start", 0), w.get("end", 0), w.get("word", "").strip()
        if not word: continue
        
        t_start = f"{int(start//3600)}:{int((start%3600)//60):02d}:{start%60:05.2f}"
        t_end = f"{int(end//3600)}:{int((end%3600)//60):02d}:{end%60:05.2f}"
        
        text = word
        if anim == "pop_up": text = f"{{\\c{h_color}&\\fscx130\\fscy130\\t(0,150,\\fscx100\\fscy100)}}{word}"
        elif anim == "hard_pop": text = f"{{\\c{h_color}&\\fscx120\\fscy120}}{word}"
        elif anim == "soft_fade": text = f"{{\\fad(150,150)}}{word}"
            
        events.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))
    return output_path

def render_with_format(video_path, transcript, format_id, output_path):
    config = FORMATS.get(format_id, FORMATS["podcast_vertical"])
    ass_path = output_path.replace(".mp4", ".ass")
    generate_ass(transcript, format_id, ass_path)
    
    fonts_dir = os.path.abspath("./assets/fonts")
    vf = f"subtitles={ass_path}:fontsdir={fonts_dir}"
    
    if config["split_screen"]:
        vf = f"[0:v]crop=iw:ih/2:0:0[top];[0:v]crop=iw:ih/2:0:ih/2[bottom];[top][bottom]vstack,subtitles={ass_path}:fontsdir={fonts_dir}"

    cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-b:a", "192k", output_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path