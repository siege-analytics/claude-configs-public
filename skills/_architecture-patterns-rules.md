---
description: Always-on architecture standards from Architecture Patterns with Python (Percival & Gregory). Apply when designing service layers, data access, or domain boundaries.
---

# Architecture Patterns with Python Standards

Apply these principles from *Architecture Patterns with Python* (Harry Percival & Bob Gregory) to service and data-access code.

## Repository pattern

- Separate data retrieval from business logic. A service that fetches Census tracts and computes demographics should not contain SQL or ORM queries inline.
- Repository methods return domain objects, not ORM models or raw dicts. The caller should not know whether data came from PostGIS, a shapefile, or a cache.
- Test business logic against a fake repository, not against mocks of the ORM. Fakes implement the same interface; mocks assert call sequences.

## Service layer

- Services orchestrate. They call repositories, apply domain logic, and return results. They do not contain HTML rendering, file I/O, or network calls.
- A service method should be callable from a management command, a REST endpoint, or a notebook with the same arguments and the same result type.
- Services own the transaction boundary. The caller should not wrap service calls in `transaction.atomic()` — the service decides when to commit.

## Unit of work

- Group related writes into a single unit of work. Populating boundaries and linking parent relationships is one operation, not two independent commits.
- If any step fails, the entire unit rolls back. Partial writes (half the tracts loaded) are worse than no write.

## Dependency inversion

- High-level modules (services, domain logic) must not depend on low-level modules (ORM, HTTP clients, file systems). Both depend on abstractions.
- Pass dependencies in, don't import them at module level. A geocoding service should accept a `GeocodeProvider` protocol, not `import nominatim` at the top.
- This makes testing possible without monkeypatching imports.

## Boundaries and ports

- Define clear boundaries between the domain and infrastructure. Crossing a boundary means translating between domain types and infrastructure types.
- Django models are infrastructure, not domain objects. If domain logic needs geographic data, define a domain type and map to/from the ORM model at the boundary.


---

## Attribution

Principles distilled from *Architecture Patterns with Python* by Harry Percival and Bob Gregory (O'Reilly, 2020). No code reproduced.
