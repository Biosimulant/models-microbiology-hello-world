# Model Standards

Acceptance criteria and conventions for this tutorial model repository.

## Required Layout

```text
labs/<lab-slug>/
├── lab.yaml
└── model/
    ├── model.yaml
    ├── README.md
    ├── src/
    │   └── <module>.py
    └── tests/
        ├── conftest.py
        └── test_<module>.py
```

## Required Checks

Before publishing changes, run:

```bash
python3 scripts/validate_manifests.py
python3 scripts/check_entrypoints.py
bash scripts/check_public_boundary.sh
python3 -m pytest -q labs/microbiology-hello-world-growth/model/tests
```

## Model Rules

- Keep the model pure Python plus `biosim`.
- Keep examples runnable without external data or network access.
- Keep CLI output understandable to a non-technical user.
- Keep public documentation free of private operating details.
- Any Python package dependency declared in a manifest must use exact `==`
  pinning.
