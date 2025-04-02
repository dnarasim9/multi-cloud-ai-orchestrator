# ADR-005: Simulated Cloud Infrastructure

## Status
Accepted

## Context
The platform must support AWS, Azure, and GCP but development and testing should not require actual cloud credentials or incur costs.

## Decision
All cloud interactions are behind port interfaces with simulated implementations:
- `SimulatedTerraformExecutor`: Generates real HCL but simulates plan/apply
- `SimulatedDriftDetector`: Produces realistic drift reports without cloud API calls
- `RuleBasedPlanningEngine`: Deterministic plan generation without LLM dependency

## Alternatives Considered
- **LocalStack**: Good for AWS but doesn't cover Azure/GCP
- **Terraform Cloud Dev**: Still requires some cloud setup
- **Mock-only**: No realistic output for integration testing

## Trade-offs
- (+) Full development cycle without cloud access
- (+) Deterministic, fast tests
- (+) Same port interfaces work with real implementations
- (-) Simulated behavior may not match real cloud behavior exactly
