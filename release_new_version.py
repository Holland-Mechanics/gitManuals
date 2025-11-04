#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HM Publish Release Script
-------------------------
Interactive helper to publish a software release from a *private* source repo
to a *public* releases repository.

Key features:
- Uses nano.exe to edit the commit/release message.
- Flexible staging detection: accepts
    1) <repo>/release/<machine>/<version>/
    2) <repo>/release/<version>/
    3) <repo>/release/
- Public release destination is: <PUBLIC_ROOT>/<machine>/<version>/
- PUBLIC_ROOT is resolved (first match wins) from:
    1) ENV HM_RELEASE_REPO_ROOT
    2) File: ~/.hm_release_repo_root.txt
    3) File: <script_dir>/hm_release_repo_root.txt
    4) File: <current_working_dir>/hm_release_repo_root.txt
- Generates CHANGELOG.txt from annotated tag history (latest first).
- Creates/overwrites tag (asks confirmation if the tag already exists).
- Commits and pushes in both repos.

Requirements:
- Python 3
- git in PATH
- nano.exe in PATH (or same directory as this script)
- Push rights to both repos.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# ----------------------------
# Utilities
# ----------------------------

def run(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a process and capture its output. Raises CalledProcessError if check=True and exit != 0.
    """
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check
    )

def ask(prompt: str, default: Optional[str] = None) -> str:
    """
    Interactive prompt (single line). Empty input returns default if provided.
    """
    sfx = f" [{default}]" if default else ""
    while True:
        val = input(f"{prompt}{sfx}: ").strip()
        if not val and default is not None:
            return default
        if val:
            return val

def ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    """
    Ask for yes/no. Returns default on empty input.
    """
    d = "Y/n" if default_yes else "y/N"
    while True:
        v = input(f"{prompt} ({d}): ").strip().lower()
        if not v:
            return default_yes
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False
        print("Please answer y or n.")

# ----------------------------
# Version/tag helpers
# ----------------------------

SEMVER_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")

def validate_version(tag: str) -> None:
    if not SEMVER_TAG_RE.match(tag):
        raise SystemExit("ERROR: Version must match syntax v1.2.3")

# ----------------------------
# Git helpers
# ----------------------------

def ensure_git_repo() -> None:
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"])
    except subprocess.CalledProcessError:
        raise SystemExit("ERROR: Not inside a git repository.")

def git_repo_root() -> Path:
    cp = run(["git", "rev-parse", "--show-toplevel"])
    return Path(cp.stdout.strip())

def git_repo_name() -> str:
    """
    Try to get the name from remote.origin.url, fallback to repo directory name.
    """
    try:
        cp = run(["git", "config", "--get", "remote.origin.url"], check=True)
        url = cp.stdout.strip()
        if url:
            name = url.split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            if name:
                return name
    except subprocess.CalledProcessError:
        pass
    return git_repo_root().name

def git_has_changes() -> bool:
    cp = run(["git", "status", "--porcelain"], check=True)
    return bool(cp.stdout.strip())

def git_add_all() -> None:
    run(["git", "add", "-A"])

def git_commit(message: str) -> bool:
    """
    Create a commit if there are staged changes. Returns True if a commit was created.
    """
    try:
        cp = run(["git", "commit", "-m", message], check=True)
        print(cp.stdout or cp.stderr)
        return True
    except subprocess.CalledProcessError as e:
        # No staged changes or pre-commit hook blocked it.
        out = (e.stdout or "") + (e.stderr or "")
        if out.strip():
            print(out.strip())
        print("No commit created (possibly no changes). Proceeding…")
        return False

def git_tag_exists(tag: str) -> bool:
    try:
        run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"])
        return True
    except subprocess.CalledProcessError:
        return False

def git_tag_create(tag: str, message: str, force: bool = False) -> None:
    """
    Create an annotated tag. If force=True, overwrite existing tag locally.
    """
    cmd = ["git", "tag"]
    if force:
        cmd.append("-f")
    cmd += ["-a", tag, "-m", message]
    run(cmd)

def git_push_with_tags() -> None:
    run(["git", "push"])
    run(["git", "push", "--tags"])

def git_tag_list_sorted_desc() -> List[str]:
    cp = run(["git", "tag", "--sort=-creatordate"])
    tags = [t.strip() for t in cp.stdout.splitlines() if t.strip()]
    return [t for t in tags if SEMVER_TAG_RE.match(t)]

def tag_date(tag: str) -> str:
    cp = run(["git", "log", "-1", "--format=%ad", "--date=short", tag])
    return cp.stdout.strip()

def commits_between(a_excl: Optional[str], b_incl: str) -> List[str]:
    rev = b_incl if a_excl is None else f"{a_excl}..{b_incl}"
    fmt = "%s"
    cp = run(["git", "log", "--no-merges", f"--pretty=format:{fmt}", rev])
    lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
    return lines

# ----------------------------
# CHANGELOG builder
# ----------------------------

def build_changelog() -> str:
    tags = git_tag_list_sorted_desc()
    if not tags:
        return "No tags found.\n"
    sections = []
    for idx, tag in enumerate(tags):
        prev_tag = tags[idx + 1] if (idx + 1) < len(tags) else None
        messages = commits_between(prev_tag, tag)
        date = tag_date(tag) or datetime.utcnow().strftime("%Y-%m-%d")
        sec = [f"## {tag} — {date}"]
        for m in messages:
            sec.append(f"- {m}")
        sections.append("\n".join(sec))
    return "\n\n".join(sections) + "\n"

# ----------------------------
# Paths & moving artifacts
# ----------------------------

def find_release_root() -> Path:
    """
    Resolve the public releases root path. First match wins:
      1) ENV HM_RELEASE_REPO_ROOT
      2) ~/.hm_release_repo_root.txt
      3) <script_dir>/hm_release_repo_root.txt
      4) <cwd>/hm_release_repo_root.txt
    Each file must contain an absolute path.
    """
    env = os.environ.get("HM_RELEASE_REPO_ROOT")
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p

    home_file = Path.home() / ".release_new_version_path.txt"
    if home_file.exists():
        txt = home_file.read_text(encoding="utf-8").strip()
        if txt:
            p = Path(txt).expanduser()
            if p.exists():
                return p

    script_dir = Path(__file__).parent
    local_file_script = script_dir / "release_new_version_path.txt"
    if local_file_script.exists():
        txt = local_file_script.read_text(encoding="utf-8").strip()
        if txt:
            p = Path(txt).expanduser()
            if p.exists():
                return p

    local_file_cwd = Path.cwd() / "release_new_version_path.txt"
    if local_file_cwd.exists():
        txt = local_file_cwd.read_text(encoding="utf-8").strip()
        if txt:
            p = Path(txt).expanduser()
            if p.exists():
                return p

    raise SystemExit(
        "ERROR: Could not resolve release repo root.\n"
        "Provide absolute path via one of:\n"
        " - ENV HM_RELEASE_REPO_ROOT\n"
        " - ~/.release_new_version_path.txt\n"
        " - release_new_version_path.txt next to this script\n"
        " - ./release_new_version_path.txt in the current working directory\n"
    )

def find_staging_dir(repo_root: Path, machine: str, version: str) -> Path:
    """
    Try common layouts and return the first existing path:
      - <repo>/release/<machine>/<version>/
      - <repo>/release/<version>/
      - <repo>/release/
    """
    candidates = [
        repo_root / "release" / machine / version,
        repo_root / "release" / version,
        repo_root / "release",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            print(f"Using staging directory: {p}")
            return p
    pretty = "\n".join(str(p) for p in candidates)
    raise SystemExit(
        "ERROR: Could not find a staging directory.\n"
        "I looked for any of:\n" + pretty + "\n"
        "Create one of these and place all binaries/scripts inside, then re-run."
    )

def move_staging_to_public(staging_dir: Path, public_root: Path, machine: str, version: str) -> Path:
    """
    Move all items from staging_dir into <public_root>/<machine>/<version>/
    Existing items at the destination are replaced.
    """
    dest = public_root / machine / version
    dest.mkdir(parents=True, exist_ok=True)
    for item in staging_dir.iterdir():
        target = dest / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))
    return dest

# ----------------------------
# Editor (nano) for commit/release message
# ----------------------------

def edit_message_with_nano(default_text: str = "") -> str:
    """
    Open nano.exe with a temp file, wait until it closes, and return the file content.
    Lines starting with '#' are ignored (like Git commit messages).
    """
    tmp = Path(tempfile.gettempdir()) / "git_commit_message.txt"
    tmp.write_text(default_text, encoding="utf-8")

    try:
        subprocess.run(["nano.exe", str(tmp)], check=True)
    except FileNotFoundError:
        raise SystemExit("ERROR: nano.exe not found. Ensure it is in PATH or next to this script.")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"ERROR: nano.exe exited with status {e.returncode}")

    # Read back, ignore comment lines starting with '#'
    msg = "\n".join(
        line for line in tmp.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#")
    ).strip()

    if not msg:
        raise SystemExit("Aborted: no message entered.")

    return msg

# ----------------------------
# Main flow
# ----------------------------

def main() -> None:
    ensure_git_repo()
    repo_root = git_repo_root()
    os.chdir(repo_root)  # ensure we're always at repo root

    machine_name = git_repo_name()
    print(f"Detected repo: {repo_root}")
    print(f"Machine name (from repo): {machine_name}")

    version = ask("Enter version (syntax v1.2.3)")
    validate_version(version)

    print("Opening nano.exe to edit commit/release message…")
    release_msg = edit_message_with_nano(
        default_text=(
            "# Enter your release/commit message below.\n"
            "# Lines starting with # are ignored.\n"
            "\n"
        )
    )
    print(f"Using commit message:\n{release_msg}\n")

    if not ask_yes_no("Is the version number in source code up-to-date?", True):
        raise SystemExit("Aborted by user.")
    if not ask_yes_no("Is the program built (fresh build)?", True):
        raise SystemExit("Aborted by user.")
    if not ask_yes_no("Are ALL binaries present in the local release folder?", True):
        raise SystemExit("Aborted by user.")

    print("\n>>> Preparing commit & tag in private repo…")
    if git_has_changes():
        git_add_all()
        git_commit(release_msg)
    else:
        print("No changes detected in working tree.")

    # Tag creation with existence check
    if git_tag_exists(version):
        print(f"Tag {version} already exists.")
        if ask_yes_no("Overwrite existing tag locally and on origin?", False):
            git_tag_create(version, release_msg, force=True)
            print(f"Overwrote tag {version} locally.")
        else:
            raise SystemExit("Aborted: tag exists. Choose a new version.")
    else:
        git_tag_create(version, release_msg)
        print(f"Created tag {version}")

    print("Pushing commit and tags to origin…")
    try:
        git_push_with_tags()
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "") + (e.stderr or "")
        if out.strip():
            print(out.strip())
        raise SystemExit("ERROR: Failed to push. Resolve and re-run.")

    print("\n>>> Generating CHANGELOG.txt from tags…")
    changelog = build_changelog()
    changelog_path = repo_root / "CHANGELOG.txt"
    changelog_path.write_text(changelog, encoding="utf-8")
    print(f"Wrote {changelog_path}")

    # Staging detection (supports multiple layouts)
    staging_dir = find_staging_dir(repo_root, machine_name, version)

    # Ensure CHANGELOG.txt is included in the staging area
    shutil.copy2(str(changelog_path), str(staging_dir / "CHANGELOG.txt"))

    # Public releases root
    public_root = find_release_root()
    print(f"Public releases repo root: {public_root}")

    # Move files to public repo
    dest = move_staging_to_public(
        staging_dir=staging_dir,
        public_root=public_root,
        machine=machine_name,
        version=version
    )
    print(f"Moved staging content to: {dest}")

    print("\n>>> Committing in public releases repo…")
    try:
        run(["git", "add", "."], cwd=public_root)
        # Don't fail if nothing changed (check=False)
        run(["git", "commit", "-m", release_msg], cwd=public_root, check=False)
        run(["git", "push"], cwd=public_root)
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "") + (e.stderr or "")
        if out.strip():
            print(out.strip())
        raise SystemExit("ERROR: Failed to push in public releases repo. Resolve and re-run.")

    print("\n✅ Done.")
    print(f"- Private repo committed/tagged: {version}")
    print(f"- CHANGELOG.txt included in public release folder")
    print(f"- Public release path: {dest}")

# ----------------------------
# Entrypoint
# ----------------------------

if __name__ == "__main__":
    main()
