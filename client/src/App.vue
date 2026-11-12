<template>
  <div class="app-shell">
    <aside id="app-sidebar" class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-brand">
        <h1>{{ t('nav.companyName') }}</h1>
        <span class="subtitle">{{ t('nav.subtitle') }}</span>
      </div>

      <nav class="sidebar-nav" :aria-label="t('nav.mainNavigation')">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path v-for="d in item.icon" :key="d" :d="d" />
          </svg>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Footer menus open upward (see global overrides below) so the sidebar's scroll container does not clip them -->
      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div v-if="sidebarOpen" class="sidebar-overlay" @click="closeSidebar"></div>

    <div class="main-column">
      <!-- Visible below 900px only -->
      <header class="mobile-bar">
        <button
          type="button"
          class="menu-button"
          :aria-label="t('nav.openNavigation')"
          aria-controls="app-sidebar"
          :aria-expanded="sidebarOpen ? 'true' : 'false'"
          @click="sidebarOpen = true"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span class="mobile-brand">{{ t('nav.companyName') }}</span>
      </header>
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const sidebarOpen = ref(false)
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    // Icons are inline SVG path data (24px grid, stroke only)
    const navItems = computed(() => [
      { to: '/', label: t('nav.overview'), icon: ['M4 13h6V4H4z', 'M14 20h6v-9h-6z', 'M14 4h6v4h-6z', 'M4 20h6v-3H4z'] },
      { to: '/inventory', label: t('nav.inventory'), icon: ['M21 8l-9-5-9 5 9 5z', 'M3 8v8l9 5 9-5V8', 'M12 13v8'] },
      { to: '/orders', label: t('nav.orders'), icon: ['M9 4h6v3H9z', 'M15 5h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2', 'M9 12h6M9 16h4'] },
      { to: '/spending', label: t('nav.finance'), icon: ['M3 7h18v12H3z', 'M3 11h18', 'M7 15h3'] },
      { to: '/demand', label: t('nav.demandForecast'), icon: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'] },
      { to: '/restocking', label: t('nav.restocking'), icon: ['M20 12a8 8 0 1 1-2.3-5.7', 'M20 4v4h-4', 'M12 8v8M8 12h8'] },
      // Not translated in the original app; left as-is on purpose
      { to: '/reports', label: 'Reports', icon: ['M6 3h9l4 4v14H6z', 'M14 3v5h5', 'M9 13h7M9 17h5'] }
    ])

    const closeSidebar = () => {
      sidebarOpen.value = false
    }

    // Close the mobile drawer after navigating
    watch(() => route.path, closeSidebar)

    const onKeydown = (e) => {
      if (e.key === 'Escape') closeSidebar()
    }

    onMounted(() => {
      loadTasks()
      window.addEventListener('keydown', onKeydown)
    })
    onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

    return {
      t,
      navItems,
      sidebarOpen,
      closeSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ------------------------------------------------------------------
   Design tokens. Palette is the app's existing slate + blue accent.
   Spacing uses a 4px scale; use only these values in shared styles.
------------------------------------------------------------------- */
:root {
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;
  --color-text-body: #334155;
  --color-text-muted: #64748b;
  --color-accent: #3b82f6;
  --color-accent-strong: #2563eb;
  --color-accent-soft: rgba(59, 130, 246, 0.1);

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);

  --sidebar-width: 248px;
  --content-max-width: 1440px;
  --topbar-height: 56px;

  /* Stacking: the filter bar is 90, dropdowns/modals inside components are 1000-2000.
     Sidebar must beat the sticky filter bar but stay below every modal. */
  --z-mobile-bar: 100;
  --z-overlay: 150;
  --z-sidebar: 200;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* ---------------- Shell ---------------- */
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: var(--z-sidebar);
}

.sidebar-brand {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.sidebar-brand h1 {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
  line-height: 1.3;
}

.subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: var(--color-bg);
  color: var(--color-text);
}

/* Routes are flat, and the exact class avoids "/" matching every page */
.nav-item.router-link-exact-active {
  background: var(--color-accent-soft);
  color: var(--color-accent-strong);
}

.nav-icon,
.menu-button svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

/* Child components style their own dropdowns (scoped) to open downward and right-aligned.
   In the sidebar footer that would be clipped by the scroll container, so flip them upward
   and fit the sidebar width. Extra specificity beats the scoped [data-v] selectors. */
.sidebar .sidebar-footer .language-button,
.sidebar .sidebar-footer .profile-button {
  width: 100%;
}

.sidebar .sidebar-footer .profile-name {
  flex: 1;
  min-width: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar .sidebar-footer .language-label {
  flex: 1;
  text-align: left;
}

.sidebar .sidebar-footer .dropdown-menu {
  top: auto;
  bottom: calc(100% + var(--space-2));
  left: 0;
  right: 0;
  min-width: 0;
}

.sidebar-overlay,
.mobile-bar {
  display: none;
}

/* min-width: 0 (also on the grid track) stops wide tables from stretching the layout */
.main-column {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* The filter bar's scoped styles assume a 70px top nav; it now sticks to the top of the column */
.app-shell .main-column .filters-bar {
  top: 0;
  background: var(--color-surface);
}

.app-shell .main-column .filters-container {
  max-width: var(--content-max-width);
  padding: 0 var(--space-6);
}

/* The main column is narrower than the old full-width bar (sidebar takes 248px),
   so let the four selects wrap instead of pushing the reset button off-screen */
.app-shell .main-column .filters-grid {
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-4);
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-6);
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  /* Off-canvas drawer; transform keeps it out of view without unmounting the footer menus */
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    width: var(--sidebar-width);
    max-width: 85vw;
    transform: translateX(-100%);
    visibility: hidden;
    transition: transform 0.2s ease, visibility 0s linear 0.2s;
    box-shadow: none;
  }

  .sidebar.open {
    transform: none;
    visibility: visible;
    transition: transform 0.2s ease;
    box-shadow: var(--shadow-md);
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.4);
    z-index: var(--z-overlay);
  }

  .mobile-bar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    height: var(--topbar-height);
    padding: 0 var(--space-4);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    position: sticky;
    top: 0;
    z-index: var(--z-mobile-bar);
  }

  .menu-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
  }

  .menu-button:hover {
    background: var(--color-bg);
  }

  .mobile-brand {
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: -0.025em;
  }

  /* Wrapped filters are ~190px tall on a phone; keeping them sticky would eat the viewport,
     so only the slim mobile bar stays pinned and the filters scroll with the page */
  .app-shell .main-column .filters-bar {
    position: static;
  }

  .main-content {
    padding: var(--space-4);
  }

  .app-shell .main-column .filters-container {
    padding: 0 var(--space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .sidebar.open,
  .nav-item,
  .stat-card,
  .card {
    transition: none;
  }
}

/* ---------------- Page header ---------------- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

/* ---------------- Shared cards ---------------- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value { color: #ea580c; }
.stat-card.success .stat-value { color: #059669; }
.stat-card.danger .stat-value { color: #dc2626; }
.stat-card.info .stat-value { color: #2563eb; }

.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

/* ---------------- Tables ---------------- */
.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-3);
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

td {
  padding: var(--space-3) var(--space-3);
  border-top: 1px solid #f1f5f9;
  color: var(--color-text-body);
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-bg);
}

/* ---------------- Badges ---------------- */
.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.3;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success,
.badge.increasing { background: #d1fae5; color: #065f46; }

.badge.warning,
.badge.medium { background: #fed7aa; color: #92400e; }

.badge.danger,
.badge.decreasing,
.badge.high { background: #fecaca; color: #991b1b; }

.badge.info,
.badge.low { background: #dbeafe; color: #1e40af; }

.badge.stable { background: #e0e7ff; color: #3730a3; }

/* ---------------- States ---------------- */
.loading {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: 0.875rem;
}
</style>
