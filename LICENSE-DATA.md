# Licence: the texts, the data, and the reading

The code is MIT — see [LICENSE](LICENSE). This file covers everything else,
which is not one licence but four, because the material arrived under four
different ones and no single label would be true of all of it.

The short version: **the texts are public domain, the reference data is CC BY
4.0, and two of the datasets require attribution that cannot be waived.** If
you reuse `docs/data/`, you must carry the credits at the bottom of this file.

---

## The texts — public domain

Every translation in `source/THE_BOOK_COMPLETE.txt` and `docs/data/works/` is
old enough to be out of copyright, or was dedicated to the public domain by
its publisher. Nothing here is drawn from a modern copyrighted translation.
The full list of editions, with dates, is in the Sources table in
[README.md](README.md).

The World English Bible, which supplies the canonical Old and New Testaments
and the deuterocanon, is dedicated to the public domain by eBible.org. The
rest — Charles 1917, the Ante-Nicene Fathers of 1885, Platt 1834, Horner 1904,
Issaverdens 1901, James 1924, Schodde 1885, Cooper and Maclean 1902, Lightfoot
and Harmer 1891 — is public domain by age.

**You may do anything you like with the texts.** No attribution is required,
though the editions are named on every page because knowing which translation
you are reading is the point of the project.

## The land outlines — public domain

`source/basemap/` is [Natural Earth](https://www.naturalearthdata.com/), which
states: "All versions of Natural Earth raster + vector map data found on this
website are in the public domain." Crediting is explicitly unnecessary. The
site credits it anyway.

## The reference data — CC BY 4.0, attribution required

Two datasets are openly licensed rather than public domain, and their terms
travel with the data:

**Word definitions** (`source/lexicon/`, `docs/data/lexicon/`) are Easton's
Bible Dictionary, 1897 — public domain by age — in a machine-readable parse by
[NEUU](https://github.com/neuu-org/bible-dictionary-dataset), released under
**CC BY 4.0**. The dictionary text is free; the parse is not, and requires
attribution.

**Place coordinates** (`source/places/`, `docs/data/places/`) are
[OpenBible.info's Bible Geocoding](https://www.openbible.info/geo/) data,
released under **CC BY 4.0**: "you can use them for any purpose you want as
long as you credit OpenBible.info." Parts of it derive from **OpenStreetMap**,
which is licensed under the
[ODbL](https://opendatacommons.org/licenses/odbl/); OpenStreetMap must be
credited for those, and a substantially derived *database* may carry the
ODbL's share-alike obligation. Rendered maps and other "Produced Works" need
only the attribution notice.

Because of these two, **the reference data cannot be released as public domain
or CC0.** The obligations were inherited and cannot be dropped by relicensing
downstream.

## Everything derived from the above — CC BY 4.0

The parse, the audit, the editorial apparatus, the chronological arrangement,
the search index, the thread definitions, the canon tables and the accuracy
report are original work built on the sources above. They are offered under
[**CC BY 4.0**](https://creativecommons.org/licenses/by/4.0/) — the same terms
as the reference data they sit beside, so that one rule covers `docs/data/`
rather than a per-file map nobody would read.

Attribute as: *The Book — Chronological Biblical Library,
https://github.com/TheoryofShadows/The-Book*

## The recorded readings — public domain, and not ours

The readings the site offers are recordings of these texts made by other
people, who put them in the public domain. They are listed in
[`tools/readings.py`](tools/readings.py), each stating its narrator, the
edition it reads, and its terms.

Most reach the site through [LibriVox](https://librivox.org/), whose readers
dedicate their recordings under the
[Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/);
one, David Williams's reading, was released without restriction by the reader
directly. **No attribution is legally required by any of them.** The site
names every narrator anyway, in the player while their reading plays — the
same choice it makes about Natural Earth, and for the same reason: a person
read a hundred hours of scripture aloud and gave it away, and the fact that
they waived the credit is not a reason to withhold it.

The recordings are mirrored rather than hot-linked, so that a chapter is one
small request instead of an hour-long file, and so that a reader is not
dependent on somebody else's directory layout. They are not stored in this
repository — roughly 1.5 GB, published as release assets. What *is* stored
here is the alignment: which second of the recording each verse begins at,
under `docs/data/audio/`. That is derived data, and is offered under
**CC BY 4.0** with the rest of it.

**A recording of the wrong translation is not usable, and none is offered.**
This volume prints particular editions, and a reading of a different one
shares the subject and not the words. That is checked by alignment rather than
asserted: audio that will not match this text is rejected and the reader falls
back to the device's own voice. `tools/readings.py` also records the
recordings that were turned down and why, so the same mistakes are not made
twice.

Nothing here is drawn from a commercial audio Bible. Those are copyrighted
recordings, and the text underneath being free does not change that.

## The synthesised reading — CC BY 4.0

[`tools/render_audio.py`](tools/render_audio.py) can synthesise a reading with
[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), whose weights are
Apache-2.0. The model licence governs the weights, which this repository does
not redistribute; it asserts nothing over audio the model produces, and the
words being read are public domain. Such audio would be offered under **CC BY
4.0**, with the rest of the derived data.

None has ever been published, and the recorded readings above are the better
answer where one exists.

---

## If you reuse the data, carry these

The minimum notice that satisfies everything above:

> Texts are public domain. Word definitions from Easton's Bible Dictionary
> (1897), parsed by NEUU, CC BY 4.0. Place coordinates from OpenBible.info's
> Bible Geocoding, CC BY 4.0, parts derived from OpenStreetMap under the ODbL.
> Land outlines from Natural Earth (public domain). Recorded readings are
> public domain, by the narrators named in tools/readings.py. Compiled by
> The Book — Chronological Biblical Library, CC BY 4.0.

The running site carries this notice on its front page, and names the source
of every definition, coordinate and recorded reading at the point of use
rather than only in aggregate here.
