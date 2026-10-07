# Universal AI Project Template

A starting kit for software and hardware projects that you build with AI helpers such as Claude Code, Codex, ChatGPT, Claude and Mistral. Your project's plan, decisions and progress live in files in the project folder (and on GitHub), so any AI can pick up where the last one stopped.

## What you need

- **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/)).
- **Git** ([git-scm.com](https://git-scm.com/downloads)).
- **Claude Code or Codex**, the AI that sets up and works on your project.
- Optional: the **GitHub CLI** (`gh`), if you want the project put on GitHub for you.

## Start a new project

Run these from this template's folder. If you are already inside a project made from it, skip to step 2.

**1. Create the project.**

```bash
python scripts/bootstrap_project.py --destination ../my-project
```

Answer the questions it asks. It asks whether hardware is involved: answer **y** for a hardware project, or **n** for software or a web app. It creates the folder, fills in your answers and sets up Git.

**2. Let the AI finish the setup.** Go into the new folder, open Claude Code (or Codex) there, and say:

> finish the bootstrap

It drafts the project plan (milestones, risks and the steps that need your sign-off), checks it, and shows it to you.

**3. Approve the plan.** When you agree with it, run this yourself in the project folder:

```bash
python scripts/bootstrap_gate.py activate
```

It shows the plan one last time and asks you to type an approval line. Until you do, the AI won't work on its own.

## Using ChatGPT, Claude or Mistral on the web

In the project folder, run the command for your service:

```bash
python scripts/web_setup.py --client chatgpt
python scripts/web_setup.py --client claude
python scripts/web_setup.py --client mistral
```

It puts the Project instructions on your clipboard and makes one zip of the files to upload, then tells you the three clicks to do.

## Every day after that

Open Claude Code (or Codex) in the project folder and ask for what you want. It reads where things stand and what's next from the project files, and writes back what it did.

## Put it on GitHub

Run `gh auth login` once, then add `--github` to step 1 to create a private GitHub repository automatically. Or see [docs/GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md).

## Learn more

- [START_HERE.md](START_HERE.md): the same steps, plus starting from GitHub's **Use this template** button.
- [docs/REFERENCE.md](docs/REFERENCE.md): what the template contains, every command's exit codes, and the folder map.
- [docs/PLATFORM_SETUP.md](docs/PLATFORM_SETUP.md) and [docs/WEBUI_SETUP.md](docs/WEBUI_SETUP.md): per-AI setup details.
- [BOOTSTRAP_PROTOCOL.md](BOOTSTRAP_PROTOCOL.md): how the approval step works and why.
- [WORK_PACKET_PROTOCOL.md](WORK_PACKET_PROTOCOL.md): handing bounded tasks to cheaper models.

Keep passwords and secrets out of the project files. Use a private repository for anything personal or confidential.
