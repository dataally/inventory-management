<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error && !maxBudget" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-row">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-readout">{{ formatMoney(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="sliderMax"
          :step="BUDGET_STEP"
          :aria-label="t('restocking.budgetSlider')"
          :style="{ '--fill': sliderFill + '%' }"
        />
        <div class="budget-scale">
          <span>{{ formatMoney(0) }}</span>
          <span>{{ formatMoney(sliderMax) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatMoney(budget) }}</div>
        </div>
        <div class="stat-card" :class="overBudget ? 'danger' : 'success'">
          <div class="stat-label">{{ t('restocking.plannedSpend') }}</div>
          <div class="stat-value">{{ formatMoney(plannedSpend) }}</div>
        </div>
        <div class="stat-card" :class="overBudget ? 'danger' : 'warning'">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatMoney(remaining) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemsCovered') }}</div>
          <div class="stat-value">{{ selectedRows.length }}</div>
        </div>
      </div>

      <div v-if="orderResult" class="card success-card" role="status">
        <h3 class="card-title">{{ t('restocking.success.title') }}</h3>
        <dl class="success-details">
          <div>
            <dt>{{ t('restocking.success.orderNumber') }}</dt>
            <dd>{{ orderResult.order_number }}</dd>
          </div>
          <div>
            <dt>{{ t('restocking.success.leadTime') }}</dt>
            <dd>{{ t('restocking.days', { count: orderResult.lead_time_days }) }}</dd>
          </div>
          <div>
            <dt>{{ t('restocking.success.expectedDelivery') }}</dt>
            <dd>{{ formatDate(orderResult.expected_delivery) }}</dd>
          </div>
        </dl>
        <router-link to="/orders" class="success-link">{{ t('restocking.success.viewOrders') }}</router-link>
      </div>

      <div v-if="error" class="error" role="alert">{{ error }}</div>

      <div class="card" :class="{ refreshing }">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ rows.length }})</h3>
        </div>

        <div v-if="rows.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th class="col-check">{{ t('restocking.table.include') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="col-num">{{ t('restocking.table.onHand') }}</th>
                <th class="col-num">{{ t('restocking.table.forecast') }}</th>
                <th class="col-qty">{{ t('restocking.table.quantity') }}</th>
                <th class="col-num">{{ t('restocking.table.unitCost') }}</th>
                <th class="col-num">{{ t('restocking.table.lineCost') }}</th>
                <th class="col-num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.sku" :class="{ 'row-off': !row.selected }">
                <td class="col-check">
                  <input
                    v-model="row.selected"
                    type="checkbox"
                    :aria-label="t('restocking.selectItem', { sku: row.sku })"
                  />
                </td>
                <td>
                  <strong>{{ row.sku }}</strong>
                  <div class="item-sub">{{ translateProductName(row.name) }}</div>
                </td>
                <td>
                  <span :class="['badge', row.trend]">{{ trendLabel(row.trend) }}</span>
                </td>
                <td class="col-num">{{ row.quantity_on_hand.toLocaleString() }}</td>
                <td class="col-num">{{ row.forecasted_demand.toLocaleString() }}</td>
                <td class="col-qty">
                  <input
                    v-model.number="row.qty"
                    type="number"
                    class="qty-input"
                    min="1"
                    :max="row.shortfall"
                    :aria-label="t('restocking.table.quantity')"
                    @change="clampQty(row)"
                  />
                </td>
                <td class="col-num">{{ formatUnitCost(row.unit_cost) }}</td>
                <td class="col-num"><strong>{{ formatMoney(lineCost(row)) }}</strong></td>
                <td class="col-num">{{ t('restocking.days', { count: row.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="order-footer">
          <div class="order-summary">
            <span v-if="selectedRows.length > 0">
              {{ t('restocking.orderLeadTime') }}: <strong>{{ t('restocking.days', { count: orderLeadTime }) }}</strong>
            </span>
            <span v-if="overBudget" class="over-budget">{{ t('restocking.overBudget') }}</span>
          </div>
          <button
            type="button"
            class="place-order"
            :disabled="!canSubmit"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

const BUDGET_STEP = 100
const DEBOUNCE_MS = 250
// Large enough to exceed any realistic total shortfall cost; the backend reports
// the real ceiling as max_useful_budget.
const PROBE_BUDGET = 1000000000
const DEFAULT_FRACTION = 0.4

const loading = ref(true)
const refreshing = ref(false)
const submitting = ref(false)
const error = ref(null)
const maxBudget = ref(0)
const budget = ref(0)
const recommendation = ref(null)
const rows = ref([])
const orderResult = ref(null)

let debounceTimer = null
// Monotonic id so slow responses from earlier slider positions are discarded
let requestSeq = 0

const currencySymbol = computed(() => (currentCurrency.value === 'JPY' ? '¥' : '$'))

// Round the slider max up to a step multiple so the final position is reachable
const sliderMax = computed(() => Math.max(BUDGET_STEP, Math.ceil(maxBudget.value / BUDGET_STEP) * BUDGET_STEP))
const sliderFill = computed(() => (sliderMax.value ? (budget.value / sliderMax.value) * 100 : 0))

// Rows may have been edited to an out-of-range value mid-typing; clamp for all math
const effectiveQty = (row) => {
  const q = Number.isFinite(row.qty) ? Math.floor(row.qty) : 0
  return Math.min(Math.max(q, 1), row.shortfall)
}
const lineCost = (row) => effectiveQty(row) * row.unit_cost

const selectedRows = computed(() => rows.value.filter(r => r.selected))
const plannedSpend = computed(() => selectedRows.value.reduce((sum, r) => sum + lineCost(r), 0))
const remaining = computed(() => budget.value - plannedSpend.value)
const overBudget = computed(() => plannedSpend.value > budget.value)
// An order arrives when its slowest line arrives
const orderLeadTime = computed(() => Math.max(0, ...selectedRows.value.map(r => r.lead_time_days)))
const canSubmit = computed(() => selectedRows.value.length > 0 && !overBudget.value && !submitting.value)

// Unit costs are small (e.g. $6.75), so keep cents; totals are rounded to whole units.
const formatUnitCost = (value) => `${currencySymbol.value}${value.toFixed(2)}`
const formatMoney = (value) => `${currencySymbol.value}${Math.round(value).toLocaleString()}`

const formatDate = (dateString) => {
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const trendLabel = (trend) => {
  const key = `trends.${trend}`
  const label = t(key)
  return label === key ? trend : label
}

const clampQty = (row) => {
  row.qty = effectiveQty(row)
}

// Replacing rows resets selection and quantities to the new recommendation
const applyRecommendation = (data) => {
  recommendation.value = data
  rows.value = data.items.map(item => ({
    ...item,
    selected: true,
    qty: item.quantity
  }))
}

const loadRecommendations = async () => {
  const seq = ++requestSeq
  refreshing.value = true
  try {
    const data = await api.getRestockRecommendations(budget.value)
    if (seq !== requestSeq) return
    error.value = null
    applyRecommendation(data)
  } catch (err) {
    if (seq !== requestSeq) return
    error.value = t('restocking.loadFailed')
    console.error('Recommendations load error:', err)
  } finally {
    if (seq === requestSeq) refreshing.value = false
  }
}

const init = async () => {
  try {
    loading.value = true
    error.value = null
    const probe = await api.getRestockRecommendations(PROBE_BUDGET)
    maxBudget.value = probe.max_useful_budget
    const start = Math.round((sliderMax.value * DEFAULT_FRACTION) / BUDGET_STEP) * BUDGET_STEP
    // Set before watcher is relevant: the first fetch below is explicit
    budget.value = start
    initialised = true
    await loadRecommendations()
  } catch (err) {
    error.value = t('restocking.loadFailed')
    console.error('Restocking init error:', err)
  } finally {
    loading.value = false
  }
}

let initialised = false

// Debounced refetch when the slider moves
watch(budget, () => {
  if (!initialised) return
  orderResult.value = null
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
})

const placeOrder = async () => {
  if (!canSubmit.value) return
  try {
    submitting.value = true
    error.value = null
    orderResult.value = null
    const lines = selectedRows.value.map(r => ({ sku: r.sku, quantity: effectiveQty(r) }))
    orderResult.value = await api.createRestockOrder({ budget: budget.value, lines })
  } catch (err) {
    error.value = err.response?.data?.detail || t('restocking.orderFailed')
    console.error('Place order error:', err)
  } finally {
    submitting.value = false
  }
}

onMounted(init)
onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  // Invalidate any in-flight request
  requestSeq++
})
</script>

<style scoped>
.budget-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.budget-readout {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #3b82f6 var(--fill), #e2e8f0 var(--fill));
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.3);
}

.budget-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.3);
}

