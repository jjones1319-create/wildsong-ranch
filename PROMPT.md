# How to build Wildsong Ranch with Claude Code

This folder already contains everything Claude needs: the rules (`docs/GAME_DESIGN.md`), the content (`docs/CONTENT.md`), the build order (`docs/BUILD_PLAN.md`) and Claude's standing instructions (`CLAUDE.md`, which Claude Code reads automatically). Your job is to paste a prompt, test on your phone, and repeat.

**Before your first run:** do Part A of `docs/PHONE_AND_GITHUB_SETUP.md` (install Node.js, Git and the GitHub CLI, and make a GitHub account).

**Steps:**
1. Open VS Code → **File → Open Folder…** → pick this folder (`Monster Rancher`).
2. Open Claude Code (the Claude icon in the sidebar, or the Command Palette → "Claude Code").
3. Paste the **Kickoff prompt** below and press Enter. Answer its questions and approve its steps.
4. When it says M0 is done, open the link on your phone and follow its checklist.
5. For every milestone after that, start a **fresh chat** (type `/clear`, or open a new Claude Code tab) and paste the **Next milestone prompt**.

---

## Kickoff prompt (paste this once)

```
You're building Wildsong Ranch, an original monster-raising game I want to play on my phone. Everything you need is in this folder: CLAUDE.md (your rules), docs/BUILD_PLAN.md (the build order), docs/GAME_DESIGN.md (the rules of the game) and docs/CONTENT.md (all the monsters, attacks and items). I'm not a programmer, so explain things simply and tell me exactly what to click whenever you need me.

My setup: VS Code is already signed in to GitHub, and I've just installed Node.js.

1. Read CLAUDE.md, then read docs/BUILD_PLAN.md, docs/GAME_DESIGN.md and docs/CONTENT.md in full. (docs/RESEARCH_NOTES.md is background only.)
2. Check my tools by running node -v, npm -v, git --version and gh --version. I need Node 24 or newer and npm 11 or newer. If anything is missing or too old, give me step-by-step Windows instructions and wait. (If Node isn't found, I probably need to restart VS Code first.) If the GitHub CLI isn't installed, ask me before installing it, or use whichever other way of creating the repo is simplest for me.
3. Use these choices unless something blocks them: game title "Wildsong Ranch", a PUBLIC GitHub repo named wildsong-ranch, MIT license. Find my GitHub username yourself if you can; otherwise ask me. Then switch to plan mode and write a detailed task list for M0 and M1 into docs/BUILD_PLAN.md.
4. Build M0 exactly as the plan describes: set up the project, create the repo, push it, turn on GitHub Pages with the GitHub Actions workflow, and get the title screen (with the version number) live. If GitHub asks me to sign in or approve something, tell me exactly what I'll see and what to click.
5. When it's live, give me the link and the steps to add it to my phone's Home Screen. Then stop and wait for me to confirm it works on my phone before you start M1.

For the whole project, follow CLAUDE.md, especially the originality rules and the phone-first rules. Work one milestone at a time, run npm run verify before every commit, keep docs/PROGRESS.md up to date, and finish every milestone with a short "Try this on your phone" checklist.
```

## Next milestone prompt (paste for M1, M2, … M9; change the number)

```
Let's do milestone M1. Re-read CLAUDE.md, the M1 section of docs/BUILD_PLAN.md, and every docs/GAME_DESIGN.md and docs/CONTENT.md section it touches. Use plan mode first and add the detailed task list to BUILD_PLAN.md. Then build it with tests, run `npm run verify` until it passes, update docs/PROGRESS.md, commit as "M1: …", and push so the site redeploys. Confirm the deploy succeeded, give me a 5-minute checklist to try on my phone, and stop.
```

---

## Handy follow-up prompts

**Something's broken:**
```
Bug: [what you did] → [what happened] → [what you expected]. Phone: [iPhone/Android + browser, installed or not]. Please find the cause, add a test that reproduces it, fix it, run verify, push, and tell me what to check.
```

**It doesn't feel right:**
```
Feedback from playing: [e.g. "my monster gets exhausted too fast" / "battles feel too long" / "the drill animation is too slow"]. Suggest 2–3 ways to fix it (tuning numbers first, not formula changes), say which you recommend and why, then do it after I pick.
```

**Edit the game's content:**
```
I changed docs/CONTENT.md: [what changed, e.g. renamed a monster, new item]. Update src/data to match, keep saves compatible (add a migration if needed), run verify, push.
```

**Add a new monster:**
```
Add a new breed: [idea, e.g. "a sleepy cloud whale that's slow but very tanky"]. Design it to fit the niches and value bands in CONTENT/GAME_DESIGN (stats, grades, growth type, lifespan, guts rate, trait, 9 original techniques, art brief). Show me the design first; after I approve, add it to CONTENT.md and the game with tests.
```

**Rename the game:**
```
Rename the game from "Wildsong Ranch" to "[new name]" everywhere (title screen, manifest, README, CREDITS). Keep the repo name and URL unless I say otherwise.
```

**Check balance:**
```
Run the raising and battle balance sims and give me a plain-English summary: which monsters are too strong or weak, how long monsters live with good vs bad care, and how fights are going. Suggest tuning changes, but don't apply them until I say so.
```

**I'm worried about my save:**
```
Walk me through backing up my save on my phone and restoring it on another device, step by step.
```

## Tips
- **One milestone per chat** keeps Claude sharp. If a chat gets long, type `/compact`.
- If Claude goes down a wrong path twice, type `/clear` and paste the milestone prompt again with a note about what went wrong.
- Claude Code asks permission before running commands. Read the one-line description; "allow" is fine for `npm`, `git` and `gh` commands in this folder.
- Everything gets saved to GitHub. If something goes really wrong, Claude can roll back to the last milestone's commit.
