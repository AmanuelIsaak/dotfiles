---
name: lecture-notes
description: Use when summarizing university lecture PDFs, preparing for a class, creating exam-oriented study notes, or turning an assignment brief into an Obsidian workspace in the Business Information Technology vault.
---

# Lecture & Assignment Note Processing

Convert course PDFs (lecture slides, assignments) into structured Obsidian study notes for the user's BSc Business Information Technology vault at `~/Documents/Dashboard/01 Business Information Technology/`.

## Vault conventions

- Structure: `<Nth Semester>/<Module Name>/` — each module folder has a `<Module Name>.md` module hub at its root.
- Store authored lecture notes in `Notes/`, source teaching files in `Materials/`, practice work in `Exercises/`, and graded or exam-related work in `Assessments/`. Create only folders that receive content.
- Semester overviews: `_0X Semester.md` in each semester folder.
- Degree overview: `00 Curriculum/_BIT Curriculum Overview.md`.
- Frontmatter style: `created`, `updated` (YYYY-MM-DD), `course: Business Information Technology (BSc)`, `semester` (number), `unread` (bool). Use Obsidian wikilinks (`[[...]]`) and callouts (`> [!abstract]`, `> [!warning]`, `> [!success]-`).

## Extracting PDF text

1. Check for the venv: `/tmp/pdfenv/bin/python -c "import pypdf"`.
2. If missing, create it: `python3 -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install --quiet pypdf` (Homebrew Python is externally managed — never `pip install --user`).
3. Extract all pages:
   ```
   /tmp/pdfenv/bin/python -c "
   from pypdf import PdfReader
   r = PdfReader('<path>')
   print('PAGES:', len(r.pages))
   for i, p in enumerate(r.pages):
       print(f'--- page {i+1} ---')
       print(p.extract_text())
   "
   ```
4. For long PDFs, extract in chunks using `head_lines`/page ranges rather than truncating silently.
5. If a page's content is mostly a diagram (extraction returns fragments), note this in the output note and ask the user about it rather than guessing.

## Processing lecture slides

Use the template at `00 Curriculum/Templates/Lecture Note Template.md` in the vault. Create the note in the module's `Notes/` folder, named after the topic (e.g., `Block02 Strategy.md` for `Materials/Block02_Strategy_HS2025.pdf`). Set `source` to an Obsidian link that resolves to the source file; do not duplicate or move the source unless organization was also requested.

Fill in every section:

1. **Learning objectives** — copy verbatim from the slides (they define exam scope).
2. **Key concepts** — precise definitions and frameworks. The final exam is closed-book, so state things exactly, not vaguely.
3. **How it connects** — link to previous block notes and the enterprise architecture "house" model (Strategy → Business Architecture → IT Architecture: Processes / Applications / Data / Infrastructure) where relevant.
4. **Exam flags** — anything the slides emphasize, repeat, or frame as "key questions".
5. **Self-quiz** — 5–10 retrieval questions (mix of recall and application), answers in a collapsed `> [!success]- Answers` callout.
6. **To-do** — include only actions and deadlines supported by the source material. Never carry a reminder, bonus rule, or deadline from one module into another.

After writing the note, add a link to it under the `## Notes` section of the module note (`<Module Name>.md`), creating the section if needed.

## Processing assignments

Use `00 Curriculum/Templates/Assignment Note Template.md`. Create the note in `Assessments/` beside the assignment source when practical. Break the task into concrete checkboxes, capture requirements/grading criteria/due date, and link the relevant lecture notes. Do not write the assignment answer for the user unless they ask — the note is a workspace, not a solution.

## Style rules

- Be exam-oriented, not encyclopedic. Prefer tables and short bullets over prose.
- Flag uncertainty: if slide text is garbled or a figure could not be read, say so in the note.
- Never fabricate slide content, page references, or deadlines.
- Keep the PDF as archive; the note is the study artifact.
- Every created or modified Markdown note must follow vault rules: frontmatter first, no duplicate `# Title`, and `unread: true`.
