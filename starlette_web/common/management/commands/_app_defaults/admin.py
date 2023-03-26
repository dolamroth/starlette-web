# flake8: noqa

from starlette_web.contrib.admin import AdminView, admin


"""
Initialize your AdminView's in this file. 
It will be automatically introspected, 
if you add "starlette_web.contrib.admin" and this app's name to settings.INSTALLED_APPS

>>> class ModelView(AdminView):
>>>     pass
>>>
>>> admin.add_view(ModelView(Model, icon="fa fa-users"))
"""
