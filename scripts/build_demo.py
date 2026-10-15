"""Render a narrated, data-backed demo. Optional Windows/FFmpeg authoring helper.

The application itself does not depend on speech synthesis or FFmpeg.
Run from the repository root: python scripts/build_demo.py --ffmpeg PATH
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from server import ResearchLab

INK, GREEN, MUTED, PAPER, LINE = "#1b302a", "#256c57", "#5c6c64", "#f6f8f5", "#dce3dc"
W, H = 1600, 900
FONT = ROOT / "web/fonts/public-sans.ttf"


def font(size):
    face = ImageFont.truetype(str(FONT), size)
    face.set_variation_by_axes([600 if size >= 35 else 450])
    return face


def text(draw, xy, value, size=28, color=INK):
    draw.text(xy, value.replace("→", "to"), font=font(size), fill=color, spacing=12)


def base(title, subtitle):
    image = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(image)
    text(d, (65, 35), "GainGuard.", 31, GREEN)
    text(d, (1150, 43), "ULTRASOUND RELIABILITY LAB", 15, MUTED)
    d.line((65, 95, 1535, 95), fill=LINE, width=2)
    text(d, (65, 128), title, 54)
    text(d, (65, 215), subtitle, 24, MUTED)
    d.line((65, 827, 1535, 827), fill=LINE, width=2)
    text(d, (65, 849), "Research demonstration only. No diagnosis or clinical recommendations.", 19, MUTED)
    text(d, (1135, 849), "Public data / MedMNIST", 19, MUTED)
    return image, d


def scan(image, source, box):
    image.paste(Image.fromarray(source).resize((box[2], box[3]), Image.Resampling.NEAREST), box[:2])


def main(ffmpeg):
    output = ROOT / "docs/demo"
    output.mkdir(exist_ok=True)
    lab = ResearchLab()
    r = lab.report
    result = lab.experiment(1, -6, 0, 0)
    from research.core import perturb
    original = lab.images[1]
    changed = perturb(original, gain=-6)
    if not result["sample"]["correct"] or result["correct"]:
        raise RuntimeError("The narration's saved-checkpoint example no longer matches; update the demo.")
    condition = next(c for c in r["conditions"] if c["stress"] == "gain_down" and c["severity"] == 2)
    if condition["metrics"]["confident_errors"] != 66:
        raise RuntimeError("Benchmark changed; update narration before rendering.")

    scenes = []
    image, d = base("Can a confident model be wrong?", "A focused acquisition-stress lab for breast-ultrasound AI researchers.")
    text(d, (70, 335), "One model.\nOne held-out split.\nVisible failure modes.", 51)
    text(d, (70, 590), "Gain, speckle and shadow proxies\nPaired experiments and actual model passes\nExplicit review reasons and workload", 25, MUTED)
    scan(image, original, (940, 310, 460, 460))
    scenes.append((image, "GainGuard is a focused research lab for breast ultrasound A I reliability. Instead of building another cancer diagnosis app, we ask a narrower question. When acquisition inspired changes alter an image, does a classifier become uncertain, or confidently wrong? We use real public benchmark images, a trained local model, and reproducible experiments. This is a research demonstration, not a diagnostic tool."))

    image, d = base("One image. A prediction flips.", "BUS-002 / Dataset label: normal or benign / Identical model, different input pixels")
    scan(image, original, (110, 310, 420, 420))
    scan(image, changed, (660, 310, 420, 420))
    text(d, (110, 277), "Original", 23, GREEN)
    text(d, (660, 277), "Simulated gain: −6 dB", 23, GREEN)
    text(d, (110, 750), f"Normal / benign · {result['sample']['confidence']:.1%}", 24)
    text(d, (660, 750), f"Malignant · {result['confidence']:.1%}", 24, "#a04435")
    text(d, (1150, 370), "Flagged\nfor review", 39, "#855112")
    text(d, (1150, 510), "Prediction changed\n+78.6 pp probability shift\nStill over 80% confident", 20, MUTED)
    scenes.append((image, "Here is a real held out example. The dataset label is normal or benign. The original model prediction matches at 95 point 5 percent confidence. After a simulated minus six decibel intensity shift, it predicts malignant at 83 point 1 percent confidence. Low confidence review alone misses this failure. Our fixed rule catches the prediction flip and the 78 point 6 percentage point shift in malignant class probability."))

    image, d = base("A benchmark, not a hand-picked claim.", "546 training / 78 validation / 156 held-out test images / 12 predefined stress conditions")
    metrics = [("Clean accuracy", f"{r['clean']['accuracy']:.1%}"), ("Malignant AUROC", f"{r['clean']['auc']:.3f}"), ("−6 dB accuracy", f"{condition['metrics']['accuracy']:.1%}")]
    for i, (name, value) in enumerate(metrics):
        x = 80 + i * 500
        text(d, (x, 320), name, 26, MUTED)
        text(d, (x, 375), value, 78, GREEN)
    text(d, (80, 555), "66 incorrect predictions remain at least 80% confident at −6 dB.", 35)
    text(d, (80, 635), "Checkpoint selection and temperature fitting use validation only.\nClean ECE: 5.6% raw → 3.9% calibrated. One small test split; one training seed.\nThe complete report includes class recall, Brier score, NLL and uncertainty limits.", 24, MUTED)
    scenes.append((image, "We preserve the official Breast M NIST splits: 546 training images, 78 validation images, and 156 test images. Checkpoint selection and temperature fitting use validation data only. Clean accuracy is 87 point 8 percent, and malignant class A U R O C is zero point eight nine zero. Under minus six decibels, accuracy falls to 42 point 3 percent. Sixty six wrong predictions still retain at least 80 percent calibrated confidence."))

    image, d = base("Select cutoffs on validation. Freeze for test.", "50% mean validation review budget / Clean + twelve stress conditions / Repeated images")
    policies = r["threshold_study"]["selected"]
    combined, confidence_only = policies["combined"]["test"], policies["confidence_only"]["test"]
    for y, label, stats, color in [(330, "Combined: 88% confidence / 15 pp shift / flips", combined, GREEN), (535, "Confidence-only cutoff: 95%", confidence_only, "#8c9e91")]:
        text(d, (80, y), label, 30)
        d.rounded_rectangle((80, y + 63, 1100, y + 110), radius=5, fill="#e0e7de")
        d.rounded_rectangle((80, y + 63, 80 + 1020 * stats['review_rate'], y + 110), radius=5, fill=color)
        text(d, (1150, y + 55), f"{stats['review_rate']:.1%} test review", 27, color)
        text(d, (80, y + 128), f"{stats['error_capture']:.1%} of test errors captured / {stats['n']:,} image-condition pairs", 24, MUTED)
    text(d, (80, 748), "Exploratory study; thresholds reuse validation. Test workloads are not matched.", 26, "#a04435")
    scenes.append((image, "We also select thresholds using validation only, under a fifty percent average review budget. The combined rule selects eighty eight percent confidence and a fifteen point shift. Frozen test evaluation captures eighty eight point seven percent of errors at fifty five point nine percent review. Confidence only selects ninety five percent and captures fifty nine percent at forty nine point four percent review. These are repeated image conditions, not independent patients or matched test workloads. The study is exploratory."))

    image, d = base("A working lab, with inspectable evidence.", "Paired scans → 9-point stress sweep → review reasons → full-split audit → export")
    steps = [("Experiment", "Adjust gain, speckle or shadow; run real local inference."), ("Benchmark", "Compare all predefined conditions and clean calibration."), ("Review", "Audit 156 images; inspect pairs and mark research notes."), ("Reproduce", "Export settings and outputs tied to the model SHA-256.")]
    for i, (title, detail) in enumerate(steps):
        y = 315 + i * 117
        text(d, (80, y), title, 35, GREEN)
        text(d, (420, y + 6), detail, 27)
        d.line((80, y + 85, 1510, y + 85), fill=LINE, width=2)
    scenes.append((image, "The working application pairs the original and stressed scans, runs nine real model passes along the stress path, and explains each review flag. Researchers can audit all 156 held out images, inspect failures, mark research notes, and export evidence tied to the model hash. The tests check deterministic transforms, metric calculations, invalid API input, and agreement between live inference and the saved report. A separate recorded browser walkthrough accompanies this video."))

    image, d = base("Built to be questioned.", "A reproducible failure-analysis prototype, with a concrete next study.")
    text(d, (80, 325), "What this does not establish", 35, "#855112")
    text(d, (80, 400), "Validated scanner physics\nPatient-level independence\nExternal clinical performance\nClinical uncertainty or safe review thresholds", 30, MUTED)
    text(d, (870, 325), "The next experiment", 35, GREEN)
    text(d, (870, 400), "External patient-grouped data\nRealistic acquisition changes\nRepeated training seeds\nValidation-selected review budgets", 30, MUTED)
    text(d, (80, 720), "GainGuard / Real images. Measured failures. Explicit limits.", 36, GREEN)
    scenes.append((image, "Our limits are explicit. Synthetic pixel changes are not validated scanner physics. The small image level dataset does not establish patient independence, and softmax confidence is not clinical uncertainty. The next experiment needs external patient grouped data, realistic acquisition changes, repeated training seeds, and validation selected review budgets. GainGuard makes observed failures visible and reproducible, without presenting them as a clinical solution."))

    metadata = []
    for i, (image, narration) in enumerate(scenes):
        image.save(output / f"scene-{i}.png")
        metadata.append({"text": narration, "audio": str(output / f"scene-{i}.wav")})
    manifest = output / "narration.json"
    reuse_audio = manifest.exists() and json.loads(manifest.read_text(encoding="utf-8")) == metadata
    reuse_audio = reuse_audio and all(Path(entry["audio"]).exists() for entry in metadata)
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    escaped_manifest = str(manifest).replace("'", "''")
    speech_script = f"""
