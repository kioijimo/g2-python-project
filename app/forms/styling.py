from django import forms

FORM_INPUT_CLASS = (
    "w-full rounded-md border border-border-default bg-surface-card px-3 py-2 text-sm text-text-primary "
    "placeholder-text-secondary/60 shadow-sm transition-colors duration-150 "
    "focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
)

FORM_SELECT_CLASS = (
    "w-full rounded-md border border-border-default bg-surface-card px-3 py-2 text-sm text-text-primary "
    "shadow-sm transition-colors duration-150 "
    "focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
)

FORM_TEXTAREA_CLASS = (
    "w-full rounded-md border border-border-default bg-surface-card px-3 py-2 text-sm text-text-primary "
    "placeholder-text-secondary/60 shadow-sm transition-colors duration-150 "
    "focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
)

FORM_CHECKBOX_CLASS = (
    "h-4 w-4 rounded border-border-default text-brand-primary focus:ring-2 focus:ring-brand-primary"
)

INPUT_CLASS = FORM_INPUT_CLASS


def apply_widget_styling(form):
    for field_name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, (forms.Select, forms.SelectMultiple)):
            css = FORM_SELECT_CLASS
        elif isinstance(widget, forms.Textarea):
            css = FORM_TEXTAREA_CLASS
        elif isinstance(widget, forms.CheckboxInput):
            css = FORM_CHECKBOX_CLASS
        else:
            css = FORM_INPUT_CLASS

        existing = widget.attrs.get("class", "")
        if existing:
            widget.attrs["class"] = f"{css} {existing}".strip()
        else:
            widget.attrs["class"] = css
