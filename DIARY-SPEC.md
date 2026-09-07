# A study diary

A private log of what you read, why you read it, and what you took from it.

Written down before building, because the decisions here are mostly about
restraint, and restraint is easier to argue with on a page than in a diff.

## The rule this has to keep

This site's argument is that it would rather print a hole than a plausible
sentence. Every part of it is built that way: the canon table says 90 of 94
rather than "complete", the recovered books say which witness they follow
and what has not been checked about them, the audit exits non-zero on a
finding nobody has written down, and the front page is held to the data by
a test so the project cannot quietly disagree with itself.

A diary is the first thing on this site that would hold a reader's own
words rather than the text. Everything below follows from asking what that
same rule demands of a page like that.

It demands three things, and they are the whole design:

1. **Never claim to have kept something it did not keep.**
2. **Never tell the reader what their reading meant.**
3. **Never become a thing they cannot leave.**

## What it is

One entry per sitting. Four fields, only the last one really required:

| Field | |
| --- | --- |
| what you read | filled in from where you were, editable, and allowed to be empty |
| why this today | free text, a line or several |
| what you took from it | free text — the entry itself |
| how it landed | an optional mark, see below |

An entry belongs to a day; a day can hold several. Nothing is shared,
nothing is sent anywhere, nothing needs an account.

## Why it fits, and why the forum does not

The reader already keeps things: `store` wraps `localStorage` under a
`thebook:` prefix, `saved` holds up to 500 items each with an `at`, and the
backup format (`thebook.saved`, version 1) merges by id on restore rather
than replacing. The `keeping` suite covers saving, unsaving, notes, a
migration from an older key, and the browser refusing to store anything at
all.

A diary is that machinery in a different shape — no server, no dependency,
works offline, same as everything else here.

That is also the honest answer about the forum: **a diary is private by
nature, so it can live in the browser; a forum is public by nature, so it
cannot.** A forum needs hosting, identity, and somebody moderating what
strangers write about scripture — a standing duty, not a feature. It is a
different project, and it should be argued for on its own terms rather than
arriving attached to this one.

## Rule 1 — never claim to have kept something it did not keep

`store.set` returns whether it actually wrote, because Safari's private
browsing gives the page a quota of zero and a browser that has been reading
for years can simply run out. The existing code already refuses to announce
a verse as saved when the write failed.

A diary raises what is at stake. A lost verse is an annoyance; a lost
paragraph somebody wrote about their own life is not, and they will not
find out until the day they come back for it.

So:

- the entry is written to storage **before** anything on screen says it was
  kept, and the confirmation is shown only if `set` returned true
- when it returns false the text stays exactly where it is, in the box,
  still selectable, and the page says plainly that nothing was stored
- `STORAGE_FAILED` is reused, because it already separates a quota — which
  the reader can do something about — from private browsing, where "try
  again" would be a lie

This is the same standard as printing a hole rather than a plausible
sentence, applied to a promise instead of a text.

## Rule 2 — never tell the reader what their reading meant

### Not a streak

The obvious feature is a chain of unbroken days, and it is the wrong
instinct here. A streak turns a missed day into a failure and reading into
scorekeeping, and it would be this site telling somebody how they are doing
at scripture.

What the page shows instead is what they have actually been reading —
which books, over what stretch of time. That is something a person cannot
see for themselves and would find genuinely interesting, and it is a fact
rather than a judgement.

No badges, no goals, no notifications, no counts framed as targets.

### The mark is a bookmark, not a grade

Four marks, none of which is a score: *settled*, *unsettled*, *unclear*,
*stayed with me*. They exist so that months later a reader can find the
passages that unsettled them, which is a real thing to want and hard to do
any other way.

They are never averaged, never compared between books, and nothing on any
page ranks anything by them. A mark is a way back to a passage.

### On proving things by logging outcomes

This is the part of the idea that most needs the site's own rule applied to
it, so it is worth being exact.

A diary can honestly show a reader **their own** history: that they kept
coming back to Job through a hard winter; that the passages they marked
*unsettled* were mostly in the prophets. That is true, it is theirs, and it
is worth having.

What it cannot honestly do is turn that into evidence about the texts, or
about anyone else. There is no control. The reader chose what to read and
chose what to write down. The sample is one person, selected by
themselves, recording what they already thought was worth recording. A page
that added those up and reported a finding would be doing exactly what this
site refuses to do everywhere else — printing a plausible sentence where
the honest answer is a hole.

So the diary shows a reader their own history and says nothing about what
it means. That is not a limitation reluctantly accepted; it is the same
standard as the rest of the site, and it is what would make this page
trustworthy enough to write anything real into.

## Rule 3 — never become a thing they cannot leave

Extend the existing backup rather than starting a second one: format
version 2, a `diary` key beside `items`. A version 1 file restores as it
does now with no diary; a version 2 file restores on an older build by
ignoring what it does not recognise.

And offer the diary on its own as plain text — dated headings, the
reference, the paragraphs — because this is the one thing on the site a
person might want to keep after they have stopped using it, and a JSON blob
is not that. Somebody should be able to print it, or paste it into whatever
they keep, without this site being involved.

## Shape of the data

    thebook:diary -> [
      {
        id:   "2026-09-07T02:14:33.219Z",   // also the sort key
        day:  "2026-09-07",                 // local date, for grouping
        ref:  { work: "psalms", chapter: 23, title: "Psalm 23" },  // or null
        why:  "…",
        took: "…",
        mark: "unsettled"                   // or null
      }, …
    ]

Same prefix, same JSON, same cap and same failure handling as `saved`.
`ref` is null for an entry tied to no chapter, which has to be allowed —
some sittings are about the whole thing.

## The view

`#/diary`, beside `#/saved`. Entries newest first under their day, each
showing its reference as a link back to the chapter.

One quiet line at the top once there is enough to say it: how many
sittings, over what span, and the books that come up most. Stated, not
visualised, and not called a summary of anything.

A "Write about this" control on the chapter page, opening the form with the
reference filled in — that is the moment somebody wants to write, and
sending them elsewhere to do it loses the thought.

## What has to be tested

Following what `keeping` already does, and in its spirit — every one of
these is a way the page could quietly lie:

- an entry survives a reload
- an entry with no reference is allowed
- the day grouping is by **local** date, not UTC: an entry written at 11pm
  belongs to that evening, and a reader in New Zealand is not filed under
  yesterday
- a refused write leaves the text on screen, says nothing was stored, and
  does not announce success
- the cap drops the oldest, never the newest
- export then import restores every entry exactly once; merging onto a
  browser that already has entries adds rather than replaces
- a version 1 backup still restores
- an entry containing markup is shown as text, never rendered
- the plain-text export contains every entry, so it is really a way out

## What this does not include

No sharing, no accounts, no sync, no server. Each turns a page that keeps a
private note into a service holding somebody's religious reflections, which
is a different undertaking with a different duty of care.

Sync will be the one that gets asked for. The honest answer today is the
export file, and saying so is better than half-building the other thing.
