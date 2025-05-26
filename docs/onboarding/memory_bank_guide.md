# Memory Bank System Guide

## Introduction to Memory Bank

LedgerFlow uses a unique "Memory Bank" system for maintaining critical documentation. The Memory Bank is a set of markdown files in the `cline_docs/` directory that contain all essential information about the project, its architecture, and its current state.

This documentation approach ensures that any team member can quickly get up to speed on the project, even if they've never seen it before. It's designed to survive "memory resets" where all context is lost.

## Memory Bank Structure

The Memory Bank consists of the following key files:

### 1. `productContext.md`

This file answers:
- Why does this project exist?
- What problems does it solve?
- How should it work?

This is the first file to read to understand the project's purpose and vision.

### 2. `activeContext.md`

This file tracks:
- What we're working on now
- Recent changes
- Next steps

This is your source of truth for the current state of development.

### 3. `systemPatterns.md`

This file documents:
- How the system is built
- Key technical decisions
- Architecture patterns

This is where you learn about the technical foundation of the project.

### 4. `techContext.md`

This file outlines:
- Technologies used
- Development setup
- Technical constraints

This is your guide to the technical environment of the project.

### 5. `progress.md`

This file records:
- What works
- What's left to build
- Progress status

This is where you check the project's completion status and roadmap.

## Working with Memory Bank

### When to Read

The Memory Bank should be read:
1. When you first join the project
2. When you start a new task
3. When you need to understand a specific area of the project
4. After a period away from the project
5. When you need to recall technical decisions

### When to Update

The Memory Bank should be updated after:
1. Significant architectural changes
2. Completion of major features
3. Resolving critical issues
4. Making important technical decisions
5. Changing the project's direction or focus

**Important**: The Memory Bank should be updated with the mindset that the next reader has no prior knowledge of the project. When documenting, imagine you're writing for a new team member who needs to understand everything from scratch.

### How to Update

To update the Memory Bank:

1. Identify which file(s) need to be updated based on the change
2. Make clear, concise updates that provide context
3. Avoid jargon or assuming prior knowledge
4. Include examples where helpful
5. Ensure changes are committed and pushed promptly

### Update Command

When it's time to update the Memory Bank, the team lead may use the phrase:

```
update memory bank
```

This signals that important changes should be documented before proceeding.

## Memory Bank vs. Other Documentation

The Memory Bank differs from other documentation in several ways:

| Memory Bank | Regular Documentation |
|-------------|------------------------|
| Focused on project context and decisions | Focused on specific features or code |
| Design assumes no prior knowledge | May assume some prior knowledge |
| Core files in one location | May be distributed throughout codebase |
| Updated after significant changes | Updated continuously |
| Emphasizes "why" over "how" | Often emphasizes "how" over "why" |

Both types of documentation are important, but Memory Bank serves as the foundation that makes other documentation useful and accessible.

## Why Memory Bank Matters

The Memory Bank system is crucial because:

1. **Onboarding**: New team members can quickly understand the project
2. **Context Retention**: Important decisions and context are never lost
3. **Project Continuity**: The project can survive team changes
4. **Decision Making**: Past decisions are documented with rationale
5. **Focus**: The team stays aligned on current priorities

By maintaining a robust Memory Bank, we ensure that LedgerFlow can continue to evolve and improve even as the team changes over time.

## Memory Bank Best Practices

1. **Keep it current**: Update after significant changes
2. **Be comprehensive**: Include context, not just facts
3. **Write clearly**: Use simple language and good structure
4. **Assume no knowledge**: Write for someone with no prior context
5. **Link to details**: Reference more detailed docs where appropriate
6. **Include examples**: Show, don't just tell
7. **Document decisions**: Record not just what, but why
8. **Use consistent formatting**: Follow markdown conventions
9. **Review regularly**: Ensure accuracy and completeness
10. **Reference in PRs**: Link to Memory Bank updates in pull requests 