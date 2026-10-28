# CLAUDE.md

This is a fork of [naver-ai/TaleBrush](https://github.com/naver-ai/TaleBrush) (CHI 2022) that is being revived to run on current tooling. The work will be presented in a demo.

## Log every change in REVIVAL_LOG.md

Every change to this repo must be recorded in [REVIVAL_LOG.md](REVIVAL_LOG.md), in the same session as the change. The log is the source material for the presentation, so it should explain the work to an audience, not just list diffs.

- Add each change under **Changes** as a numbered `###` heading, with a **Why:** paragraph (what was broken or missing, and the root cause) and a **Fix:** paragraph (what changed, and why that approach was chosen over the alternatives).
- Include the exact error message when a change fixes a failure.
- Add a row to the **Timeline** table for each set of changes. The user makes the commits, so leave the commit column as `—` for them to fill in.
- Keep **How to run it now** and **Known open items** accurate. Update or remove entries that a change makes outdated.
- Record findings that didn't lead to a code change but affect the project, such as the model files that are no longer available.

## Working conventions

- The user makes all commits. Don't commit or push.
- [WORKPLAN_LLM_BACKEND.md](WORKPLAN_LLM_BACKEND.md) tracks the planned LLM backend. Mark items `[x]` as they're completed.
