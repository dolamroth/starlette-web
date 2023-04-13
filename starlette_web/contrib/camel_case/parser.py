from webargs_starlette import StarletteParser

from starlette_web.contrib.camel_case.utils import underscoreize


class CamelCaseStarletteParser(StarletteParser):
    async def _async_load_location_data(self, schema, req, location):
        data = await super()._async_load_location_data(schema, req, location)
        return underscoreize(data, no_underscore_before_number=True)
