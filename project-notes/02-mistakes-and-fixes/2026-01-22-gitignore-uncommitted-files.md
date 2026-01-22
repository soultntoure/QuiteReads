# Lesson: .gitignore Doesn't Protect Uncommitted Files

## Problem
Added a markdown file to `.gitignore`, moved it to a new directory, then discarded that directory. Since Git never tracked the file, it was permanently deleted from the filesystem.

## What Happened
- File added to `.gitignore` → Git ignores it (never tracked)
- File moved to new directory → Still untracked by Git
- Directory discarded → IDE/Git deleted untracked directory contents from filesystem
- No Git history exists → File cannot be recovered through Git

The file was only stored locally, not in Git's object database.

## Solution
**For recovery:** Try OS-level file recovery tools (Windows File History, macOS Time Machine, or undelete utilities) if deletion just happened.

**For prevention:**
- Commit important files before adding them to `.gitignore`
- If a file must be ignored but you want to keep a backup, commit it first, then use `git rm --cached filename` to untrack it while keeping the local copy
- Make backups outside Git for sensitive files you can't commit
- Use `git clean -n` (dry run) before actually cleaning to preview what will be deleted

## Lesson Learned
`.gitignore` is not a safety mechanism—it's an exclusion mechanism. Git can only recover what it knows about through commits. Always treat untracked files as vulnerable to permanent loss during Git operations.
