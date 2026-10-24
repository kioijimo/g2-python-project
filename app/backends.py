from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class ActiveSessionBackend(ModelBackend):
    """
    Recognize inactive users from their existing session.

    Login still rejects inactive accounts through ModelBackend.authenticate(),
    but this lets the access decorators see a deactivated session so they can
    log it out instead of silently treating it as anonymous.
    """

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
