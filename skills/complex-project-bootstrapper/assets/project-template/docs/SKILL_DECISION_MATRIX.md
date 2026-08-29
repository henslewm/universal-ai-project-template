# Skill Decision Matrix

## Use an existing skill when

- The workflow is common and a trusted maintained skill already covers it.
- The skill's source, permissions, scripts, and connector dependencies have been reviewed.
- The workflow is stable enough that reuse saves time without hiding important judgment.

## Create a custom skill when

- The workflow repeats.
- Inputs and outputs are concrete.
- Project-specific rules or source boundaries matter.
- Scripts or validation reduce error.
- A consistent checklist is more important than open-ended creativity.

## Do not create a skill when

- The request is one-off or trivial.
- The procedure changes every time.
- The real need is better project instructions, a template, a connector, or a script.
- The skill would merely restate generic good practice.

## Discovery and installation

- ChatGPT/Codex: inspect available skills with the Skills interface or Codex skill commands; use the skill creator for a custom workflow.
- Codex/Claude Code: current GitHub CLI versions can search, preview, and install public `SKILL.md` packages. Review before installation.
- Project-scoped locations:
  - Codex: `.agents/skills/<name>/SKILL.md`
  - Claude Code: `.claude/skills/<name>/SKILL.md`

## Baseline categories

Enable only when relevant:

- Project planning / execution plans
- Official documentation lookup
- GitHub CI diagnosis
- PDF, DOCX, spreadsheet, presentation, or image deliverables
- Domain research and source-ledger workflows
- Repetitive project-specific intake, review, filing, report, or handoff workflows
