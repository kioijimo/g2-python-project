# BulSU Campus Equipment System — Design System Specification

A modern, institutional, accessible, and high-performance design system for the **Bulacan State University (BulSU)** Campus Equipment System, built on **Django 6.1** and **Tailwind CSS v4 Standalone**.

---

## 1. Brand Identity & Visual Direction

The visual system is derived from the official **Bulacan State University (BulSU)** visual identity:

* **Dominant Brand Color**: **Deep Crimson Red** (`#AE0014`) represents university pride, institutional credibility, authority, and academic legacy.
* **Primary Accent Color**: **Golden Yellow** (`#FBB526`) brings high-energy vibrancy, emphasis on key metrics, badges, and selected primary highlights.
* **Secondary Depth**: **Dark Maroon** (`#800000`) provides depth for rich ambient gradients, dark chrome surfaces, and elevated brand layers.
* **Neutral Backgrounds**: Warm neutral canvas (`#F7F5F2`) and pure white cards (`#FFFFFF`) framed by restrained borders (`#E5E7EB`).
* **Operational Purpose**: The application manages daily equipment inventory, lab loans, and administrative workflows. Legibility, scannability, clear status differentiation, and operational efficiency always take priority over decorative clutter.

---

## 2. Design Principles

1. **Institutional Dignity & Operational Clarity**
   - High information density with crisp hierarchy. The crimson-and-gold identity communicates university authenticity without turning functional tools into promotional posters.
2. **Strict Semantic Separation of Status and Brand**
   - Brand crimson and gold must **never** displace functional status colors:
     - **Emerald (`#059669` / emerald-700)**: Available units, Active catalogs, Successful actions.
     - **Amber (`#D97706` / amber-700)**: Maintenance units, Pending loan reviews, Reserved equipment.
     - **Rose (`#E11D48` / rose-700)**: Overdue requests, Damaged units, Retired assets, Destructive actions.
     - **Purple (`#7E22CE` / purple-700)**: Staff / Administrator role pill.
3. **WCAG 2.2 AA Accessibility by Design**
   - **White text on Crimson (`#AE0014`)**: Contrast ratio is **7.47:1** (exceeds WCAG AAA 7:1 for normal text).
   - **Golden Yellow (`#FBB526`) Contrast Rule**: White text on `#FBB526` yields only 1.4:1 contrast (complete failure). Therefore:
     - Golden yellow buttons (`variant="accent"`) MUST use **dark text** (`text-gray-950 font-bold`), delivering **9.09:1** contrast.
     - Golden accent badges (`variant="accent"`) on soft gold backgrounds (`#FFF4D6`) MUST use deep golden amber text (`text-[#8F5B00]`), delivering **5.5:1** contrast.
     - Never use yellow background with white text. Never use yellow text on white surfaces.
4. **Zero-Dependency Tailwind v4 Standalone**
   - Built exclusively on Django standard templating (`{% extends %}`, `{% include %}`) and **Tailwind CSS v4 Standalone** via `pytailwindcss`.
   - **No npm, Node.js, bundlers, or external CSS CDNs.** Compiles natively in milliseconds.

---

## 3. Centralized Design Tokens

All tokens are centrally declared in `theme/static_src/src/styles.css` using Tailwind CSS v4's native `@theme` directive:

### 3.1 Brand Palette Tokens

| Token Name | CSS Variable | Hex Value | Semantic Role & Usage |
| :--- | :--- | :--- | :--- |
| `brand-primary` | `--color-brand-primary` | `#AE0014` | BulSU Deep Crimson. Primary buttons, institutional headers, active nav items. |
| `brand-primary-hover` | `--color-brand-primary-hover` | `#8F0010` | Darker Crimson. Hover and active states for primary buttons and links. |
| `brand-primary-dark` | `--color-brand-primary-dark` | `#800000` | Dark Maroon. Radial gradient depth, dark tooltips, deep structural chrome. |
| `brand-primary-subtle` | `--color-brand-primary-subtle` | `#FCEBED` | Light Crimson Tint. Card header pills, avatar backgrounds, active row tints. |
| `brand-accent` | `--color-brand-accent` | `#FBB526` | Golden Yellow. High-contrast accent buttons, active indicator dots, metrics. |
| `brand-accent-hover` | `--color-brand-accent-hover` | `#E5A016` | Darker Gold. Interactive hover state for accent buttons. |
| `brand-accent-subtle` | `--color-brand-accent-subtle` | `#FFF4D6` | Soft Gold Tint. Accent notice containers and badge backgrounds. |
| `background-default` | `--color-background-default` | `#F7F5F2` | Warm Neutral Canvas. Page body background behind cards. |
| `background-muted` | `--color-background-muted` | `#F3F4F6` | Secondary cool neutral for table headers and subtle container fills. |
| `surface-card` | `--color-surface-card` | `#FFFFFF` | Pure white cards, modal dialogs, data table bodies, dropdowns. |
| `border-default` | `--color-border-default` | `#E5E7EB` | Restrained card borders, table row dividers, input borders. |
| `border-strong` | `--color-border-strong` | `#D1D5DB` | High-contrast input outlines and active state borders. |
| `text-primary` | `--color-text-primary` | `#222222` | Charcoal text for maximum readability on white and warm neutral backgrounds. |
| `text-secondary` | `--color-text-secondary` | `#6B7280` | Muted secondary text, column headers, timestamps, helper descriptions. |
| `focus-ring` | `--color-focus-ring` | `#AE0014` | Universal crimson keyboard focus outline color. |

