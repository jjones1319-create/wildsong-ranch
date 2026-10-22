# Getting Wildsong Ranch onto your phone (plain-English guide)

**How it works:**
1. Claude Code builds the game in this folder on your PC.
2. Claude puts a copy on **GitHub**, a free website for storing code.
3. GitHub's free hosting, **GitHub Pages**, turns the game into a web address like `https://YOURNAME.github.io/wildsong-ranch/`.
4. You open that address on your phone and "add it to your Home Screen", so it opens full-screen like a normal app and works offline.
5. Every time Claude finishes a milestone and pushes it to GitHub, the game on your phone updates within a few minutes.

**Is GitHub OK for this?** Yes, it's a good choice:
- It's free for public projects.
- There's nothing to install on your phone.
- It works on both iPhone and Android.

The one catch: on a free account the project must be **public**. Anyone could see the code, and anyone with the link could play. That's normal for hobby games and is why everything in the game is original. Don't put personal information in the project.

---

## Part A: One-time setup on your Windows PC (about 20 minutes)

1. **Node.js** (the engine that builds the game)
   - Go to **https://nodejs.org/en/download**, choose the **LTS** version (24 or newer), Windows Installer (.msi), and run it.
   - Click Next through the installer and keep the defaults.
2. **Git** (saves versions of your project and sends them to GitHub)
   - Go to **https://git-scm.com/install/windows**, download and run it. Keep all the defaults.
3. **A GitHub account**
   - Go to **https://github.com** → Sign up. A free account is fine.
   - Remember your **username**. It becomes part of your game's web address.
4. **GitHub CLI** (lets Claude create the GitHub project for you; optional but easiest)
   - Open the **Start menu**, type **PowerShell**, and open it.
   - Paste this and press Enter: `winget install --id GitHub.cli --source winget`
   - Close PowerShell, open it again, then type `gh auth login` and press Enter.
   - Pick **GitHub.com → HTTPS → Yes (authenticate Git) → Login with a web browser**, then follow the browser steps.
5. **VS Code + Claude Code**
   - Install VS Code from **https://code.visualstudio.com** if you don't have it.
   - In VS Code, open the **Extensions** panel (the four-squares icon), search **Claude Code**, install it, and sign in.
6. **Restart your PC.** This makes sure everything is found.

If any step gives you trouble, just tell Claude Code: "Help me install [thing]". It can check what's missing and walk you through it.

## Part B: Start the build

Open `PROMPT.md` in this folder and follow it. In short:
1. Open this folder in VS Code.
2. Open Claude Code.
3. Paste the Kickoff prompt.

Claude will set everything up and give you your game's link.

## Part C: Put the game on your phone

**iPhone (Safari):**
1. Open the link Claude gave you in **Safari**.
2. Tap the **Share** button (the square with an arrow).
3. Tap **Add to Home Screen**. If you see **"Open as Web App"**, leave it switched on.
4. Tap **Add**.
5. Open the game from its **new icon**, not from Safari. It opens full-screen.

**Android (Chrome):**
1. Open the link in **Chrome**.
2. Tap **⋮** (top right), then **Install app**. If you see **Add to Home screen** instead, tap that.
3. Open the game from its new icon.

**Tips:**
- Always play from the **icon**. Your saves live inside the installed app, and Safari tabs keep a *separate* set of saves.
- Sound starts after your first tap (phones require that). On iPhone, check that the side switch isn't on silent.
- Vibration feedback only works on Android. iPhones don't allow it for web apps.

## Part D: Your saves and backups

- **Where saves live:** inside the game on your phone. They aren't on GitHub and they aren't uploaded anywhere.
- **Back up:** in the game, go to **Settings → Backup → Export save**, then save the file to Files, Google Drive or email. The game reminds you every week or so.
- **Move to a new phone, or from a Safari tab to the installed app:** export on one, then **Settings → Backup → Import** on the other.
- **Why bother backing up?**
  - Phones can clear website data when storage is low, or when a site hasn't been used in a while. Installed Home Screen apps are much safer from this.
  - Deleting the Home Screen icon deletes its saves.
  - A backup protects you from all of it.
- **Share a single monster:** in the **Monster Lab**, use **Export → Copy code** (or the QR code) and send it to a friend. They paste it into their Monster Lab.

## Part E: Getting updates

When Claude finishes a milestone, it "pushes" the update to GitHub, and GitHub rebuilds the site in about 1–3 minutes. Next time you open the game you'll see **"Update ready → Restart"**. Tap it; your saves are kept.

## Part F: If something goes wrong

| Problem | Try this |
|---|---|
| The link shows "404" | Wait 2–3 minutes after the first setup. If it's still 404, tell Claude: "GitHub Pages shows 404". The usual fix is GitHub repo **Settings → Pages → Source: GitHub Actions**. |
| A white or blank screen | Tell Claude: "the site is blank on my phone". It's usually a one-line setting (the "base path"). |
| The phone keeps showing an old version | Close the app fully (swipe it away), then reopen it. Wait for "Update ready". |
| No sound | Tap the screen once; check the silent switch or volume; check Settings → Sound in the game. |
| I lost my progress | Import your latest backup (Part D). |
| Claude is stuck or confused | Type `/clear` in Claude Code, paste the milestone prompt again, and describe what went wrong. |

## Part G: Good to know

- **Cost:** GitHub, GitHub Pages and these tools are free for this project. Claude Code needs your Claude account, and Claude will ask before anything that might cost money.
- **Private instead of public?** Paid GitHub plans can host from a private project. Even then, the *game website* itself is still public to anyone who has the link.
- **The real Monster Rancher on your phone:** Koei Tecmo's official *Monster Rancher 1 & 2 DX* is sold on the iPhone App Store, as well as on Switch and Steam. As of late 2026 it wasn't on Android outside Japan. This project is our own original game inspired by that series. It isn't a copy of it.
