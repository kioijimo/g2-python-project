# Campus Equipment System — Design System

A simple, practical, and maintainable design system tailored for **g2-python-project** (Django 6.1 + Tailwind CSS v4 Standalone).

---

## 1. Design Principles

1. **Utility & Productivity First**
   - The application manages inventory, equipment borrowing, and administrative tracking. Interfaces must prioritize fast scanning, clear form completion, and unambiguous system status over visual ornament.

2. **Zero-Overhead Architecture**
   - Built entirely on Django standard templating (`{% include %}`, template inheritance) and Tailwind CSS v4 Standalone.
   - **No npm or Node.js runtime required.** Never introduce unnecessary JavaScript libraries or build tools for basic styling.

3. **Accessibility by Default**
   - High visual contrast (WCAG AA compliant) across all text, borders, and interactive elements.
   - Visible, distinct focus rings on every interactable element (`focus:ring-2 focus:ring-blue-600 focus:ring-offset-2`).
   - Accessible error states communicating status with both color and descriptive text.

4. **Predictable Component Consistency**
   - Standard semantic tokens for actions (Primary Blue), surfaces (Neutral Slate/Gray), and statuses (Emerald for active/available, Amber for maintenance/pending, Rose for danger/error).

---

## 2. Design Tokens

### 2.1 Color Palette

| Token Name | Tailwind Class | Hex / Variable | Purpose |
| :--- | :--- | :--- | :--- |
| **Brand Primary** | `bg-blue-700` / `text-blue-700` | `#1d4ed8` | Main action buttons, active navigation links, brand identity |
| **Brand Primary Hover** | `hover:bg-blue-800` | `#1e40af` | Hover/focus state for primary actions |
| **Brand Surface / Tint** | `bg-blue-50` / `border-blue-200` | `#eff6ff` / `#bfdbfe` | Informational callouts, active link highlights |
| **Neutral Surface** | `bg-gray-50` | `#f9fafb` | Full-page background behind cards |
| **Card Surface** | `bg-white` | `#ffffff` | Content containers, modals, table bodies |
| **Border Neutral** | `border-gray-200` / `border-gray-300` | `#e5e7eb` / `#d1d5db` | Card borders, table dividers, input borders |
| **Text Primary** | `text-gray-900` | `#111827` | Headings, primary labels, table values |
| **Text Muted** | `text-gray-600` / `text-gray-500` | `#4b5563` / `#6b7280` | Subtitles, helper text, timestamps, captions |
| **Status: Success / Available** | `bg-emerald-50 text-emerald-700 border-emerald-200` | `#047857` | Active user, available item, successful action flash |
| **Status: Warning / In-Use** | `bg-amber-50 text-amber-700 border-amber-200` | `#b45309` | Under maintenance, pending approval |
| **Status: Danger / Inactive** | `bg-rose-50 text-rose-700 border-rose-200` | `#be123c` | Inactive user, destructive action, form errors |
| **Status: Admin Role** | `bg-purple-50 text-purple-700 border-purple-200` | `#7e22ce` | Staff/Administrator badge indicator |

### 2.2 Typography

