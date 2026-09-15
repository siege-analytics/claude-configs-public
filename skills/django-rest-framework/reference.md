# Django REST Framework Reference Recipes

Load when the [SKILL.md](SKILL.md) decision tree points here for a specific recipe. Companion to `[`django-rest-framework`](../_django-rest-framework-rules.md)`, ``_django-rules.md` (planned)`, and `[`python`](../_python-rules.md)`.

## Serializers

### ModelSerializer with explicit allowlist

```python
from rest_framework import serializers
from .models import Donor

class DonorSerializer(serializers.ModelSerializer):
    contribution_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Donor
        fields = ["id", "name", "email", "created_at", "contribution_total"]
        read_only_fields = ["id", "created_at", "contribution_total"]
        extra_kwargs = {
            "email": {"write_only": False, "required": True},
        }
```

Never `fields = "__all__"` on a model that has sensitive columns. Never `Meta.depth`.

### Field-level and object-level validation

```python
class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = ["id", "donor", "amount", "contribution_date"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate(self, attrs):
        donor = attrs["donor"]
        if donor.is_foreign_national and attrs["amount"] > 0:
            raise serializers.ValidationError(
                "Foreign nationals cannot contribute."
            )
        return attrs
```

Single-field checks in `validate_<field>`. Cross-field checks in `validate()`. Uniqueness in `Meta.validators`, not `validate()`.

### Per-action serializer switch

```python
class DonorViewSet(viewsets.ModelViewSet):
    queryset = Donor.objects.all()
    permission_classes = [IsAuthenticated, IsDonorOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return DonorListSerializer   # compact
        if self.action in ("create", "update", "partial_update"):
            return DonorWriteSerializer  # accepts writable relations
        return DonorDetailSerializer     # full read shape
```

### Related fields, not nested serializers

```python
# GOOD -- one query per collection, client-controlled expansion
class DonationSerializer(serializers.ModelSerializer):
    donor = serializers.PrimaryKeyRelatedField(queryset=Donor.objects.all())
    committee = serializers.SlugRelatedField(
        slug_field="fec_id", queryset=Committee.objects.all(),
    )

    class Meta:
        model = Donation
        fields = ["id", "donor", "committee", "amount"]

# WHEN nested is genuinely required -- pair with prefetch in the viewset
class DonationWithDonorSerializer(serializers.ModelSerializer):
    donor = DonorSerializer(read_only=True)

    class Meta:
        model = Donation
        fields = ["id", "donor", "amount"]

class DonationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DonationWithDonorSerializer

    def get_queryset(self):
        return Donation.objects.select_related("donor").all()
```

## ViewSets

### ModelViewSet with per-action queryset

```python
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectMember]
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "owner"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        base = Project.objects.select_related("owner").prefetch_related("members")
        if self.action == "list":
            return base.filter(members=self.request.user)
        return base
```

### GenericAPIView for one action

```python
class ProjectArchiveView(generics.GenericAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectOwner]

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        project.archive(by_user=request.user)
        return Response(self.get_serializer(project).data)
```

## Permissions

### Object-level permission

```python
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsDonorOwnerOrReadOnly(BasePermission):
    """
    Read: any authenticated user.
    Write: only the donor's owning user.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id
```

### Composing permissions

```python
class DonorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated & (IsDonorOwner | IsStaffAuditor)]
```

`&`, `|`, `~` compose `BasePermission` subclasses without a custom class.

### Explicit object-permission check when bypassing get_object()

```python
class BulkArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids", [])
        projects = Project.objects.filter(id__in=ids)
        for project in projects:
            self.check_object_permissions(request, project)  # required
            project.archive(by_user=request.user)
        return Response(status=204)
```

## Pagination

### Cursor pagination for time-ordered feeds

```python
class DonationCursorPagination(pagination.CursorPagination):
    page_size = 50
    max_page_size = 200
    ordering = "-contribution_date"
    cursor_query_param = "cursor"
```

### Page-number pagination with max cap

```python
class ProjectPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
```

Never omit `max_page_size` / `max_limit`. An unbounded page size is a DoS primitive.

## Throttling

### Scoped rate throttle

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "1000/hour",
        "login": "5/minute",
        "password_reset": "3/hour",
        "bulk_export": "10/day",
    },
}

# views.py
class LoginView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
```

## Testing

### APITestCase happy + failure paths

```python
from rest_framework import status
from rest_framework.test import APITestCase
from .factories import UserFactory, ProjectFactory

class ProjectViewSetTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.project = ProjectFactory(owner=self.user)

    def test_list_returns_only_own_projects(self):
        ProjectFactory(owner=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/projects/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == self.project.id

    def test_unauthenticated_returns_401(self):
        response = self.client.get("/api/projects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_user_cannot_update_returns_403(self):
        self.client.force_authenticate(self.other_user)
        response = self.client.patch(
            f"/api/projects/{self.project.id}/", {"name": "hacked"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_returns_404(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/projects/99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_payload_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/projects/", {"name": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data
```

### pytest-django + APIClient fixture

```python
# conftest.py
import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user)
    return api_client

# test_projects.py
def test_list_projects(authenticated_client, project):
    response = authenticated_client.get("/api/projects/")
    assert response.status_code == 200
    assert response.data["count"] == 1
```

## Schema documentation

### drf-spectacular setup

```python
# settings.py
INSTALLED_APPS = [..., "drf_spectacular"]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Project API",
    "DESCRIPTION": "Contribution tracking API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

### @extend_schema for cases introspection cannot handle

```python
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class ProjectViewSet(viewsets.ModelViewSet):
    @extend_schema(
        request=ProjectArchiveRequestSerializer,
        responses={
            204: OpenApiResponse(description="Archived successfully."),
            409: OpenApiResponse(description="Already archived."),
        },
        examples=[
            OpenApiExample(
                "Archive with note",
                value={"note": "End of fiscal year."},
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive the project. Idempotent; already-archived returns 409."""
        ...
```

### Schema in CI

```yaml
# .github/workflows/schema-diff.yml
- name: Generate schema
  run: python manage.py spectacular --file schema.yml
- name: Check for uncommitted schema drift
  run: git diff --exit-code schema.yml
```

Uncommitted schema drift is a silent contract break; the CI diff turns it into a review conversation.

## Versioning

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1", "v2"],
}

# urls.py
urlpatterns = [
    path("api/<version>/", include("projects.urls")),
]

# views.py -- dispatch on request.version
class ProjectViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.request.version == "v2":
            return ProjectV2Serializer
        return ProjectV1Serializer
```
