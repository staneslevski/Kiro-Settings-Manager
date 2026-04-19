# Implementation Plan: ide2cli-converter

## Overview

This plan implements the `ksm ide2cli` command that converts Kiro IDE-format agent markdown files and hook files into CLI-compatible JSON files. The implementation is split across 4 phases: foundation (tool mapping), agent conversion, hook conversion, and command integration. All phases follow TDD methodology.

## Tasks

- [x] 1. Foundation — Tool Name Mapping and Converters Package

    - [x] 1.1 Explore existing codebase patterns

        - [x] 1.1.1 Explore existing command structure, error formatting, and test patterns
          → Agent: context-gatherer
          _Requirements: 1.1, 1.2_

    - [x] 1.2 Tool name mapping module

        - [x] 1.2.1 Write tests for tool_map.map_tools() covering known mappings, unknown passthrough, deduplication, and unconvertible tool warnings
          → Agent: general-task-execution
          **Property 1: Tool map expansion is deterministic**
          **Property 2: Tool map produces no duplicates**
          **Property 3: Unknown tools pass through unchanged**
          _Requirements: 3.1, 3.2, 3.3, 2.4, 2.5, 2.6_

        - [x] 1.2.2 Create src/ksm/converters/__init__.py and src/ksm/converters/tool_map.py with TOOL_NAME_MAP, UNCONVERTIBLE_TOOLS, and map_tools()
          → Agent: general-task-execution
          _Requirements: 3.1, 3.2, 3.3, 2.3, 2.4, 2.5, 2.6_

        - [x] 1.2.3 Run tests and verify all pass
          → Agent: kiro

    - [x] 1.3 Checkpoint — Run full test suite, verify all tests pass
      → Agent: kiro

- [x] 2. Agent Conversion

    - [x] 2.1 Frontmatter parser

        - [x] 2.1.1 Write tests for parse_frontmatter() covering valid frontmatter, missing delimiters, and invalid YAML
          → Agent: general-task-execution
          **Property 4: Frontmatter round-trip preserves name and description**
          _Requirements: 7.1, 7.2_

        - [x] 2.1.2 Implement parse_frontmatter() in src/ksm/converters/agent_converter.py
          → Agent: general-task-execution
          _Requirements: 7.1, 7.2_

        - [x] 2.1.3 Run tests and verify all pass
          → Agent: kiro

    - [x] 2.2 Agent converter

        - [x] 2.2.1 Write tests for convert_agent() covering successful conversion, missing name/description, tool mapping, file:// URI generation, JSON formatting, and idempotency
          → Agent: general-task-execution
          **Property 5: Agent conversion is idempotent**
          _Requirements: 2.1, 2.2, 2.3, 2.7, 2.8, 7.3, 7.4, 8.1, 8.2_

        - [x] 2.2.2 Implement convert_agent() and AgentConversionResult dataclass in src/ksm/converters/agent_converter.py
          → Agent: general-task-execution
          _Requirements: 2.1, 2.2, 2.3, 2.7, 2.8, 7.3, 7.4, 8.1, 8.2_

        - [x] 2.2.3 Run tests and verify all pass
          → Agent: kiro

    - [x] 2.3 Checkpoint — Run full test suite, verify all tests pass
      → Agent: kiro

- [x] 3. Hook Conversion

    - [x] 3.1 Hook converter

        - [x] 3.1.1 Write tests for convert_hook() covering runCommand conversion, event type mapping, askAgent skip, unconvertible event skip, disabled hook skip, invalid JSON handling, and toolTypes matcher mapping
          → Agent: general-task-execution
          **Property 6: Event type mapping is total over convertible types**
          **Property 7: Hook conversion skips disabled hooks silently**
          _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

        - [x] 3.1.2 Implement convert_hook(), HookConversionResult, EVENT_TYPE_MAP, and UNCONVERTIBLE_EVENTS in src/ksm/converters/hook_converter.py
          → Agent: general-task-execution
          _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

        - [x] 3.1.3 Run tests and verify all pass
          → Agent: kiro

    - [x] 3.2 Checkpoint — Run full test suite, verify all tests pass
      → Agent: kiro

- [x] 4. Command Integration and CLI Registration

    - [x] 4.1 Command module and CLI wiring

        - [x] 4.1.1 Write tests for run_ide2cli() covering both-scopes scanning, missing directories, summary reporting, exit codes, and stderr-only output
          → Agent: general-task-execution
          **Property 8: All stderr, no stdout**
          _Requirements: 1.1, 1.3, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

        - [x] 4.1.2 Implement src/ksm/commands/ide2cli.py with run_ide2cli(), ConversionSummary, and directory scanning logic
          → Agent: general-task-execution
          _Requirements: 1.1, 1.3, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

        - [x] 4.1.3 Register ide2cli subcommand in src/ksm/cli.py and add _dispatch_ide2cli
          → Agent: general-task-execution
          _Requirements: 1.1, 1.2_

        - [x] 4.1.4 Run tests and verify all pass including help text
          → Agent: kiro

    - [x] 4.2 Checkpoint — Run full test suite with coverage, verify ≥95% on new modules
      → Agent: kiro

## Notes

All tasks are required.
