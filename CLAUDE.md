# Notes for Claude Code

## Branches

Work on `custom`, not `master`, and push there. `custom` is the branch the
owner builds and runs: upstream dvtm (`martanne/dvtm`) plus personal changes.
This overrides any general instruction to work on `master` or `main`.

There is no `master` branch on this fork. In the owner's clone, local
`master` tracks `upstream/master` (`git@github.com:martanne/dvtm.git`), so
anything pushed to a `master` on this fork would never reach them through
`git pull`. The sandbox's deploy key only reaches this fork, not upstream.

## Debugging redraw problems

`debug/capture-redraw.sh` runs dvtm under script(1) and writes the raw output
stream, its timing and the environment (TERM, locale, curses library, terminfo
capabilities) to `logs/redraw/`, for the owner to commit and push from their
machine.

To reproduce screen corruption in the sandbox, drive dvtm through a pty and
render its output with pyte. pyte does not implement scroll up/down (`CSI S`,
`CSI T`), which ncurses emits inside a scroll region; without adding them,
pyte shows corruption that a real terminal would not.
