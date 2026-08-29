# Start Here

Choose the path that matches where you are working.

## A. Codex or Claude Code

1. Clone or unzip the base template, or create a repository with GitHub **Use this template**.
2. Open a terminal at the repository root.
3. For a fresh GitHub-template repository, tailor it in place:

   ```bash
   python scripts/bootstrap_project.py --interactive --destination .
   ```

   To preserve the base template locally and create a separate project directory instead:

   ```bash
   python scripts/bootstrap_project.py --interactive --destination ../your-project-name
   ```

4. Open the tailored repository in Codex or Claude Code.
5. The client automatically discovers `AGENTS.md` or `CLAUDE.md`.
6. Run `python scripts/validate_project.py` before the first substantive commit.

## B. ChatGPT web Project

1. Create a new ChatGPT Project, preferably with project-only memory for sensitive or bounded work.
2. Paste `.chatgpt/PROJECT_INSTRUCTIONS.md` into Project settings.
3. Add the files listed in `.chatgpt/PROJECT_FILES.md`.
4. Connect GitHub. Add Google Drive, Gmail, Calendar, Contacts, or a legal/research source only when the project actually needs them.
5. Start with the prompt in `prompts/BOOTSTRAP_NEW_PROJECT.md`.

## C. Claude web Project

1. Create a Claude Project.
2. Paste `.claude-web/PROJECT_INSTRUCTIONS.md` into project instructions.
3. Add the GitHub repository through Claude's GitHub integration.
4. Add only the active control files listed in `.claude-web/PROJECT_KNOWLEDGE.md` if the full repo is not connected.
5. Start with `prompts/BOOTSTRAP_NEW_PROJECT.md`.

## D. Publish this prepared local repo to GitHub

See `docs/GITHUB_PUBLISH.md`. The default command is:

```bash
gh auth login
gh repo create henslewm/universal-ai-project-template --private --source . --remote origin --push
```

After publishing, mark it as a **Template repository** in GitHub Settings so future projects can use **Use this template**.
