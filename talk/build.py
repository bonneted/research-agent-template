"""Build the talk "Doing research with AI agents" (November 2026) on the KU Leuven template.

    uv run --with python-pptx --with cairosvg python talk/build.py TEMPLATE.pptx

TEMPLATE.pptx is `powerpoint/kuleuven-mech/kuleuven-mech.pptx` of the templates repository
(https://gitlab.kuleuven.be/r2d/researchers/damien/templates). Writes
`talk/doing-research-with-ai-agents.pptx` (out of git) and `talk/fig-inquiry.png`, from
`docs/figures/inquiry.svg`; export the PDF from the .pptx. Every slide has speaker notes.
"""

import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).parent
ROOT = HERE.parent
ACCENT, DARK, LIGHT, GOLD, WHITE, GREY = (RGBColor.from_string(c) for c in
                                          ("1D8DB0", "2F4D5D", "DCE7F0", "E7B037", "FFFFFF", "6B7C86"))  # fmt: skip
PALE = RGBColor.from_string("F8E7BE")
CODE = RGBColor.from_string("F4F6F8")
MONO = "Consolas"
REPO = "github.com/bonneted/research-knowledge-tree"


# --- slide bookkeeping -------------------------------------------------------------------------

def delete_slide(prs, slide) -> None:
    ids = prs.slides._sldIdLst
    for sld in list(ids):
        if prs.part.related_part(sld.rId) is slide.part:
            prs.part.drop_rel(sld.rId)
            ids.remove(sld)


def renumber(prs) -> None:
    """Name the slide parts slide1..N in order: python-pptx names a new slide by the count, which
    collides with a surviving part after deletions."""
    for i, s in enumerate(prs.slides):
        s.part.partname = PackURI(f"/ppt/slides/tmp{i + 1}.xml")
    for i, s in enumerate(prs.slides):
        s.part.partname = PackURI(f"/ppt/slides/slide{i + 1}.xml")


def move_to_end(prs, slide) -> None:
    ids = prs.slides._sldIdLst
    for sld in list(ids):
        if prs.part.related_part(sld.rId) is slide.part:
            ids.remove(sld)
            ids.append(sld)


def set_paragraphs(sh, lines: list[str]) -> None:
    """Replace a text frame's paragraphs, keeping the first run's formatting of each."""
    txbody = sh.text_frame._txBody
    paras = txbody.findall(qn("a:p"))
    while len(paras) < len(lines):
        clone = copy.deepcopy(paras[-1])
        paras[-1].addnext(clone)
        paras.append(clone)
    for p in paras[len(lines):]:
        txbody.remove(p)
    for p, line in zip(paras, lines, strict=False):
        runs = p.findall(qn("a:r"))
        if not runs:
            r = etree.SubElement(p, qn("a:r"))
            etree.SubElement(r, qn("a:t"))
            runs = [r]
        for extra in runs[1:]:
            p.remove(extra)
        for br in p.findall(qn("a:br")):
            p.remove(br)
        runs[0].find(qn("a:t")).text = line


def notes(slide, text_: str) -> None:
    slide.notes_slide.notes_text_frame.text = text_


# --- drawing -----------------------------------------------------------------------------------