* **Font Family**: Standard system UI font stack (`font-sans`: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
* **Scale**:
  * **Page Title**: `text-2xl sm:text-3xl font-bold tracking-tight text-gray-900`
  * **Section / Card Header**: `text-lg font-semibold text-gray-900`
  * **Card Subtitle / Metadata**: `text-sm text-gray-600`
  * **Body / Form Labels**: `text-sm font-medium text-gray-700`
  * **Input Text & Button Text**: `text-sm`
  * **Badges & Microcopy**: `text-xs font-semibold`

### 2.3 Spacing & Sizing Scale

* **Component Padding**:
  * Buttons: `px-4 py-2` (standard), `px-3 py-1.5` (compact/navbar)
  * Form inputs: `px-3 py-2`
  * Card containers: `p-6 sm:p-8`
* **Grid & Stack Gaps**:
  * Form fields stack: `space-y-4` or `space-y-5`
  * Grid gap between form columns: `gap-4 sm:grid-cols-2`
  * Grid gap between dashboard cards: `gap-6 sm:grid-cols-2 lg:grid-cols-3`
* **Radii**:
  * Buttons & Form Inputs: `rounded-md` (`0.375rem`)
  * Cards & Containers: `rounded-xl` (`0.75rem`)
  * Badges & Status Pills: `rounded-full` (`9999px`)
* **Shadows**:
  * Subtle elevation: `shadow-sm`
  * Never use heavy, dark drop-shadows.

---

## 3. Component Guidelines

### 3.1 Buttons

| Variant | Classes | When to Use |
| :--- | :--- | :--- |
| **Primary** | `inline-flex items-center justify-center rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed` | Main form submission ("Create Account", "Save Item", "Sign in") |
| **Secondary / Outline** | `inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2` | Secondary actions ("Cancel", "Back to Users", "Log out") |
| **Danger** | `inline-flex items-center justify-center rounded-md bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2` | Irreversible actions ("Delete User", "Retire Item") |

**Template partial available**:
```django
{% include "components/button.html" with text="Save Changes" type="submit" variant="primary" %}
```

---

### 3.2 Form Controls & Field Groups

All form inputs in `app/forms/` must use the unified widget class constants from `app/forms/styling.py`:

```python
# In app/forms/styling.py:
FORM_INPUT_CLASS = (
    "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 "
    "placeholder-gray-400 shadow-sm transition-colors duration-150 "
    "focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
)
```

**Standard Template Markup for Form Fields**:
```html
<div>
  <label for="{{ form.email.id_for_label }}" class="mb-1.5 block text-sm font-medium text-gray-700">
    Email Address
  </label>
  {{ form.email }}
  {% if form.email.errors %}
  <p class="mt-1 text-xs text-rose-600">{{ form.email.errors.0 }}</p>
  {% elif form.email.help_text %}
  <p class="mt-1 text-xs text-gray-500">{{ form.email.help_text }}</p>
  {% endif %}
</div>
```

---

### 3.3 Status Badges & Roles

**Template partial available**:
```django
{% include "components/badge.html" with label="Admin" variant="admin" %}
{% include "components/badge.html" with label="Active" variant="success" %}
{% include "components/badge.html" with label="Maintenance" variant="warning" %}
{% include "components/badge.html" with label="Inactive" variant="danger" %}
```

---

### 3.4 Cards & Surfaces

Standard container for dashboards, forms, and item lists:
```html
<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
  <div class="mb-5 border-b border-gray-100 pb-4">
    <h2 class="text-lg font-semibold text-gray-900">Card Title</h2>
    <p class="mt-1 text-sm text-gray-600">Card description or context.</p>
  </div>
  <!-- Card Content -->
</div>
```

---

### 3.5 Feedback Alerts & Toast Notifications (Django Messages)

Floating Toast notifications are rendered at the bottom-right via `templates/components/toast.html` and integrated directly into `templates/base.html` and `templates/auth_base.html`:
* **Position**: Fixed bottom-right (`fixed bottom-5 right-5 z-50`), non-blocking container with interactive cards.
* **Auto-Dismiss**: Automatically fades and slides out after 5 seconds; timer pauses on hover.
* **Manual Close**: Accessible button with `aria-label="Dismiss notification"`.
* **Variants**:
  * **Success**: `border-emerald-200 bg-emerald-50 text-emerald-600`
  * **Error**: `border-rose-200 bg-rose-50 text-rose-600`
  * **Warning**: `border-amber-200 bg-amber-50 text-amber-600`
  * **Info**: `border-blue-200 bg-blue-50 text-blue-600`

---

### 3.6 Navigation & Header

The top navigation bar is provided in `templates/components/navbar.html` and loaded automatically by `templates/base.html`:
* Brand logo + name linking to the role-appropriate dashboard (`/manage/` for Admin, `/portal/` for User).
* Navigation tabs based on user permissions.
* Current user email display.
* Role badge pill (`Admin` or `User`).
* Secure POST logout button with CSRF token.

---

## 4. Layout & Responsive Rules

1. **Dashboard Shell (`templates/base.html`)**:
   - Outer container: `mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-8`
   - Use for: Administrative management, user portal, inventory catalogs, category lists, data tables.

2. **Authentication Shell (`templates/auth_base.html`)**:
   - Outer container: `sm:mx-auto sm:w-full sm:max-w-md` (centered card)
   - Use for: `/login/`, `/portal/register/`, password resets.

3. **Breakpoints**:
   - `sm` (640px): 2-column form grids, visible email address in navbar.
   - `md` (768px): Tablet views.
   - `lg` (1024px): 3-column dashboard layouts (e.g. 2-column main form + 1-column sidebar card).

---

## 5. Interaction & Accessibility Standards

* **Focus States**: Never remove outlines without providing a visible focus ring. Always pair `focus:outline-none` with `focus:ring-2 focus:ring-blue-600 focus:ring-offset-2`.
* **Keyboard Navigation**: All interactive actions must be native `<button>`, `<a>`, or `<input>` elements. Forms must support submission via `Enter`.
* **Logout Safety**: Always use a `<form method="post" action="{% url 'logout' %}">` with `{% csrf_token %}` to satisfy Django's `@require_POST` security requirement.
* **Form Errors**: Place field error messages directly below the corresponding input using `text-xs text-rose-600` so screen readers and users can immediately associate them.

---

## 6. Implementation Guidelines

### 6.1 Creating a New Page
1. Determine whether the page is a **dashboard view** or an **auth/minimal view**:
   * Dashboard: `{% extends "base.html" %}`
   * Auth/Minimal: `{% extends "auth_base.html" %}`
2. Use `{% block title %}Page Title | Campus Equipment System{% endblock %}`
3. Use the standardized card wrapper (`rounded-xl border border-gray-200 bg-white p-6 shadow-sm`).

### 6.2 Adding a New Django Form
1. In the appropriate module under `app/forms/`, define your `ModelForm` or `Form`.
2. In `__init__`, call `apply_widget_styling(self)`:
   ```python
   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       apply_widget_styling(self)
   ```
   This automatically applies the design system classes to all inputs, textareas, selects, and checkboxes without manual boilerplate.

### 6.3 Rebuilding Tailwind
After adding new template markup, run:
```powershell
python manage.py tailwind build
```
*(Or keep `python manage.py tailwind start` running in a second terminal during development).*

---

## 7. Rules for AI Coding Agents

When generating, modifying, or refactoring UI in this project, **all AI coding agents MUST adhere to these rules**:

1. **Reuse Existing Tokens & Classes**:
   - **DO NOT** invent arbitrary hex codes (e.g., `bg-[#2a4d8f]`). Always use the project's color palette (`blue-700`, `gray-900`, `gray-600`, `emerald-700`, `rose-700`, `amber-700`).
   - **DO NOT** create custom CSS classes when standard Tailwind utility classes exist.

2. **Template Inheritance**:
   - **DO NOT** create standalone HTML documents with custom `<html>` or `<body>` tags.
   - For all authenticated screens, extend `{% extends "base.html" %}`.
   - For authentication / onboarding screens, extend `{% extends "auth_base.html" %}`.

3. **Form Styling**:
   - **DO NOT** hardcode repetitive widget CSS strings across multiple forms.
   - Always call `apply_widget_styling(self)` in form `__init__` or reference `FORM_INPUT_CLASS` / `FORM_SELECT_CLASS` from `app/forms/styling.py`.

4. **Component Partials**:
   - Place reusable markup components into `templates/components/` (e.g., `button.html`, `badge.html`, `navbar.html`).
   - Use `{% include "components/<name>.html" with ... %}` rather than copying raw markup.

5. **No External Dependencies**:
   - **DO NOT** install npm packages, external icon CDNs, or JavaScript UI frameworks.
   - Use inline SVG icons or Tailwind classes exclusively.

6. **Logout Method**:
   - Never generate `<a href="/logout/">Log out</a>`. Logout in this project requires a POST request with CSRF protection:
     ```html
     <form method="post" action="{% url 'logout' %}">
       {% csrf_token %}
       <button type="submit" class="...">Log out</button>
     </form>
     ```
