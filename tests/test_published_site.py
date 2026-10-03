"""Guards the published docs site (issue #75).

The site kept describing a product that no longer existed, and nothing failed. The repo
was renamed to trazo (#52), the delivery model became a mountable overlay (#0005), the
flywheel commands were removed (#73), and the `/semilla` command was renamed (#72) — while
`handbook/`, which is `docs_dir`, went on publishing:

    <title>semilla</title>
    "A self-improving template for starting software projects"
    "Every project grows from it, and each one sends what it learned back"

None of that is checkable by a build. A rename PR can leave it behind, and the only thing
that caught it was curling the live page — the same out-of-band class as #52's workflow
gate and #61's squash merge.

So these assert the invariants that made the drift possible:

1. **The site's identity matches the repository.** `site_name` becomes the `<title>` on
   every page, and `site_description` the meta description.
2. **No published page claims a delivery model that was removed.** "Template" and the
   lesson-flywheel sentence are the two claims that went false, and a substitution cannot
   fix either — they have to be rewritten, which is what this issue did.
3. **The overlay is actually documented.** `src/overlay/` is the product (installed here as
   `.trazo/`), and before this nothing on the site explained what it was or what
   contract a mounted repo must satisfy.
4. **The logo is not the old pun.** The mark was a seed/sprout, because the repo used to
   be called *semilla*.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MKDOCS = REPO_ROOT / "mkdocs.yml"
HANDBOOK = REPO_ROOT / "handbook"
LOGO = HANDBOOK / "assets" / "logo.svg"
FAVICON = HANDBOOK / "assets" / "favicon.svg"

# Every file `docs_dir` publishes. lessons.md and changelog.md are `--8<--` includes of
# .template/, so they follow automatically and are excluded here.
PUBLISHED = ("index.md", "guide.md", "playbook.md", "team.md", "overlay.md")

# Spelling here so the scan below does not match this file's own source.
OLD_NAME = "sem" + "illa"


def _text_files() -> list[Path]:
    return [HANDBOOK / name for name in PUBLISHED if (HANDBOOK / name).exists()]


def test_site_identity_matches_the_repository() -> None:
    """`site_name` becomes the `<title>` on every page. This is the drift itself."""
    mkdocs = MKDOCS.read_text(encoding="utf-8")
    name = re.search(r"^site_name:\s*(.+)$", mkdocs, re.MULTILINE)
    assert name, "no site_name in mkdocs.yml"
    assert name.group(1).strip() == "Trazo", (
        f"site_name is {name.group(1).strip()!r}; it is the <title> on every page"
    )
    desc = re.search(r"^site_description:\s*(.+)$", mkdocs, re.MULTILINE)
    assert desc, "no site_description"
    assert OLD_NAME not in desc.group(1), "site_description still names the old project"
    assert "overlay" in desc.group(1).lower(), (
        "the description must lead with the overlay; that is what the project is now"
    )


def test_no_published_page_names_the_old_project() -> None:
    offenders = []
    for path in _text_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"\b{OLD_NAME}\b", line, re.IGNORECASE):
                offenders.append(f"{path.name}:{lineno}: {line.strip()[:70]}")
    assert not offenders, "published pages still call the project the old name:\n" + "\n".join(
        offenders
    )


def test_no_page_claims_a_flywheel_that_was_removed() -> None:
    """`/template-improve` and `/template-sync` were deleted in #73. The sentence
    "each one sends what it learned back" advertised exactly that, and a find-and-replace
    would have left it in place."""
    for path in _text_files():
        text = path.read_text(encoding="utf-8").lower()
        assert "sends what it learned back" not in text, (
            f"{path.name} still promises an automatic lesson flywheel that no longer exists"
        )
        assert "template-improve" not in text
        assert "template-sync" not in text


def test_the_overlay_is_documented_and_reachable() -> None:
    """The gap that made the site wrong: `.trazo/` is the product and nothing explained
    it -- not the layout, and not the one contract a mounted repo must satisfy."""
    overlay = HANDBOOK / "overlay.md"
    assert overlay.exists(), "handbook/overlay.md is missing; the overlay is undocumented"
    text = overlay.read_text(encoding="utf-8")

    assert "mount-time contract" in text.lower(), "the contract is what makes mounting work"
    assert re.search(r"hermetic", text, re.IGNORECASE), "the contract must state hermetic"
    for path in ("rules.md", "charter/", "adr/", "workstreams/"):
        assert path in text, f"the layout omits {path}"
    assert "judgment" in text.lower(), "the judgment layer is the differentiator; say so"
    assert "stop rule" in text.lower()

    # Reachable: in the nav, and linked from the home page.
    mkdocs = MKDOCS.read_text(encoding="utf-8")
    assert "overlay.md" in mkdocs, "overlay.md is not in mkdocs nav, so it is unreachable"
    assert "overlay.md" in (HANDBOOK / "index.md").read_text(encoding="utf-8"), (
        "the home page must link it, or a reader never finds out the product exists"
    )


def test_the_home_page_leads_with_the_overlay_not_the_cloud() -> None:
    """AWS is still true and still supported, but it is a deploy choice for a Trazo-owned
    repo -- it stopped being the headline qualifier at the pivot, and leading with it
    describes the old product."""
    index = (HANDBOOK / "index.md").read_text(encoding="utf-8")
    assert "overlay" in index.lower(), "the home page does not say it is an overlay"
    # The tagline is the first bolded paragraph after the H1, not the whole page: AWS is
    # legitimately discussed further down in its own section.
    tagline = next((ln for ln in index.splitlines()[1:] if ln.strip().startswith("**")), "").lower()
    assert tagline, "no bolded tagline under the H1"
    assert "aws" not in tagline, (
        "AWS is in the tagline again; that is the pre-pivot pitch, where the cloud choice "
        "was the headline qualifier instead of the overlay"
    )
    assert "skeptic" in index.lower(), "the judgment layer is not mentioned on the home page"


def test_the_logo_is_not_the_old_pun() -> None:
    """It was a seed/sprout, because the repo used to be called *semilla* — a pun that could
    drift away from the product. The mark is now the badge from the brand style guide.

    The old assertion that the logo be *wider than tall* (it was a wordmark) and that it use
    `currentColor` no longer hold, and neither should they:

    - the badge is square by construction, which is what makes it work as a favicon, an App
      icon and a 16px GitHub glyph;
    - `currentColor` existed because a stroked wordmark on MkDocs' black header is invisible
      in one scheme unless it inherits. The badge is a filled circle in fixed brand colours,
      so it is legible on any background without inheriting.

    What replaces them is the invariant that actually matters: the header mark and the
    favicon are the same drawing, and it is drawn in the specified palette.
    """
    for path in (LOGO, FAVICON):
        assert path.exists(), f"{path.name} is missing"
    svg = LOGO.read_text(encoding="utf-8")
    assert "Trazo" in svg, "the mark carries no accessible name"

    viewbox = re.search(r'viewBox="([^"]+)"', svg)
    assert viewbox, "no viewBox"
    _, _, w, h = (float(v) for v in viewbox.group(1).split())
    assert w == h, f"viewBox is {w}x{h}; the badge is square so it scales as an icon"

    for colour in ("#C8102E", "#1FBCB3"):
        assert colour in svg, f"the brand colour {colour} is missing from the mark"


def test_the_svgs_are_well_formed_xml() -> None:
    """A browser refuses to render malformed SVG. It shows a broken-image icon instead.

    This exists because it already shipped once. `logo.svg` carried a comment written with a
    double hyphen as a dash, which XML forbids inside a comment, so the deployed header showed
    a broken image for a full release. Nothing caught it: the monogram test regexes `d="..."`
    out of the file and counts paths, which a file no browser will parse satisfies perfectly.

    That is the whole lesson. A structural assertion on an asset is only worth anything if the
    asset is also checked for being *loadable*, so this parses both files for real. The regex
    checks above stay, because path count cannot tell you the browser will render the result.
    """
    for path in (LOGO, FAVICON):
        try:
            # noqa is honest here: this parses two static SVG files committed in this repo,
            # never anything a caller supplies. S314 warns about untrusted input, and entity
            # expansion is not a concern for a 1.5KB file whose bytes are in version control.
            ET.parse(path)  # noqa: S314
        except ET.ParseError as exc:
            pytest.fail(f"{path.name} is not well-formed XML and will not render: {exc}")


def test_the_header_mark_and_the_favicon_are_the_same_drawing() -> None:
    """Two files holding the same mark will drift unless something says they must match.

    `mkdocs.yml` points `logo:` and `favicon:` at two separate files. Nothing at runtime
    compares them, so a colour or geometry change applied to one and not the other is
    invisible until someone notices the header and the tab disagree.
    """
    logo = LOGO.read_text(encoding="utf-8")
    favicon = FAVICON.read_text(encoding="utf-8")

    def geometry(text: str) -> set[str]:
        return set(re.findall(r"<(?:circle|path)\b[^>]*", text))

    assert geometry(logo) == geometry(favicon), (
        "logo.svg and favicon.svg no longer draw the same mark; they must be identical "
        "apart from their comments"
    )
    logo_colours = set(re.findall(r"#[0-9A-Fa-f]{6}", logo))
    favicon_colours = set(re.findall(r"#[0-9A-Fa-f]{6}", favicon))
    assert logo_colours == favicon_colours, (
        f"palette differs: logo has {sorted(logo_colours)}, favicon has {sorted(favicon_colours)}"
    )


def test_the_monogram_is_legible_at_header_size() -> None:
    """The header logo renders at ~19px, and that is the size it has to read at.

    The first version of this mark came verbatim from the brand style guide, whose own note
    claims it holds "visible detail" at 16px. Measured on the built site it does not: the
    swash crossbar hooks down at both ends and the terminal flick reads as a dot, so at 19px
    on the black navbar the mark reads as a **question mark**. Nobody caught it for a whole
    review cycle because the 512px render looks correct.

    `mkdocs.yml` sets the header `primary: black` in *both* schemes, so the mark always sits
    on black.

    What this can and cannot do: it cannot prove a mark is legible, that is a visual
    judgement, and the only honest check is rendering it at 19px and looking. What it does
    catch is the specific structural cause — a crossbar that overhangs the stem on one side
    only (a hook) or a stem that stops short of the baseline (a detached dot). It does so by
    requiring the crossbar and the stem to be separate subpaths, which is why a single
    continuous swash is rejected: in one stroke you cannot guarantee a symmetric crossbar,
    which is precisely how the guide's mark went wrong.
    """
    svg = LOGO.read_text(encoding="utf-8")
    paths = re.findall(r'\sd="([^"]+)"', svg)
    assert len(paths) >= 3, (
        f"the monogram should be a crossbar, a stem and a terminal; found {len(paths)} "
        "path(s). A single continuous swash cannot guarantee a symmetric crossbar, which "
        "is how the style guide's mark read as a question mark at header size."
    )

    numbers = [[float(n) for n in re.findall(r"-?\d*\.?\d+", p)] for p in paths]
    spans = [(max(n[0::2]) - min(n[0::2]), n) for n in numbers]

    # The crossbar is the widest element. If it is not, there is no T.
    crossbar_w, crossbar = max(spans, key=lambda t: t[0])
    stem = min(spans, key=lambda t: t[0])[1]

    stem_cx = (min(stem[0::2]) + max(stem[0::2])) / 2
    bar_left, bar_right = min(crossbar[0::2]), max(crossbar[0::2])
    overhang_left = stem_cx - bar_left
    overhang_right = bar_right - stem_cx

    # Both sides. A one-sided overhang is a hook, which is exactly what made the guide's
    # mark read as a question mark rather than a T.
    assert overhang_left > 0 and overhang_right > 0, (
        f"the crossbar (x {bar_left}-{bar_right}) does not overhang the stem (x centre "
        f"{stem_cx}) on both sides: {overhang_left} / {overhang_right}"
    )
    assert min(overhang_left, overhang_right) > 0.12 * crossbar_w, (
        "the crossbar overhangs the stem by only "
        f"{min(overhang_left, overhang_right) / crossbar_w:.0%} of its width; at 19px the "
        "crossbar disappears and only the stem survives"
    )

    # The stem must reach the baseline rather than stopping short and reading as a dot.
    baseline = max(max(n[1::2]) for n in numbers)
    stem_bottom = max(stem[1::2])
    assert baseline - stem_bottom < 12, (
        f"the stem ends {baseline - stem_bottom:.0f} units above the lowest point of the "
        "mark, which reads as a separate dot"
    )
