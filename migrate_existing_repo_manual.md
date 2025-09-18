# Migrate an Existing Local Git Repository to the GitHub Organization

## Goal
Take an existing local Git repository and publish it to the GitHub organization **holland-mechanics**.  
We will **replace** the old remote, push **all branches and tags**, and use **HTTPS** to avoid SSH key issues.

---

## Prerequisites
- You are in the repository **root** (the folder that contains the `.git/` directory).
- `git` and `gh` (GitHub CLI) are installed and available in `PATH`.
- You are authenticated with `gh` and have permission to create/push to the org:
  - `gh auth status`
  - If needed: `gh auth login`
- (Recommended) Use the Git Credential Manager for HTTPS:
  - `git config --global credential.helper manager`
  - `gh auth setup-git`

---

## Steps (replace <REPO_NAME> with your desired repo name)

1) Create the repository on GitHub under the organization
    ```
    gh repo create holland-mechanics/<REPO_NAME> --private
    ```

2) Point your local repository to the new **HTTPS** remote (replace any old remote)
    ```
    git remote remove origin 2> NUL
    git remote add origin https://github.com/Holland-Mechanics/<REPO_NAME>.git
    git remote -v
    ```

3) Push **all branches** and **all tags**
    ```
    git push --all origin
    git push --tags origin
    ```


Notes:
- This sends all branches and their commits.
- Tags (releases, version markers) are sent with the second command.
- Pull Request refs (`refs/pull/*`) are not needed on GitHub and will be rejected if pushed; the two commands above avoid them.


4) (Optional) Set the default branch to `main` and track it
    ```
    git branch -M main
    git push -u origin main
    ```

5) Verify online
- Open: `https://github.com/Holland-Mechanics/<REPO_NAME>`
- Check branches and tags; confirm the default branch if needed in **Settings → Branches**.

---

## Troubleshooting

- **Authentication prompts every time**  
  Ensure the credential manager is enabled:
  ```
  git config --global credential.helper manager
  gh auth setup-git
  ```

- **403 / permission denied**  
  Make sure your GitHub account has rights to create/push in the `holland-mechanics` organization and that your SSO/PAT is authorized for the org.

- **Default branch mismatch**  
  Rename your local default branch and push it as the primary branch:
  ```
  git branch -M main
  git push -u origin main
  ```

- **Submodules or Git LFS**  
  After migration, you may need to sync and initialize submodules and set up LFS if used:
  ```
  git submodule sync --recursive
  git submodule update --init --recursive
  git lfs install
  ```

---

## Summary
- Create repo on GitHub org.
- Replace local `origin` with the new **HTTPS** GitHub URL.
- Push **all branches** and **all tags**.
- (Optional) Set default branch to `main`.
