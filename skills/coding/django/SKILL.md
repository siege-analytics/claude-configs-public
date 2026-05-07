---
name: django
description: "Django conventions for models, views, settings, forms, and testing. TRIGGER: *.py importing from django.*, writing a view/model/form/migration, or configuring settings. Stacks with python and sql sub-skills."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py,**/settings/*.py"
---

# Django

## Companion shelves

For service-boundary and modeling rationale:
- [skill:clean-architecture] — keep frameworks at the edges, not in the domain.
- [skill:domain-driven-design] — aggregates, bounded contexts when the app grows.

Apply when editing code that imports `django.*`. See [reference.md](reference.md) for deployment, security hardening, and recipe-style snippets.

Draws from:
- Greenfeld & Greenfeld — *Two Scoops of Django 3.x* (the "fat models, thin views" canon)
- Will Vincent — *Django for Professionals* (Django 5.x, test-first approach)
- Adam Johnson's blog (adamj.eu) — continuously updated patterns

## Decision tree

```
START: I'm writing Django code
  │
  ├─ What am I building?
  │   ├─ A model → fat model; put ALL business logic on the model, managers, or QuerySet methods
  │   ├─ A view → thin view; orchestrate; defer to model methods
  │   ├─ A form → represents user input; validation lives here, not on the model
  │   ├─ A template tag → last resort; prefer context processors or model methods
  │   └─ A management command → business logic stays on models; command is the entry point
  │
  ├─ Is this recurring logic?
  │   ├─ YES → QuerySet method on a custom Manager, NOT duplicated across views
  │   └─ NO → one-off; still consider extracting if a second use-site shows up
  │
  └─ Does this need to run async?
      ├─ Rare; Django's sync-first model is fine for most workloads
      └─ If yes → ASGI + asyncio, but understand the ORM sync constraints first
```

## Settings stratification

Never one `settings.py`. Split by environment:

```
config/
├── settings/
│   ├── __init__.py
│   ├── base.py         # Shared across all envs
│   ├── development.py  # DEBUG=True, dev toolbar, SQLite OK
│   ├── staging.py      # production-like, separate DB
│   ├── production.py   # DEBUG=False, real SECRET_KEY from env
│   └── test.py         # fast in-memory DB, disabled migrations
```

`manage.py` picks via `DJANGO_SETTINGS_MODULE`:
```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
```

**Never** commit real secrets. `.env` + `django-environ` is standard:
```python
# settings/base.py
from environ import Env
env = Env()
env.read_env()

SECRET_KEY = env("DJANGO_SECRET_KEY")
DATABASE_URL = env.db_url("DATABASE_URL")
```

## Models — fat, with intent

```python
class Donation(models.Model):
    contributor = models.ForeignKey("Contributor", on_delete=models.PROTECT)
    committee = models.ForeignKey("Committee", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    contribution_date = models.DateField()

    # Managers
    objects = models.Manager()
    published = PublishedDonationManager()

    class Meta:
        indexes = [
            models.Index(fields=["committee", "contribution_date"]),
            models.Index(fields=["contributor"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="donation_amount_positive",
            ),
        ]

    # Intent-named predicates
    @property
    def is_individual_over_limit(self) -> bool:
        return self.amount > INDIVIDUAL_CONTRIBUTION_LIMIT

    # Domain operations
    def mark_reviewed(self, by_user, *, note: str = "") -> None:
        self.review_status = self.ReviewStatus.APPROVED
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "review_note"])
```

**Rules:**
- `on_delete` explicit (PROTECT or CASCADE, not SET_NULL unless you mean it)
- Indexes defined in `Meta.indexes`, not as `db_index=True` on fields (easier to audit)
- Check constraints at the DB level, not just Python (they survive direct SQL writes)
- `save(update_fields=...)` when you're only changing specific fields — avoids race conditions and unnecessary signal firing

## QuerySet / Manager methods — the real interface

Logic that filters, annotates, or aggregates belongs on a custom QuerySet:

```python
class DonationQuerySet(models.QuerySet):
    def for_cycle(self, cycle: int):
        return self.filter(cycle=cycle)

    def over_limit(self):
        return self.filter(amount__gt=INDIVIDUAL_CONTRIBUTION_LIMIT)

    def with_contributor_totals(self):
        return self.annotate(
            contributor_total=models.Sum("contributor__donations__amount"),
        )


class PublishedDonationManager(models.Manager):
    def get_queryset(self):
        return DonationQuerySet(self.model, using=self._db).filter(published=True)


# Usage — composable in views
Donation.published.for_cycle(2024).over_limit().with_contributor_totals()
```

A view that reaches for `Donation.objects.filter(...)` with complex conditions is a missed QuerySet method.

## Views — thin

```python
# BAD — business logic in view
def donor_report(request, donor_id):
    donor = Contributor.objects.get(id=donor_id)
    donations = Donation.objects.filter(contributor=donor, published=True)
    total = sum(d.amount for d in donations)
    over = [d for d in donations if d.amount > 2900]
    return render(request, "donor_report.html", {"donor": donor, "total": total, "over": over})

# GOOD — view orchestrates
def donor_report(request, donor_id):
    donor = get_object_or_404(Contributor, id=donor_id)
    return render(request, "donor_report.html", {
        "donor": donor,
        "stats": donor.contribution_stats(),  # model method
    })
```

Class-based views are fine when inheritance genuinely helps. Function-based views are fine when they don't. Don't adopt one style dogmatically.

## Migrations

- **Squash old migrations** only when you can coordinate deployment. Never on a branch with concurrent feature work.
- **Data migrations run one-way.** Write a reverse if you can; if you can't, make the forward migration idempotent.
- **Never edit an applied migration** in shared environments. Add a new one.
- **Check for long locks.** Adding a NOT NULL column with a default on a 50M-row table locks for minutes. Two-step migration: add nullable → backfill → set NOT NULL.
- **Test the rollback.** If you can't roll a migration back (or forward over the rolled-back state), it's a one-way door.

## Forms — where input validation lives

```python
class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ["contributor", "committee", "amount", "contribution_date"]

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise ValidationError("Amount must be positive.")
        return amount

    def clean(self):
        cleaned = super().clean()
        # Cross-field validation only; single-field stays in clean_<field>
        if cleaned.get("contributor") and cleaned.get("amount"):
            if cleaned["contributor"].is_foreign_national and cleaned["amount"] > 0:
                raise ValidationError("Foreign nationals cannot contribute.")
        return cleaned
```

Don't duplicate validation on both the form AND the model `save()` — pick one layer. Generally form for user input, model for API / programmatic writes.

## Signals — almost always wrong

Greenfield rule from *Two Scoops*: **don't use signals for new code.** Instead:

- Use an overridden `save()` method on the model
- Use a `@classmethod create_with_side_effects(...)` factory
- Use an explicit service function called from the view/task

Signals hide control flow. A new contributor in `Donation.save()` who reads the 50-line save method will never discover the `post_save` handler in `auth/signals.py` that fires a webhook. That's a support ticket waiting to happen.

If you already have signals (migrating from old code), document them in the model docstring and in `AppConfig.ready()`.

## Testing

- **pytest-django** over `django.test.TestCase` for modern projects. Cleaner fixture model.
- **factory_boy** for test data, NOT JSON fixtures (which rot).
  ```python
  class DonationFactory(factory.django.DjangoModelFactory):
      class Meta:
          model = Donation
      contributor = factory.SubFactory(ContributorFactory)
      committee = factory.SubFactory(CommitteeFactory)
      amount = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
      contribution_date = factory.Faker("date_this_year")
  ```
- **Disable migrations in tests** for speed (`--no-migrations` flag with `pytest-django`; use `SQLITE` in-memory DB for unit tests; keep a full-migration test for release verification).
- **Test QuerySets and model methods directly**, not through views. Views become thin integration tests.

## Performance

- **`select_related`** for ForeignKey followers. **`prefetch_related`** for reverse relations and ManyToMany. Profile before optimizing — Django Debug Toolbar shows the query count.
- **Bulk operations** beat loops:
  ```python
  Donation.objects.bulk_create(new_donations, batch_size=1000)
  Donation.objects.filter(cycle=2024).update(status="archived")
  ```
- **N+1 detection** with `django-n-plus-one` or `nplusone`. Add to dev settings.
- **Raw SQL** is fine for performance-critical paths. Wrap in a manager method so the surface remains ORM-shaped.

## Deployment essentials

- **WSGI**: Gunicorn (battle-tested) or uWSGI (older but fine). Not `runserver` in production.
- **ASGI**: Uvicorn + Gunicorn worker class for async views.
- **Static files**: WhiteNoise (simplest) or S3/CloudFront via django-storages. `collectstatic` at deploy time.
- **Health endpoint**: `/healthz` returning 200 — probes should pass only when the DB connection is healthy, not just `HttpResponse("ok")`.
- **Logging**: structlog or Python's stdlib `logging` with JSON output to stdout (12-factor). Do NOT write to files in containerized environments.

## Anti-patterns (Two Scoops's list + current)

| Smell | Why | Fix |
|---|---|---|
| One gigantic `views.py` | Hard to navigate | Package `views/` with one file per resource |
| Model methods named `get_X()` | Confuses with getter pattern, shadows `.get()` | Name for intent: `primary_email`, `calculate_total` |
| Business logic in templates | Uneditable, untestable | Move to model methods or template tags |
| Raw SQL in views | Bypasses ORM safety, brittle | Manager method wrapping the SQL |
| Settings.py with 500+ lines | Can't diff environments | Stratify into `settings/` package |
| Direct `.filter()` chains in views | Logic scattered, can't test | QuerySet method |
| `post_save` signals for anything important | Invisible control flow | Explicit service function |
| Fat `forms.py` with template literals in `render()` | Presentation leaks into logic | Use templates + form widgets |
| `make_related` fixtures | Rot quickly; fragile | factory_boy with SubFactory |
| `USE_TZ = False` | Timezone bugs downstream | Always True; store UTC |

## References

- Greenfeld & Greenfeld — *Two Scoops of Django 3.x* (principal source for doctrine)
- Will Vincent — *Django for Professionals* 5.x (current, test-first)
- Adam Johnson — adamj.eu (continuously updated; the current canonical blog)
- Django docs — docs.djangoproject.com/en/stable/ (always newer than any book)
- `django-upgrade` — automated migration tool between Django versions

## Attribution Policy

See [rule:output]. NEVER include AI or agent attribution.
