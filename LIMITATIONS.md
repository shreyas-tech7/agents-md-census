# Limitations

Read these before you quote a number.

1. **The sample is stratified, not proportional.** Each of the 72 strata gets the same number of repos. Popular repos (1,000 stars or more) make up a third of the sample but a tiny share of GitHub. The headline numbers describe this sample. Use the breakdowns by star band to see how much stars matter.
2. **The sample still leans toward visible repos.** Search only returns repos with at least 10 stars here, and its ranking inside a stratum is "best match". A random page helps but does not remove the lean.
3. **Fixed paths miss files.** The proxy in the build session blocked tree calls, so the collector asks for nine fixed paths. It misses `.cursor/rules/` folders, nested `SKILL.md` files, instruction files in subfolders, other names such as `.windsurfrules`, and files on branches other than the default.
4. **Drift checks root manifests only.** Monorepos often keep their scripts in subfolders. Commands run with `cd`, `-C` or workspace flags are counted as unverifiable, not as drift.
5. **Other ecosystems are not covered.** Commands come from `package.json` scripts, `Makefile` targets and `[tool.poe.tasks]` in `pyproject.toml`. Cargo, Go, Gradle, Maven, Rake, just, Taskfile and `uv run` commands are not checked.
6. **The detector misses some drift.** It reads only code spans, blocks and `$ ` lines. It skipped PowerShell prompts and commands quoted inside `bash -c "..."` in the held-out set. It treats any Makefile with a pattern rule as open, which hides real drift.
7. **Drift is not breakage.** A drifted command names a script that the root manifest lacks. The script may live in a CI file, a shell alias or an old branch. And a command that exists can still be wrong.
8. **Command intervals assume independence.** Commands cluster inside files and files cluster inside repos. The Wilson interval for "checkable commands that drift" is narrower than it should be.
9. **Section detection uses heading keywords.** A file can cover testing in prose under another heading. Section shares are lower bounds.
10. **The detector check uses synthetic snippets.** The snippets were written to cover known cases, so their precision and recall may be higher than on real files. The held-out set from a separate agent is a harder check, and it is small.
11. **One point in time.** The cache holds one collection date. Files change daily.
12. **No human has checked the labels yet.** Both label sets came from AI agents.
