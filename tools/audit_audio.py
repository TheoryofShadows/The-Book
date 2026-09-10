#!/usr/bin/env python3
"""Sweep every rendered chapter and rank the ones worth listening to.

    python3 tools/audit_audio.py
    python3 tools/audit_audio.py --top 40
    python3 tools/audit_audio.py --csv dist/audio-audit.csv

check_audio.py asks whether the recording is there. verify_audio_upload.py
asks whether it arrived. Neither asks the question you are left with once
both pass: out of 1,559 chapters and 91 hours, which ones came out wrong?

Ninety-one hours cannot be listened through, so this does the part a machine
can do and hands back a ranked list for the part it cannot. It reads the Opus
files themselves rather than the render log -- the log records what the
renderer believed it wrote, which is exactly the thing in question.

What it measures, per chapter:

  * The true duration, off the Ogg granule positions in the last page of the
    stream. That is what the file actually contains, as opposed to what the
    sidecar JSON claims about it.
  * Whether the JSON's own duration agrees with it. A recording that stops
    early still has offsets running past the end, and every verse after the
    cut points into silence.
  * Whether the verse offsets are sane in themselves: ordered, non-negative,
    non-overlapping, none past the end, and one per verse in the source text.
  * Seconds per word, against the median for the whole corpus. This is the
    one that finds the bad renders. A chapter reading far too fast for its
    word count has dropped text; far too slow means it stalled, repeated, or
    filled with silence.
  * Lead-in silence and end padding, from the first and last verse offsets --
    the two faults already fixed once in this repo, so the two most likely to
    come back.

Nothing here is a judgement about how the voice sounds. That is not a thing
this or any check in this repository claims to know.
"""

import argparse
import io
import json
import os
import statistics
import struct
import sys

AUDIO = os.path.join("dist", "audio")
WORKS = os.path.join("docs", "data", "works")


def ogg_duration(path):
    """Seconds of audio in an Ogg Opus file, from its last granule position.

    Opus granules count at a fixed 48 kHz regardless of the sample rate the
    stream was encoded at, and the last page's granule is the end of the
    stream. The pre-skip in the identification header is priming samples that
    are not audio and is subtracted, which is the difference between this and
    a duration that is a few milliseconds long on every single file.

    Reads the head of the file for the header and the tail for the last page,
    rather than the whole 1.4 GB corpus.
    """
    size = os.path.getsize(path)
    if size < 4:
        return None, "file is empty or a stub (%d bytes)" % size

    with io.open(path, "rb") as fh:
        head = fh.read(4096)
        if not head.startswith(b"OggS"):
            return None, "not an Ogg stream"

        pre_skip = 0
        at = head.find(b"OpusHead")
        if at >= 0 and at + 12 <= len(head):
            pre_skip = struct.unpack_from("<H", head, at + 10)[0]

        # The last Ogg page starts at the last "OggS" in the tail.
        fh.seek(max(0, size - 65536))
        tail = fh.read()

    last = tail.rfind(b"OggS")
    if last < 0 or last + 14 > len(tail):
        return None, "no final Ogg page -- file is truncated"

    granule = struct.unpack_from("<q", tail, last + 6)[0]
    if granule < 0:
        return None, "final page has no granule position"

    secs = (granule - pre_skip) / 48000.0
    if secs <= 0:
        return None, "decodes to no audio at all"
    return secs, None


