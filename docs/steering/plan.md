---
inclusion: always
---

# Planning

## Conciseness
- ALL planning documents MUST be concise
- Review after writing: eliminate verbosity, increase precision
- Avoid redundancy

## Task File Limit
- Max 500 lines per task file
- Break into separate feature specs when approaching limit
- Each spec self-contained with requirements, design, tasks

## Decomposition
1. Identify feature boundaries
2. Create master plan with execution order
3. Ensure clear interfaces and dependencies
4. Use steering folder for cross-cutting concerns

## Planning stage
- You MUST follow these rules during the planning stage of a feature (i.e. when you are drafting or reviewing the requirements.md, design.md, or tasks.md files)

### Tasks.md
1. The tasks file should have 3 tiers. This means that individual task numbers should be of the format #.#.#
    - The first task will be 1.1.1
    - The second task will be 1.1.2 etc
    The three tiers should be: 
        1. Phase tier - This is the phase of the implementation. You should identify high level tasks that you'll need to achieve and place them in this tier and in chronological order.
        2. Group tier - You should group tasks together and execute them in the order required to achieve the high level goal of completeing this phase.  
        3. Task tier - This should be individual tasks which you're going to complete.

    e.g.

```
- [ ] 1. Make a module run faster

    - [ ] 1.1 Refactor a python module

        - [ ] 1.1.1 Refactor the code

        - [ ] 1.1.2 Refactor the tests

        - [ ] 1.1.3 Verify the tests still pass
```


## Documentation
- All projects should have thorough documentation
- From a user's perspective, write documentation which explains how the project should be used
