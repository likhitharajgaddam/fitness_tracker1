from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticate against Django's User model using either a username
    (exact or case-insensitive) or a registered email address (case-insensitive).

    Always validates passwords using Django's salted password hash verification
    (check_password) and respects user_can_authenticate() (is_active).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username
        if identifier is None:
            identifier = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get("email")

        if not identifier or password is None:
            return None

        identifier = str(identifier).strip()
        if not identifier:
            return None

        candidates = []
        seen_ids = set()

        # 1. Exact username match first
        exact_user = UserModel._default_manager.filter(
            **{UserModel.USERNAME_FIELD: identifier}
        ).first()
        if exact_user is not None:
            candidates.append(exact_user)
            seen_ids.add(exact_user.pk)

        # 2. Case-insensitive username match
        for user in UserModel._default_manager.filter(
            **{f"{UserModel.USERNAME_FIELD}__iexact": identifier}
        ).order_by("pk"):
            if user.pk not in seen_ids:
                candidates.append(user)
                seen_ids.add(user.pk)

        # 3. Case-insensitive email match
        if "@" in identifier:
            for user in UserModel._default_manager.filter(
                email__iexact=identifier
            ).order_by("pk"):
                if user.pk not in seen_ids:
                    candidates.append(user)
                    seen_ids.add(user.pk)

        if not candidates:
            # Run the default password hasher once to reduce timing difference
            # between existing and non-existing users.
            UserModel().set_password(password)
            return None

        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None
