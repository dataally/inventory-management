# Shell patterns for the sidebar redesign

Starter material. Adapt names, colors and sizes to the app; do not paste blindly.

## Token set

Define on `:root` in the global stylesheet (often the unscoped `<style>` in `App.vue`). Fill color values from the palette already in the app.

```css
:root {
  /* Colors: take values from the app's existing palette */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-accent: #3b82f6;
  --color-accent-soft: rgba(59, 130, 246, 0.1);

  /* Spacing scale (4px base). Use only these in the shell. */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-sm: 6px;
  --radius-md: 8px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);

  /* Layout */
  --sidebar-width: 248px;
  --content-max-width: 1280px;
  --z-sidebar: 40;
  --z-overlay: 30;
}
```

## Layout skeleton

```vue
<div class="app-shell">
  <aside class="sidebar" :class="{ open: sidebarOpen }">
    <div class="sidebar-brand"><!-- logo + subtitle --></div>
    <nav class="sidebar-nav" aria-label="Main">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item">
        <svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><!-- icon path --></svg>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer"><!-- LanguageSwitcher, ProfileMenu --></div>
  </aside>

  <div class="overlay" v-if="sidebarOpen" @click="sidebarOpen = false"></div>

  <div class="main-column">
    <header class="mobile-bar"><!-- menu button, brand: shown below the breakpoint only --></header>
    <!-- existing filter bar -->
    <main class="main-content"><router-view /></main>
  </div>
</div>
```

`router-link` already adds `router-link-active` / `router-link-exact-active`; style those instead of hand-rolled `$route.path` checks when the routes are flat. Keep the existing check if the app's logic differs (for example the `/` route would match everything with the non-exact class, so use the exact class for it).

```css
.app-shell { display: grid; grid-template-columns: var(--sidebar-width) 1fr; min-height: 100vh; background: var(--color-bg); }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  display: flex; flex-direction: column; gap: var(--space-4);
  padding: var(--space-4); background: var(--color-surface);
  border-right: 1px solid var(--color-border); z-index: var(--z-sidebar);
}
.sidebar-nav { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.nav-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
  color: var(--color-text-muted); text-decoration: none; font-weight: 500;
}
.nav-item:hover { background: var(--color-bg); color: var(--color-text); }
.nav-item.router-link-exact-active { background: var(--color-accent-soft); color: var(--color-accent); }
.nav-item:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.nav-icon { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.75; }
.sidebar-footer { display: flex; flex-direction: column; gap: var(--space-3); padding-top: var(--space-4); border-top: 1px solid var(--color-border); }
.main-column { min-width: 0; } /* min-width: 0 stops wide tables from stretching the grid */
.main-content { max-width: var(--content-max-width); margin: 0 auto; padding: var(--space-6); }
.mobile-bar, .overlay { display: none; }

@media (max-width: 900px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { position: fixed; inset: 0 auto 0 0; width: var(--sidebar-width); transform: translateX(-100%); transition: transform 0.2s ease; }
  .sidebar.open { transform: none; }
  .overlay { display: block; position: fixed; inset: 0; background: rgba(15, 23, 42, 0.4); z-index: var(--z-overlay); }
  .mobile-bar { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-4); background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
}
@media (prefers-reduced-motion: reduce) { .sidebar { transition: none; } }
```

## Things that commonly go wrong

- **Dropdowns clipped by the sidebar.** The sidebar has `overflow-y: auto`, so a profile menu that opens downward from the footer gets cut off. Open footer menus upward or position them `fixed`.
- **Modals under the sidebar.** Give modals a higher z-index than `--z-sidebar`; check the existing modal styles.
- **Sticky header leftovers.** Old `position: sticky; top: 0` rules on a filter bar or header may now overlap; re-check their offsets inside the main column.
- **Wide tables.** Without `min-width: 0` on the main column, a wide table pushes the grid wider than the viewport.
- **Close on navigate.** Close the mobile sidebar when the route changes (watch `$route` or use `router.afterEach`).
