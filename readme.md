# GIT Manuals

Practical docs and scripts for setting up Git projects and migrating code to the GitHub organisation **holland-mechanics**.

## What’s in here?
This repo contains:
- **Manuals** (`*.md`) — step-by-step guides
- **Scripts** (`*.py`) — interactive helpers that run the commands from the manuals
- **Data** (`gitea_repos.json`) — list of repositories on the internal Gitea used by the migration script


## 1) Create User Credentials
The very first thing you need to do, is to surf to [www.github.com](github.com) and register an acount, using your Holland Mechanics E-mail acount. For acount name use: `<front_name> - <last_name>`, like `jan-smit`. After that get in touch with Bas or Nelson, they will invite you to the holland mechanics organisation and will grant you certain rights.

---

### 1.1) Additional required GitHub setup (2FA + PAT)

Before Git can access **private organisation repositories**, two things MUST be completed:

#### **1.1.1 — Enable Two-Factor Authentication**
GitHub requires 2FA for all Holland Mechanics organisation members.

Steps:
1. Go to **GitHub → Settings → Password and authentication**
2. Enable **Two-Factor Authentication**
3. Install an authenticator app (recommended)
4. Store your backup codes safely

### **1.1.2 — Create a Personal Access Token (PAT)**  
GitHub no longer allows password login for Git operations.  
A **PAT replaces your password** when using `git.exe`.

Create one:

1. Go to: https://github.com/settings/tokens?type=beta  
2. Click **Generate new token**
3. Choose **Fine-grained personal access token**
4. Select:
   - **Resource owner:** your user  
   - **Repository access:** *All repositories* (unless restricted)
5. Grant **Contents: Read and Write**
6. Click **Generate**
7. Copy the token and keep it safe  
   (You will need it **only once**, Git will store it securely.)

---

## 2) Install Git tools (Git Bash + GitHub CLI)
This manual explains about tools that you need to have in order to work with git.

git.exe itself is the only one that is mandatory

gh.exe is github's command line tool. It allows us to create a repo on github.com without having to open a browser. If you don'h have it or don't want to use it you can make repos directly via github.com. It is optional

Pyhton scripts can be used to automize some tasks, such as creating a git repo. Besides manuals there are also scripts to help migrate a project from forge to github, directly migrate a repo from your PC to github, to create a repository or to automate releases. It is optional

- Manual: [install_gitbash.md](./install_gitbash.md)

### **2.1 — Configure your identity in git.exe**
Run these commands in **Git Bash**:

```
git config --global user.name "your_user_name"
git config --global user.email "your_email@hollandmechanics.com"
```

### **2.2 — Ensure the Git Credential Manager is active**
On Windows this is normally already enabled, but enforce it with:

```
git config --global credential.helper manager
```

### **2.3 — Store your GitHub username**
This ensures Git never falls back to the wrong account:

```
git config --global credential.username "<github-username>"

```

Example:

```
git config --global credential.username "jan-smit"

```

### **2.4 — Store your PAT in the Git credential helper (without gh.exe)**
Replace `<github-username>` and `<PAT>`:

```
printf "protocol=https
host=github.com
username=<github-username>
password=<PAT>

" | git credential approve

```

Git will now authenticate against private organisation repos with HTTPS without prompting again.

To verify:

```

git credential fill <<EOF
protocol=https
host=github.com

EOF

```

You should see your GitHub username and the PAT.

---

## 3) Create a **new** repository on GitHub (from local folder)
For starting a fresh project and pushing it to the organisation. Can be done via a terminal or webbrowser

- Manual: [create_new_repo_manual.md](./create_new_repo_manual.md)  
- Script: [create_new_repo_script.py](./create_new_repo_script.py)

**What the script does**
- Initializes a new local repo
- Interactively asks which files/folders to add 
- Creates the GitHub repo under `holland-mechanics`
- Pushes the initial commit

---

## 4) Migrate an **existing local** repository to GitHub (replace old remote)
For a project you already have locally; keep full history (branches + tags).
Essentially you alter the remote and push the repo.

- Manual: [migrate_existing_repo_manual.md](./migrate_existing_repo_manual.md)  
- Script: [migrate_existing_repo_script.py](./migrate_existing_repo_script.py)

**What the script does**
- Creates the repo in the organisation (if missing)
- Replaces `origin` with the GitHub HTTPS remote
- Pushes **all branches** and **all tags**

---

## 5) Migrate a repo directly from Forge (Gitea) to GitHub
For copying a repo (with full history, branches and tags) from `forge.dev.hollandmechanics.com` into the org.  
Uses **HTTPS** to avoid SSH key issues and skips PR refs.

- Manual: [migrate_repo_manual.md](./migrate_repo_manual.md)  
- Script: [migrate_repo_script.py](./migrate_repo_script.py)  
- Data: [gitea_repos.json](./gitea_repos.json)

**What the script does**
- Lists repos from `gitea_repos.json`
- You pick one by name
- Mirror-clones from Forge, creates the GitHub repo, and pushes **branches + tags**

## 6) Release software

We release software using the github way of doing this. This can be done via the browsers and some manual actions or you can use `release_version_script.py` to help you in this.

- Manual: [release_version_manual.md](./migrate_repo_manual.md)  
- Script: [release_version_script.py](./migrate_repo_script.py)
