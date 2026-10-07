# Web UI Setup Checklist

Run `python scripts/web_setup.py --client chatgpt` (or `claude`, `mistral`) from the project folder first. It zips the files to upload and puts the Project instructions on your clipboard.

## ChatGPT Project

- [ ] Create a dedicated Project.
- [ ] Use project-only memory for bounded or sensitive work when available.
- [ ] Paste the instructions (already on your clipboard after `web_setup.py --client chatgpt`).
- [ ] Upload the files inside `web-setup-chatgpt.zip`.
- [ ] Connect GitHub.
- [ ] Add Drive/Gmail/Calendar/Contacts only if selected in `CONNECTOR_PLAN.md`.
- [ ] Install the bootstrap skill if recurring project creation is desired.
- [ ] Pin or save the bootstrap, start-session, and end-session prompts.

## Claude Project

- [ ] Create a dedicated Project.
- [ ] Paste the instructions (already on your clipboard after `web_setup.py --client claude`).
- [ ] Add the GitHub repository through the integration.
- [ ] When the GitHub integration is unavailable, upload the files inside `web-setup-claude.zip`.
- [ ] Add Drive or other integrations only if selected.
- [ ] Start with the shared bootstrap or session prompt.

## Cross-model handoff

- [ ] All clients read the same branch.
- [ ] `HANDOFF_CURRENT.md` is current.
- [ ] `PROJECT_STATE.md` reflects verified reality.
- [ ] New decisions and sources are recorded.
- [ ] Validation passes before switching clients.
