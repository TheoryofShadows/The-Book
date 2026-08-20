# The Book

## Read it here → https://theoryofshadows.github.io/The-Book/

The link is case sensitive. `/The-Book/` works; `/the-book/` does not.

---

Every text of the Jewish, Protestant, Catholic, Eastern Orthodox and Ethiopian
canons — together with the pseudepigrapha, the New Testament apocrypha and the
Apostolic Fathers — arranged by when scholars believe each was written, and
published as a searchable, interactive reader.

It opens with the Song of the Sea, not with Genesis.

**165 works · 2,246 chapters · 40,070 numbered verses · 1.13 million words**

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

## Seeing the disagreement

Every work with a position record carries a **date card**: the traditional and
the critical dating drawn as two bars on one scale, so how far apart they are
is a thing you see rather than a thing you work out. On Amos the bars sit on
top of each other. On Genesis they are seven centuries apart.

The bars are read out of the prose positions by `tools/dates.py`, and it
refuses to guess. Where a position names a person rather than a time — "Samuel",
"Moses, shortly before his death" — there is no bar and the card says why.
About two in five traditional positions have none, which is a fact about the
tradition rather than a gap in the data. A span read from a century or a named
period is drawn as the looser claim it is.

**The library on one axis** draws every work as a bar against time, under
either column. Switching the column reorders the whole library: under the
traditional dating the Torah moves eight hundred years and lands on top of
everything else, which is the disagreement this volume is about. A bar placed
by a work's own dated position is drawn solid; one placed by the era it is
filed under is drawn fainter, because it is a looser claim; a range with one
end unstated runs off the edge rather than stopping at a year nobody named.
The works that carry no date under a column are listed rather than dropped.

