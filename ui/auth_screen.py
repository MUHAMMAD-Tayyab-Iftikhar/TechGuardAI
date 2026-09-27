"""
ui/auth_screen.py
-----------------
Premium login / sign-up / forgot-password screen for TechGuardAI.

Improvements in this version
─────────────────────────────
• Email verification enforced on login
• Show / Hide password toggle on all password fields
• Firebase footer branding removed
• Proper confirm-password & length validation
• Clean, specific user-facing status messages
"""

import threading
import customtkinter as ctk

# ── Palette ───────────────────────────────────────────────────────────────────
_BG           = "#0a0f1e"
_CARD_BG      = "#111827"
_CARD_BORDER  = "#1e3a5f"
_INPUT_BG     = "#1c2a3a"
_INPUT_BORDER = "#2a4a6a"
_ACCENT       = "#3b82f6"
_ACCENT_HOVER = "#2563eb"
_SECONDARY    = "#1e3a5f"
_SECONDARY_HV = "#1e40af"
_TEXT_PRIMARY = "#e2e8f0"
_TEXT_MUTED   = "#64748b"
_ERROR        = "#ef4444"
_SUCCESS      = "#22c55e"
_WARNING      = "#f59e0b"


class AuthScreen(ctk.CTkFrame):
    """
    Fullscreen authentication gate.
    Calls `on_success(email)` after a confirmed, verified login.
    """

    def __init__(self, master, on_success):
        super().__init__(master, fg_color=_BG)
        self._on_success = on_success
        self._mode       = "login"          # "login" | "signup" | "forgot"
        self._show_pw    = False            # password visibility state

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_card()

    # ─────────────────────────────────────────────────────────────────────────
    # Card
    # ─────────────────────────────────────────────────────────────────────────

    def _build_card(self):
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)

        self._card = ctk.CTkFrame(
            center,
            fg_color=_CARD_BG,
            corner_radius=20,
            border_width=1,
            border_color=_CARD_BORDER,
            width=440,
        )
        self._card.pack()
        self._card.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_fields()
        self._build_actions()
        self._build_status()
        # Footer branding intentionally omitted

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self._card, fg_color="transparent")
        hdr.grid(row=0, column=0, pady=(36, 0), padx=40, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="⚡  TechGuard AI",
            font=("Roboto Medium", 26, "bold"),
            text_color=_TEXT_PRIMARY,
        ).grid(row=0, column=0)

        ctk.CTkLabel(
            hdr,
            text="AI-Powered System Assistant",
            font=("Roboto", 12),
            text_color=_TEXT_MUTED,
        ).grid(row=1, column=0, pady=(4, 0))

        ctk.CTkFrame(hdr, height=2, fg_color=_ACCENT, corner_radius=2
                     ).grid(row=2, column=0, sticky="ew", pady=(18, 0))

        self._title_lbl = ctk.CTkLabel(
            hdr, text="Welcome Back",
            font=("Roboto Medium", 18, "bold"), text_color=_TEXT_PRIMARY,
        )
        self._title_lbl.grid(row=3, column=0, pady=(18, 0))

        self._subtitle_lbl = ctk.CTkLabel(
            hdr, text="Sign in to your account to continue",
            font=("Roboto", 12), text_color=_TEXT_MUTED,
        )
        self._subtitle_lbl.grid(row=4, column=0, pady=(4, 0))

    # ── Fields ────────────────────────────────────────────────────────────────

    def _build_fields(self):
        f = ctk.CTkFrame(self._card, fg_color="transparent")
        f.grid(row=1, column=0, padx=40, pady=(28, 0), sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        self._fields_frame = f

        # ── Email ──
        ctk.CTkLabel(f, text="Email Address",
                     font=("Roboto Medium", 12), text_color=_TEXT_MUTED,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._email_var = ctk.StringVar()
        self._email_entry = ctk.CTkEntry(
            f, textvariable=self._email_var,
            placeholder_text="you@example.com",
            fg_color=_INPUT_BG, border_color=_INPUT_BORDER, border_width=1,
            text_color=_TEXT_PRIMARY, placeholder_text_color=_TEXT_MUTED,
            corner_radius=10, height=44, font=("Roboto", 13),
        )
        self._email_entry.grid(row=1, column=0, sticky="ew")

        # ── Password ──
        self._pw_label = ctk.CTkLabel(f, text="Password",
                                      font=("Roboto Medium", 12),
                                      text_color=_TEXT_MUTED, anchor="w")
        self._pw_label.grid(row=2, column=0, sticky="w", pady=(14, 4))

        self._pw_var = ctk.StringVar()
        self._pw_entry = ctk.CTkEntry(
            f, textvariable=self._pw_var,
            placeholder_text="••••••••", show="•",
            fg_color=_INPUT_BG, border_color=_INPUT_BORDER, border_width=1,
            text_color=_TEXT_PRIMARY, placeholder_text_color=_TEXT_MUTED,
            corner_radius=10, height=44, font=("Roboto", 13),
        )
        self._pw_entry.grid(row=3, column=0, sticky="ew")

        # ── Confirm Password (signup only) ──
        self._cpw_label = ctk.CTkLabel(f, text="Confirm Password",
                                       font=("Roboto Medium", 12),
                                       text_color=_TEXT_MUTED, anchor="w")
        self._cpw_var = ctk.StringVar()
        self._cpw_entry = ctk.CTkEntry(
            f, textvariable=self._cpw_var,
            placeholder_text="••••••••", show="•",
            fg_color=_INPUT_BG, border_color=_INPUT_BORDER, border_width=1,
            text_color=_TEXT_PRIMARY, placeholder_text_color=_TEXT_MUTED,
            corner_radius=10, height=44, font=("Roboto", 13),
        )
        # Hidden until signup mode

        # ── Show / Hide password checkbox ──
        self._show_pw_var = ctk.BooleanVar(value=False)
        self._show_pw_chk = ctk.CTkCheckBox(
            f,
            text="Show Password",
            variable=self._show_pw_var,
            font=("Roboto", 12),
            text_color=_TEXT_MUTED,
            fg_color=_ACCENT,
            hover_color=_ACCENT_HOVER,
            checkmark_color="#ffffff",
            border_color=_INPUT_BORDER,
            corner_radius=5,
            command=self._toggle_pw_visibility,
        )
        self._show_pw_chk.grid(row=4, column=0, sticky="w", pady=(10, 0))

        # ── Forgot password link ──
        self._forgot_btn = ctk.CTkButton(
            f, text="Forgot Password?",
            fg_color="transparent", hover_color=_CARD_BG,
            text_color=_ACCENT, font=("Roboto", 12),
            height=20, anchor="e", command=self._show_forgot,
        )
        self._forgot_btn.grid(row=5, column=0, sticky="e", pady=(6, 0))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _build_actions(self):
        a = ctk.CTkFrame(self._card, fg_color="transparent")
        a.grid(row=2, column=0, padx=40, pady=(20, 0), sticky="ew")
        a.grid_columnconfigure(0, weight=1)
        self._actions_frame = a

        self._primary_btn = ctk.CTkButton(
            a, text="Sign In",
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            text_color="#ffffff", font=("Roboto Medium", 14, "bold"),
            height=46, corner_radius=12, command=self._handle_primary,
        )
        self._primary_btn.grid(row=0, column=0, sticky="ew")

        ctk.CTkFrame(a, fg_color="transparent", height=12).grid(row=1, column=0)

        self._secondary_btn = ctk.CTkButton(
            a, text="Create Account",
            fg_color=_SECONDARY, hover_color=_SECONDARY_HV,
            text_color=_TEXT_PRIMARY, font=("Roboto Medium", 13),
            height=42, corner_radius=12, command=self._show_signup,
        )
        self._secondary_btn.grid(row=2, column=0, sticky="ew")

        self._back_btn = ctk.CTkButton(
            a, text="← Back to Sign In",
            fg_color="transparent", hover_color=_CARD_BG,
            text_color=_TEXT_MUTED, font=("Roboto", 12),
            height=28, command=self._show_login,
        )
        # Hidden until signup / forgot mode

    # ── Status ────────────────────────────────────────────────────────────────

    def _build_status(self):
        self._status_lbl = ctk.CTkLabel(
            self._card, text="",
            font=("Roboto Medium", 12), text_color=_ERROR,
            wraplength=360, justify="center",
        )
        self._status_lbl.grid(row=3, column=0, padx=40, pady=(12, 28))

    # ─────────────────────────────────────────────────────────────────────────
    # Show / Hide password
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_pw_visibility(self):
        char = "" if self._show_pw_var.get() else "•"
        self._pw_entry.configure(show=char)
        self._cpw_entry.configure(show=char)

    # ─────────────────────────────────────────────────────────────────────────
    # Mode switches
    # ─────────────────────────────────────────────────────────────────────────

    def _show_login(self):
        self._mode = "login"
        self._clear_status()

        self._title_lbl.configure(text="Welcome Back")
        self._subtitle_lbl.configure(text="Sign in to your account to continue")
        self._primary_btn.configure(text="Sign In",
                                    fg_color=_ACCENT, hover_color=_ACCENT_HOVER)

        self._pw_label.grid()
        self._pw_entry.grid()
        self._cpw_label.grid_remove()
        self._cpw_entry.grid_remove()

        self._show_pw_chk.grid()
        self._forgot_btn.grid()
        self._secondary_btn.configure(text="Create Account",
                                      command=self._show_signup)
        self._secondary_btn.grid()
        self._back_btn.grid_remove()

    def _show_signup(self):
        self._mode = "signup"
        self._clear_status()

        self._title_lbl.configure(text="Create Account")
        self._subtitle_lbl.configure(text="Join TechGuardAI — it's free")
        self._primary_btn.configure(text="Sign Up",
                                    fg_color=_ACCENT, hover_color=_ACCENT_HOVER)

        self._pw_label.grid()
        self._pw_entry.grid()
        self._cpw_label.grid(row=5, column=0, sticky="w", pady=(14, 4))
        self._cpw_entry.grid(row=6, column=0, sticky="ew")

        # Move show-pw checkbox and remove forgot link
        self._show_pw_chk.grid(row=7, column=0, sticky="w", pady=(10, 0))
        self._forgot_btn.grid_remove()
        self._secondary_btn.grid_remove()
        self._back_btn.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def _show_forgot(self):
        self._mode = "forgot"
        self._clear_status()

        self._title_lbl.configure(text="Reset Password")
        self._subtitle_lbl.configure(text="Enter your email to receive a reset link")
        self._primary_btn.configure(text="Send Reset Link",
                                    fg_color=_WARNING, hover_color="#d97706")

        self._pw_label.grid_remove()
        self._pw_entry.grid_remove()
        self._cpw_label.grid_remove()
        self._cpw_entry.grid_remove()
        self._show_pw_chk.grid_remove()
        self._forgot_btn.grid_remove()
        self._secondary_btn.grid_remove()
        self._back_btn.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # Primary button handler
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_primary(self):
        email   = self._email_var.get().strip()
        pw      = self._pw_var.get()
        confirm = self._cpw_var.get()

        if not email:
            self._show_status("Please enter your email address.", _ERROR)
            return

        if self._mode == "forgot":
            self._run_async(self._do_forgot, email)
            return

        if not pw:
            self._show_status("Please enter your password.", _ERROR)
            return

        if self._mode == "signup":
            if len(pw) < 6:
                self._show_status("Password must be at least 6 characters.", _ERROR)
                return
            if pw != confirm:
                self._show_status("Passwords do not match.", _ERROR)
                return
            self._run_async(self._do_signup, email, pw)
        else:
            self._run_async(self._do_login, email, pw)

    # ─────────────────────────────────────────────────────────────────────────
    # Firebase operations (background thread)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_async(self, fn, *args):
        self._set_loading(True)
        threading.Thread(target=self._thread_wrapper,
                         args=(fn, *args), daemon=True).start()

    def _thread_wrapper(self, fn, *args):
        try:
            fn(*args)
        finally:
            self.after(0, lambda: self._set_loading(False))

    # ── Login ──

    def _do_login(self, email, pw):
        from auth.firebase_auth import sign_in, is_email_verified
        try:
            user = sign_in(email, pw)
            # ── Email verification gate ────────────────────────────────────
            if not is_email_verified(user["idToken"]):
                self.after(0, lambda: self._show_status(
                    "⚠️  Please verify your email before logging in.\n"
                    "Check your inbox for the verification link.",
                    _WARNING,
                ))
                return
            # ── Success ───────────────────────────────────────────────────
            self.after(0, lambda: self._on_login_ok(email))
        except Exception as e:
            msg = self._friendly_error(str(e), "login")
            self.after(0, lambda: self._show_status(msg, _ERROR))

    # ── Sign up ──

    def _do_signup(self, email, pw):
        from auth.firebase_auth import sign_up
        try:
            sign_up(email, pw)          # creates account + sends verification email
            self.after(0, lambda: self._on_signup_ok())
        except Exception as e:
            msg = self._friendly_error(str(e), "signup")
            self.after(0, lambda: self._show_status(msg, _ERROR))

    # ── Forgot password ──

    def _do_forgot(self, email):
        from auth.firebase_auth import reset_password
        try:
            reset_password(email)
            self.after(0, lambda: self._show_status(
                "Password reset email sent 📧\nCheck your inbox.", _SUCCESS))
        except Exception as e:
            msg = self._friendly_error(str(e), "reset")
            self.after(0, lambda: self._show_status(msg, _ERROR))

    # ── Result handlers ──

    def _on_login_ok(self, email):
        self._show_status("Login successful ✅  Loading app...", _SUCCESS)
        self.after(600, lambda: self._on_success(email))

    def _on_signup_ok(self):
        # Switch to login mode and show confirmation — user must verify first
        self._show_status(
            "Account created. Verification email sent 📧\n"
            "Please verify your email, then sign in.",
            _SUCCESS,
        )
        self.after(2000, self._show_login)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_loading(self, loading: bool):
        state = "disabled" if loading else "normal"
        label = "Please wait..." if loading else self._primary_label()
        self._primary_btn.configure(state=state, text=label)
        self._secondary_btn.configure(state=state)
        self._back_btn.configure(state=state)
        self._email_entry.configure(state=state)
        self._pw_entry.configure(state=state)
        self._cpw_entry.configure(state=state)

    def _primary_label(self) -> str:
        return {"login": "Sign In",
                "signup": "Sign Up",
                "forgot": "Send Reset Link"}.get(self._mode, "Submit")

    def _show_status(self, msg: str, color: str):
        self._status_lbl.configure(text=msg, text_color=color)

    def _clear_status(self):
        self._status_lbl.configure(text="")

    @staticmethod
    def _friendly_error(raw: str, context: str) -> str:
        r = raw.lower()
        if "email_not_found"          in r: return "Invalid email or password ❌"
        if "invalid_login_credentials" in r: return "Invalid email or password ❌"
        if "wrong_password"           in r: return "Invalid email or password ❌"
        if "invalid_password"         in r: return "Invalid email or password ❌"
        if "invalid_email"            in r: return "That doesn't look like a valid email ❌"
        if "email_exists"             in r: return "An account with this email already exists ❌"
        if "weak_password"            in r: return "Password must be at least 6 characters ❌"
        if "too_many_attempts"        in r: return "Too many attempts — please try again later ⚠️"
        if "user_disabled"            in r: return "This account has been disabled ⚠️"
        if "network"                  in r: return "No internet connection 🌐"
        if "timeout"                  in r: return "Request timed out — check your connection 🌐"
        # Generic fallback
        if context == "login":  return "Invalid email or password ❌"
        if context == "signup": return "Could not create account — please try again ❌"
        if context == "reset":  return "Could not send reset email — check the address ❌"
        return "Something went wrong — please try again ❌"
