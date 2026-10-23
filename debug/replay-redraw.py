#!/usr/bin/env python3
# Replay logs/redraw/typescript through pyte and print the screen at chosen
# points, to inspect what a real terminal would have shown.
#
# Usage: replay-redraw.py [--at SECONDS ...] [--gaps MIN_PAUSE] [dir]
#   --at     snapshot at these offsets (seconds since dvtm started)
#   --gaps   snapshot before every pause in output longer than MIN_PAUSE
# If the capture has a sizes file, the screen is resized as the real
# terminal was; without one it stays at the size script(1) recorded.
# Needs pyte (pip install pyte).

import argparse
import re
import pyte


class Screen(pyte.Screen):
    # pyte lacks SU/SD (CSI S, CSI T), which ncurses emits inside a scroll
    # region; without them the replay shows corruption a terminal would not.
    def scroll_up(self, count=1):
        top, bottom = self.margins or pyte.screens.Margins(0, self.lines - 1)
        for _ in range(count or 1):
            for y in range(top, bottom):
                self.buffer[y] = self.buffer[y + 1]
            self.buffer.pop(bottom, None)
        self.dirty.update(range(self.lines))

    def scroll_down(self, count=1):
        top, bottom = self.margins or pyte.screens.Margins(0, self.lines - 1)
        for _ in range(count or 1):
            for y in range(bottom, top, -1):
                self.buffer[y] = self.buffer[y - 1]
            self.buffer.pop(top, None)
        self.dirty.update(range(self.lines))


class Stream(pyte.ByteStream):
    csi = dict(pyte.ByteStream.csi, S="scroll_up", T="scroll_down")


def load(d):
    raw = open(f"{d}/typescript", "rb").read()
    head = raw[: raw.index(b"\n") + 1]
    m = re.search(rb'COLUMNS="(\d+)" LINES="(\d+)"', head)
    cols, lines = int(m[1]), int(m[2])
    body = raw[len(head):]
    tail = body.rfind(b"\nScript done on")
    if tail >= 0:
        body = body[:tail]
    chunks, pos, t = [], 0, 0.0
    for line in open(f"{d}/timing"):
        delay, n = line.split()
        t += float(delay)
        chunks.append((t, body[pos:pos + int(n)]))
        pos += int(n)
    sizes = []
    try:
        rows = [l.split() for l in open(f"{d}/sizes")]
        t0 = float(rows[0][0])
        sizes = [(float(e) - t0, int(r), int(c)) for e, r, c in rows]
    except (OSError, IndexError, ValueError):
        pass
    return cols, lines, chunks, sizes


def show(screen, t, i):
    print(f"===== t={t:.3f}s after chunk {i},"
          f" {screen.lines}x{screen.columns} =====")
    for y, row in enumerate(screen.display):
        print(f"{y:2d}|{row.rstrip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default="logs/redraw")
    ap.add_argument("--at", type=float, nargs="*", default=[])
    ap.add_argument("--gaps", type=float)
    a = ap.parse_args()
    cols, lines, chunks, sizes = load(a.dir)
    screen = Screen(cols, lines)
    stream = Stream(screen)
    at = sorted(a.at)
    # Resizes and requested snapshots are applied in time order between
    # chunks; a snapshot at the same time as a resize sees the new size.
    events = sorted([(t, 0, s[1:]) for s in sizes for t in [s[0]]] +
                    [(t, 1, None) for t in a.at])
    i = -1
    for i, (t, data) in enumerate(chunks):
        while events and events[0][0] < t:
            et, kind, size = events.pop(0)
            if kind == 0:
                screen.resize(*size)
            else:
                show(screen, et, i - 1)
        stream.feed(data)
        nxt = chunks[i + 1][0] if i + 1 < len(chunks) else None
        if a.gaps is not None and (nxt is None or nxt - t > a.gaps):
            show(screen, t, i)
    for et, kind, size in events:
        if kind == 0:
            screen.resize(*size)
        else:
            show(screen, et, i)

if __name__ == "__main__":
    main()
