# Migrate a repository to GitHub/holland-mechanics

## Goal
Mirror-clone a repository from the local Gitea server and publish it to the GitHub organization `holland-mechanics` with full history.  

## Prerequisites
- git installed and in PATH
- gh.exe (GitHub CLI) installed and authenticated with work credentials
- We will **use HTTPS** for GitHub pushes

## Example repository
- Source (Gitea): `git@forge.dev.hollandmechanics.com:bask185/yourRepoName.git`
- Target (GitHub): `https://github.com/Holland-Mechanics/yourRepoName.git`

## Steps

1) Mirror-clone from the local Gitea server
```
git clone --mirror git@forge.dev.hollandmechanics.com:bask185/yourRepoName.git ./mirrors/yourRepoName.git
```

2) Create the empty repository on GitHub (private)
```
gh repo create holland-mechanics/yourRepoName --private
```

3) Configure HTTPS credentials for Git (prevents the credential-manager-core warning)
```
git config --global credential.helper manager
```
```
gh auth setup-git
```

4) Add a **HTTPS** remote to the mirror (avoids SSH key prompts)
```
cd ./mirrors/yourRepoName.git
```
```
git remote remove github 2> NUL
```
```
git remote add github https://github.com/Holland-Mechanics/yourRepoName.git
```
```
git remote -v
```

5) Push branches and tags only (avoids refs/pull/* rejects)
```
git push --all github
```
```
git push --tags github
```

6) Verify on GitHub
- Open: https://github.com/Holland-Mechanics/yourRepoName
- Check branches, tags, default branch

## Notes
- Using HTTPS means Git Credential Manager will cache your token after the first push.
- The `--all` + `--tags` push transfers everything you need for code history. GitHub will manage PR refs itself.
- For other repositories, replace `yourRepoName` with the repo name and repeat the same sequence.