### 3.2 Semantic Status Tokens

| Semantic Role | Classes | Contrast & Meaning |
| :--- | :--- | :--- |
| **Available / Active / Success** | `border-emerald-200 bg-emerald-50 text-emerald-700` | Available equipment units, Active catalog items, Success flash alerts. |
| **Maintenance / Pending / Reserved** | `border-amber-200 bg-amber-50 text-amber-700` | Units under repair, Requests pending review, Reserved units. |
| **Overdue / Damaged / Danger** | `border-rose-200 bg-rose-50 text-rose-700` | Overdue borrowing loans, Damaged equipment, Rejected requests, Error toasts. |
| **Reserved / Information** | `border-sky-200 bg-sky-50 text-sky-700` | Allocated loan units, Informational status banners. |
| **Role: Administrator** | `border-purple-200 bg-purple-50 text-purple-700` | Staff and System Administrator role badge. |
| **Role: Student / User** | `border-brand-primary/20 bg-brand-primary-subtle text-brand-primary` | Student and Basic Borrower role badge. |

---

## 4. Typography, Spacing, and Elevation

### 4.1 Typography
* **Primary System Stack**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
* **Display Font (Accent)**: `Bebas Neue` (used in authentication branding and display headings).
* **Hierarchy**:
  * **Page Title**: `text-2xl sm:text-3xl font-bold tracking-tight text-text-primary`
  * **Section Heading**: `text-lg font-bold text-text-primary`
  * **Card / Modal Heading**: `text-base sm:text-lg font-bold text-text-primary`
  * **Table Column Header**: `text-xs font-semibold uppercase tracking-wider text-text-secondary`
  * **Form Labels**: `text-xs font-semibold uppercase tracking-wider text-text-secondary`
  * **Body Text & Cells**: `text-sm text-text-primary`
  * **Microcopy & Status**: `text-xs font-semibold`

### 4.2 Elevation & Radii
* **Inputs & Standard Buttons**: `rounded-md` (`0.375rem`) or `rounded-lg` (`0.5rem`)
* **Cards & Containers**: `rounded-xl` (`0.75rem`)
* **Pill Badges & Avatars**: `rounded-full` (`9999px`)
* **Shadows**: Subtle `shadow-xs` or `shadow-sm`. Never use heavy, dark drop-shadows on content containers.

---

## 5. Component Standards & Usage

### 5.1 Buttons (`templates/components/button.html`)

```django
{% include "components/button.html" with text="Submit Request" type="submit" variant="primary" %}
{% include "components/button.html" with text="Special Action" variant="accent" %}
{% include "components/button.html" with text="Cancel" variant="secondary" %}
{% include "components/button.html" with text="Delete Item" variant="danger" %}
```

* **Primary (`variant="primary"`)**: `bg-brand-primary text-white hover:bg-brand-primary-hover focus:ring-brand-primary`
* **Accent (`variant="accent"`)**: `bg-brand-accent text-gray-950 font-bold hover:bg-brand-accent-hover focus:ring-brand-accent` (Dark text guarantees WCAG AA).
* **Secondary (`variant="secondary"`)**: `border border-border-default bg-surface-card text-text-primary hover:bg-background-muted focus:ring-brand-primary`
* **Danger (`variant="danger"`)**: `bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500`

### 5.2 Forms & Widgets (`app/forms/styling.py`)

All Django form widgets inherit from centralized constants in `app/forms/styling.py` using `apply_widget_styling(self)`:

```python
# app/forms/styling.py
FORM_INPUT_CLASS = (
    "w-full rounded-md border border-border-default bg-surface-card px-3 py-2 text-sm text-text-primary "
    "placeholder-text-secondary/60 shadow-sm transition-colors duration-150 "
    "focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
)
```

In any Django form:
```python
from app.forms.styling import apply_widget_styling

class BorrowRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_styling(self)
```

### 5.3 Status Badges (`templates/components/badge.html`)

Standardized pill tags for status, categories, and roles:
```django
{% include "components/badge.html" with label="Available" variant="success" %}
{% include "components/badge.html" with label="Maintenance" variant="warning" %}
{% include "components/badge.html" with label="Overdue" variant="danger" %}
{% include "components/badge.html" with label="BulSU Gold" variant="accent" %}
{% include "components/badge.html" with label="Admin" variant="admin" %}
{% include "components/badge.html" with label="Student" variant="user" %}
```

