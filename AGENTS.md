# Web-view working agreement

Communicate with the user in Portuguese. Write repository documentation, issue
content, and pull request text in clear, natural English. Read `CLAUDE.md` for
the project conventions and apply the `dev-quality` skill before writing code.
The user's instructions take precedence when a convention conflicts with them.

## Issue workflow

- Work on one issue at a time. Use a separate branch or worktree based on the
  current `main` and preserve existing work.
- Keep commits small and grouped by concern. Only create a commit when the user
  has authorized committing the current work; do not infer authorization from
  the preference for granular commits alone.
- Open a pull request for the user to review and show it in the user's existing
  work-profile Chrome window through CDP. Do not merge it automatically. Wait
  for the user to merge or explicitly request a merge.
- Keep the original PR description as the initial description of the change.
  Record subsequent corrections and their validation as PR comments so the
  sequence remains visible. Do not rewrite the description to add corrections.
- When validation finds a defect in the current PR, correct it in that PR when
  appropriate. Track unrelated defects in separate issues after checking for
  duplicates; do not expand the implementation scope without authorization.

## Independent headed validation

- Before presenting an implementation as ready for review, test it with a fresh,
  independent Codex session that reads the installed web-view skill and a
  concrete test scenario. Give the session the intended behavior and success
  criteria without supplying implementation details that would bias its check.
- Do not force a successful path by supplying the exact commands, selectors,
  fixes, or workarounds an agent should discover. Give it the task, necessary
  fixture access, safety boundaries, and expected outcome. Observe its choices;
  a guided reproduction can diagnose a failure but does not validate that a
  fresh session can independently complete the task.
- When an agent takes an unproductive or invalid path, determine whether the
  skill, CLI help, or implementation needs improvement. Make the appropriate
  changes and repeat the original scenario in a new session without embedding
  the discovered solution in its instructions. Report unresolved limitations.
- Run the relevant scenario in a visible Chrome session, using the updated local
  CLI and skill. Reproduce the original motivation where practical and safe;
  include success, failure, and timeout or ambiguity cases when applicable.
  Use a generic local fixture when the real scenario cannot be safely repeated.
- Preserve existing browser sessions, tabs, drafts, and application data. Use
  bounded waits and an overall deadline; monitor the session and interrupt it if
  it loops, stalls, or behaves unexpectedly. Report what was verified and any
  limitations. Correct defects in the open PR or create a separate issue when
  appropriate, then repeat independent validation for affected behavior.
- Run the project's automated tests and quality checks as well. Independent
  browser validation complements those checks; it does not replace them.

## Version and documentation

- Follow semantic versioning: increase the patch component for corrections and
  the minor component for backward-compatible public functionality, subject to
  the user's specific instructions. Increment the patch version for subsequent
  fixes to a version already installed for review, even while its PR is open.
- Review and update the version, `CHANGELOG.md`, README, bundled skill, and
  relevant CLI help whenever the change affects them. Keep examples aligned with
  actual behavior and record corrections in the changelog.
- Keep the user's installed CLI and skill current for testing, including changes
  from an open PR when requested. Verify the installed version and preserve the
  configured skill source and symlink. State when the installation tracks a PR
  branch rather than `main`; do not publish a release or tag without approval.

## Public repository and private context

- Never identify a private client, employer, project, organization, URL, account,
  data, or screenshot in public issues, PRs, comments, or fixtures. Generalize
  the motivating scenario while retaining enough detail to reproduce the problem
  before and after the change.
- For backlog issues, include the motivation, a reproducible generic example,
  acceptance criteria, and a reminder to review the skill, version, README, and
  relevant CLI help. Check for duplicates before creating an issue.
