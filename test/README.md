# Test tree for logs_redirect

**Purpose:** local HTML tree to test navigation logging (depth, branches, back-navigation).

## Tree structure

- **Level 0:** `index.html` — 4 links → `1-0` … `1-3`
- **Level 1:** 4 pages — each has 2 links → `2-x-0`, `2-x-1`
- **Level 2:** 8 pages — each has 2 links → `3-x-x-0`, `3-x-x-1`
- **Level 3:** 16 pages — leaves (no child links)

**Total:** 29 pages. Each page has “Back to parent” and “Root (index)” links.

```
index
├── 1-0 → 2-0-0, 2-0-1 → (4 leaves)
├── 1-1 → 2-1-0, 2-1-1 → (4 leaves)
├── 1-2 → 2-2-0, 2-2-1 → (4 leaves)
└── 1-3 → 2-3-0, 2-3-1 → (4 leaves)
```

Regenerate: from `Main`, run `python gen_tree_pages.py`.
