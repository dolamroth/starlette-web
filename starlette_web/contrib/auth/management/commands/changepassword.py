from starlette_web.common.management.base import BaseCommand, CommandError
from starlette_web.contrib.auth.models import User
from starlette_web.contrib.auth.management.auth_command_mixin import AuthCommandMixin


class Command(AuthCommandMixin, BaseCommand):
    help = "Create a user with admin privileges"

    async def handle(self, **options):
        async with self.app.session_maker() as session:
            email = self.get_input_data("Input email (username): ")
            self.validate_field("email", email)
            user = await User.async_get(db_session=session, email=email)
            if user is None:
                raise CommandError(details=f"User with email = {email} not found.")

            password_1 = self.get_input_data("Input new password: ")
            self.validate_field("password", password_1)
            password_2 = self.get_input_data("Retype new password: ")
            if password_1 != password_2:
                raise CommandError(details="Password mismatch.")

            await User.async_update(
                db_session=session,
                db_commit=True,
                filter_kwargs=dict(email=email),
                update_data=dict(password=User.make_password(password_1)),
            )

            # TODO: use logging ?
            print(f"Password for user {user} updated successfully.")
