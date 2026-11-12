---
name: saas-sidebar-redesign
description: Redesign a Vue 3 app's shell into a modern SaaS-style layout, replacing the top navigation bar with a vertical left sidebar and applying a consistent spacing scale and polished, professional styling. Use this whenever the user wants a sidebar or left nav, to move navigation from the top to the side, to make the app look like a modern SaaS dashboard or admin panel, to modernize or polish the layout, or to fix inconsistent spacing in the app shell, even if they never say "sidebar" or "SaaS".
---

# SaaS sidebar redesign for Vue 3

Turn a top-navbar Vue 3 app into a modern SaaS shell: a fixed left sidebar for navigation, a content area with consistent spacing, and a restrained professional look. The goal is a layout change plus visual polish, not a rebrand, so keep the app's existing colors, routes, behavior and translations.

## Scope

Change the app shell and navigation only: the root component (usually `App.vue`), the navigation markup, and the global shell styles. Leave page views, data loading and component logic alone. Page content gets the new spacing through the shell's content container, so views need no edits unless they hardcode their own outer margins that clash with it. Staying inside this scope keeps the diff reviewable and avoids breaking pages you were not asked to touch.

If the repo has a Vue specialist agent (for example `vue-expert`) or a rule that `.vue` edits go through one, follow it.

## Workflow

1. **Read before designing.** Open the root component, the router file, any global stylesheet, and the shared components rendered in the header (language switcher, profile menu, filter bar). Note: the nav items and their i18n keys, the active-route logic, what else lives in the header, and whether the script uses Options API or `<script setup>` (match it; do not convert).
2. **Extract the existing palette.** Collect the colors already in use (text, muted text, borders, background, accent, status colors) from the global styles. Reuse them as CSS variables. Inventing a new palette makes the app look unrelated to its own pages, which is the most common way this kind of redesign goes wrong.
3. **Define design tokens** on `:root` in the global styles: colors, a spacing scale, radii, one or two shadows, and layout sizes (sidebar width, content max width). See `references/shell-patterns.md` for the token set and a starter layout. A single spacing scale (4px base: 4, 8, 12, 16, 24, 32) applied everywhere is what makes the result feel consistent, so use only scale values in the shell.
4. **Build the sidebar.** Move the logo/brand to the top of the sidebar, navigation links as a vertical list in the middle, and utilities (language switcher, profile menu) pinned to the bottom. Keep every existing route and i18n label. Active item gets a clear but quiet treatment (tinted background plus accent text or left indicator), hover state is subtle, and focus rings stay visible for keyboard users.
5. **Rebuild the layout.** Use a two-column CSS grid or flex layout: fixed-width sidebar, scrollable main column. The sidebar is sticky and full height. The existing filter bar or page header becomes a slim bar at the top of the main column. Constrain the content width and give it consistent padding so pages do not touch the sidebar edge.
6. **Make it responsive.** Below roughly 900px the sidebar collapses off-canvas behind a menu button in a slim top bar, with an overlay and close-on-navigate. Without this the redesign breaks on laptops with split windows and on mobile.
7. **Polish.** Consistent radii and borders, one soft shadow level, readable type scale, aligned baselines, no emoji in the UI unless the app already uses them, and `prefers-reduced-motion` respected for transitions.
8. **Verify in a browser.** Run the dev server and look at it; build success alone does not show a broken layout. Check at least: desktop width, a narrow width with the menu button, the active state on two different routes, and that existing modals and dropdowns (profile menu, tasks) still open above the sidebar with correct stacking. Fix z-index conflicts you introduced.

## Rules that keep the result good

- Keep all behavior: routes, `router-link` active logic, translation keys, emitted events, and modal wiring must work exactly as before. A redesign that loses a nav item or a language option is a regression, however nice it looks.
- Hardcoded nav labels (not using i18n) stay as they are; mention them in your summary rather than silently changing them.
- Prefer CSS variables over repeated literals so the user can retheme in one place.
- Do not add dependencies (no UI library, no icon package). Use inline SVG for icons, small and consistent in size and stroke.
- Add short comments for non-obvious layout logic (sticky offsets, z-index choices, why a wrapper exists), since that is easy to break later.
- If the app has a project convention file (such as `CLAUDE.md`) with design rules, those override the defaults here.

## Output

Finish with a brief summary: files changed, the tokens introduced, how the sidebar behaves on small screens, anything you noticed but deliberately left alone (for example views with their own outer margins, or unlabeled nav items), and how you verified it.