[How the dating was decided](#) is a page of its own: what the arrangement is
and is not, where each date comes from, how the bars are derived, the boundary
of every named period and the event that fixes it, and the two things the bars
cannot tell you — that a composite book has one bar and several dates, and that
overlapping bars are not agreement.

Any verse can be copied out as a citation or a BibTeX entry that names the
public-domain edition and where the passage sits in the composition order,
which is the part an ordinary reference leaves out and the part this
arrangement exists for.

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

## Listening to it

Every chapter can be read aloud. There is no audiobook of these translations
in the public domain and 1.13 million words cannot be recorded, so the reading
is done by the speech engine already in the browser: press **Listen** in any
chapter, or `l`.

- The verse being spoken is marked, and the word inside it is highlighted where
  the browser supports the Custom Highlight API.
- Speed, voice, time remaining and a sleep timer are in the player, and **♪**
  reads a sentence in the selected voice so a chapter is not the way you find
  out what it sounds like.
- It announces each chapter, then runs on: to the next chapter, and at the end
  of a work into the work written next, stepping over the entries that carry no
  text. Left alone it plays the library in composition order. The toggle in the
  player stops it at the end of the chapter instead.
- Where you stopped is remembered per chapter, the way **Resume** works for
  reading, and any verse can be the starting point from its verse menu.

The voices are the ones your device has installed, and they are synthetic: no
audio is downloaded, no text is sent anywhere, and it works offline.

### Which voice, and why it used to sound like that

A device does not offer a voice, it offers a drawer of them, and the drawer is
not sorted by how they sound. macOS files two dozen novelties — Zarvox,
Bubbles, Deranged, Trinoids — beside its good ones, and the MacinTalk voices of
the early nineties beside those. Linux answers with eSpeak. Windows still ships
the old SAPI *Desktop* voices alongside its neural ones. And the voice a system
flags as its default is very often the worst thing in the drawer.

So the drawer is now scored rather than taken in the order it arrives. Apple's
enhanced and premium downloads, Microsoft's natural voices, Google's, and
anything the browser synthesises on a server rather than on the device are
preferred and grouped first; the relics sit under them; the novelties and the
other languages sit under those, labelled rather than hidden, because a device
may have nothing else and the choice stays yours. The Web Speech API has no
field for quality and no way to ask, so this is a list of what the platforms
are known to ship, and it will age. It is only ever a default: one selection in
the player overrides all of it.

### On an iPhone or iPad, the voice is a download

Most platforms write the quality into the voice's name — *Natural*, *Neural*,
*Online*. Apple does the opposite: the name is bare and the grade is in the
identifier, so the same Samantha arrives as

```
com.apple.voice.compact.en-US.Samantha      nothing downloaded
com.apple.voice.enhanced.en-US.Samantha     the free download
com.apple.voice.premium.en-US.Samantha      the larger free download
```

and an iPhone out of the box has only the compact set — the thin, clipped
reading this whole section is about. So the identifier is read as well as the
name: a downloaded voice outranks the stock one of the same name, the drawer
labels which Samantha is which, and a device carrying nothing but the compact
set is told so, with the path to the download rather than a shrug.

**Settings › Accessibility › Spoken Content › Voices › English**, then pick a
voice and download its Enhanced or Premium version. That single download does
more for how this sounds than everything else here put together, and nothing a
web page does can substitute for it: the audio is the operating system's.

Three other things were making the reading sound mechanical whatever voice was
doing it, and are fixed:

- **The apparatus was being read out.** Charles prints his in the running text
  — daggers round a corrupt reading, angle brackets round a restoration, plus
  signs round an emendation. The eye steps over them; an engine says "dagger".
  They are blanked before speaking and left standing on the page.
- **Long verses were cut mid-clause.** Chrome stops a single utterance at about
  fifteen seconds, so long passages have to be broken up — and an engine drops
  its pitch and takes a breath at the end of every utterance, so a break inside
  a clause is heard as a full stop that is not there. Breaks are now taken at
  the nearest comma, semicolon, colon or dash: across the library that moved
  the proportion of pieces ending mid-clause from 31% to 0.25%.
- **There were no pauses.** Engines run one utterance straight into the next,
  so a chapter arrived as an unbroken wall. A verse now gets the beat a person
  reading aloud would take and the chapter heading a longer one, while a
  sentence cut only because it was too long gets none — that seam is the one
  place a pause would be a lie.

None of this synthesises audio. If a device has nothing but eSpeak or the
compact set installed, nothing a web page can do will make those sound like a
person; the player says so, and opens to say where better voices are a free
download on each platform, rather than leaving you to conclude the site is
broken. It opens rather than hovering, because the phone that most needs it has
no tooltips.

A browser with no speech support is not offered the control at all, and a
device that has the support but no installed voice — a Linux desktop without
speech-dispatcher, for instance — is told exactly that rather than left
pressing a button that does nothing. On a phone the reading
usually stops when the screen locks or you switch app — the browser suspends
the page, and this is speech, not a track playing in the background.

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
| `tools/build_standalone.py` | Inlines the whole library into one HTML file that runs offline |
| `tools/textnorm.py` | The one rule that folds text into a search token or a lookup key |
| `tools/dates.py` | Reads a numeric span out of a position statement, and refuses to where there is none |
| `tools/lint.sh` | Everything parses, and every data file is the JSON it claims to be |
| `tools/test.sh` | Runs the unit tests and the browser checks in `tests/` |

The audit is the point: if a count on the site is wrong, `tools/audit.py` will
say so, and the build will stop. Findings are stated so they can be falsified.

`tools/audit-baseline.txt` is what makes that a gate rather than a report.
Every finding the audit produces is either a defect or a known property of the
printed edition — the World English Bible really does omit Luke 17:36 — and the
baseline is where the second kind is written down, in groups, each with a
reason. A finding that is not in it fails the build; so does a baseline entry
that no longer occurs. Nothing regenerates the file by itself: a baseline that
rewrote itself would let the next regression through under a passing build.

Until that existed the audit collected 157 findings and returned zero
regardless. Three chapters of Ignatius and fifty-six chapter openings were
missing from the volume the whole time it was running.

## Checking it

Three layers, cheapest first.

```bash
./tools/lint.sh                     # everything parses (seconds)
python3 -m unittest discover -s tests/python -t tests/python
./tools/test.sh                     # both of the above, then the browser
./tools/test.sh listening           # one browser suite
```

The unit tests cover the build scripts — the layer that decides what the text
of the volume actually is — and need nothing installed beyond Python, for the
same reason the site ships no dependencies. The browser checks need Node, and
install Playwright and a Chromium into `tests/node_modules` on first run; set
`CHROME_PATH` to use a browser already on the machine instead.

| Suite | Checks |
| --- | --- |
| `tests/python` | The parser function by function: where a verse begins, what is a chapter heading and what is an OCR artifact, what gets cut out as scrape furniture, and how a word becomes a key. One of them runs the reader's own copy of the folding rule against the Python one, because the two are written in different languages and a divergence between them is silent |
| `routes` | Every page renders, search returns verses, a saved verse survives a reload, nothing throws |
| `layout` | At 320–430px every nav link is on screen, nothing scrolls sideways, the bar tucks away as you read, desktop is unchanged |
| `dating` | The date card against the spans the parser read, the method page, and that a citation names the edition and the era rather than just a URL |
| `search` | Result counts against known answers rather than "more than zero": phrases against their words, several terms meaning all of them, the three different ways a search can end with nothing, and that an accented or ligatured spelling on the page is reachable by an ordinary one |
| `words` | Turning a word on the page into an entry — by selection, by keyboard, by alias — what a missing entry says, and the places panel |
| `keeping` | Saving, unsaving, notes, the migration from the old bookmarks key, and what happens when the browser refuses to store anything at all |
| `resilience` | The data failing to load, malformed data, routes that name nothing, the keyboard shortcuts, the skip link, and what a screen reader is actually told |
| `listening` | What is spoken and in what order, which voice out of a bad drawer is picked, that the apparatus is never read out, where long passages are broken and how long the pauses are at each pace, the transport, the remembered place, chapter-to-chapter and work-to-work continuation, and the three ways a device can fail to speak |
| `offline` | The single-file build opens from `file://` and every feature in it works with no network at all |

The unit tests and the lint run on every pull request and again before every
deploy. The browser checks used to run on pull requests only, which meant
anything pushed straight to `main` went live without a browser having opened
the site; they now gate the deploy as well.

The player also offers a **pace** — natural, measured, liturgical — which sets
how long the silences are. Conversational pauses are wrong for verse, where
the line is the unit and the silence after it is part of the line. It is the
reader's control rather than something the volume decides: there is no genre
data here, Job is verse inside a prose frame, the prophets move between the two
mid-chapter, and a hand-written list of "the poetry books" would be an
editorial claim with no citation behind it.

**What they cannot check: whether a voice actually sounds right.** A headless
browser has no speech engine — the one these run in reports zero voices and
fails every utterance — so the engine is replaced with a stand-in that records
what it was asked to say. Everything above that line is the site's own code.
The last inch, audible sound, needs a real device.

## How the site works

Static files only — no build step, no dependencies, no tracking. Work texts and
search-index shards are fetched on demand, so the first paint is small even
though the library is seven megabytes. Read-aloud is the browser's own
`speechSynthesis`, with each passage cut into utterances short enough to clear
Chrome's fifteen-second cut-off.

Search is a two-stage design: a chapter-granularity inverted index (1.45 MB
across 27 shards) narrows candidates, then only the matching works are fetched
and scanned for exact verses. Quote a phrase to match it exactly.

## Deploying

`.github/workflows/pages.yml` runs the lint and the unit tests, rebuilds the
data from source, fails the build if `docs/data` has drifted or the audit finds
anything not in the baseline, runs the browser checks, and only then publishes
`docs/`.

**One manual step is required before the site can go live:** open
**Settings → Pages** and set **Source: GitHub Actions**. The workflow cannot do
this for you — `GITHUB_TOKEN` has no admin right to create a Pages site, so
until the switch is flipped the deploy job fails with *"Get Pages site failed"*.
The verify job runs regardless, so the data is still checked on every push.

Once enabled, re-run the workflow (Actions → Deploy site to GitHub Pages →
Run workflow) and the site appears at
`https://theoryofshadows.github.io/The-Book/`.

## Licence

Texts are public domain. The code, the audit and the editorial apparatus are
offered freely; use them.
