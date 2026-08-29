# Publish to GitHub

The repository is already initialized locally by the bootstrap workflow.

## Preferred: GitHub CLI

Install and authenticate the GitHub CLI, then run from the repository root:

```bash
gh auth login
gh repo create henslewm/universal-ai-project-template --private --source . --remote origin --push
```

For a generated project, replace the repository name.

## Make this a GitHub template repository

After publishing:

1. Open the repository on GitHub.
2. Open **Settings**.
3. In **General**, enable **Template repository**.
4. Future projects can use **Use this template** and start with a clean unrelated history.

## Create a project directly from the template

```bash
gh repo create henslewm/new-project --private --template henslewm/universal-ai-project-template --clone
```

Then tailor the cloned project in place:

```bash
cd new-project
python scripts/bootstrap_project.py --interactive --destination .
```

## Install the project bootstrap skill from GitHub

With a current GitHub CLI that supports agent skills:

```bash
gh skill install henslewm/universal-ai-project-template skills/complex-project-bootstrapper --agent codex --scope user
gh skill install henslewm/universal-ai-project-template skills/complex-project-bootstrapper --agent claude-code --scope user
```

Preview public skills before installing them.
