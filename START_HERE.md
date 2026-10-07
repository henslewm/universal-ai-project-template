# Start Here

The short version is in [README.md](README.md). This page adds the other ways in.

## A. From this template's folder (recommended)

1. Create the project and answer the questions. Answer **y** to "hardware?" for a hardware project, or **n** for software or a web app (the `web-ui` track):

   ```bash
   python scripts/bootstrap_project.py --destination ../your-project-name
   ```

   Git is set up for you. Add `--github` (after `gh auth login`) to also create a private GitHub repository, or `--no-git` to skip Git.
2. Go into the new folder, open Claude Code or Codex there, and say "finish the bootstrap". It completes the plan in section D and shows it to you.
3. When you agree, run `python scripts/bootstrap_gate.py activate` yourself and type the approval line it asks for.

## B. From GitHub's "Use this template" button

Create your repository with **Use this template**, clone it, and tailor it in place from its folder:

```bash
python scripts/bootstrap_project.py --destination .
```

Then continue with steps 2 and 3 of section A.

If you already have answers saved as JSON, add `--answers verified-intake.json`; only missing answers are asked. The generator refuses to re-bootstrap a folder that already has bootstrap state or an initialized project. Revise and re-review the existing plan instead of overwriting it.

## C. ChatGPT, Claude or Mistral on the web

Create the project with section A or B first; the web chats can't run the setup commands themselves. Then, in the project folder, run one of:

```bash
python scripts/web_setup.py --client chatgpt
python scripts/web_setup.py --client claude
python scripts/web_setup.py --client mistral
```

It copies the Project instructions to your clipboard (or names the file to paste from), zips the files to upload, and prints the steps. Connect GitHub to the web Project as well, so chats read the latest files. Add Drive, Gmail, Calendar or Contacts only when `CONNECTOR_PLAN.md` calls for them. Setup details per service: [docs/PLATFORM_SETUP.md](docs/PLATFORM_SETUP.md).

## D. What the AI completes, and what approval means

"Finish the bootstrap" has the AI follow `prompts/INTERACTIVE_BOOTSTRAP.md` and [BOOTSTRAP_PROTOCOL.md](BOOTSTRAP_PROTOCOL.md). It fills in `config/bootstrap.json`: architecture boundaries, milestones and their dependencies, sources, risks, routing, workflow, the actions reserved for you, and domain details. Then it runs `python scripts/bootstrap_gate.py review`, which writes `BOOTSTRAP_REVIEW.md` for you to read.

Only you run `python scripts/bootstrap_gate.py activate`. It shows the exact plan and asks for your name and `APPROVE <fingerprint>`; nothing approves on its own. The fingerprint covers the plan and the hashes of `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md` and `DOMAIN_PROFILE.md`, so changing any of them later withdraws the approval until you review and approve again.

Every session, the AI checks `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` before working on its own. After activation, routine work inside the approved scope goes ahead without asking each time; the actions reserved for you, and anything consequential outside the repository, still need your explicit say-so.

The gate catches ordinary bypasses and stale approvals. It does not authenticate people or stop someone who rewrites the gate code or the approval record, and it does not configure AI providers or widen permissions.

## E. Publish to GitHub

Publishing is separate from setup and approval. See [docs/GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md).
