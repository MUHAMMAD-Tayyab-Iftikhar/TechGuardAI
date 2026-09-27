import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyACWjMkiGhiBRhr5tSK_nZ0Eq_LIGYG298",
    "authDomain": "techguard-ai.firebaseapp.com",
    "databaseURL": "",
    "projectId": "techguard-ai",
    "storageBucket": "techguard-ai.firebasestorage.app",
    "messagingSenderId": "379561012456",
    "appId": "1:379561012456:web:5243f5f59e75b5dbbd2d5d"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth     = firebase.auth()


def sign_up(email, password):
    """Create a new account and immediately send a verification email."""
    user = auth.create_user_with_email_and_password(email, password)
    auth.send_email_verification(user["idToken"])
    return user


def sign_in(email, password):
    """Sign in and return the user object (idToken included)."""
    return auth.sign_in_with_email_and_password(email, password)


def reset_password(email):
    """Send a password-reset link to the given email."""
    return auth.send_password_reset_email(email)


def is_email_verified(id_token: str) -> bool:
    """Return True only if the user has clicked the verification link."""
    try:
        info = auth.get_account_info(id_token)
        return info["users"][0]["emailVerified"]
    except Exception:
        return False