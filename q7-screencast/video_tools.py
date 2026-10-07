"""macOS speech + FFmpeg production helpers (isolated document/video environment).

Run .local/qwen-tools/.venv/bin/python backend/q7-screencast/video_tools.py
prepare|render|verify from the workspace. Requires imageio-ffmpeg; no product
dependency changes. Synthesized speech is explicitly disclosed in the movie.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import textwrap
import wave
from pathlib import Path

import imageio_ffmpeg

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
WORK = ROOT / ".local/demo-video"
MOVIE = SOURCE / "screencast.mp4"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((SOURCE / "video-narration.json").read_text())
    for scene in scenes:
        speech = WORK / (scene["id"] + ".txt")
        aiff = WORK / (scene["id"] + ".aiff")
        wav = WORK / (scene["id"] + ".wav")
        speech.write_text(scene["text"])
        run(["say", "-v", "Samantha", "-r", "175", "-f", str(speech), "-o", str(aiff)])
        run([FFMPEG, "-y", "-i", str(aiff), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        with wave.open(str(wav)) as audio:
            scene.update(duration=audio.getnframes()/audio.getframerate(), audio=str(wav))
        print(f"{scene['id']}: {scene['duration']:.2f}s", flush=True)
    (WORK / "audio.json").write_text(json.dumps(scenes, indent=2))
    print(f"Total narration: {sum(c['duration'] for c in scenes):.2f}s; words: {sum(len(c['text'].split()) for c in scenes)}")


def timestamp(seconds, ass=False):
    units = round(seconds * (100 if ass else 1000))
    scale = 100 if ass else 1000
    h, remain = divmod(units, 3600 * scale)
    m, remain = divmod(remain, 60 * scale)
    s, frac = divmod(remain, scale)
    return f"{h}:{m:02}:{s:02}.{frac:02}" if ass else f"{h:02}:{m:02}:{s:02},{frac:03}"


def render():
    timeline = json.loads((WORK / "timeline.json").read_text())
    assert timeline["failure"] is None, "Failed takes remain retained; do not encode as successful demonstration"
    duration = timeline["duration"]
    assert duration < 480, f"Recording exceeds 8-minute assignment limit: {duration}s"
    frames = timeline["frames"]
    # No time compression: each sampled frame lasts until the next real capture.
    manifest = ["ffconcat version 1.0"]
    for i, frame in enumerate(frames):
        end = frames[i+1]["at"] if i+1 < len(frames) else duration
        escaped = frame["file"].replace("'", "'\\''")
        manifest += [f"file '{escaped}'", f"duration {max(0.001,end-frame['at']):.6f}"]
    manifest += [f"file '{frames[-1]['file']}'"]
    (WORK / "frames.ffconcat").write_text("\n".join(manifest)+"\n")

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,Arial,21,&H00FFFFFF,&H00FFFFFF,&H00101827,&H00101827,0,0,0,0,100,100,0,0,1,0,0,2,28,28,8,1
Style: Chapter,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00101827,&H00101827,-1,0,0,0,100,100,0,0,1,0,0,7,18,18,11,1
Style: Disclosure,Arial,15,&H00B5CEE9,&H00B5CEE9,&H00101827,&H00101827,0,0,0,0,100,100,0,0,1,0,0,9,18,18,13,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,0:00:00.00,{timestamp(duration,True)},Disclosure,,0,0,0,,Automated live UI · computer-generated voice"]
    subtitles = []
    for scene in timeline["scenes"]:
        start, end = scene["start"], scene["end"]
        events.append(f"Dialogue: 0,{timestamp(start,True)},{timestamp(end,True)},Chapter,,0,0,0,,{scene['title']}")
        # Equal speech-word timing within each generated utterance. Audio begins
        # at exactly the recorded beat start; long captions split into 2 lines.
        words = scene["text"].split()
        groups, group = [], []
        for word in words:
            if len(" ".join(group+[word])) > 110 and group:
                groups.append(group); group=[]
            group.append(word)
        if group: groups.append(group)
        offset = 0
        for group in groups:
            cap_start = start + scene["duration"] * offset / len(words)
            offset += len(group)
            cap_end = start + scene["duration"] * offset / len(words)
            caption = "\n".join(textwrap.wrap(" ".join(group), width=84))
            ass_text = caption.replace("\n", "\\N")
            events.append(f"Dialogue: 1,{timestamp(cap_start,True)},{timestamp(cap_end,True)},Subtitle,,0,0,0,,{ass_text}")
            subtitles.append(f"{len(subtitles)+1}\n{timestamp(cap_start)} --> {timestamp(cap_end)}\n{caption}\n")
    (WORK / "captions.ass").write_text(header+"\n".join(events)+"\n")
    (SOURCE / "screencast.srt").write_text("\n".join(subtitles))
    fonts = WORK / "fonts"
    fonts.mkdir(exist_ok=True)
    for name in ["Arial.ttf", "Arial Bold.ttf"]:
        # System font metadata includes protected macOS flags. Only the bytes
        # are needed by libass; copying those flags fails on ordinary files.
        shutil.copyfile(Path("/System/Library/Fonts/Supplemental") / name, fonts / name)

    # Construct one actual soundtrack with speech placed on the wall-clock
    # timeline; preserve silent action/wait periods rather than trimming them.
    rate = 48000
    samples = bytearray(int((duration+0.05)*rate)*2)
    for scene in timeline["scenes"]:
        with wave.open(scene["audio"]) as audio:
            assert audio.getframerate() == rate and audio.getsampwidth() == 2
            data = audio.readframes(audio.getnframes())
        begin = round(scene["start"]*rate)*2
        samples[begin:begin+len(data)] = data
    soundtrack = WORK / "soundtrack.wav"
    with wave.open(str(soundtrack),"wb") as audio:
        audio.setparams((1,2,rate,0,"NONE","not compressed"));audio.writeframes(samples)
    args = [FFMPEG,"-y","-hide_banner","-f","concat","-safe","0","-i",str(WORK/"frames.ffconcat"),"-i",str(soundtrack),
            "-vf",f"pad=1280:720:0:44:color=0x101827,ass='{WORK}/captions.ass':fontsdir='{fonts}'",
            "-r","24","-c:v","libx264","-preset","fast","-crf","23","-maxrate","1100k","-bufsize","2200k",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","96k","-t",str(duration),"-movflags","+faststart",
            "-metadata","title=SkipQ live application demonstration",
            "-metadata","comment=Automated real UI recording with computer-generated narration; all elapsed waits preserved.",str(MOVIE)]
    print("Encoding",len(frames),"real frames; duration",duration,flush=True)
    result=run(args)
    (WORK/"encode.log").write_text(result.stderr)
    chapters = [f"{timestamp(c['start']).split(',')[0]} — {c['title']}" for c in timeline["scenes"]]
    (SOURCE / "video-chapters.md").write_text("# Video chapters\n\nComputer-generated voice; automated live browser actions. No error/retry cuts.\n\n"+"\n".join("- "+c for c in chapters)+"\n")
    print("Encoded",MOVIE,"bytes",MOVIE.stat().st_size,flush=True)


def verify():
    # FFmpeg's full decode validates both streams without relying on a file
    # extension. showinfo supplies the decoded size and terminal timestamp.
    result=run([FFMPEG,"-hide_banner","-i",str(MOVIE),"-vf","showinfo","-af","volumedetect","-f","null","-"])
    log = result.stderr
    assert re.search(r"Video: h264.*1280x720",log)
    assert "Audio: aac" in log and "s:1280x720" in log
    times = re.findall(r"pts_time:([0-9.]+)",log)
    elapsed = float(times[-1])
    assert 0 < elapsed < 480 and MOVIE.stat().st_size < 100_000_000
    volume=re.search(r"mean_volume: ([\-0-9.]+) dB",log)
    assert volume and float(volume.group(1)) > -45
    # One preview per scene at its real action/narration midpoint.
    timeline=json.loads((WORK/"timeline.json").read_text())
    preview=WORK/"previews";preview.mkdir(exist_ok=True)
    for scene in timeline["scenes"]:
        at=min(scene["start"]+max(3,scene["duration"]*0.55),scene["end"]-0.2)
        run([FFMPEG,"-y","-loglevel","error","-ss",str(at),"-i",str(MOVIE),"-frames:v","1",str(preview/(scene["id"]+".png"))])
    result={"file":"screencast.mp4","sha256":hashlib.sha256(MOVIE.read_bytes()).hexdigest(),"bytes":MOVIE.stat().st_size,
            "decoded_last_video_timestamp_seconds":elapsed,"resolution":"1280x720","video_codec":"H.264","audio_codec":"AAC",
            "audio_mean_volume_db":float(volume.group(1)),"full_audio_video_decode_exit":0,"live_ui_checks":"passed",
            "queue_number":timeline["queue"],"chapters":len(timeline["scenes"]),"captured_frames":len(timeline["frames"]),
            "narration":"macOS Samantha, computer generated","actions":"Playwright, actual running UI",
            "editing":"All elapsed recording time retained; persona view switches labelled. Captions and narration composited.",
            "external_playback_access":"not tested by this local media verification command; see separate publication/access evidence"}
    (SOURCE/"video-verification.json").write_text(json.dumps(result,indent=2)+"\n")
    (WORK/"decode.log").write_text(log)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=["prepare","render","verify"])
    globals()[parser.parse_args().mode]()
