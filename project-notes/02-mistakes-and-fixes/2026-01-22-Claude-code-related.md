# Lesson: Insufficient Context Handoff Between Conversations

## Problem
When starting a new conversation with Claude, I didn't provide enough context, forcing Claude to spend time exploring and reading the codebase unnecessarily.

## Missing Information
- Current state/placeholders being used in the project
- Folder structure and file locations for research repo
- Where to find relevant documentation or references

## Impact
- Wasted time on exploration that could have been avoided
- Unnecessary token usage and API credits consumed
- Slower resolution of the actual task

## Solution
For future conversations, provide an **upfront context summary** that includes:
- Current project state and any work-in-progress items
- Relevant folder structure and key file locations
- Links to existing documentation or examples
- Specific constraints or decisions already made

**Tip**: Copy relevant sections from CLAUDE.md or README into the initial prompt when context matters.