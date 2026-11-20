# Prompt for Claude Cowork

Paste everything below the line into Claude Cowork after you have pushed the repo to GitHub (step 1 of `docs/HUMAN_STEPS.md`).

---

You are helping Shreyas finish the GitHub setup of his private repo `shreyas-tech7/agents-md-census`. Do not ask questions. Do not stop without a deliverable outcome. Write in plain, simple English.

Hard limits. Do not make the repo public. Do not publish any package. Do not enter, create or paste any token or key. Do not sign in for Shreyas. Do not pay for anything. Do not merge pull requests. If a step needs any of these, skip it and list it in your final message.

Do these browser steps. Each one is free and can be undone.

1. Open the repo's Actions page. Check that the `ci` workflow ran on the branch `claude/build-agents-md-census`. Write down whether it passed, and copy the first error line if it failed.
2. In the repo's About box (the gear next to "About"), set the description to: "A census of how public repos write instructions for AI coding agents, and how often those instructions drift from the real commands." Add the topics listed in `docs/topics.txt`.
3. In Settings, General, Social preview, upload `docs/social-preview.png` from the repo.
4. Open `docs/report/index.html` from the repo (download it or view it raw) and check that it shows tables with percentages and intervals.

Then finish with a prompt for the next Claude Code session, in a fenced block. It must hold:

- Context: the repo, the branch `claude/build-agents-md-census`, and that the release candidate is v0.1.0-rc1.
- What is complete: the steps above that you did, with what you saw.
- What is open: the CI result if it failed, and the steps you skipped.
- This launcher, word for word: "Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/build-agents-md-census. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback."
