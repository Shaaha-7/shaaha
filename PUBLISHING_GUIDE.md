# How to Publish Shaaha & Make Everyone Use It

## Step 1 — Create a GitHub Repository

1. Go to https://github.com/new
2. Name it `shaaha`
3. Set it to **Public**
4. Push your code:

```bash
cd shaaha/
git init
git add .
git commit -m "feat: initial release of Shaaha v1.0.0"
git remote add origin https://github.com/<your-username>/shaaha.git
git push -u origin main
```

---

## Step 2 — Publish to PyPI (So Anyone Can `pip install shaaha`)

### 2a. Create a PyPI account
- Register at https://pypi.org/account/register/
- Enable **2FA** (required for new packages)

### 2b. Build your package

```bash
pip install build twine
python -m build          # creates dist/shaaha-1.0.0.tar.gz and .whl
```

### 2c. Upload to PyPI

```bash
twine upload dist/*
# Enter your PyPI username and password (or API token)
```

**After this, anyone in the world can run:**
```bash
pip install shaaha
```

### 2d. Automate future releases with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

---

## Step 3 — Set Up GitHub for Open Source Contributions

Create these files so the community can contribute:

### `.github/CONTRIBUTING.md`
Explain how to add a new backend to `registry.py` (it's just 5 lines).

### `.github/ISSUE_TEMPLATE/`
Add templates for "Add new backend", "Bug report", "Feature request".

### `LICENSE`
MIT License — already set in `pyproject.toml`. Create the file:
```
MIT License
Copyright (c) 2025 Shaaha
Permission is hereby granted, free of charge, to any person obtaining a copy...
```

---

## Step 4 — Make People Aware of Shaaha

### 4a. Reddit (biggest Python community)
Post in these subreddits:
- **r/Python** — "I built Shaaha: import numpy/polars/torch without caring which one you have"
- **r/MachineLearning** — focus on the GPU auto-detection angle
- **r/datascience** — focus on pandas vs polars auto-selection

**Template post title:**
> "I built a Python library called Shaaha that automatically picks the best backend (numpy/cupy, pandas/polars, sklearn/torch) based on your hardware. Zero config, zero dependencies."

### 4b. Hacker News
Submit to https://news.ycombinator.com/submit
Title: `Shaaha – Python meta-dispatcher that picks numpy/polars/torch automatically`

### 4c. Twitter / X
```
Just released Shaaha — a Python library that makes import numpy/polars/torch 
irrelevant. Write `import shaaha.math` and it picks the best backend 
for your hardware automatically.

pip install shaaha

GitHub: github.com/<you>/shaaha

#Python #MachineLearning #OpenSource
```

### 4d. Dev.to / Medium Article
Write a blog post titled:
**"Stop writing `try: import cupy except: import numpy`. Use Shaaha instead."**
Explain the problem → your solution → how PEP 302 makes it possible.

### 4e. Python Weekly / PyCoder's Weekly
Submit to these newsletters (they reach 100k+ Python developers):
- https://www.pythonweekly.com/
- https://pycoders.com/submissions

### 4f. LinkedIn
Post for academic/professional audience:
> "As part of my MSc thesis, I built and open-sourced Shaaha — a Python 
> Intelligent Meta-Dispatcher that uses PEP 302 import hooks to automatically 
> select the optimal backend (numpy/cupy, pandas/polars, scikit-learn/torch) 
> based on hardware and dependencies. pip install shaaha"

---

## Step 5 — Write Good Documentation

Host docs for free on **Read the Docs**:
1. Go to https://readthedocs.org/
2. Connect your GitHub repository
3. It auto-builds every time you push

---

## Growth Checklist

- [ ] Code pushed to GitHub (public)
- [ ] Package published on PyPI (`pip install shaaha` works)
- [ ] README has clear examples and a GIF/demo
- [ ] Posted on r/Python
- [ ] Submitted to Hacker News
- [ ] Submitted to Python Weekly newsletter
- [ ] LinkedIn post published
- [ ] Read the Docs set up
- [ ] GitHub Topics set: `python`, `import-hook`, `meta-dispatcher`, `machine-learning`

---

## MSc Thesis Reference

You can cite Shaaha as:
> Shaaha (2025). *Shaaha: An Intelligent Meta-Dispatcher for Python using PEP 302 
> Import Hooks.* MIT License. https://github.com/<you>/shaaha
