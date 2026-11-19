# Question Lineage

Lineage integrity: all parents exist, generations are consistent, no cycles.

## Families

```
p1-a2
└── representation → m-p1-a2-rep [PASS]
    └── parameter → m2-p1-a2-rep-par [PASS]

p1-a3
└── reasoning_path → m-p1-a3-path [PASS]

p1-a4
└── constraint → m-p1-a4-con [PASS]

p1-a6
└── surface → m-p1-a6-surf [PASS]

p1-b1
└── parameter → m-p1-b1-par [PASS]

p1-b2
└── surface → m-p1-b2-surf [PASS]

p1-b3
└── reverse → m-p1-b3-rev [PASS]

p2-a2
└── difficulty → m-p2-a2-diff [PASS]

p2-a3
└── parameter → m-p2-a3-par [PASS]

p2-a4
└── reverse → m-p2-a4-rev [PASS]

p2-a5
└── context_transfer → m-p2-a5-ctx [PASS]

p2-b1
└── reasoning_path → m-p2-b1-path [PASS]

p2-b3
└── constraint → m-p2-b3-con [PASS]

p3-a2
└── difficulty → m-p3-a2-diff [PASS]

p3-a3
└── context_transfer → m-p3-a3-ctx [PASS]

p3-a4
└── representation → m-p3-a4-rep [REVIEW_REQUIRED]

p3-b1
└── difficulty → m-p3-b1-diff [PASS]

p3-b2
└── representation → m-p3-b2-rep [PASS]
```
