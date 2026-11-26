# Human steps

Only Shreyas can do these. Do them in order. The release commit is `bc546808a5df57dbf699c5ba4e504da9e7cb2649` on branch `claude/build-agents-md-census`.

1. **Create the GitHub repo and push the work.** The build ran with a local stand-in for GitHub.
   - Create the repo `shreyas-tech7/agents-md-census` on https://github.com/new (no README, no license).
   - Then run:
     ```bash
     git clone /path/to/agents-md-census.bundle agents-md-census
     cd agents-md-census
     git remote set-url origin https://github.com/shreyas-tech7/agents-md-census.git
     git push origin --all
     ```
     The bundle is `portfolio/bundles/agents-md-census.bundle` in the project files.
2. **Check CI.** Open the Actions tab and confirm the `ci` workflow passes on the branch. It runs the same steps as `./init.sh`, which passed locally in the build session.
3. **Open a pull request** from `claude/build-agents-md-census` into `main`. Read the diff. Merge with a merge commit, so the release commit stays in the history of `main`.
4. **Tag the release candidate.**
   ```bash
   git fetch origin
   git tag -a v0.1.0-rc1 bc546808a5df57dbf699c5ba4e504da9e7cb2649 -m "Release candidate 1"
   git push origin v0.1.0-rc1
   ```
   Or create a pre-release with that tag on GitHub.
5. **Set the About box and topics.** Description: "A census of how public repos write instructions for AI coding agents, and how often those instructions drift from the real commands." Topics: the list in `docs/topics.txt`. The build could not reach the GitHub settings API.
6. **Upload the social preview.** Settings, General, Social preview: `docs/social-preview.png`.
7. **Do the human checks** listed in the README under "How this was built": read the drift labels in `eval/`, and spot check a few drift verdicts. Then update that README list.
8. **Run the secret scan once more:** `gitleaks git -v .`
9. **Decide whether `docs/build/BUILD_PROMPT.md` stays public.** It holds the full build prompt.
10. **Make the repo public.** Done 2026-11-26: the repo is public.
11. **Turn on GitHub Pages** (Settings, Pages, branch `main`, folder `/docs`) if you want the report online. It then lives at `docs/report/index.html` on the Pages site.
12. **Run the full census.** Create a fine-grained token that can only read public repositories, or rely on the Actions `GITHUB_TOKEN`. Never paste a token in chat. Then start the `full-run` workflow from the Actions tab. It collects in chunks, so run it again until its log shows every repo done. It commits the new dataset to the branch it ran on.
13. **Pin the repo** or list it in your profile README.

Not needed: PyPI publishing (the project has no package to publish) and model provider keys (the census calls no model).
