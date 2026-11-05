# Package manifests

One entry per line. `#` starts a comment.

| Syntax      | Meaning                                                              |
|-------------|----------------------------------------------------------------------|
| `pkg`       | Required. The build fails if it is not in any enabled repository.    |
| `a\|b\|c`   | Required, first available alternative wins (handles Artix/Arch name differences). |
| `?pkg`      | Optional. Skipped with a warning if unavailable.                     |
| `?a\|b`     | Optional with alternatives.                                          |

`build/lib/packages.sh` resolves these lists against the live repositories and
writes the exact result (with versions) to `out/<iso>.packages.txt`, which is
the reproducibility manifest for that ISO.