$ErrorActionPreference = 'Stop'
$entries = Get-Content -LiteralPath '{escaped_manifest}' -Raw | ConvertFrom-Json
$speaker = New-Object -ComObject SAPI.SpVoice
foreach ($candidate in $speaker.GetVoices()) {{ if ($candidate.GetDescription() -like '*Zira*') {{ $speaker.Voice = $candidate }} }}
$speaker.Rate = 1
foreach ($entry in $entries) {{
  $stream = New-Object -ComObject SAPI.SpFileStream
  $stream.Open($entry.audio, 3, $false)
  $speaker.AudioOutputStream = $stream
  [void]$speaker.Speak($entry.text)
  $stream.Close()
}}
"""
    if not reuse_audio:
        subprocess.run(["powershell", "-NoProfile", "-Command", speech_script], check=True, capture_output=True)
    total = 0
    for i in range(len(scenes)):
        with wave.open(str(output / f"scene-{i}.wav")) as audio:
            duration = audio.getnframes() / audio.getframerate() + 1.0
        total += duration
        walkthrough = ROOT / "docs/evidence/walkthrough.mp4"
        video_input = ["-loop", "1", "-i", str(output / f"scene-{i}.png")]
        video_filter = "format=yuv420p"
        if i == 4 and walkthrough.exists():
            video_input = ["-i", str(walkthrough)]
            video_filter = "scale=1296:900,pad=1600:900:152:0:color=0xf6f8f5,tpad=stop_mode=clone:stop_duration=10,format=yuv420p"
        command = [ffmpeg, "-y", "-loglevel", "error", *video_input,
                   "-i", str(output / f"scene-{i}.wav"), "-t", str(duration), "-vf", video_filter,
                   "-af", "apad=pad_dur=1", "-r", "24", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-c:a", "aac", "-b:a", "128k", str(output / f"scene-{i}.mp4")]
        subprocess.run(command, check=True)
        print(f"Rendered scene {i + 1}/{len(scenes)} ({duration:.1f}s)", flush=True)
    if total > 180:
        raise RuntimeError(f"Demo exceeds three minutes ({total:.1f}s); shorten the narration.")
    concat = output / "segments.txt"
    concat.write_text("\n".join(f"file 'scene-{i}.mp4'" for i in range(len(scenes))), encoding="utf-8")
    target = ROOT / "docs/gainguard-demo.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c", "copy", "-movflags", "+faststart", str(target)], check=True)
    print(f"Narrated demo: {target} ({total:.1f}s)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg:
        try:
            import imageio_ffmpeg
            args.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            parser.error("Provide --ffmpeg PATH (demo authoring only).")
    if sys.platform != "win32":
        parser.error("This optional narration helper uses Windows SAPI.")
    main(args.ffmpeg)
