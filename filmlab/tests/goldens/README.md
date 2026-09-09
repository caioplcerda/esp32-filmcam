# Golden renders

One `.npy` per film stock: the developed output of the synthetic test chart in
`test_golden.py`, with a fixed grain seed.

These are committed deliberately. A failing golden test means the look changed.
If that was intended, regenerate and review the diff as part of the change:

    FILMLAB_UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_golden.py

Never regenerate to make a red test go green without looking at why it moved.