def m4a_duration(path):
    """Seconds of audio in an mp4, from the movie header.

    The reading exists twice on the item: Ogg/Opus for the browsers that take
    it, AAC in mp4 for Safari and every iPhone, which do not. Both are indexed
    by the same sidecar, so both have to agree with it -- an m4a that came out
    a different length would put every verse mark on that phone slightly wrong
    while looking perfect on a desktop.

    mvhd carries a timescale and a duration in it. Version 1 widens the times
    to 64 bits and shifts the two fields along; both layouts are read rather
    than assuming the one ffmpeg happens to write.
    """
    try:
        with io.open(path, "rb") as fh:
            head = fh.read(65536)
    except OSError as exc:
        return None, str(exc)
    at = head.find(b"mvhd")
    if at < 0:
        return None, "no mvhd box -- not an mp4, or truncated"
    try:
        if head[at + 4] == 1:
            scale = struct.unpack_from(">I", head, at + 24)[0]
            ticks = struct.unpack_from(">Q", head, at + 28)[0]
        else:
            scale = struct.unpack_from(">I", head, at + 16)[0]
            ticks = struct.unpack_from(">I", head, at + 20)[0]
    except struct.error:
        return None, "mvhd is too short to read"
    if not scale:
        return None, "mvhd has no timescale"
    return ticks / float(scale), None


def source_verse_counts():
    """How many verses each chapter is supposed to have, from the text."""
    counts = {}
    for name in sorted(os.listdir(WORKS)):
        if not name.endswith(".json"):
            continue
        with io.open(os.path.join(WORKS, name), encoding="utf-8") as fh:
            work = json.load(fh)
        wid = work.get("id") or name[:-5]
        for i, ch in enumerate(work.get("chapters") or []):
            verses = ch.get("verses") or []
            words = sum(len((v.get("t") or "").split()) for v in verses)
            counts["%s/%d" % (wid, i)] = (len(verses), words)
    return counts


def audit():
    if not os.path.isdir(AUDIO):
        sys.exit("audit_audio: no %s -- nothing rendered here." % AUDIO)

    source = source_verse_counts()
    rows, broken = [], []

    for work in sorted(os.listdir(AUDIO)):
        wdir = os.path.join(AUDIO, work)
        if not os.path.isdir(wdir):
            continue
        for f in sorted(os.listdir(wdir)):
            if not f.endswith(".opus"):
                continue
            idx = f[:-5]
            key = "%s/%s" % (work, idx)
            opus = os.path.join(wdir, f)
            side = os.path.join(wdir, idx + ".json")

            faults = []
            real, err = ogg_duration(opus)
            if err:
                broken.append((key, err, os.path.getsize(opus)))
                continue

            claimed, offsets = None, []
            if not os.path.exists(side):
                faults.append("no offsets file")
            else:
                try:
                    with io.open(side, encoding="utf-8") as fh:
                        meta = json.load(fh)
                    claimed = meta.get("d")
                    offsets = meta.get("v") or []
                except (ValueError, OSError) as exc:
                    faults.append("offsets unreadable (%s)" % exc)

            drift = None
            if claimed:
                drift = claimed - real
                if abs(drift) > 2.0:
                    faults.append("offsets claim %.1fs, audio is %.1fs (%+.1fs)"
                                  % (claimed, real, drift))

            last_end = 0.0
            past_end = 0
            for row in offsets:
                if len(row) < 3:
                    faults.append("a verse offset is malformed")
                    break
                start, end = float(row[1]), float(row[2])
                if start < 0 or end < start:
                    faults.append("a verse ends before it starts")
                    break
                if start < last_end - 0.05:
                    faults.append("verse offsets overlap")
                    break
                if start > real + 0.5:
                    past_end += 1
                last_end = max(last_end, end)
            if past_end:
                faults.append("%d verse(s) start after the audio ends" % past_end)

            want_verses, words = source.get(key, (None, None))
            if want_verses is not None and offsets and len(offsets) != want_verses:
                faults.append("%d offsets for %d verses in the text"
                              % (len(offsets), want_verses))

            # The Safari copy, where there is one. Same sidecar, so it has to
            # be the same length: a drift here is verse marks landing wrong on
            # every iPhone while a desktop plays it perfectly.
            m4a_path = os.path.join(wdir, idx + ".m4a")
            m4a_secs = None
            if os.path.exists(m4a_path):
                m4a_secs, m4a_err = m4a_duration(m4a_path)
                if m4a_err:
                    faults.append("the m4a is unreadable (%s)" % m4a_err)
                elif abs(m4a_secs - real) > 0.25:
                    faults.append("the m4a is %.2fs against the opus's %.2fs "
                                  "(%+.2fs)" % (m4a_secs, real, m4a_secs - real))

            lead = float(offsets[0][1]) if offsets else 0.0
            tailpad = real - last_end if offsets else 0.0
            if lead > 2.5:
                faults.append("%.1fs of silence before the first verse" % lead)
            if tailpad > 6.0:
                faults.append("%.1fs of audio after the last verse" % tailpad)

            spw = (real / words) if words else None
            rows.append({
                "key": key, "real": real, "claimed": claimed, "drift": drift,
                "words": words, "spw": spw, "lead": lead, "tail": tailpad,
                "verses": len(offsets), "want": want_verses,
                "bytes": os.path.getsize(opus), "faults": faults,
                "m4a": m4a_secs,
            })

    return rows, broken


