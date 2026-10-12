# Contributing to Horkos

These are the rules for everyone who works in this repository. They keep `main` working, stop us from overwriting each other, and make our history easy to follow.

## The three kinds of branches

| Branch | What it is | Can I push to it directly? |
| --- | --- | --- |
| `main` | The final, working version. This is what judges see. | **No, never.** |
| `dev` | Where finished work from everyone comes together. | **No.** Only through a pull request. |
| Your own branch (for example `frontend/oath-page`) | Where you do your work. | **Yes.** This is the only place you push. |

## Golden rules

1. **Never push to `main` or `dev`.** All work happens on your own branch.
2. **Always start from an up-to-date `dev`.** Pull before you start any task.
3. **Open a pull request with `dev` as the base branch.** Your branch is the one being merged in.
4. **Do not merge your own pull request.** The other teammate reviews it and merges it.
5. **`main` changes only at release time.** When `dev` is stable, we open one pull request from `dev` into `main`, and both of us agree before it is merged.

## Daily workflow

### 1. Start a new task

```bash
git checkout dev
git pull origin dev
git checkout -b frontend/oath-page
```

Check you are on your new branch with `git branch --show-current`. It must **not** print `main` or `dev`.

### 2. Do the work and commit often

```bash
git add frontend
git commit -m "Add oath page form and validation"
```

Add only the folder you worked in. Avoid `git add .` unless you have checked `git status` first.

### 3. Push your own branch

```bash
git push -u origin frontend/oath-page
```

### 4. Open a pull request

On GitHub, click **Compare & pull request** and set:

- **Base branch:** `dev`
- **Compare branch:** your branch

Write one or two lines on what changed. For screens, add a screenshot. Then ask your teammate to review. **Do not click Merge yourself.**

### 5. After it is merged

Update your local copy before your next task:

```bash
git checkout dev
git pull origin dev
```

## Branch names

Use `area/short-task-name`, in lowercase with dashes:

- `frontend/oath-page`
- `frontend/trust-board`
- `backend/paypal-hold`
- `docs/readme-update`

## Who works where

- **Frontend** (`frontend/`): the person building the screens.
- **Backend** (`backend/`): the person building the server, PayPal integration and AI.
- Please stay inside your own folder. If you need a change in the other person's area, ask them.

### Shared files: message first

Tell the other person **before** you change any of these:

- `README.md`
- `docs/api-contract.md`
- `.env.example`
- `LICENSE`
- `.gitignore`

If the API contract changes, both of us must agree. The screens and the server depend on it.

## Never commit these

- `.env` or any file with real keys or secrets (PayPal and OpenAI credentials)
- `.venv/`, `node_modules/`, `__pycache__/`, `.next/`
- Large or personal files, such as screenshots with other people's names or faces

Only `.env.example` (with empty or fake values) belongs in the repo. If a secret is ever committed by mistake, tell the team right away. Deleting the file is not enough, and the key must be replaced.

## Before you open a pull request

- [ ] I started from an up-to-date `dev`.
- [ ] The app runs (frontend) or the tests pass (backend).
- [ ] I only changed files in my own area, or I told the other person about shared files.
- [ ] There are no secrets or junk files in my changes (check `git status`).
- [ ] My pull request does one task, and the description says what it does.

## Commit messages

Write short messages in the present tense that say what the commit does:

- `Add Money Tracker status steps`
- `Fix sidebar highlight on Trust Board`
- `Connect payment hold to PayPal sandbox`

## If something goes wrong

- **Pushed to the wrong branch?** Tell your teammate before doing anything else. Do not force-push.
- **Merge conflict?** Pull `dev` into your branch, fix the marked sections, test, and commit. Ask your teammate if you are unsure.
- **Not sure about a command?** Ask first. It is easier to prevent a mistake than to repair one.

## Releasing to `main`

1. All planned work is merged into `dev`, and the full demo works from start to end.
2. One of us opens a pull request from `dev` into `main`.
3. The other person tests the demo and approves it.
4. We merge, then run through the README setup steps once on a clean copy of the repo.

## Recommended GitHub settings

In the repository, go to **Settings → Branches** and add protection rules for `main` and `dev`:

- Require a pull request before merging.
- Require at least one approval.

Some options depend on the plan and the repository's visibility. If a rule is not available, we follow it by habit.