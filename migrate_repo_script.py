#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea -> GitHub migration (HTTPS).
- Clone (mirror) from Gitea using your current credentials (e.g., bask185).
- Push via git.exe under a specific GitHub user (default: sebastiaan-knippels).
- No global/system writes; repo-local config only. Push uses inline -c overrides to defeat VS Code AskPass and global helpers.

JSON format (gitea_repos.json):
[
  {"name": "a51", "ssh": "git@forge.example.org/team/a51.git"},
  {"name": "xyz", "ssh": "git@forge.example.org/team/xyz.git"}
]

Requirements:
- git installed
- gh installed (only needed for repo creation and when using gh as credential helper)
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# ---------- Settings ----------
ALLOWED_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# ---------- Small utils ----------
def log(msg: str) -> None:
    print(msg, flush=True)

def run(cmd, *, cwd=None, check=True, env=None, echo=True):
    if echo:
        print(f"\n$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=check, env=env)

def run_quiet(cmd, *, cwd=None) -> bool:
    try:
        subprocess.run(cmd, cwd=cwd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def gh_repo_exists(full_name: str) -> bool:
    return run_quiet(["gh", "repo", "view", full_name])

def gh_whoami() -> str:
    try:
        out = subprocess.check_output(
            ["gh", "api", "user", "-H", "Accept: application/vnd.github+json", "-q", ".login"],
            text=True
        ).strip()
        return out
    except Exception:
        return ""

def force_remove_readonly(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        raise

def rmtree_force(p: Path):
    if p.exists():
        shutil.rmtree(p, onerror=force_remove_readonly)

def ensure_work_clean(work_root: Path, repo_name: str) -> Path:
    bare = work_root / f"{repo_name}.git"
    rmtree_force(bare)
    work_root.mkdir(exist_ok=True)
    return bare

# ---------- Push helper ----------
def push_mirror_force(temp_dir: Path, remote_name: str, push_user: str, use_gh_helper: bool):
    """
    Mirror push using git.exe with inline -c overrides.
    - Disables VS Code AskPass completely (core.askpass= and no GIT_ASKPASS/SSH_ASKPASS env).
    - Forces credential.username to desired user.
    - For github.com, uses gh helper or leaves manager as fallback (but still inline overrides).
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "0"
    # remove any askpass to stop GUI popups
    for var in ("GIT_ASKPASS", "SSH_ASKPASS"):
        if var in env:
            del env[var]

    cmd = [
        "git", "-C", str(temp_dir),

        # absolutely disable GUI prompts from VS Code
        "-c", "core.askpass=",

        # ignore any global helper (we define our own per-host below)
        "-c", "credential.helper=",

        # force the username that Git passes to the helper(s)
        "-c", f"credential.username={push_user}",

        # drop any stale/bad headers that might carry auth
        "-c", "http.https://github.com/.extraheader=",
    ]

    if use_gh_helper:
        # make git.exe ask gh.exe for a token for github.com
        cmd += ["-c", "credential.https://github.com.helper=!gh auth git-credential"]
    else:
        # rely on Windows Git Credential Manager (stored PAT for this user/host)
        cmd += ["-c", "credential.helper=manager"]

    cmd += ["push", "--mirror", remote_name]

    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Migrate a single repo from Gitea to GitHub.")
    p.add_argument("--json", default="gitea_repos.json", help="Path to JSON list of repos.")
    p.add_argument("--org", default="Holland-Mechanics", help="Target GitHub org (canonical caps).")
    p.add_argument("--user", default="sebastiaan-knippels", help="GitHub username to push under.")
    p.add_argument("--helper", choices=["gh", "gcm"], default="gh",
                   help="Credential provider for github.com during push: gh (OAuth via gh.exe) or gcm (Windows GCM/PAT).")
    p.add_argument("--workdir", default=".mirror_work", help="Temp working folder for bare clone.")
    return p.parse_args()

# ---------- Main ----------
def main():
    args = parse_args()
    here = Path.cwd()
    json_path = here / args.json

    if not json_path.exists():
        print(f"[ERROR] Cannot find '{json_path}'."); sys.exit(1)

    try:
        items = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {e}"); sys.exit(1)
    if not isinstance(items, list):
        print("[ERROR] JSON must be a list of objects."); sys.exit(1)

    names = sorted({i["name"] for i in items if isinstance(i, dict) and i.get("name")})
    print("=== Available repositories from JSON ===")
    for n in names:
        print(f" - {n}")
    print()

    target = input("Type the repository name to migrate: ").strip()
    if not target:
        print("[ERROR] Name cannot be empty."); sys.exit(1)
    if not ALLOWED_RE.match(target):
        print("[ERROR] Invalid name. Allowed: letters, numbers, underscore, hyphen, dot."); sys.exit(1)
    if target not in names:
        print("[ERROR] Name not found in JSON list."); sys.exit(1)

    entry = next((x for x in items if x.get("name") == target), None)
    if not entry or not entry.get("ssh"):
        print("[ERROR] Selected repo has no 'ssh' URL in JSON."); sys.exit(1)

    ssh_source = entry["ssh"]
    work_root = here / args.workdir
    temp_dir  = ensure_work_clean(work_root, target)  # <repo>.git (bare)

    full_name = f"{args.org}/{target}"
    # IMPORTANT: remote URL with the desired push user embedded to avoid accidental other usernames
    https_url_with_user = f"https://{args.user}@github.com/{full_name}.git"

    try:
        # --- Step 1: mirror-clone from Gitea (bare) ---
        log("\n=== Step 1: Mirror-clone from Gitea (bare) ===")
        run(["git", "clone", "--mirror", ssh_source, str(temp_dir)])

        # --- Step 2: ensure GitHub repo exists (private) ---
        log("\n=== Step 2: Ensure GitHub repo exists (private) ===")
        if gh_repo_exists(full_name):
            print(f"GitHub repo already exists: https://github.com/{full_name}")
        else:
            # create via gh; if you don't want this, create manually and comment out next line
            run(["gh", "repo", "create", full_name, "--private"])
            print(f"✓ Created: https://github.com/{full_name}")

        # --- Step 3: verify gh identity when using gh helper ---
        use_gh_helper = (args.helper == "gh")
        if use_gh_helper:
            log("\n=== Step 3: Verify gh identity (only when --helper gh) ===")
            who = gh_whoami()
            if who != args.user:
                print(f"[ERROR] gh is logged in as '{who or 'UNKNOWN'}', expected '{args.user}'.")
                print("Run: gh auth login -h github.com  (and authorize SSO if required)")
                sys.exit(1)
            # Make sure gh wires itself into git (does not touch system, only Git's notion)
            run(["gh", "auth", "setup-git"])
            run(["gh", "auth", "status", "--hostname", "github.com"])

        # --- Step 4: add/verify remote and set EXACTLY the requested local configs ---
        log("\n=== Step 4: Configure remote and set requested repo-local credentials ===")

        # Remote: explicitly set URL WITH the desired user to avoid VS Code prompting with the wrong one
        run(["git", "-C", str(temp_dir), "remote", "remove", "github"], check=False)
        run(["git", "-C", str(temp_dir), "remote", "add", "github", https_url_with_user])
        run(["git", "-C", str(temp_dir), "remote", "set-url", "github", https_url_with_user])
        run(["git", "-C", str(temp_dir), "remote", "-v"])

        # === YOUR THREE LINES, EXACTLY AFTER CHANGING THE REMOTE ===
        # Use Windows Git Credential Manager
        run(["git", "-C", str(temp_dir), "config", "--local", "credential.helper", "manager"])
        # Pin the desired GitHub user in this repo
        run(["git", "-C", str(temp_dir), "config", "--local", "credential.username", args.user])
        # Let gh provide the token for github.com (highest priority)
        # (No quoting required here; subprocess does not use a shell.)
        run(["git", "-C", str(temp_dir), "config", "--local",
             "credential.https://github.com.helper", "!gh auth git-credential"])
        # Clean any bad extra headers if they ever existed
        subprocess.run(["git", "-C", str(temp_dir), "config", "--local",
                        "--unset-all", "http.https://github.com/.extraheader"], check=False)

        # --- Step 5: mirror push via git.exe (inline -c; AskPass disabled; hard username) ---
        log("\n=== Step 5: Push (mirror) to GitHub — forced, non-interactive ===")
        push_mirror_force(temp_dir=temp_dir,
                          remote_name="github",
                          push_user=args.user,
                          use_gh_helper=use_gh_helper)

        print("\n✓ Mirror push completed.")
        print(f"Repo URL: https://github.com/{full_name}")

    except subprocess.CalledProcessError as e:
        print("\n[ERROR] Command failed.")
        print(f"Exit code: {e.returncode}")
        print("Hints:")
        print(" - If using --helper gh: ensure 'gh auth status -h github.com' shows '{args.user}' "
              "and SSO is authorized (gh auth refresh -h github.com -s repo,workflow).")
        print(" - If using --helper gcm: ensure a valid PAT for github.com is stored for that username.")
        sys.exit(1)

    finally:
        log("\n=== Step 6: Cleanup temporary mirror folder ===")
        rmtree_force(temp_dir)
        try:
            work_root.rmdir()
            print(f"Removed empty folder: {work_root}")
        except OSError:
            rmtree_force(work_root)
        print("Cleanup completed.")

    print("\n=== Done ===")
    print("Branches and tags should now be visible.")

if __name__ == "__main__":
    main()
