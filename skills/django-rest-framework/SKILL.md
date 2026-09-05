---
name: django-rest-framework
description: "Django REST Framework conventions for serializers, viewsets, permissions, pagination, throttling, testing, and OpenAPI schema. TRIGGER: *.py importing from rest_framework.*, writing a serializer/viewset/permission/DRF test, or configuring REST_FRAMEWORK settings. Stacks on top of the django skill."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py"
---

# Django REST Framework

## Companion shelves

Parent skill: `[skill:django]` -- ORM, models, migrations, settings stratification, factory_boy patterns all apply here unchanged. Read that first.

Complementary rule shelves:
- `[rule:python]` -- always-on Python style.
- `[rule:django-rest-framework]` -- the numbered principles this skill operationalizes.
- `[rule:testing-frameworks]` -- test framework declaration in PROJECT.md; DRF tests declare `rest_framework.test.APITestCase` or `pytest-django` + `APIClient` fixtures.
- `[rule:writing-releases]` -- deprecation and BREAKING discipline for versioned endpoints.
- `[rule:data-trust]` -- serializer input is untrusted data; validate at the boundary.

Apply when editing code that imports `rest_framework.*`. See [reference.md](reference.md) for recipe snippets (paginators, custom permissions, `@extend_schema` patterns, common test shapes).

Draws from:
- DRF docs -- <https://www.django-rest-framework.org/> (Tom Christie; the framework's canonical reference)
- William S. Vincent -- *Django for APIs* (test-first DRF for Django 5.x)
- Adam Johnson -- adamj.eu (operational patterns, performance)
- `drf-spectacular` docs -- OpenAPI 3.1 schema generation

## Decision tree

```
START: I'm writing DRF code
  │
  ├─ What am I building?
  │   ├─ A serializer
  │   │   ├─ 1:1 with a model, standard CRUD → ModelSerializer with explicit fields = [...]
  │   │   ├─ Cross-model payload / external state → Serializer (not ModelSerializer)
  │   │   ├─ Write shape differs from read shape → two serializers, dispatch via get_serializer_class()
  │   │   └─ Reaching for Meta.depth → STOP; use nested serializer explicitly with select_related, or use PrimaryKeyRelatedField
  │   │
  │   ├─ A viewset / view
  │   │   ├─ Full CRUD on a queryset → ModelViewSet
  │   │   ├─ Subset of verbs (read-only, list-only) → GenericViewSet + specific mixins
  │   │   ├─ One custom action, still queryset-backed → GenericAPIView + mixin
  │   │   └─ Not queryset-backed at all (auth, webhook, RPC) → APIView
  │   │
  │   ├─ A permission
  │   │   ├─ Resource-kind gate (owner-or-readonly, project member) → custom BasePermission with has_object_permission
  │   │   ├─ Composing multiple invariants → compose existing classes with &, |, ~
  │   │   └─ "Just is_staff" → STOP; is_staff is a Django-admin flag, not a business role
  │   │
  │   ├─ A test → APITestCase or pytest-django + APIClient; test the failure modes explicitly (401, 403, 404, 400)
  │   │
  │   └─ Schema documentation → drf-spectacular; docstring on the viewset action; @extend_schema only for edge cases
  │
  ├─ Is this endpoint public / third-party consumable?
  │   ├─ YES → versioning MUST be in place; throttling MUST distinguish anon vs auth; pagination MUST have max_page_size
  │   └─ NO (internal / admin) → pagination and throttling still required; versioning optional if consumer is deployed together
  │
  └─ Does the queryset span multiple joins?
      ├─ Add select_related / prefetch_related in get_queryset()
      └─ Never trust nested serializers to be free; profile query count
```

## What lives where

| Concern | Lives in | Does not live in |
|---|---|---|
| Field validation (single field) | `validate_<field>` on serializer | View, permission, model save() |
| Cross-field validation | `validate()` on serializer | View, model clean() (which DRF does not call) |
| Uniqueness across fields | `UniqueTogetherValidator` in `Meta.validators` | `validate()` (loses DRF error shape) |
| Auth check | Permission class (`IsAuthenticated`) | View body, serializer |
| Ownership / object-level access | `has_object_permission` on permission class | View `get_object()` override |
| Per-action serializer switch | `get_serializer_class()` dispatching on `self.action` | `dispatch()`, `initial()` |
| Per-action queryset filter | `get_queryset()` dispatching on `self.action` | `list()` / `retrieve()` overrides |
| Response envelope | Pagination class or custom `Response` | View body per-request |
| Rate limit | Throttle class as class attribute | Middleware, view body |

