# Production Readiness

`loopos.production.ProductionReadinessGate` evaluates whether the latest loop
iteration has enough evidence for production delivery.

It blocks when:

- build evidence is simulated only;
- test evidence is missing, failing, partial, or simulated only;
- blocking review findings remain open.

The gate emits `ProductionReadinessReport`, which delivery surfaces can link to
as deployability evidence.
