# The Book

Every text of the Jewish, Protestant, Catholic, Eastern Orthodox and Ethiopian
canons — together with the pseudepigrapha, the New Testament apocrypha and the
Apostolic Fathers — arranged by when scholars believe each was written, and
published as a searchable, interactive reader.

It opens with the Song of the Sea, not with Genesis.

**162 works · 2,231 chapters · 40,070 numbered verses · 1.12 million words**

---

## What this is

A printed Bible arranges books by category and tradition. This arranges them by
composition date, so the library reads as a sequence: what came first, what
answered it, what was written during the exile, what was written under Greek
rule, and what the earliest churches were reading before the canon closed.

Alongside the reader there is a published **accuracy report**. Every chapter and
verse count was checked against independent reference figures rather than
against the source file's own claims, and the disagreements are listed rather
than quietly patched.

## The order is a reconstruction, not a fact

This dates *books*, not the events or the traditions inside them. Genesis sits in
Section V because critical scholarship dates the Torah's final written form to
the Persian period — which says nothing about the age of the stories it carries,
much of which is far older than the book. Traditional Jewish and Christian
teaching assigns the Torah to Moses. This arrangement does not settle that
question and cannot.

Some placements are firm: Amos as the oldest prophetic book, Daniel's visions
in the Maccabean crisis of 167–164 BCE, Mark before Matthew and Luke, 2 Peter
last in the New Testament. Others are contested by centuries — James alone has
been placed anywhere between 45 and 120 CE. The site flags which is which.

## Sources

Everything here is public domain. Nothing is drawn from a modern copyrighted
translation.

| Source | Covers |
| --- | --- |
| World English Bible with Deuterocanon (eBible.org) | Old and New Testaments, full deuterocanon, wider Orthodox canon |
| R. H. Charles, 1917 | 1 Enoch, Jubilees |
| Ante-Nicene Fathers, ed. Roberts and Donaldson, 1885 | Apostolic Fathers, Testaments of the Twelve Patriarchs, NT apocrypha, Shepherd of Hermas, Ignatius (shorter recension) |

## What the audit found

Verified correct:

- All 66 Protestant books present with the correct chapter counts.
- All 66 match the World English Bible **verse for verse**, including its
  deliberate omissions (Acts 8:37, 15:34, 24:7 and Luke 17:36 are absent from
  the critical text the WEB follows) and its Revelation 12/13 versification.
- The Catholic canon of 73 and the Eastern Orthodox additions are complete.
- No duplicate chapters, no empty chapters, no broken verse sequences.

Corrected in this edition:

- **~31,000 characters of website furniture** were embedded in the scripture
  text — Ante-Nicene Fathers editorial introductions running on into the end of
  1 Clement, Diognetus, Polycarp, the Martyrdom of Polycarp and Barnabas, and an
  advertisement reading *"Please buy the CD to support the site"* closing all
  seven letters of Ignatius. Every removal is itemised in the report.
- A **false chapter heading** in 1 Enoch: an OCR artifact shaped like a chapter
  marker was splitting 1 Enoch 24 in two.
- **~1,900 verse boundaries** lost where a verse number fell at a line wrap.

Corrected claims:

- The source states *"Every book in every one of these canons is printed in full
  in this volume."* That does not hold for the Ethiopian Orthodox Tewahedo
  canon: 1 Enoch and Jubilees are here, but 4 Baruch, Ethiopic Clement, the
  Didascalia, the Sinodos and the Book of the Covenant are not.

Gaps inherited from the source editions, left honest rather than invented:

- **1 Clement is missing its great intercessory prayer.** The 1885 printing
  followed Codex Alexandrinus, which has a lacuna at roughly 57:7–63:4, so the
  chapters run 1–59 rather than 1–65.
- Ignatius to the Smyrnaeans lacks chapter 13; Polycarp to the Philippians
  breaks off mid-sentence in chapter 14.
- The Shepherd of Hermas is missing Similitudes 1 and 10.
- The Psalms of Solomon and Philo are described but have no text.
- The Dead Sea Scrolls appear as summaries — every English translation of the
  1947-and-later finds is under copyright.

## Building it

```bash
./tools/build.sh                    # regenerate everything from source/
python3 -m http.server 8000 -d docs # then open http://localhost:8000
```

| Tool | Does |
| --- | --- |
| `tools/parse_book.py` | Turns the source text into structured JSON, logging every removal |
| `tools/audit.py` | Checks chapter and verse counts against reference figures |
| `tools/build_canon.py` | Builds canon membership and checks coverage claims |
| `tools/build_index.py` | Builds the sharded search index |

The audit is the point: if a count on the site is wrong, `tools/audit.py` will
say so. Findings are stated so they can be falsified.

## How the site works

Static files only — no build step, no dependencies, no tracking. Work texts and
search-index shards are fetched on demand, so the first paint is small even
though the library is seven megabytes.

Search is a two-stage design: a chapter-granularity inverted index (1.45 MB
across 27 shards) narrows candidates, then only the matching works are fetched
and scanned for exact verses. Quote a phrase to match it exactly.

## Deploying

`.github/workflows/pages.yml` rebuilds the data from source, fails the build if
`docs/data` has drifted, and publishes `docs/`. Enable it once under
**Settings → Pages → Source: GitHub Actions**.

## Licence

Texts are public domain. The code, the audit and the editorial apparatus are
offered freely; use them.