## Common DRF mistakes

| Smell | Why | Fix |
|---|---|---|
| `fields = "__all__"` on a model with sensitive fields | Password / admin flag exposed via API | Explicit `fields = [...]` allowlist |
| `Meta.depth = 2` for "nice nested output" | Uncontrolled N+1; hides schema | Nested serializer + `select_related` / `prefetch_related` |
| `IsAuthenticated` alone on user-scoped endpoint | Any user can read/write any other user's data | Compose with object-level permission |
| Rolling own object lookup in `get_object()` | Bypasses `has_object_permission` | Call `self.check_object_permissions(request, obj)` explicitly |
| `PageNumberPagination` with no `max_page_size` | `?page_size=100000` DoSes the DB | Set `max_page_size` on every pagination class |
| `ModelViewSet` mounted on user model with default serializer | `PATCH /users/1/ {"is_staff": true}` escalates privilege | Explicit `fields`, explicit permission |
| Validation logic in `perform_create()` | Bypasses DRF error shape; not reused | `validate()` on serializer |
| `Meta.exclude` used defensively | Silent inclusion when new field is added to model | Explicit `fields = [...]` |
| Test asserts `response.status_code == 200` (int) | Reads as magic number | `status.HTTP_200_OK` |
| Test asserts against `response.content` | Byte-level; brittle to serializer format changes | Assert against `response.data` |
| Nested serializer writes without `create()` / `update()` | DRF raises "not writable" at runtime | Implement `create()` / `update()` on the parent serializer, or split write endpoint |
| Version added retroactively | Existing clients break; no migration path | Version at bootstrap; document the deprecation timeline |
| `drf-yasg` in a new project | Stuck on Swagger 2.0; no OpenAPI 3.x support | `drf-spectacular` |

## Serializer / viewset / permission split

The rule of thumb inherited from `[skill:django]`'s "fat models, thin views" doctrine:

- **Model** owns business invariants and domain operations (unchanged from `[skill:django]`).
- **Serializer** owns the wire-format contract: field shapes, input validation, output projection. Serializers do not know about HTTP.
- **ViewSet** owns the HTTP-to-queryset orchestration: which serializer per action, which queryset per action, permission composition, pagination, throttling. ViewSets do not know about validation.
- **Permission** owns the access-control invariant: given a request and (optionally) an object, is this allowed? Permissions do not know about serializers or querysets.

A serializer that reaches into `self.context["request"].user` for anything other than filtering `queryset` on a `PrimaryKeyRelatedField` is doing permission work in the wrong layer. A viewset that hand-rolls validation is doing serializer work in the wrong layer.

## Testing surface

Every viewset MUST have tests for:

1. **200 / 201 happy path** -- authenticated user with correct role, valid payload, expected response shape.
2. **401 unauthenticated** -- no credentials; expect `HTTP_401_UNAUTHORIZED`.
3. **403 forbidden** -- authenticated but wrong role or wrong object owner; expect `HTTP_403_FORBIDDEN`.
4. **404 not-found** -- valid credentials, `pk` that does not exist (or does not belong to user); expect `HTTP_404_NOT_FOUND`.
5. **400 validation failure** -- authenticated, one field invalid; expect `HTTP_400_BAD_REQUEST` and the field-shaped error dict.
6. **Pagination / ordering / filter shape** (list actions only) -- assert `count`, `next`, `previous`, `results`; assert ordering param; assert filter param.

Missing any of 1-5 for a viewset action is a test-gap that composes with `[rule:writing-tests]` writing-tests:5 (every `except` block exercised). DRF handlers translate exceptions to HTTP responses; the handler branch is untested until the failure path is asserted.

## References

- DRF docs -- <https://www.django-rest-framework.org/>
- Vincent -- *Django for APIs* 5.x
- Adam Johnson -- adamj.eu (tag: `drf`)
- `drf-spectacular` -- <https://drf-spectacular.readthedocs.io/>
- Tom Christie's original REST Framework talks and blog posts at <https://www.dabapps.com/insights/>

## Attribution Policy

See `[rule:output]`. NEVER include AI or agent attribution.