def report(rows, broken, top, csv_path):
    paced = [r["spw"] for r in rows if r["spw"]]
    med = statistics.median(paced) if paced else 0.0

    # Pace is judged against the corpus, so it is scored after the sweep.
    for r in rows:
        if r["spw"] and med:
            ratio = r["spw"] / med
            r["ratio"] = ratio
            if ratio < 0.55:
                r["faults"].append("reads %.0f%% faster than the corpus -- "
                                   "text may be missing" % ((1 - ratio) * 100))
            elif ratio > 1.9:
                r["faults"].append("reads %.1fx slower than the corpus -- "
                                   "stall, repeat or silence" % ratio)
        else:
            r["ratio"] = 1.0

    print("Swept %d chapters, %.1f hours."
          % (len(rows), sum(r["real"] for r in rows) / 3600.0))
    withm4a = sum(1 for r in rows if r.get("m4a") is not None)
    print("%d of them also have the m4a Safari and the iPhone need."
          % withm4a)
    print("Median pace %.3f s/word.\n" % med)

    if broken:
        print("UNREADABLE -- these are not playable files:")
        for key, err, size in broken:
            print("  %-46s %s (%d bytes)" % (key, err, size))
        print("")

    flagged = [r for r in rows if r["faults"]]
    flagged.sort(key=lambda r: (-len(r["faults"]), -abs(r["ratio"] - 1.0)))

    if not flagged:
        print("No chapter failed any check.")
    else:
        print("%d chapter(s) worth listening to, worst first:\n" % len(flagged))
        for r in flagged[:top]:
            print("  %-44s %6.1fs  %s"
                  % (r["key"], r["real"], "; ".join(r["faults"])))
        if len(flagged) > top:
            print("\n  ...and %d more (use --top)." % (len(flagged) - top))

    if csv_path:
        with io.open(csv_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("chapter,seconds,m4a_seconds,claimed,drift,words,"
                     "s_per_word,pace_ratio,lead_in,tail_pad,offsets,"
                     "verses_in_text,bytes,faults\n")
            for r in sorted(rows, key=lambda x: x["key"]):
                fh.write("%s,%.2f,%s,%s,%s,%s,%s,%.3f,%.2f,%.2f,%d,%s,%d,%s\n" % (
                    r["key"], r["real"],
                    "%.2f" % r["m4a"] if r.get("m4a") is not None else "",
                    "%.2f" % r["claimed"] if r["claimed"] else "",
                    "%.2f" % r["drift"] if r["drift"] is not None else "",
                    r["words"] if r["words"] is not None else "",
                    "%.4f" % r["spw"] if r["spw"] else "",
                    r["ratio"], r["lead"], r["tail"], r["verses"],
                    r["want"] if r["want"] is not None else "",
                    r["bytes"], chr(34) + "; ".join(r["faults"]) + chr(34)))
        print("\nEvery chapter written to %s" % csv_path)

    return 1 if broken else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=30,
                    help="how many flagged chapters to print (default 30)")
    ap.add_argument("--csv", help="write every chapter's figures here")
    args = ap.parse_args()

    rows, broken = audit()
    sys.exit(report(rows, broken, args.top, args.csv))


if __name__ == "__main__":
    main()
