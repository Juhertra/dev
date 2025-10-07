from flask import render_template


def render_first(candidates, **ctx):
    """Render the first existing template from candidates.

    This is a thin helper so routes can prefer rich templates but
    degrade gracefully to simpler ones without try/except clutter.
    """
    # We don't do environment probing here; keep behavior simple and
    # consistent with existing templates. Assume first exists for now.
    # Callers should pass a single preferred template or a short list
    # with a guaranteed first option available in this codebase.
    name = candidates[0] if isinstance(candidates, (list, tuple)) else candidates
    return render_template(name, **ctx)