def text(slide, x, y, w, h, paras, size=15, color=DARK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         italic=False, space=4, font="Arial"):  # fmt: skip
    """A text box. `paras`: a string, or a list of paragraphs, each a string or a list of
    (text, {"bold", "color", "italic", "size", "font"}) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    fill_text(tb.text_frame, paras, size, color, bold, align, anchor, italic, space, font)
    return tb


def fill_text(tf, paras, size=15, color=DARK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False,
              space=4, font="Arial"):  # fmt: skip
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    paras = [paras] if isinstance(paras, str) else paras
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        for chunk, style in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = chunk
            f = r.font
            f.name = style.get("font", font)
            f.size = Pt(style.get("size", size))
            f.bold = style.get("bold", bold)
            f.italic = style.get("italic", italic)
            f.color.rgb = style.get("color", color)
            if "link" in style:
                r.hyperlink.address = style["link"]


def box(slide, x, y, w, h, fill=LIGHT, kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, line=None):
    sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    sh.text_frame.text = ""
    return sh


def circle(slide, x, y, d, label, fill=ACCENT, color=WHITE):
    sh = box(slide, x, y, d, d, fill, kind=MSO_SHAPE.OVAL)
    fill_text(sh.text_frame, str(label), size=17, color=color, bold=True, align=PP_ALIGN.CENTER,
              anchor=MSO_ANCHOR.MIDDLE, space=0)  # fmt: skip
    sh.text_frame.margin_left = sh.text_frame.margin_right = 0
    return sh


def card(slide, x, y, w, h, title, body, fill=LIGHT, title_color=ACCENT, badge=None, badge_fill=ACCENT,
         title_size=17, body_size=14):  # fmt: skip
    box(slide, x, y, w, h, fill)
    tx = x + 0.2
    if badge is not None:
        circle(slide, x + 0.2, y + 0.2, 0.5, badge, badge_fill)
        tx = x + 0.82
    text(slide, tx, y + 0.17, x + w - tx - 0.15, 0.6, title, size=title_size, color=title_color, bold=True,
         anchor=MSO_ANCHOR.MIDDLE if badge is not None else MSO_ANCHOR.TOP)  # fmt: skip
    if body:
        top = 0.85 if badge is not None else 0.66
        text(slide, x + 0.2, y + top, w - 0.35, h - top - 0.1, body, size=body_size, space=8)


def banner(slide, y, paras, fill=ACCENT, color=WHITE, h=0.62, size=16):
    sh = box(slide, 0.63, y, 12.07, h, fill)
    fill_text(sh.text_frame, paras, size=size, color=color, bold=True, align=PP_ALIGN.CENTER,
              anchor=MSO_ANCHOR.MIDDLE, space=0)  # fmt: skip
    return sh


def code(slide, x, y, w, h, lines, size=12.5):
    """A code or file block: monospace lines on a pale panel."""
    box(slide, x, y, w, h, CODE, line=LIGHT)
    text(slide, x + 0.12, y + 0.1, w - 0.24, h - 0.2, lines, size=size, font=MONO, space=1)


def tag(slide, x, y, label="illustrative"):
    sh = box(slide, x, y, 1.45, 0.32, PALE, radius=0.5)
    fill_text(sh.text_frame, label, size=11, color=DARK, italic=True, align=PP_ALIGN.CENTER,
              anchor=MSO_ANCHOR.MIDDLE, space=0)  # fmt: skip


def arrow(slide, x1, y1, x2, y2, color=ACCENT, width=2.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    tail = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd"))
    tail.set("type", "triangle")
    return c


# --- the deck ----------------------------------------------------------------------------------

def content_slide(prs, footer_src, title: str, section: str):
    layout = next(lay for lay in prs.slide_layouts if lay.name == "Title and Content")
    s = prs.slides.add_slide(layout)
    for ph in list(s.placeholders):
        idx = ph.placeholder_format.idx
        if idx == 0:
            ph.text_frame.text = title
        elif idx == 13:
            ph.text_frame.text = section
        else:
            ph._element.getparent().remove(ph._element)
    for el in footer_src:
        s.shapes._spTree.append(copy.deepcopy(el))
    return s


def figure() -> Path:
    import cairosvg

    png = HERE / "fig-inquiry.png"
    cairosvg.svg2png(url=str(ROOT / "docs/figures/inquiry.svg"), write_to=str(png), output_width=2400)
    return png


def deck(template: Path, out: Path) -> None:
    prs = Presentation(str(template))
    title, cards, two, closing = list(prs.slides)
    by_name = {sh.name: sh for sh in cards.shapes}
    footer_src = [copy.deepcopy(by_name[n]._element) for n in ("Footer Placeholder 2", "Slide Number Placeholder 3")]
    delete_slide(prs, cards)
    delete_slide(prs, two)
    renumber(prs)

    # 1. Title
    shapes = {sh.name: sh for sh in title.shapes}
    set_paragraphs(shapes["TextBox 9"], ["Doing research with AI agents"])
    subtitles = sorted((sh for sh in title.shapes if sh.name == "Sous-titre 2"), key=lambda sh: sh.top)
    set_paragraphs(subtitles[0], ["Lab seminar"])
    head = shapes["TextBox 9"]
    text(title, head.left / 914400, (head.top + head.height) / 914400 + 0.05, 8.6, 0.6,
         "Rigour made affordable: a knowledge tree of inquiries", size=20, color=WHITE)
    set_paragraphs(subtitles[1], ["Damien Bonnet-Eymard"])
    shapes["TextBox 2"].width = Inches(4.0)
    set_paragraphs(shapes["TextBox 2"], ["November 2026"])
    notes(title, "Twenty minutes: what goes wrong when an agent does research, the rules that fix it, the "
                 "structure that holds them, and how to start tomorrow.")

    # 2. What goes wrong
    s = content_slide(prs, footer_src, "What happens when an agent does research unchecked?", "Motivation")
    failures = [("It cites what it never read",
                 ["Plausible references and values that do not exist.", "Walters & Wilder 2023"]),
                ("It tries forty variants, reports one",
                 ["The garden of forking paths, now nearly free.", "Gelman & Loken 2014"]),
                ("It agrees with you",
                 ["Models tend to tell users what they want to hear.", "Sharma et al. 2024"])]
    for k, (head, (body, source)) in enumerate(failures):
        card(s, 0.63 + k * 4.1, 1.75, 3.87, 2.3, head,
             [body, [(source, {"italic": True, "color": GREY, "size": 12})]],
             badge="!", badge_fill=GOLD, title_color=DARK, title_size=15)  # fmt: skip
    banner(s, 4.45, "Research has long known the cure: preregistration, verification, published negatives, "
                    "review. It could rarely afford all of it.", fill=DARK, h=0.8, size=16)  # fmt: skip
    notes(s, "Three failures an agent amplifies. Fabricated citations look exactly like real ones. Trying "
             "variants used to cost days; an agent tries forty in an afternoon and shows you the one that "
             "worked. And models are trained to please: they agree with the hypothesis you bring. None of "
             "this is new to science; the reproducibility literature has the countermeasures. What was "
             "missing was the time to apply them all.")

    # 3. The rules
    s = content_slide(prs, footer_src, "Agents make rigour affordable: twelve rules, four groups", "The rules")
    groups = [("Planning", "Fix the protocol before the runs: explore or confirm.", "testing what the data suggested"),
              ("Evidence", "Every number traces to a run, a derivation or a page.", "numbers nobody can rebuild"),
              ("Claims", "Publish the negatives and the denominator; cite the page you checked.",
               "forty variants, one reported; invented citations"),
              ("The tree", "The human confirms, after a blind review.", "the agent agreeing with you")]  # fmt: skip
    for k, (head, rule, fixes) in enumerate(groups):
        card(s, 0.63 + k * 3.09, 1.55, 2.86, 2.75, head,
             [rule, [("fixes: ", {"bold": True, "color": GOLD}), (fixes, {"italic": True})]],
             badge=k + 1, body_size=14)  # fmt: skip
    banner(s, 4.6, "12 rules, 5 of them fixed. The agent shows them to you at the start, and asks before you "
                    "set one aside.", h=0.7)  # fmt: skip
    text(s, 0.63, 5.4, 12.07, 0.4, "Grounded in the reproducibility literature: Ioannidis 2005; Munafò et al. "
         "2017; full map in docs/literature.md.", size=11, italic=True, color=GREY)  # fmt: skip
    notes(s, "Each rule answers a failure from the previous slide. Planning: a confirm phase fixes its "
             "analysis, stopping rule and the result that would refute it before it runs. Evidence: every "
             "number traces, with its unit and uncertainty. Claims: every finding says how many attempts it "
             "took, negatives included, and every citation was checked against its page. The tree: you, not "
             "the agent, promote a finding to confirmed, after a reviewer that never saw the conversation tried "
             "to break it. Five rules are fixed; the others can be set aside per project, with the reason "
             "written down. Most of this was too expensive to do by hand. An agent does it for minutes of compute.")

    # 4. Anatomy
    s = content_slide(prs, footer_src, "Anatomy of an agent: own the top layer", "Anatomy")
    layers = [("Your framework", "the memory",
               "Plain Markdown in your folder: AGENTS.md · .agents/skills/ · docs/wiki/ · inquiry.yaml", ACCENT),
              ("Harness", "the hands",
               "Reads and writes files, runs code, loops until done: Claude Code · Codex · Gemini CLI · OpenCode", DARK),
              ("LLM", "the brain",
               "Predicts the next token; knows nothing of your project: Claude · GPT · Gemini · Qwen", GREY)]  # fmt: skip
    for k, (name, role, body, colour) in enumerate(layers):
        y = 1.55 + k * 1.45
        b = box(s, 0.63, y, 2.3, 1.2, colour)
        fill_text(b.text_frame, [[(name, {"bold": True, "size": 17})], [(role, {"italic": True, "size": 13})]],
                  color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=2)  # fmt: skip
        text(s, 3.1, y, 5.6, 1.2, body, size=14, anchor=MSO_ANCHOR.MIDDLE)
    card(s, 9.0, 1.55, 3.7, 4.1, "Own the top layer",
         ["Models and harnesses change every few months, and so do the leaders.",
          "Keep what you build in plain Markdown in your folder: switch model or harness, keep your knowledge.",
          "AGENTS.md is read by most harnesses; Claude Code reads it through CLAUDE.md."])  # fmt: skip
    notes(s, "Three layers. The model predicts tokens and knows nothing of your project. The harness gives it "
             "hands: files, code, loops. The top layer is yours: Markdown instructions, skills and the wiki. "
             "It is the only layer that stays when the others change, so that is where the work goes.")

    # 5. Inside an inquiry
    s = content_slide(prs, footer_src, "One folder, one question: sources, wiki, code", "An inquiry")
    s.shapes.add_picture(str(figure()), Inches(1.05), Inches(1.4), width=Inches(11.2))
    banner(s, 5.6, "Sources are digested into the wiki, code changes update it, and the agent reads index.md "
                   "first and cites the notes it used.", h=0.75)  # fmt: skip
    notes(s, "An inquiry is one git repository answering one question. Sources: the bibliography and a pool "
             "of PDFs, code and data outside git. Code: one folder per phase. The wiki in the middle is what "
             "the inquiry knows: concepts, one digest per source, one note per phase, and the findings. The "
             "agent keeps it current in the same turn as the work, and reads its index before answering.")

    # 6. The wiki has two readers
    s = content_slide(prs, footer_src, "The wiki has two readers", "An inquiry")
    card(s, 0.63, 1.55, 3.9, 2.55, "You, in Obsidian",
         ["Browse from index.md, follow the links", "The graph: how sources and concepts connect",
          "“What did we take from X?” in seconds"], body_size=13)  # fmt: skip
    card(s, 0.63, 4.25, 3.9, 2.55, "The agent, as context",
         ["Reads index.md before answering", "Lands on the 2–3 right notes, not 40 PDFs",
          "Cites the notes, so you can check"], body_size=13)  # fmt: skip
    code(s, 4.8, 1.55, 7.9, 3.7, [
        "# Kooijman et al. (2011): a bicycle stable",
        "#   without gyroscopic or caster effects",
        "",
        "[@kooijman2011bicycle]. A purpose-built bicycle",
        "with neither effect still balances itself.",
        "",
        "## What we take",
        "- **Neither effect is necessary.**",
        "  → [gyroscopic](../concepts/gyroscopic.md)",
        "",
        "## What we don't take",
        "Their prototype's mass layout, for now."], size=13)  # fmt: skip
    tag(s, 11.15, 1.65)
    text(s, 4.8, 5.4, 7.9, 1.2, "One note per source or concept. A digest is a selection, not a summary: what "
         "the inquiry uses or rejects, with a link to where.", size=14, italic=True)  # fmt: skip
    notes(s, "The same files serve two readers. You browse them in Obsidian. The agent reads the index first "
             "and lands on two or three notes instead of forty PDFs, and cites them, so its answers can be "
             "checked. A digest is a selection: what this inquiry takes from the paper and what it leaves. "
             "The example is illustrative; the paper is real (Kooijman et al., Science, 2011).")

    # 7. The tree
    s = content_slide(prs, footer_src, "When a question is too broad, it grows a tree", "The tree")
    code(s, 0.63, 1.55, 6.6, 3.55, [
        "bicycle/            why does a moving bicycle",
        "│                   stay upright?",
        "└── inquiries/",
        "    ├── benchmark-model/",
        "    │   └── inquiries/speed-sweep/",
        "    ├── gyroscopic/",
        "    └── trail/"], size=14)  # fmt: skip
    steps = [("Zoom in", ("“Spawn a sub-inquiry for the gyroscopic effect”: a child repository with its own "
                         "question, under its parent.")),
             ("Zoom out", ("Adopt an existing repository under a broader question; merging two is a new root "
                          "and two adopts.")),
             ("Knowledge flows", "Down by link, up by findings, one level at a time; never sideways.")]  # fmt: skip
    for k, (head, body) in enumerate(steps):
        card(s, 7.5, 1.55 + k * 1.2, 5.2, 1.08, head, None, title_size=15)
        text(s, 9.6, 1.6 + k * 1.2, 3.05, 1.0, body, size=12.5, anchor=MSO_ANCHOR.MIDDLE)
    banner(s, 5.35, "Every index routes to its children, the open questions and what is out of scope: asked a "
                    "broad question, the agent descends one index at a time.", h=0.8, size=15)  # fmt: skip
    notes(s, "Start with one inquiry. When the question proves too broad, it spawns sub-inquiries for its "
             "parts; when two projects turn out to answer parts of a bigger question, a new root adopts them. "
             "A child inherits its parent's rules and may only tighten them. Knowledge goes up as findings, "
             "restated in the parent's terms, one level at a time. Siblings never link to each other: what "
             "two branches share lives at their common ancestor. And the tree never strengthens a claim: a "
             "synthesis is no stronger than the weakest finding it rests on.")

    # 8. What it looks like
    s = content_slide(prs, footer_src, "What it looks like", "Example")
    text(s, 0.63, 1.35, 5.9, 0.4, "docs/wiki/index.md, at the root", size=13, bold=True, color=ACCENT)
    code(s, 0.63, 1.75, 5.9, 3.75, [
        "## Sub-inquiries",
        "- [gyroscopic](…/index.md): how much does",
        "  wheel spin contribute? Active.",
        "  Dive here for: wheel spin, precession.",
        "- [trail](…/index.md): …",
        "",
        "### Open",
        "- How much does the rider's steering",
        "  contribute? (no inquiry yet)"], size=12.5)  # fmt: skip
    text(s, 6.8, 1.35, 5.9, 0.4, "docs/findings/…, at the root", size=13, bold=True, color=ACCENT)
    code(s, 6.8, 1.75, 5.9, 3.75, [
        "status: hint      # its children are hints",
        "tried: 3          # explanations tested",
        "evidence:",
        "  - kind: sub-inquiry",
        "    finding: …/gyroscopic/blob/8be41d0/…",
        "    status: hint",
        "",
        "# Neither wheel spin nor trail alone",
        "# keeps the benchmark bicycle upright",
        "Scope: the model only; not yet validated."], size=12.5)  # fmt: skip
    tag(s, 11.25, 1.38)
    banner(s, 5.75, "rkt check verifies what a machine can tell: links, routes, the denominator, no parent "
                    "stronger than its children.", h=0.7, size=15)  # fmt: skip
    notes(s, "Two files from the root of the bicycle tree. The index routes to each child and lists the "
             "question still open. The finding is a synthesis: it rests on two children's findings, both "
             "hints, so it stays a hint, says how many explanations were tried, and states its scope. The "
             "tool checks the mechanical parts; whether a baseline was competent stays the reviewer's "
             "judgement, and yours. Illustrative example.")

    # 9. Limits
    s = content_slide(prs, footer_src, "Limits", "Limits")
    limits = [("Errors get rarer, not impossible",
               ["The rules and the checks make invention harder.", "Check what matters against the source."]),
              ("Confidentiality",
               ["Files and prompts go to the model provider.",
                "Keep confidential material out of the inquiry; deny it in your harness's settings."]),
              ("Cost and lock-in",
               ["Subscriptions, quotas and leaders change.", "Plain Markdown keeps your work portable."])]
    for k, (head, body) in enumerate(limits):
        card(s, 0.63 + k * 4.1, 1.75, 3.87, 2.4, head, body, badge="!", badge_fill=GOLD, title_color=DARK,
             title_size=15)
    banner(s, 4.5, "You remain the author: of the questions, of the code you merge, and of every claim you sign.",
           fill=DARK, h=0.7)  # fmt: skip
    notes(s, "Three limits. The rules reduce errors, they do not abolish them. Whatever the agent reads is "
             "sent to the provider: check your institution's and your partners' rules, and keep confidential "
             "material outside the folder. And costs and leaders move: the Markdown stays yours.")

    # 10. Who decides
    s = content_slide(prs, footer_src, "The tools will change. Who decides should not.", "Perspective")
    text(s, 0.63, 1.55, 6.4, 3.9, [
        "Models and harnesses improve every few months: this kit may be obsolete within a year.",
        "What stays human is choosing the questions, where to point the tools, and judging what they return.",
        [("Rule 12 builds that in: ", {"bold": True, "color": ACCENT}),
         (("you approve every protocol and every confirmed finding. Staying in the loop is part of the method, "
          "not a wish."), {})]], size=17, space=16)  # fmt: skip
    card(s, 7.35, 1.55, 5.35, 3.0, "Use the agent to learn",
         ["Ask it to explain, then explain it back", "Derive by hand, then let it check you",
          "Read the digest, then the paper", "Let a grilling skill question your plan",
          "The wiki is written for you too: read it"], body_size=14)  # fmt: skip
    banner(s, 4.9, "A result nobody understands, remembers or communicates is wasted computation.", fill=DARK,
           h=0.7)  # fmt: skip
    notes(s, "The pace is real: weeks of work redone in an afternoon, and this kit itself may not survive the "
             "next generation of tools. What keeps its value is yours: the questions, the judgement, the "
             "understanding, and the people you tell. The rules keep you in the loop by design. And use the "
             "agent to learn, not only to produce.")

    # 11. Start tomorrow
    s = content_slide(prs, footer_src, "Start tomorrow: point your agent at the repo", "Start")
    code(s, 0.63, 1.55, 12.07, 1.5, [
        f"Install research-knowledge-tree from {REPO},",
        "make this folder an inquiry, and start it.",
        "My question is: …"], size=16)  # fmt: skip
    card(s, 0.63, 3.3, 7.0, 2.25, "Or by hand",
         [[("uv tool install \\", {"font": MONO, "size": 11})],
          [(f"  git+https://{REPO}@v2.0.0", {"font": MONO, "size": 11})],
          [("rkt init", {"font": MONO, "size": 12}), ("   then: “start the inquiry”", {})]], body_size=14)  # fmt: skip
    card(s, 7.9, 3.3, 4.8, 2.25, "You need",
         ["An agent: Claude Code, Codex, Gemini CLI…", "Obsidian, to read the wiki",
          "Zotero: recommended, not required"], body_size=14)  # fmt: skip
    banner(s, 5.8, "Start small: one inquiry, five papers, one question.", h=0.7)
    notes(s, "The easiest setup is to let your agent do it: give it the repository and your question. It "
             "installs the tool, makes the folder an inquiry, interviews you and shows you the rules. Start "
             "small; the tree grows when the question asks for it.")

    # 12. Closing: the author, then the three affiliations in evenly spaced columns, each a logo,
    # a name and a link. The template's EU funding notice is removed.
    pics = {sh.name: sh for sh in closing.shapes}
    for name in ("ZoneTexte 7", "Image 6", "Group 18"):
        pics[name]._element.getparent().remove(pics[name]._element)
    text(closing, 0.63, 1.5, 12.07, 1.0,
         [[("Damien Bonnet-Eymard", {"bold": True, "color": ACCENT, "size": 24})], "KU Leuven"],
         size=16, align=PP_ALIGN.CENTER)  # fmt: skip
    col_w, gap, x0, logo_y, logo_h = 3.6, 0.63, 0.63 + (12.07 - 3 * 3.6 - 2 * 0.63) / 2, 3.1, 1.2
    affiliations = [
        ("Reliable & Robust Design (R2D)", "https://iiw.kuleuven.be/onderzoek/R2D", "iiw.kuleuven.be/onderzoek/R2D"),
        ("Mecha(tro)nic System Dynamics", "https://www.mech.kuleuven.be/en/mod", "mech.kuleuven.be/en/mod"),
        ("Flanders Make", "https://www.flandersmake.be", "flandersmake.be")]  # fmt: skip
    for k, (name, url, shown) in enumerate(affiliations):
        cx = x0 + k * (col_w + gap) + col_w / 2
        if k == 0:
            logo = closing.shapes.add_picture(str(HERE / "logo-r2d.png"), 0, 0, height=Inches(logo_h * 0.75))
        elif k == 1:
            logo = text(closing, cx - col_w / 2, logo_y, col_w, logo_h, "LMSD", size=48, bold=True, color=ACCENT,
                        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)  # fmt: skip
        else:
            logo = pics["Picture 2"]
            logo.height, logo.width = Inches(logo_h), int(Inches(logo_h) * logo.width / logo.height)
        logo.left = int(Inches(cx) - logo.width / 2)
        logo.top = int(Inches(logo_y + logo_h / 2) - logo.height / 2)
        logo.click_action.hyperlink.address = url
        text(closing, cx - col_w / 2, logo_y + logo_h + 0.35, col_w, 0.9,
             [[(name, {"bold": True})], [(shown, {"color": ACCENT, "size": 13, "link": url})]],
             size=15, align=PP_ALIGN.CENTER)  # fmt: skip

    move_to_end(prs, closing)
    renumber(prs)
    prs.save(str(out))


if __name__ == "__main__":
    deck(Path(sys.argv[1]), HERE / "doing-research-with-ai-agents.pptx")
    print("wrote", HERE / "doing-research-with-ai-agents.pptx")
