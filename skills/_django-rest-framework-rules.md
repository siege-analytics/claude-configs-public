---
description: Always-on Django REST Framework standards. Apply when writing or reviewing Python code that imports from rest_framework.*. Stacks on top of [rule:python] and [rule:django].
---

# Django REST Framework Standards

Apply these principles to all code that imports from `rest_framework.*`. Layers on top of `[rule:python]` for Python style and `[rule:django]` for ORM, model, and settings conventions. This shelf covers the DRF-specific surface: serializers, viewsets, permissions, pagination, throttling, testing, versioning, and schema documentation.

## Serializers

- Use `ModelSerializer` when the shape maps 1:1 to a model with no cross-cutting concerns. Break out to `Serializer` (or `serializers.Serializer` subclass) when the payload spans multiple models, when field validation depends on external state, or when the write shape differs materially from the model shape
- Every `ModelSerializer` declares `fields = [...]` or `exclude = [...]` explicitly. Never use `fields = "__all__"` on a model that has any field the API should not expose (`password`, `is_staff`, internal FK, audit columns)
- Read-only surface goes in `read_only_fields`; write-only surface (passwords, tokens) goes in `write_only_fields`. `extra_kwargs` is the catch-all when a field needs both `write_only=True` and a validator
- Prefer `PrimaryKeyRelatedField`, `SlugRelatedField`, or `HyperlinkedIdentityField` over nested serializers for relations. Nested serializers are appropriate only when the client needs the full related object AND the N+1 cost is addressed via `select_related` / `prefetch_related` in the viewset's `get_queryset`
- Never use `Meta.depth`. It bypasses field allowlisting, produces uncontrolled N+1 queries, and hides the schema from readers of the serializer file
- Field-level validation lives in `validate_<field>(self, value)`; cross-field validation lives in `validate(self, attrs)`; uniqueness constraints across multiple fields live in `UniqueTogetherValidator` on `Meta.validators`, not in `validate()`
- Override `to_representation` only when the output shape must differ from the field definitions (e.g. conditional field inclusion by request user). Override `to_internal_value` only when the input shape needs pre-parsing before field validators run. Both are escape hatches; reaching for them often signals the serializer should be a `Serializer` not a `ModelSerializer`

## ViewSets and views

- Decision order: `ModelViewSet` for full CRUD on a resource; `GenericViewSet` + specific mixins (`ListModelMixin`, `RetrieveModelMixin`) when only a subset of verbs is intended; `GenericAPIView` + mixins when you need one action shape but with custom orchestration; `APIView` when the endpoint does not map to a queryset at all
- Filter backends, pagination class, permission classes, throttle classes, and authentication classes are declared as class attributes -- never computed per-request in `dispatch()` or `initial()`
- `permission_classes` is set explicitly on every view whose access matters. Do not rely on `DEFAULT_PERMISSION_CLASSES` to gate sensitive endpoints; the default is a floor, and a settings change should never widen a specific endpoint's access
- Per-action variation goes in `get_queryset()` and `get_serializer_class()`, dispatching on `self.action`. Do not read `self.request.method` in these methods when `self.action` is available -- action is the DRF-native dispatch key
- Never expose a `ModelViewSet` on a model with sensitive fields (auth tokens, PII, admin flags) without an explicit `fields = [...]` allowlist on the serializer AND a permission class that enforces object-level access

## Permissions

- Custom `BasePermission` subclasses are named for the resource kind and reused across viewsets (`IsDonorOwnerOrReadOnly`, not `IsAllowed`). One permission class per invariant; compose with `&`, `|`, `~` at the viewset
- `has_object_permission` MUST be implemented whenever the viewset looks up an object by `pk` (retrieve, update, partial_update, destroy). DRF calls it only when `get_object()` is invoked; a viewset that hand-rolls object lookup bypasses this hook and MUST call `self.check_object_permissions(request, obj)` explicitly
- `IsAuthenticated` alone is never a sufficient permission on any endpoint that returns or mutates user-scoped data. Compose with an object-level check (`IsOwner`, `HasProjectMembership`) or a role check
- `IsAdminUser` gates `is_staff`, which is a Django-admin flag, not a business role. Custom role permissions belong in project-specific `BasePermission` subclasses, not overloaded onto `is_staff`

## Pagination