.budget-slider:focus-visible {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
}

.card.refreshing .table-container {
  opacity: 0.6;
  transition: opacity 0.15s;
}

.restock-table {
  width: 100%;
}

.col-check {
  width: 70px;
  text-align: center;
}

.col-num {
  text-align: right;
  white-space: nowrap;
}

.col-qty {
  width: 110px;
  text-align: right;
}

.qty-input {
  width: 80px;
  padding: 0.375rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #0f172a;
  text-align: right;
}

.qty-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.row-off {
  opacity: 0.5;
}

.item-sub {
  font-size: 0.813rem;
  color: #64748b;
}

.empty-state {
  padding: 2rem 1.5rem;
  text-align: center;
  color: #64748b;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.order-summary {
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

.order-summary strong {
  color: #0f172a;
}

.over-budget {
  color: #dc2626;
  font-weight: 600;
}

.place-order {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  background: #3b82f6;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.place-order:hover:not(:disabled) {
  background: #2563eb;
}

.place-order:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.success-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
  border-color: #86efac;
  background: #f0fdf4;
}

.success-details {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  margin: 0.75rem 0;
}

.success-details dt {
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
}

.success-details dd {
  margin: 0.25rem 0 0;
  font-weight: 600;
  color: #0f172a;
}

.success-link {
  color: #3b82f6;
  font-weight: 500;
  text-decoration: none;
}

.success-link:hover {
  text-decoration: underline;
}
</style>
