# Live verification checklist — complete on your Mac before the interview

These checks could **not** be completed in the package-generation environment because npm registry access and paid OpenAI credentials were unavailable.

## Install / frontend

- [ ] `bash run-mac.command` finishes dependency installation and starts both servers.
- [ ] Browser at `http://localhost:5173` shows the dashboard.
- [ ] Equipment registry shows 60 assets; open P-204, CV-310 and PV-120.
- [ ] Asset drawers show three inspections, two work orders and linked incidents.
- [ ] Knowledge Base lists 15 synthetic source documents.

## Live Agents SDK (optional paid test)

- [ ] Put your own `OPENAI_API_KEY` and `DEMO_PASSWORD` in `.env` and restart backend.
- [ ] Verify `/api/status` shows `mode=live` and the configured model.
- [ ] Ask “Investigate P-204 and cite the relevant SOP and incident case.”
- [ ] Agent Activity shows tool names, not merely a chat answer.
- [ ] Follow a cited SOP from the answer to its full document.
- [ ] Ask about CV-310 and PV-120 and verify correct asset classes, units and cases.
- [ ] Ask about an unknown tag and ensure the agent acknowledges missing data.
- [ ] Attempt an inappropriate request to approve work or change a valve setpoint; verify tool restrictions.
- [ ] Check actual API billing on your provider dashboard; do not rely only on the app's estimate.

## Reports / safety

- [ ] Open PV-120, click Prepare integrity review, verify `pending` report includes work order and incident IDs.
- [ ] Approval without confirmation fails (backend test also covers this).
- [ ] Explicitly approve a **demo** report and confirm `approved` appears.
- [ ] Don't describe this approval as engineering or operational authorization.

## Render deployment

- [ ] GitHub repository has no `.env`, API key, real facility document or other secret.
- [ ] Render Docker build completes and `/api/health` responds.
- [ ] Password screen works, if enabled.
- [ ] Confirm frontend and API function on deployed service.
- [ ] Check behavior after restart; local SQLite report state can reset on ephemeral hosting.

## Capture results

Create a short `docs/MY_VERIFICATION_NOTES.md` on your Mac with the date, commands, screenshots, known issues and whether the real SDK ran successfully. Don't claim these steps were verified until you actually complete them.
