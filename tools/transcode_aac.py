#!/usr/bin/env python3
"""A second copy of the reading, in the one format every iPhone plays.

    python3 tools/transcode_aac.py
    python3 tools/transcode_aac.py --only genesis
    python3 tools/transcode_aac.py --jobs 8

The reading was rendered as Opus in an Ogg container, which is the right
choice for the size -- 34 kbps for something worth listening to. It is also
the one common format Apple was last to take, and on an iPhone it does not
play: the reader chooses the recording, waits, and is dropped onto the
device's own voice. On a site whose whole point is scripture on a phone, that
is the platform that matters most.

Two things are wrong on that path and this fixes both:

  * The codec. AAC-LC in an mp4 container is what every iPhone has played
    since there were iPhones. Same audio, ~23% larger, and nothing about the
    reading changes.
  * The content type. archive.org does not recognise ".opus" and serves it as
    application/octet-stream. Chrome sniffs the bytes and plays it anyway;
    Safari is stricter and refuses. ".m4a" it does recognise, and serves as
    audio/mp4.

This does NOT re-render. The expensive part -- 91 hours of synthesis, and the
per-verse offsets that were measured while it happened -- is done and is
reused exactly. A transcode is sample-accurate about length, so the sidecar
JSON that says where each verse begins is as true of the m4a as of the opus,
and is copied rather than recomputed.

Safe to stop and safe to re-run: a chapter whose .m4a already exists and is
newer than its .opus is skipped, so an interrupted pass resumes where it
stopped rather than starting again.
"""

import argparse
import concurrent.futures as futures
import os
import subprocess
import sys
import time

AUDIO = os.path.join("dist", "audio")


def ffmpeg_exe():
    """ffmpeg, from PATH or from the imageio-ffmpeg wheel."""
    from shutil import which
    found = which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("transcode_aac: no ffmpeg. Install one, or:\n"
                 '    "C:\\Program Files\\Python313\\python.exe" '
                 "-m pip install imageio-ffmpeg")


def chapters(only):
    """Every rendered chapter, as (opus, m4a, sidecar) paths."""
    out = []
    for work in sorted(os.listdir(AUDIO)):
        if only and work != only:
            continue
        wdir = os.path.join(AUDIO, work)
        if not os.path.isdir(wdir):
            continue
        for f in sorted(os.listdir(wdir)):
            if not f.endswith(".opus"):
                continue
            stem = f[:-5]
            out.append((os.path.join(wdir, f),
                        os.path.join(wdir, stem + ".m4a"),
                        os.path.join(wdir, stem + ".json")))
    return out


def needs_doing(opus, m4a):
    """Already converted, and not from an older opus than the one here."""
    if not os.path.exists(m4a):
        return True
    if os.path.getsize(m4a) == 0:
        return True
    return os.path.getmtime(m4a) < os.path.getmtime(opus)


def convert(ff, opus, m4a):
    """One chapter. Written beside its target and moved into place, so an
    interrupted run never leaves a half file that the skip would believe."""
    part = m4a + ".part"
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
           "-i", opus,
           "-c:a", "aac", "-b:a", "40k", "-ar", "48000", "-ac", "1",
           # The index at the front, so a browser can start playing before it
           # has the whole file -- which is the difference between seeking to
           # a verse and downloading a chapter to seek inside it.
           "-movflags", "+faststart",
           "-f", "mp4", part]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        if os.path.exists(part):
            os.remove(part)
        return "%s: %s" % (os.path.basename(opus),
                           (exc.stderr or b"").decode("utf-8", "replace")[:200])
    except OSError as exc:
        return "%s: %s" % (os.path.basename(opus), exc)
    os.replace(part, m4a)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="one work id, for a trial run")
    ap.add_argument("--jobs", type=int, default=max(2, (os.cpu_count() or 4) - 1),
                    help="how many at once (default: cores - 1)")
    args = ap.parse_args()

    if not os.path.isdir(AUDIO):
        sys.exit("transcode_aac: no %s -- nothing rendered here." % AUDIO)

    ff = ffmpeg_exe()
    todo = [c for c in chapters(args.only) if needs_doing(c[0], c[1])]
    allof = chapters(args.only)
    done_already = len(allof) - len(todo)

    print("%d chapters, %d already converted, %d to do, %d at a time."
          % (len(allof), done_already, len(todo), args.jobs))
    if not todo:
        print("Nothing to do.")
        return 0

    started = time.time()
    failures = []
    with futures.ThreadPoolExecutor(args.jobs) as pool:
        running = {pool.submit(convert, ff, o, m): (o, m)
                   for o, m, _ in todo}
        for i, fut in enumerate(futures.as_completed(running), 1):
            err = fut.result()
            if err:
                failures.append(err)
            if i % 50 == 0 or i == len(todo):
                per = (time.time() - started) / i
                left = (len(todo) - i) * per
                print("  %d/%d  %.1f/s  about %d min left"
                      % (i, len(todo), 1 / per if per else 0, left / 60))

    total = sum(os.path.getsize(m) for _, m, _ in allof if os.path.exists(m))
    print("\n%d converted, %d failed, %.2f GB of AAC in %.1f min."
          % (len(todo) - len(failures), len(failures), total / 1e9,
             (time.time() - started) / 60))
    for f in failures[:20]:
        print("  FAILED", f)
    print("\n[transcode finished]" if not failures else "\n[transcode had failures]")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
