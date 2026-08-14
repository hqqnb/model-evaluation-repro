# Multimodal Evaluation Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a four-question multimodal evaluation set with clear ground truth, high model separation, and scoring that non-specialists can verify.

**Architecture:** Keep one real licensed street photo for natural-scene complexity and generate the handwritten table, complex chart, and engineering sketch deterministically with Pillow. Store public-image provenance beside the assets, place candidate-facing prompts in the question document, and keep exact answers plus a shared 10-point rubric in the internal scoring document.

**Tech Stack:** Python 3, Pillow, Markdown, Wikimedia Commons metadata

---

### Task 1: Validate The Street-Scene Asset

**Files:**
- Verify: `assets/MM1_实景街景.jpg`
- Create: `assets/MM1_实景街景_来源.md`

- [ ] **Step 1: Inspect the original-resolution image**

Confirm that `Spadina Ave`, the no-left-turn hours, streetcar route display, vehicle number, traffic lights, and selected storefront text are visibly recoverable.

- [ ] **Step 2: Record source metadata**

Write the Wikimedia Commons page, original file URL, author, license, capture date, download date, and whether the file was modified.

- [ ] **Step 3: Check attribution completeness**

Confirm that the metadata names The City of Toronto / Jose San Juan and CC BY 2.0.

### Task 2: Generate Three Controlled Assets

**Files:**
- Modify: `assets/generate_assets.py`
- Create: `assets/MM2_手写表格.png`
- Create: `assets/MM3_复杂图表.png`
- Create: `assets/MM4_工程草图.png`

- [ ] **Step 1: Add handwritten-table rendering**

Render a household purchase sheet with seven rows, one crossed-out quantity, one ambiguous handwritten character, and a deliberately incorrect written total. Keep all underlying values fixed in code.

- [ ] **Step 2: Add complex-chart rendering**

Render monthly actual sales, forecast sales, return rate, a forecast band, one missing actual value, and a truncated sales axis. Label values so answers are independently checkable.

- [ ] **Step 3: Add engineering-sketch rendering**

Render front and side views of a wall shelf bracket with dimensions, hole positions, and a maximum shelf-depth note. Omit material and load capacity intentionally.

- [ ] **Step 4: Generate the image files**

Run:

```bash
python3 assets/generate_assets.py
```

Expected: the existing `M1-M5` images and new `MM2-MM4` images are saved without exceptions.

### Task 3: Replace The Candidate-Facing Test

**Files:**
- Modify: `题目/03_多模态能力测试.md`

- [ ] **Step 1: Define common answer rules**

Require models to separate visible facts, derived conclusions, and indeterminate claims; uncertain text must be marked rather than guessed.

- [ ] **Step 2: Write four complete prompts**

Each question must include direct extraction, a calculation or rule-based inference, and at least one request whose correct response is “cannot be determined from the image.”

- [ ] **Step 3: Add timing fields**

Record time to first output and time to completed answer separately from the 40-point intelligence score.

### Task 4: Replace The Internal Answer Key

**Files:**
- Modify: `内部答案/03_多模态答案与评分.md`

- [ ] **Step 1: Add exact ground truth**

List all OCR strings, numeric values, calculations, visual relationships, and intentionally unavailable facts.

- [ ] **Step 2: Apply the shared rubric**

Score every question out of 10: detail recognition 3, OCR 2, reasoning 3, hallucination control 2.

- [ ] **Step 3: Add human verification guidance**

For each scoring item, state exactly where the evaluator can look in the image and what partial credit is allowed.

### Task 5: Verify The Finished Set

**Files:**
- Verify: `assets/MM1_实景街景.jpg`
- Verify: `assets/MM2_手写表格.png`
- Verify: `assets/MM3_复杂图表.png`
- Verify: `assets/MM4_工程草图.png`
- Verify: `题目/03_多模态能力测试.md`
- Verify: `内部答案/03_多模态答案与评分.md`

- [ ] **Step 1: Inspect every image visually**

Confirm that intended text is readable, ambiguity is deliberate, no labels overlap, and all diagram dimensions are visible.

- [ ] **Step 2: Run structural checks**

Run:

```bash
python3 -m py_compile assets/generate_assets.py
rg -n "MM1|MM2|MM3|MM4" 题目/03_多模态能力测试.md 内部答案/03_多模态答案与评分.md
```

Expected: Python compilation succeeds and both documents contain all four question IDs.

- [ ] **Step 3: Cross-check answers against generator constants**

Recalculate totals, percentages, chart deltas, and bracket fit conditions; correct any mismatch before delivery.
