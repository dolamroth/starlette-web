# Core application settings

APP_DEBUG = False
APPLICATION_CLASS = "starlette_web.common.app.BaseStarletteApplication"

SECRET_KEY = ""
INSTALLED_APPS = []
MIDDLEWARES = []
ROUTES = None

LOGGING = {}

# Used in contrib.auth
SITE_URL = "http://localhost:80"

# TODO: for future support of i18n
LANGUAGE_CODE = "en-us"

# Database settings

DB_ASYNC_SESSION_CLASS = "sqlalchemy.ext.asyncio.AsyncSession"
DB_USE_CONNECTION_POOL_FOR_MANAGEMENT_COMMANDS = False
DB_POOL_RECYCLE = 3600
DB_ECHO = False

# Must be overridden in user-defined settings
DATABASE_DSN = None

# Common.cache

CACHES = {
    "default": {
        "BACKEND": "starlette_web.common.caches.local_memory.LocalMemoryCache",
        "OPTIONS": {
            "name": "default",
        },
    },
}

# Common.http

ERROR_RESPONSE_SCHEMA = "starlette_web.common.http.schemas.ErrorResponseSchema"
DEFAULT_REQUEST_PARSER = "webargs_starlette.StarletteParser"
DEFAULT_RESPONSE_RENDERER = "starlette_web.common.http.renderers.JSONRenderer"

# Common.files

STORAGES = {
    "default": {
        "BACKEND": "starlette_web.common.files.storages.MediaFileSystemStorage",
    },
}

# Common.email

EMAIL_SENDER = None

# Contrib.auth

AUTH_PASSWORD_HASHERS = [
    "starlette_web.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"BACKEND": "starlette_web.contrib.auth.password_validation.NumericPasswordValidator"},
    {"BACKEND": "starlette_web.contrib.auth.password_validation.PasswordLengthValidator"},
    {"BACKEND": "starlette_web.contrib.auth.password_validation.UsernameSimilarityValidator"},
]

# see https://pyjwt.readthedocs.io/en/latest/algorithms.html for details
AUTH_JWT_EXPIRES_IN = 300  # 5 min
AUTH_JWT_REFRESH_EXPIRES_IN = 30 * 24 * 3600  # 30 days
AUTH_JWT_ALGORITHM = "HS512"
AUTH_INVITE_LINK_EXPIRES_IN = 3 * 24 * 3600  # 3 day
AUTH_RESET_PASSWORD_LINK_EXPIRES_IN = 3 * 3600  # 3 hours

# Contrib.constance

CONSTANCE_CONFIG = {}
CONSTANCE_DATABASE_CACHE_BACKEND = None
CONSTANCE_BACKEND = None

# Contrib.scheduler

PERIODIC_JOBS_BACKEND = None
