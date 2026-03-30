# PlantUML Writing Guide

This file records general-purpose rules for writing and refining architecture diagrams in this repository.

## Scope

- Applies to all new or modified `.puml` files in this repository.
- Especially relevant to diagrams under `puml/`.

## Goal

- Optimize layout readability without oversimplifying the architecture.
- Preserve important runtime layers and data flow details.
- Prefer cleaner routing, spacing, and grouping over deleting nodes or relationships.

## Required Modeling Rules

- Use the real runtime entry point as the anchor of the diagram.
  - Prefer the actual executed startup/orchestration module, not just a utility file.
- When describing a subsystem or runtime path, cover the full flow around it, not just the local file being read.
- Keep the key architectural layers visible when they exist.
- Prefer a generalized layered view such as:
  - entry / startup / orchestration
  - task / scheduling / behavior layer
  - shared data contracts / interface boundaries
  - planning / gait / trajectory generation
  - control core / execution logic
  - kinematics / dynamics / low-level mapping
  - closed-loop environment interaction
    - for example simulation, hardware, middleware, sensors, or actuators
  - visualization / logging / telemetry when relevant
- Show reuse boundaries clearly.
  - Mark any shared core that is reused by multiple runtime variants, backends, or deployment targets.

## Layout Rules

- Optimize, do not simplify.
  - Do not remove important modules only to make the figure cleaner.
  - Prefer restructuring and port-ization before deleting detail.
- Prefer left-to-right global flow unless a specific diagram clearly benefits from another direction.
- Keep the main runtime spine visually readable:
  - intent / task -> core logic -> execution / adapters -> environment / plant -> observation -> state feedback
- Reduce visual density in crowded regions by:
  - adding bus/port nodes
  - splitting dense fan-in/fan-out through intermediate components
  - using hidden layout constraints
  - separating explanatory text from core routing
- Avoid letting notes dominate layout.
  - Prefer `caption` or compact legend-style summaries for global notes.
  - Only use attached notes when they genuinely improve understanding and do not distort layout.
- Prefer medium-length segmented paths over one huge crossing line when possible.
- If a local improvement damages the global balance, keep the more stable overall layout.

## Port-ization Rules

- When a region becomes too dense, introduce explicit bus/port nodes instead of drawing many direct edges.
- Good candidates for bus nodes include:
  - input aggregation
  - output aggregation
  - state read / write paths
  - task dispatch
  - feedback input aggregation
- Use bus nodes to make data ownership and routing clearer, not just as decoration.

## Edge Rules

- Keep arrows semantically correct according to code flow.
- Prefer directional arrows that reflect runtime data flow.
- Label only meaningful flows, such as:
  - task outputs
  - measured state
  - desired motion
  - gait parameters
  - joint targets
  - controller state update
  - sensors / kinematics
- Avoid redundant labels on every edge.
- If one edge is both visually ugly and semantically suspicious, verify the code path before adjusting layout.

## Styling Rules

- Prefer these baseline settings unless a specific diagram needs something else:

```puml
skinparam componentStyle rectangle
skinparam packageStyle rectangle
skinparam shadowing false
skinparam defaultFontName Consolas
skinparam wrapWidth 240
skinparam maxMessageSize 220
skinparam linetype ortho
skinparam ArrowThickness 2
skinparam nodesep 100
skinparam ranksep 120
left to right direction
```

- Keep line width slightly stronger than PlantUML defaults for readability.
- Keep spacing loose enough that adjacent lines do not visually merge.
- Use packages to separate major layers.
- Use concise component labels, but include file paths for key modules.

## Content Rules

- Make the abstract layers concrete with the actual modules in the codebase.
- Include the components that materially define runtime behavior, such as:
  - orchestration / entry modules
  - task, scheduling, or behavior sources
  - shared state, commands, configs, or interface contracts
  - planning, trajectory, or intermediate decision layers
  - core controllers, policies, or execution logic
  - low-level mapping such as kinematics, dynamics, allocation, or command translation
  - adapters to simulation, hardware, middleware, services, or external systems
  - observability surfaces such as logs, viewers, plots, metrics, or telemetry
- If the same core logic is reused across multiple runtime paths, show both:
  - what is shared
  - what is swapped per backend or deployment target
- If a diagram is domain-specific, keep the rules generic but express the nodes concretely.
  - Example patterns: simulator vs hardware path, offline vs online path, planner vs executor path.

## Examples

- Entry point examples:
  - CLI main
  - service bootstrap
  - simulation launcher
  - robot runtime loop
- Environment / plant examples:
  - simulation engine
  - physical hardware
  - middleware graph
  - external service boundary
- Adapter examples:
  - sensor bridge
  - actuator interface
  - network client
  - file / data loader

## Iteration Rules

- After changing a `.puml`, render it and inspect the output instead of judging only from source text.
- Favor incremental layout refinement:
  - first fix semantic mistakes
  - then resolve the worst dense region
  - then polish secondary spacing issues
- When several variants are tried, keep the version with the best overall visual balance, not the most aggressive local optimization.

## Practical Review Checklist

- Is the entry point clear?
- Are the important architectural layers present for this system?
- Is the shared core vs variant-specific path obvious?
- Are the densest regions port-ized enough?
- Are there any obviously wrong arrows?
- Is any note/legend pulling the layout off balance?
- Does the rendered result look more readable without losing architectural detail?
