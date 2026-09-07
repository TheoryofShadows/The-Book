#!/usr/bin/env python3
"""Put the rendered audio on archive.org, at the addresses the reader uses.

    python3 tools/upload_audio.py --item the-book-audio-trial --only psalms/22,matthew/4
    python3 tools/upload_audio.py --dry-run
    python3 tools/upload_audio.py

The layout is the whole point of this script, and the reason it exists rather
than a line in a runbook.

`ia upload <item> dist/audio` uploads each file under the path it was given,
so the files arrive as `dist/audio/psalms/22.opus`. The reader asks for
`psalms/22.opus`. Every chapter 404s, the player falls back to the device
voice without saying why, and nothing anywhere reports it -- which is exactly
what happened on the trial item, with two files, before it happened with five
thousand.

Running from inside the directory does not fix it: `ia upload <item> .` sends
`/../psalms/22.opus` and the server rejects the bucket name outright.

So the remote name of every file is stated rather than inferred. That is the
only form that gives exact control, and control over this is the difference
between an audiobook and a silent fallback.

It uploads only what is missing, so an interrupted run is resumed by running
it again rather than by starting over -- 1.4 GB over a home connection will
be interrupted.
"""

import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
ITEM = "the-book-read-aloud"

METADATA = {
    "title": "The Book — the library read aloud",
    "mediatype": "audio",
    "licenseurl": "https://creativecommons.org/publicdomain/zero/1.0/",
    "description": (
        "A complete reading of 172 biblical and related ancient texts, "
        "arranged by date of composition. One Opus file per chapter, with a "
        "JSON of per-verse offsets beside it so a reader can seek to a verse "
        "exactly. Synthesised speech (Kokoro, voice bm_lewis), not a human "
        "narrator. Companion to https://thebookandme.com/"),
    "subject": "bible; scripture; audiobook; public domain; apocrypha; "
               "pseudepigrapha; Apostolic Fathers",
}


def pairs(audio_dir, only=None):
    """Every chapter as {remote path: local file}.

    A chapter is its .opus and the .json beside it, and neither is any use
    without the other: audio with no index has no verse marks, an index with
    no audio is a promise of a file that is not there. So they are collected
    as a pair and a chapter missing either is reported rather than half sent.
    """
    want = set(only or [])
    out, half = {}, []
    for dirpath, _, names in os.walk(audio_dir):
        for name in sorted(names):
            if not name.endswith(".opus"):
                continue
            work = os.path.relpath(dirpath, audio_dir).replace(os.sep, "/")
            chapter = name[:-5]
            key = "%s/%s" % (work, chapter)
            if want and key not in want:
                continue
            opus = os.path.join(dirpath, name)
            meta = os.path.join(dirpath, chapter + ".json")
            if not os.path.exists(meta):
                half.append(key)
                continue
            out[key + ".opus"] = opus
            out[key + ".json"] = meta
    return out, half


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--item", default=ITEM)
    ap.add_argument("--audio", default=os.path.join(ROOT, "dist", "audio"))
    ap.add_argument("--only", default="",
                    help="comma-separated work/chapter, for a partial upload")
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be sent and stop")
    args = ap.parse_args()

    try:
        from internetarchive import get_item, upload
    except ImportError:
        raise SystemExit("upload_audio.py needs the archive.org client:\n"
                         "  pip install internetarchive\n"
                         "and credentials in ~/.config/internetarchive/ia.ini")

    only = [s.strip() for s in args.only.split(",") if s.strip()]
    files, half = pairs(args.audio, only)
    if half:
        print("%d chapter(s) have audio but no verse index, and are not being "
              "sent:" % len(half))
        for k in half[:10]:
            print("   ", k)
        print("Re-render those before publishing; a chapter with no index has "
              "no verse marks.\n")
    if not files:
        raise SystemExit("nothing to upload from %s" % args.audio)

    chapters = len(files) // 2
    size = sum(os.path.getsize(p) for p in files.values())
    print("%d chapters, %d files, %.2f GB -> %s"
          % (chapters, len(files), size / 1024 ** 3, args.item))

    # Only what is missing. An interrupted 1.4 GB upload is resumed by running
    # this again, and re-sending what is already there costs the same as
    # sending it did.
    try:
        have = {f.name for f in get_item(args.item).get_files()}
    except Exception:
        have = set()
    todo = {k: v for k, v in files.items() if k not in have}
    print("%d already there, %d to send" % (len(files) - len(todo), len(todo)))

    if args.dry_run:
        for k in sorted(todo)[:6]:
            print("  would send", k)
        if len(todo) > 6:
            print("  ... and %d more" % (len(todo) - 6))
        return 0
    if not todo:
        print("Nothing to do.")
        return 0

    # Sent in batches so an interruption leaves a known amount done, and so
    # the progress means something on a run measured in hours.
    keys = sorted(todo)
    sent = failed = 0
    BATCH = 100
    for i in range(0, len(keys), BATCH):
        chunk = {k: todo[k] for k in keys[i:i + BATCH]}
        try:
            rs = upload(args.item, files=chunk,
                        metadata=METADATA if i == 0 else None,
                        verbose=False, retries=5)
            for r in rs:
                if getattr(r, "status_code", 0) == 200:
                    sent += 1
                else:
                    failed += 1
        except Exception as exc:
            failed += len(chunk)
            print("  batch failed: %s" % str(exc)[:120])
        print("  %d/%d sent%s" % (sent, len(keys),
                                  (", %d failed" % failed) if failed else ""))

    print()
    if failed:
        print("%d file(s) did not go. Run this again -- it sends only what is "
              "missing." % failed)
        return 1
    print("All sent. archive.org processes uploads after they arrive, so give "
          "it a few minutes, then:")
    print("  python3 tools/check_audio_live.py --item %s --sample psalms/22"
          % args.item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
