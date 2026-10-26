/**
 * Bundled Lovelace chart for Dynamic Energy Prices.
 *
 * Renders the hourly_prices attribute of a price sensor as a bar chart. It
 * starts at local midnight today and includes tomorrow's prices as soon as
 * the provider publishes them, so future hours are visible instead of only
 * recorded history.
 */

const CARD_TAG = "dynamic-energy-prices-chart";
const CARD_NAME = "Dynamic Energy Prices Chart";
const CARD_DESCRIPTION =
  "Shows today's and tomorrow's hourly electricity prices, including upcoming hours.";

const ESCAPE_MAP = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ESCAPE_MAP[char]);

const formatNumber = (value, decimals = 3) =>
  Number.isFinite(value) ? value.toFixed(decimals) : "-";

class DynamicEnergyPricesChart extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = undefined;
    this._hass = undefined;
    this._pending = false;
    this._lastKey = undefined;
    this._html = "";
    this._nowTimer = undefined;
    if (typeof ResizeObserver !== "undefined") {
      this._resizeObserver = new ResizeObserver(() => {
        this._lastKey = undefined;
        this._requestRender();
      });
    }
  }

  static getStubConfig(_hass, entities = []) {
    return {
      entity: entities.find((entityId) => entityId.startsWith("sensor.")) || "",
    };
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity) {
      throw new Error("You need to define an entity");
    }
    this._config = config;
    this._lastKey = undefined;
    this._requestRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._requestRender();
  }

  connectedCallback() {
    if (this._resizeObserver) {
      this._resizeObserver.observe(this);
    }
    if (this._nowTimer) {
      window.clearInterval(this._nowTimer);
    }
    this._nowTimer = window.setInterval(() => this._requestRender(), 60000);
    this._requestRender();
  }

  disconnectedCallback() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
    if (this._nowTimer) {
      window.clearInterval(this._nowTimer);
      this._nowTimer = undefined;
    }
  }

  getCardSize() {
    return 5;
  }

  _requestRender() {
    if (!this._hass || !this._config || this._pending) {
      return;
    }
    this._pending = true;
    requestAnimationFrame(() => {
      this._pending = false;
      this._render();
    });
  }

  _render() {
    const stateObj = this._hass.states[this._config.entity];
    const averageObj = this._config.average_entity
      ? this._hass.states[this._config.average_entity]
      : undefined;
    const title = this._config.title || "Electricity prices";
    const now = new Date();

    if (!stateObj) {
      this._setHtml(this._emptyHtml(title, "Entity not found."));
      return;
    }

    const prices = this._visiblePrices(stateObj, now);
    if (!prices.length) {
      this._setHtml(this._emptyHtml(title, "No price data available yet."));
      return;
    }

    const width = Math.max(280, Math.round(this.clientWidth || 500));
    const height = Math.max(160, Number(this._config.height) || 220);
    const key = [
      stateObj.last_updated,
      stateObj.state,
      prices.length,
      prices[0].start.getTime(),
      prices[prices.length - 1].end.getTime(),
      averageObj ? averageObj.state : "",
      width,
      height,
      Math.floor(now.getTime() / 60000),
    ].join("|");
    if (key === this._lastKey) {
      return;
    }
    this._lastKey = key;

    this._setHtml(
      this._chartHtml(title, stateObj, averageObj, prices, width, height, now)
    );
  }

  _visiblePrices(stateObj, now) {
    const attrs = stateObj.attributes || {};
    const raw = Array.isArray(attrs.hourly_prices)
      ? attrs.hourly_prices
      : [];
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const prices = [];

    for (const item of raw) {
      if (!item || typeof item !== "object") {
        continue;
      }
      const start = new Date(item.start_iso || item.start);
      const end = new Date(item.end_iso || item.end);
      const price = Number(item.price);
      if (
        !Number.isFinite(price) ||
        Number.isNaN(start.getTime()) ||
        Number.isNaN(end.getTime()) ||
        end <= todayStart
      ) {
        continue;
      }
      prices.push({ start, end, price });
    }

    prices.sort((a, b) => a.start - b.start);
    return prices;
  }

  _chartHtml(title, stateObj, averageObj, prices, width, height, now) {
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrowStart = new Date(todayStart);
    tomorrowStart.setDate(tomorrowStart.getDate() + 1);

    const xMin = todayStart.getTime();
    const xMax = Math.max(prices[prices.length - 1].end.getTime(), xMin + 1);
    const margin = { top: 18, right: 24, bottom: 34, left: 54 };
    const plotWidth = Math.max(10, width - margin.left - margin.right);
    const plotHeight = Math.max(10, height - margin.top - margin.bottom);

    const unit = stateObj.attributes.unit_of_measurement || "";
    const average = averageObj ? Number(averageObj.state) : NaN;
    const hasAverage = Number.isFinite(average);

    const allValues = prices.map((point) => point.price);
    if (hasAverage) {
      allValues.push(average);
    }
    const rawMin = Math.min(...allValues);
    const rawMax = Math.max(...allValues);
    const spread =
      rawMax - rawMin || Math.max(0.05, Math.abs(rawMax) * 0.2);
    const yMin = rawMin - spread * 0.12;
    const yMax = rawMax + spread * 0.12;

    const x = (value) =>
      margin.left + ((value - xMin) / (xMax - xMin)) * plotWidth;
    const y = (value) =>
      margin.top +
      plotHeight -
      ((value - yMin) / (yMax - yMin)) * plotHeight;

    const zeroInRange = yMin <= 0 && 0 <= yMax;
    const baseline = zeroInRange ? y(0) : margin.top + plotHeight;

    const yTicks = [0, 1, 2, 3]
      .map((index) => yMax - ((yMax - yMin) * index) / 3)
      .map((value) => {
        const py = y(value);
        return (
          `<line class="grid" x1="${margin.left}" y1="${py}" ` +
          `x2="${width - margin.right}" y2="${py}"></line>` +
          `<text class="axis-label" x="${margin.left - 8}" y="${py + 3}" ` +
          `text-anchor="end">${formatNumber(value)}</text>`
        );
      })
      .join("");

    const hourFormatter = new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    const dayFormatter = new Intl.DateTimeFormat(undefined, {
      day: "numeric",
      month: "short",
    });
    const slotFormatter = new Intl.DateTimeFormat(undefined, {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

    const tickStep = 6 * 60 * 60 * 1000;
    const xTicks = [];
    for (let tick = xMin; tick <= xMax; tick += tickStep) {
      xTicks.push(tick);
      if (xTicks.length > 48) {
        break;
      }
    }
    const xLabels = xTicks
      .map((tick) => {
        const date = new Date(tick);
        const useDay = tick !== xMin && date.getHours() === 0;
        const label = useDay
          ? dayFormatter.format(date)
          : hourFormatter.format(date);
        return (
          `<text class="axis-label" x="${x(tick)}" y="${height - 12}" ` +
          `text-anchor="middle">${escapeHtml(label)}</text>`
        );
      })
      .join("");

    const bars = prices
      .map((point) => {
        const x0 = x(point.start.getTime());
        const x1 = x(point.end.getTime());
        const barWidth = Math.max(1, x1 - x0 - 1.5);
        const priceY = y(point.price);
        const barY = Math.min(priceY, baseline);
        const barHeight = Math.max(1, Math.abs(baseline - priceY));
        const isCurrent = now >= point.start && now < point.end;
        const className = isCurrent
          ? "bar current"
          : now >= point.end
            ? "bar past"
            : "bar future";
        const label =
          `${slotFormatter.format(point.start)}-` +
          `${slotFormatter.format(point.end)} | ` +
          `${formatNumber(point.price)}${unit ? ` ${unit}` : ""}`;
        return (
          `<rect class="${className}" x="${x0 + 0.75}" y="${barY}" ` +
          `width="${barWidth}" height="${barHeight}" rx="1">` +
          `<title>${escapeHtml(label)}</title></rect>`
        );
      })
      .join("");

    const averageEnd = Math.min(tomorrowStart.getTime(), xMax);
    const averageLine = hasAverage
      ? `<line class="average-line" x1="${x(todayStart.getTime())}" ` +
        `y1="${y(average)}" x2="${x(averageEnd)}" y2="${y(average)}"></line>`
      : "";
    const nowX = x(now.getTime());
    const nowLine =
      `<line class="now-line" x1="${nowX}" y1="${margin.top}" ` +
      `x2="${nowX}" y2="${margin.top + plotHeight}"></line>`;

    const currentValue = Number(stateObj.state);
    const currentText = Number.isFinite(currentValue)
      ? formatNumber(currentValue)
      : stateObj.state;
    const subtitle =
      xMax > tomorrowStart.getTime() ? "Today and tomorrow" : "Today";
    const legend = [
      '<span class="legend-item"><i class="swatch past"></i>Past</span>',
      '<span class="legend-item"><i class="swatch current"></i>Current</span>',
      '<span class="legend-item"><i class="swatch future"></i>Upcoming</span>',
      '<span class="legend-item"><i class="swatch now"></i>Now</span>',
      hasAverage
        ? '<span class="legend-item"><i class="swatch average"></i>Today\'s average</span>'
        : "",
    ].join("");

    return `
      <style>${this._style()}</style>
      <ha-card>
        <div class="header">
          <div>
            <div class="title">${escapeHtml(title)}</div>
            <div class="subtitle">${escapeHtml(subtitle)}</div>
          </div>
          <div class="current">
            <span class="value">${escapeHtml(currentText)}</span>
            <span class="unit">${escapeHtml(unit)}</span>
          </div>
        </div>
        <svg class="chart" viewBox="0 0 ${width} ${height}" role="img"
             aria-label="${escapeHtml(title)}">
          ${yTicks}
          ${bars}
          ${averageLine}
          ${nowLine}
          ${xLabels}
        </svg>
        <div class="legend">${legend}</div>
      </ha-card>
    `;
  }

  _emptyHtml(title, message) {
    return `
      <style>${this._style()}</style>
      <ha-card>
        <div class="header">
          <div class="title">${escapeHtml(title)}</div>
        </div>
        <div class="empty">${escapeHtml(message)}</div>
      </ha-card>
    `;
  }

  _style() {
    return `
      :host {
        display: block;
      }
      ha-card {
        overflow: hidden;
      }
      .header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        padding: 16px 16px 4px;
      }
      .title {
        color: var(--primary-text-color);
        font-size: 16px;
        font-weight: 500;
      }
      .subtitle {
        margin-top: 2px;
        color: var(--secondary-text-color);
        font-size: 12px;
      }
      .current {
        text-align: right;
        white-space: nowrap;
      }
      .current .value {
        color: var(--primary-text-color);
        font-size: 20px;
        font-weight: 500;
      }
      .current .unit {
        margin-left: 4px;
        color: var(--secondary-text-color);
        font-size: 11px;
      }
      .chart {
        display: block;
        width: 100%;
        height: auto;
      }
      .grid {
        stroke: var(--divider-color, rgba(127, 127, 127, 0.25));
        stroke-width: 1;
      }
      .axis-label {
        fill: var(--secondary-text-color);
        font-size: 10px;
      }
      .bar.past {
        fill: var(--secondary-text-color);
        opacity: 0.4;
      }
      .bar.future {
        fill: var(--primary-color, #03a9f4);
        opacity: 0.85;
      }
      .bar.current {
        fill: var(--accent-color, #ff9800);
      }
      .average-line {
        stroke: var(--secondary-text-color);
        stroke-width: 1.5;
        stroke-dasharray: 4 3;
        opacity: 0.8;
      }
      .now-line {
        stroke: var(--error-color, #db4437);
        stroke-width: 1.5;
        stroke-dasharray: 2 2;
      }
      .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        padding: 0 16px 14px;
        color: var(--secondary-text-color);
        font-size: 11px;
      }
      .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 5px;
      }
      .swatch {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 2px;
      }
      .swatch.past {
        background: var(--secondary-text-color);
        opacity: 0.5;
      }
      .swatch.future {
        background: var(--primary-color, #03a9f4);
      }
      .swatch.current {
        background: var(--accent-color, #ff9800);
      }
      .swatch.now {
        height: 0;
        border-radius: 0;
        border-top: 2px dashed var(--error-color, #db4437);
        background: transparent;
      }
      .swatch.average {
        height: 0;
        border-radius: 0;
        border-top: 2px dashed var(--secondary-text-color);
        background: transparent;
      }
      .empty {
        padding: 4px 16px 18px;
        color: var(--secondary-text-color);
        font-size: 13px;
      }
    `;
  }

  _setHtml(html) {
    if (html === this._html) {
      return;
    }
    this._html = html;
    this.shadowRoot.innerHTML = html;
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, DynamicEnergyPricesChart);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: CARD_NAME,
    description: CARD_DESCRIPTION,
    preview: false,
  });
}
