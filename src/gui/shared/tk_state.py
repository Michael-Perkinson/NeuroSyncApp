"""Helpers for synchronizing Tk variables with plain Python state objects."""

from __future__ import annotations


def bind_tk_var(tk_var, state_obj, field_name: str):
    """Bind a Tk variable to a field on *state_obj*.

    The state value is pushed into the Tk var immediately, and subsequent Tk
    writes keep the plain state in sync.
    """
    tk_var.set(getattr(state_obj, field_name))
    tk_var.trace_add("write", lambda *_: setattr(state_obj, field_name, tk_var.get()))
    return tk_var
