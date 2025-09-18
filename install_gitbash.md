# Installation Guide: Git Bash and GitHub CLI (gh.exe)

## Goal
- Git Bash: a Linux-like shell on Windows, included with "Git for Windows".  
  It provides the familiar black terminal with `MINGW64:/c/Users/...` in the prompt.  
- GitHub CLI (gh.exe): a tool to manage GitHub repositories and workflows from the command line.

---

## 1. Install Git Bash (Git for Windows)

Download and install:
1. Go to: https://git-scm.com/download/win
2. Download the 64-bit Git for Windows installer (.exe).
3. Run the installer:
   - Enable **"Git Bash Here"** → allows you to right-click in Windows Explorer and open Git Bash directly.
   - For the PATH option: choose **“Git from Git Bash only”** (recommended).
   - Default editor: choose e.g. Visual Studio Code.
   - Leave other settings as default.
4. Finish the installation.

Verify:
Open **Git Bash** from the Start menu. You should see a prompt like:

MINGW64:/c/Users/yourName

Test git:
git --version

If you see a version (e.g. `git version 2.x.y`), Git Bash works correctly.

---

## 2. Install GitHub CLI (gh.exe)

Option A – via winget:
winget install --id GitHub.cli

Option B – via Chocolatey:
choco install gh -y

Option C – Manual installation:
1. Go to: https://github.com/cli/cli/releases
2. Download the **Windows MSI installer** (64-bit).
3. Run the installer; gh.exe will be added to your PATH automatically.

Verify:
gh --version

---

## 3. Authenticate with GitHub

Login to GitHub with your work or personal account:
gh auth login

- Choose **GitHub.com**  
- Choose authentication via browser or Personal Access Token (PAT)  
- With multiple accounts: use `gh auth switch` to switch  

---

## 4. Install Python (Windows)

Option A – via winget:
winget install --id Python.Python.3.12

Option B – via Microsoft Store:
1. Open the Microsoft Store app
2. Search for "Python 3.x" (latest stable release, e.g. 3.12)
3. Click Install

Option C – manual installer:
1. Go to: https://www.python.org/downloads/windows/
2. Download the latest Windows installer (64-bit).
3. Run the installer:
   - Make sure to check **“Add Python to PATH”** at the bottom.
   - Choose "Install Now" or "Customize installation" if you want more control.
4. Finish the installation.

Verify installation:
Open PowerShell, CMD, or Git Bash:
python --version
pip --version


## 5. Summary
- **Git Bash**: install from git-scm.com, this gives you the MINGW64 prompt.  
- **gh.exe (GitHub CLI)**: install via winget, choco or MSI.  
- **Python**: install via winget, Microsoft Store, or python.org installer.  
- Verify installations with:
  git --version
  gh --version
  python --version
  pip --version