### 5.4 Toast Notifications (`templates/components/toast.html`)

Accessible, auto-dismissing notifications positioned fixed at `bottom-5 right-5 z-50`:
* Automatically handles Django messages: `success`, `error`, `warning`, `info`.
* Fades out after 5 seconds with pause-on-hover.
* Accessible close button with keyboard focus indicator.

### 5.5 Navigation & Layout Shells

* **`templates/base.html`**: Standard authenticated application shell containing top navbar (`templates/components/navbar.html`), responsive container (`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8`), and toast container.
* **`templates/auth_base.html`**: Authentication shell for login and registration with BulSU Crimson and Gold ambient backdrops.
* **`templates/components/admin_navbar.html`**: Institutional administrator sidebar and mobile drawer with active route indicators, quick action buttons, and CSRF POST logout.
* **`templates/components/user_navbar.html`**: User portal navigation bar with catalog links, active requests counter, profile menu, and sign-in CTA.

---

## 6. Accessibility & Usability Standards (WCAG 2.2 AA)

1. **Color Contrast Verification**:
   - BulSU Crimson (`#AE0014`) on pure white (`#FFFFFF`): Contrast ratio = **7.47:1** (Passes WCAG AAA).
   - BulSU Crimson (`#AE0014`) on light crimson tint (`#FCEBED`): Contrast ratio = **6.54:1** (Passes WCAG AA).
   - Golden Yellow (`#FBB526`) with dark text (`#222222` / `text-gray-950`): Contrast ratio = **9.09:1** (Passes WCAG AAA).
   - Deep Golden Brown (`#8F5B00`) on soft gold tint (`#FFF4D6`): Contrast ratio = **5.5:1** (Passes WCAG AA).
2. **Keyboard Navigation & Visible Focus**:
   - Every interactive element includes explicit focus styling: `focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2`.
3. **Descriptive Error Messaging**:
   - Field errors are paired with descriptive error text (`text-xs font-medium text-rose-600`) directly underneath the input, with `aria-invalid="true"`.
4. **Accessible Tables**:
   - All inventory, loan, and request data tables are wrapped in responsive horizontal scrolling containers (`overflow-x-auto`) to ensure seamless navigation on mobile devices.

---

## 7. Tailwind CSS v4 Standalone Workflow

This project uses **Tailwind CSS v4 Standalone** via `pytailwindcss`. No Node.js runtime is installed or required.

### 7.1 File Architecture
* **Source CSS**: `theme/static_src/src/styles.css`
  * Contains `@import "tailwindcss";`
  * Central `@theme` token definitions
  * Content scanning directive: `@source "../../../**/*.{html,py,js}";`
* **Compiled CSS Output**: `theme/static/css/dist/styles.css`
  * Automatically generated by the standalone compiler. **Never edit this file manually.**

### 7.2 Build Commands
To compile CSS after modifying templates or forms:
```powershell
python manage.py tailwind build
```
To run the continuous watcher during active development:
```powershell
python manage.py tailwind start
```

---

## 8. Rules for Future AI Coding Agents

When adding new features or modifying existing pages in this repository, **all AI agents must strictly follow these rules**:

1. **Strictly Reuse Brand Tokens**:
   - Use `brand-primary`, `brand-primary-hover`, `brand-primary-dark`, `brand-primary-subtle`, `brand-accent`, `brand-accent-hover`, `brand-accent-subtle`, `background-default`, `surface-card`, `border-default`, `text-primary`, and `text-secondary`.
   - **Never hardcode arbitrary hex values** (e.g., `bg-[#AE0014]`) in HTML templates or Python code.
2. **Never Confuse Brand and Status Colors**:
   - Do **not** use `brand-accent` (golden yellow) for error states or warnings.
   - Do **not** use `brand-primary` (crimson) to indicate that an item is available or successful.
3. **Never Use White Text on Golden Yellow**:
   - Any button or badge utilizing `bg-brand-accent` MUST use dark text (`text-gray-950 font-bold`).
4. **Preserve Standalone Architecture**:
   - **DO NOT** install npm, Node.js packages, webpack, Vite, or external icon CDN links (e.g., FontAwesome).
   - Use inline SVG icons and existing components.
5. **Maintain Component Hierarchy**:
   - Always extend `templates/base.html` for application views and `templates/auth_base.html` for authentication.
   - Reuse partials from `templates/components/` (`button.html`, `badge.html`, `toast.html`, `form_field.html`, `pagination.html`).
6. **Always Use POST with CSRF for Logout**:
   - Never generate `<a href="/logout/">Logout</a>`. Django requires a POST request with `{% csrf_token %}`:
     ```html
     <form method="post" action="{% url 'logout' %}">
       {% csrf_token %}
       <button type="submit">Log out</button>
     </form>
     ```
7. **Rebuild Tailwind After Changes**:
   - Always execute `python manage.py tailwind build` after adding new utility classes to templates.
