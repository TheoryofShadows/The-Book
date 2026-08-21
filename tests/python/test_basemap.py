#!/usr/bin/env python3
"""The two pieces of geometry the basemap rests on.

Both are the kind of code that fails quietly. A simplifier that is slightly
too keen deletes an island and the map still draws; a clipper that is slightly
wrong turns a filled continent into an outline and the map still draws. Neither
raises, and neither is obvious in a 74 KB file of numbers.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))

import build_basemap as bm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def square(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


class Visvalingam(unittest.TestCase):

    def test_a_straight_line_collapses_to_its_ends(self):
        line = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0)]
        out = bm.visvalingam(line, threshold=1.0, keep_min=2)
        self.assertEqual(out, [(0, 0), (7, 0)])

    def test_a_corner_is_never_dropped(self):
        line = [(0, 0), (1, 0), (2, 0), (2, 5), (2, 9)]
        out = bm.visvalingam(line, threshold=0.5, keep_min=2)
        self.assertIn((2, 0), out, "the corner carries the shape")

    def test_the_ends_are_kept_so_a_ring_stays_closed(self):
        ring = square(0, 0, 10, 10)
        out = bm.visvalingam(ring, threshold=1000.0, keep_min=2)
        self.assertEqual(out[0], out[-1])

    def test_it_never_goes_below_the_floor(self):
        # A threshold big enough to erase anything, against the floor that
        # exists to stop Cyprus and Crete disappearing.
        ring = square(0, 0, 1, 1)
        out = bm.visvalingam(ring, threshold=1e9, keep_min=bm.KEEP_MIN)
        self.assertGreaterEqual(len(out), min(bm.KEEP_MIN, len(ring)))

    def test_a_ring_already_at_the_floor_is_returned_whole(self):
        ring = square(0, 0, 1, 1)
        self.assertEqual(bm.visvalingam(ring, 1e9, keep_min=99), ring)

    def test_a_threshold_of_zero_changes_nothing(self):
        ring = [(0, 0), (1, 3), (4, 2), (6, 5), (0, 0)]
        self.assertEqual(bm.visvalingam(ring, 0.0), ring)

    def test_simplifying_harder_never_yields_more_points(self):
        ring = [(i, (i * 7) % 11) for i in range(60)]
        sizes = [len(bm.visvalingam(ring, t, keep_min=2))
                 for t in (0.0, 1.0, 5.0, 20.0)]
        self.assertEqual(sizes, sorted(sizes, reverse=True), sizes)


class Clipping(unittest.TestCase):

    FRAME = (0.0, 0.0, 10.0, 10.0)

    def test_a_shape_wholly_inside_is_left_alone(self):
        ring = square(2, 2, 8, 8)
        out = bm.clip_ring(ring, self.FRAME)
        self.assertEqual(set(out), set(ring))

    def test_a_shape_wholly_outside_disappears(self):
        self.assertEqual(bm.clip_ring(square(20, 20, 30, 30), self.FRAME), [])

    def test_a_shape_crossing_the_edge_is_cut_at_it(self):
        out = bm.clip_ring(square(5, 5, 20, 20), self.FRAME)
        self.assertTrue(out)
        for x, y in out:
            self.assertLessEqual(x, 10.0001)
            self.assertLessEqual(y, 10.0001)

    def test_the_cut_shape_is_closed_so_it_fills_as_land(self):
        # The whole point: land running off the frame must be closed along the
        # frame's edge, or it draws as a coastline where the map stops.
        out = bm.clip_ring(square(5, 5, 20, 20), self.FRAME)
        self.assertEqual(out[0], out[-1])

    def test_the_cut_keeps_the_corner_of_the_frame(self):
        out = bm.clip_ring(square(5, 5, 20, 20), self.FRAME)
        self.assertIn((10.0, 10.0), out)

    def test_a_shape_larger_than_the_frame_becomes_the_frame(self):
        out = bm.clip_ring(square(-5, -5, 15, 15), self.FRAME)
        self.assertEqual(set(out), {(0.0, 0.0), (10.0, 0.0),
                                    (10.0, 10.0), (0.0, 10.0)})

    def test_a_degenerate_result_is_dropped_not_returned_as_a_sliver(self):
        self.assertEqual(bm.clip_ring([(0, 0), (1, 1), (0, 0)], self.FRAME), [])


class Committed(unittest.TestCase):
    """What is actually in docs/data/basemap, which is what ships."""

    def layer(self, name):
        import json
        path = os.path.join(ROOT, "docs", "data", "basemap", name + ".json")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)["rings"], os.path.getsize(path)

    def test_both_layers_are_within_budget(self):
        for name in ("world", "levant"):
            _, size = self.layer(name)
            self.assertLessEqual(size, bm.BUDGET[name],
                                 f"{name} is {size} bytes")

    def test_every_ring_is_closed(self):
        for name in ("world", "levant"):
            rings, _ = self.layer(name)
            for i, r in enumerate(rings):
                self.assertEqual(len(r) % 2, 0, f"{name} ring {i} is not pairs")
                self.assertEqual((r[0], r[1]), (r[-2], r[-1]),
                                 f"{name} ring {i} is not closed")

    def test_no_ring_is_a_degenerate_sliver(self):
        for name in ("world", "levant"):
            rings, _ = self.layer(name)
            for i, r in enumerate(rings):
                self.assertGreaterEqual(len(r) // 2, 4, f"{name} ring {i}")

    def test_the_levant_layer_stays_inside_its_frame(self):
        rings, _ = self.layer("levant")
        west, south, east, north = bm.FRAME
        for r in rings:
            for i in range(0, len(r), 2):
                self.assertTrue(west - 0.01 <= r[i] <= east + 0.01, r[i])
                self.assertTrue(south - 0.01 <= r[i + 1] <= north + 0.01, r[i + 1])

    def test_the_islands_the_texts_name_survived_simplification(self):
        """Cyprus, Crete and Rhodes are the reason there is a floor per ring.

        A threshold picked for the mainland deletes all three, and the map
        still looks plausible -- which is what makes it worth a test.
        """
        rings, _ = self.layer("levant")
        boxes = []
        for r in rings:
            xs, ys = r[0::2], r[1::2]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))

        for name, lon, lat in (("Cyprus", 33.0, 35.1),
                               ("Crete", 24.8, 35.2),
                               ("Rhodes", 28.0, 36.2)):
            hit = any(x0 - 0.6 <= lon <= x1 + 0.6 and y0 - 0.6 <= lat <= y1 + 0.6
                      for x0, y0, x1, y1 in boxes)
            self.assertTrue(hit, f"{name} is missing from the Levant layer")

    def test_the_whole_map_feature_stays_under_its_budget(self):
        """Basemap plus mention index, which is what the map added."""
        total = 0
        base = os.path.join(ROOT, "docs", "data", "basemap")
        for fn in os.listdir(base):
            total += os.path.getsize(os.path.join(base, fn))
        total += os.path.getsize(os.path.join(ROOT, "docs", "data", "mentions.json"))
        self.assertLessEqual(total, 250 * 1024, f"{total/1024:.0f} KB")


if __name__ == "__main__":
    unittest.main()
