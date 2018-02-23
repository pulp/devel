django\_db
==========

Create and run migrations

When executed, this role will:

1. Create migrations for the Pulp application with label `app_label`.
2. Run all migrations.

Sample invocation from a role:

```yaml
- include_role:
    name: django_db
  vars:
    app_label: my_app
```