- Cursor pagination (`CursorPagination`) for time-ordered or append-mostly collections -- avoids offset-drift when rows are inserted mid-page
- Page-number pagination (`PageNumberPagination`) for user-facing catalogs where the client shows page numbers
- Limit-offset pagination (`LimitOffsetPagination`) for internal tooling and admin surfaces only; do not expose to third-party API consumers
- Every pagination class sets `max_page_size` (or `max_limit` for limit-offset). Unbounded page size is a denial-of-service primitive; the default `page_size` must be a reasonable floor, and the max must be a hard ceiling
- Do not disable pagination on a list endpoint that can return more than ~100 rows in any realistic scenario. `pagination_class = None` is a claim the collection is bounded; verify at review time

## Throttling

- Use `ScopedRateThrottle` with per-resource scope names for endpoints with distinct rate profiles (login, password-reset, search, bulk-export). Global `DEFAULT_THROTTLE_RATES` is a floor for undifferentiated traffic, not a ceiling for sensitive endpoints
- Anonymous vs authenticated rate distinction is mandatory for any public endpoint. `AnonRateThrottle` and `UserRateThrottle` set at different rates in `DEFAULT_THROTTLE_RATES`
- Throttling is not a substitute for authentication or authorization. A throttle limits abuse rate; a permission decides whether the request is legitimate at all

## Testing

- Use `rest_framework.test.APITestCase` and `APIClient` (or `APIRequestFactory`) over Django's `Client` / `TestCase`. DRF-specific auth (`force_authenticate`, `credentials`) and response parsing require the DRF test surface
- Fixtures via `pytest-django` + `factory-boy`, not `fixtures/*.json`. See `[skill:django]` for the factory pattern; DRF tests use the same factories to build the request payload
- Every viewset action has explicit tests for: 200/201 happy path, 401 unauthenticated, 403 forbidden (authenticated but not authorized), 404 not-found, 400 validation failure (field-level and object-level). List actions additionally test pagination shape (`count`, `next`, `previous`, `results`), ordering, and filter parameters
- Assert against `response.data` (parsed) not `response.content` (raw bytes) for payload shape. Assert against `response.status_code` using `status.HTTP_*` constants, not integer literals

## Versioning

- Choose a versioning scheme at project bootstrap: `URLPathVersioning` (`/api/v1/...`), `NamespaceVersioning` (URL-namespaced), or `AcceptHeaderVersioning`. Do not add versioning retroactively -- a v1 that was never labelled v1 is unversionable without a breaking flag day
- Set `DEFAULT_VERSION` and `ALLOWED_VERSIONS` in `REST_FRAMEWORK` settings. An unversioned request must resolve to a specific version, not to "latest"
- Deprecation of a version follows `[rule:writing-releases]` writing-releases:1 (BREAKING in the changelog) and writing-releases:3 (deprecation messages name a removal target). A v1 endpoint slated for removal has both an `X-API-Deprecated` header on responses and a documented removal version

## Documentation

- Use `drf-spectacular` (OpenAPI 3.1). Do not use `drf-yasg` in new projects -- it is stuck on Swagger 2.0 and does not support the current OpenAPI feature surface
- Every viewset action has a docstring. `drf-spectacular` picks it up as the operation description; a missing docstring produces an unlabelled endpoint in the generated schema
- Use `@extend_schema` for cases the introspection cannot infer: custom action response shape, request/response examples, deprecation markers, tag reassignment. Do not use it as a substitute for well-typed serializers -- fix the serializer first
- The generated OpenAPI schema is checked into version control (or generated in CI and diffed against the checked-in copy). An undetected schema change is a silent contract break for API consumers

---

## Attribution

Draws from:
- Django REST Framework documentation -- <https://www.django-rest-framework.org/> (BSD-licensed; the canonical source for all DRF conventions)
- Tom Christie -- *Django REST Framework* (the framework's author; the docs ARE the book)
- William S. Vincent -- *Django for APIs* (Vincent, 2022; test-first DRF walkthrough for Django 4.x/5.x)
- Adam Johnson -- adamj.eu (continuously updated Django/DRF operational patterns)
- `drf-spectacular` documentation -- <https://drf-spectacular.readthedocs.io/>

Defers to `[rule:output]`. No AI / agent attribution in code, commits, or comments.
