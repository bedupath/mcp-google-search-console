from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_development_skills_have_valid_frontmatter_and_no_missing_links():
    skills = ROOT / ".agents" / "skills"
    # sdist intentionally contains runtime source/tests, not contributor-agent guidance.
    if not skills.exists():
        return
    assert {p.name for p in skills.iterdir()} == {"gsc-engineer", "gsc-reviewer", "gsc-verify"}
    root_guide = (ROOT / "AGENTS.md").read_text()
    for folder in skills.iterdir():
        entrypoint = folder / "SKILL.md"
        content = entrypoint.read_text()
        frontmatter = yaml.safe_load(content.split("---", 2)[1])
        assert frontmatter["name"] == folder.name
        assert isinstance(frontmatter["description"], str) and frontmatter["description"].strip()
        assert f".agents/skills/{folder.name}/SKILL.md" in root_guide


def test_runtime_source_does_not_load_development_skills():
    from mcp_google_search_console import __file__ as package_file

    package = Path(package_file).parent
    assert not (package / ".agents").exists()
    for source in package.glob("*.py"):
        assert "SKILL.md" not in source.read_text()
