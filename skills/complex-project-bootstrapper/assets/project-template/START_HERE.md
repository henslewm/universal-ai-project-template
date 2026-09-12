# Start Here

Choose the path that matches where you are working.

## A. Codex or Claude Code

1. Clone or unzip the base template, or create a repository with GitHub **Use this template**.
2. Open a terminal at the repository root.
3. Choose `software-hardware`, `family-law`, or `civil-rights-nc`. For an uninitialized GitHub-template repository, tailor it in place:

   ```bash
   python scripts/bootstrap_project.py --interactive --profile software-hardware --destination . --no-git
   ```

   To preserve the base template and create a separate project in a new/empty directory:

   ```bash
   python scripts/bootstrap_project.py --interactive --profile software-hardware --destination ../your-project-name --no-git
   ```

4. Add `--answers verified-intake.json` if recovered intake is available. Interactive mode reuses supplied values and asks only missing common/profile orientation fields. The generator writes `config/bootstrap.json` in `INTAKE` with autonomy off and `BOOTSTRAP_REVIEW.md` with readiness gaps.
5. Open the tailored repository; the client discovers `AGENTS.md` or `CLAUDE.md`. Complete the architecture package and approval flow in section D before autonomous substantive work.
6. Run `python scripts/validate_project.py` before completing material changes. A passing repository validator does not activate the project.

The generator refuses rebootstrap when a destination already has bootstrap state or initialized project configuration. Preserve existing records and evidence through a retrofit; revise and review an existing package instead of overwriting it or deleting approval state.

## B. ChatGPT web Project

1. Create a new ChatGPT Project, preferably with project-only memory for sensitive or bounded work.
2. Paste `.chatgpt/PROJECT_INSTRUCTIONS.md` into Project settings.
3. Add the files listed in `.chatgpt/PROJECT_FILES.md`.
4. Connect GitHub. Add Google Drive, Gmail, Calendar, Contacts, or a legal/research source only when the project actually needs them.
5. Start with the prompt in `prompts/BOOTSTRAP_NEW_PROJECT.md`.
6. Follow section D with a repository runtime. If no runtime can run the validator, prepare the bootstrap files and a runtime handoff; autonomy stays off.

## C. Claude web Project

1. Create a Claude Project.
2. Paste `.claude-web/PROJECT_INSTRUCTIONS.md` into project instructions.
3. Add the GitHub repository through Claude's GitHub integration.
4. Add only the active control files listed in `.claude-web/PROJECT_KNOWLEDGE.md` if the full repo is not connected.
5. Start with `prompts/BOOTSTRAP_NEW_PROJECT.md`.
6. Follow section D with a repository runtime. If no runtime can run the validator, prepare the bootstrap files and a runtime handoff; autonomy stays off.

## D. Review the architecture and record explicit approval

1. Follow `prompts/INTERACTIVE_BOOTSTRAP.md` and `BOOTSTRAP_PROTOCOL.md`. Complete architecture boundaries, milestones/dependencies, sources, risks, routing, workflow, reserved human actions, and domain orientation in `config/bootstrap.json`. Resolve all `unresolved` architecture blockers and align the charter, connector plan, skill plan, domain profile, and project configuration.
2. From the generated project's root, run `python scripts/bootstrap_gate.py review`. This revokes previous approval first, snapshots `config/project.json`, and computes SHA-256 hashes of `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`. Only a ready package becomes `AWAITING_APPROVAL`; failure leaves autonomy off.
3. Present `BOOTSTRAP_REVIEW.md` and the bound documents, including routine permissions, reserved actions, defaults, and fingerprint. Resolve revisions and rerun review when needed.
4. Only after explicit user authorization for the approval interaction, run `python scripts/bootstrap_gate.py activate`. It presents the exact package and asks for user identity plus `APPROVE <fingerprint>`. There is no noninteractive autoapprove option. Do not supply agent-invented approval; automated tests use disposable fixtures only.
5. Successful activation saves the receipt in `config/bootstrap.json`; the review remains the pre-approval proposal. Run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` to verify.

Run `--require-active` before autonomous substantive work in every session. The fingerprint includes domain, workflow, unresolved blockers, configuration, and document hashes alongside project/architecture fields, and validation checks the current files. Missing, invalid, or inactive state, stale bindings, or unavailable runtime means no autonomy; resume bootstrap/review or a runtime handoff. After activation, routine work within approved scope and existing permissions may proceed without repeated approval. Reserved actions and consequential external writes retain their explicit-authority requirements.

The local gate detects normal bypass and stale approvals; it does not authenticate humans or constrain actors who rewrite gate code or approval records. It does not configure providers or expand permissions. Canonical templates include snapshots of existing domain documents; detailed domain work remains assigned to #9/#10/#11.

## E. Publish this prepared local repo to GitHub

Publishing is separate from setup and activation and requires explicit authority. See `docs/GITHUB_PUBLISH.md`. For this template repository, the documented command is:

```bash
gh auth login
gh repo create henslewm/universal-ai-project-template --private --source . --remote origin --push
```

After publishing, mark it as a **Template repository** in GitHub Settings so future projects can use **Use this template**.
