### ModelMixin helper methods

**Note**: This will probably change in the future, if better implementation is found.

All model classes are inherited from `sqlalchemy.orm.declarative_base`, 
which means they support all [declarative base methods](https://docs.sqlalchemy.org/en/20/orm/mapped_sql_expr.html#mapper-sql-expressions).

In addition, `starlette_web` provides a small subsets of methods, to more closely match the Django behavior.
These methods, however, have different names and only work for queries without join relations and subqueries.

- `prepare_query` - make a select query with passed `limit`, `offset`, `order_by` and `**kwargs`
- `to_dict`

All following methods require a `db_session: AsyncSession` input parameter, 
and all (except `async_get`) accept optional `db_commit=False` parameter.

- `async_filter`
- `async_get` - works as Django `.first`, i.e. always returns first found object or `None`
- `async_update`
- `async_delete`
- `async_create`
- `async_create_or_update`
- `async_get_or_create`
- `update`
- `delete`

All filter parameters allow using a certain set of non-relational lookups:
`eq, ne, lt, gt, is, in, notin, inarr, icontains`. Usage is similar to Django ORM:

```python
object = await Model.async_get(db_session=session, field__in=["value"], intfield__gt=5)
```
