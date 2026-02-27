"""Shared test fixtures for SearchCarriers plugin + skill validation."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


@pytest.fixture
def repo_root():
    return ROOT


@pytest.fixture
def all_skill_files(repo_root):
    """Find all SKILL.md files in skills/ and plugins/."""
    skills = list(repo_root.glob("skills/**/SKILL.md"))
    skills += list(repo_root.glob("plugins/**/SKILL.md"))
    return skills


@pytest.fixture
def all_plugin_dirs(repo_root):
    """Find all plugin directories."""
    plugins_dir = repo_root / "plugins"
    if not plugins_dir.exists():
        return []
    return [d for d in plugins_dir.iterdir() if d.is_dir()]


@pytest.fixture
def all_plugin_jsons(all_plugin_dirs):
    """Find all plugin.json files."""
    jsons = []
    for d in all_plugin_dirs:
        pj = d / ".claude-plugin" / "plugin.json"
        if pj.exists():
            jsons.append(pj)
    return jsons


def parse_frontmatter(skill_path: Path) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    content = skill_path.read_text()
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    import yaml
    try:
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}
