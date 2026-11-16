"""flac-hunter Web GUI 前端页面（参考 FlClash-UI 四层无边框设计系统，纯标准库零外部依赖）。

后端见仓库根 gui.py；API：/api/state /api/prepare /api/download /api/upgrade
/api/audit /api/audit/last /api/job/<id> /api/tracks。
"""

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<script>
try {
  var s = localStorage.getItem("fh-color-scheme");
  if (s === "light" || s === "dark") {
    document.querySelector('meta[name="color-scheme"]').content = s;
  }
  var qp = new URLSearchParams(location.search).get("lang");
  var lng = (qp === "en" || qp === "zh") ? qp : localStorage.getItem("fh-lang");
  if (lng === "en" || lng === "zh") {
    document.documentElement.lang = lng === "en" ? "en" : "zh-CN";
    document.documentElement.dataset.lang = lng;
  }
} catch (e) {}
</script>
<title>flac-hunter</title>
<style>
:root {
  color-scheme: light dark;

  --fc-seed-h: 212;
  --fc-seed-s: 100%;
  --fc-seed-l-light: 52%;
  --fc-seed-l-dark: 63%;

  --fc-primary-light: hsl(var(--fc-seed-h) var(--fc-seed-s) var(--fc-seed-l-light));
  --fc-primary-dark: hsl(var(--fc-seed-h) var(--fc-seed-s) var(--fc-seed-l-dark));
  --fc-primary: light-dark(var(--fc-primary-light), var(--fc-primary-dark));
  --fc-on-primary: light-dark(#ffffff, #14110e);
  --fc-primary-tint: color-mix(in oklab, var(--fc-primary) 12%, var(--fc-surface-card));
  --fc-primary-tint-strong: color-mix(in oklab, var(--fc-primary) 20%, var(--fc-surface-card));
  --fc-series-2: color-mix(in oklab, var(--fc-primary) 42%, var(--fc-surface-card));

  /* 四层无边框表面层级：page -> card -> block -> inset + chrome */
  --fc-surface-page-light: #eff1f5;
  --fc-surface-card-light: #fafbfd;
  --fc-surface-block-light: #eef0f4;
  --fc-surface-inset-light: #e3e6ec;
  --fc-surface-chrome-light: #e6e8ee;

  --fc-surface-page-dark: #121110;
  --fc-surface-card-dark: #1e1c1a;
  --fc-surface-block-dark: #2a2724;
  --fc-surface-inset-dark: #36322e;
  --fc-surface-chrome-dark: #171614;

  --fc-surface-page: light-dark(var(--fc-surface-page-light), var(--fc-surface-page-dark));
  --fc-surface-card: light-dark(var(--fc-surface-card-light), var(--fc-surface-card-dark));
  --fc-surface-block: light-dark(var(--fc-surface-block-light), var(--fc-surface-block-dark));
  --fc-surface-inset: light-dark(var(--fc-surface-inset-light), var(--fc-surface-inset-dark));
  --fc-surface-chrome: light-dark(var(--fc-surface-chrome-light), var(--fc-surface-chrome-dark));
  --fc-surface-floating: light-dark(var(--fc-surface-card-light), var(--fc-surface-block-dark));

  --fc-on-surface-light: #16181d;
  --fc-on-surface-dark: #f5f4f2;
  --fc-on-surface: light-dark(var(--fc-on-surface-light), var(--fc-on-surface-dark));
  --fc-on-surface-variant-light: #646a75;
  --fc-on-surface-variant-dark: #a8a29c;
  --fc-on-surface-variant: light-dark(var(--fc-on-surface-variant-light), var(--fc-on-surface-variant-dark));

  --fc-divider: color-mix(in srgb, var(--fc-on-surface) 14%, transparent);
  --fc-divider-subtle: color-mix(in srgb, var(--fc-on-surface) 8%, transparent);
  --fc-hover-overlay: color-mix(in srgb, var(--fc-on-surface) 4%, transparent);
  --fc-press-overlay: color-mix(in srgb, var(--fc-on-surface) 9%, transparent);

  --fc-success: light-dark(#15803d, #4ade80);
  --fc-success-container: light-dark(#76f082, #125c24);
  --fc-on-success-container: light-dark(#063814, #d7ffe0);

  --fc-warning: light-dark(#c25e00, #fb923c);
  --fc-warning-container: light-dark(#ffedd5, #572909);
  --fc-on-warning-container: light-dark(#7c2d12, #ffedd5);

  --fc-error: light-dark(#dc2626, #f87171);
  --fc-error-container: light-dark(#fee2e2, #5c1919);
  --fc-on-error-container: light-dark(#7f1d1d, #fee2e2);

  --fc-font-sans: "SF Pro Display", "SF Pro Text", "Inter", -apple-system, BlinkMacSystemFont,
    "Noto Sans SC", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif;
  --fc-font-mono: "SF Mono", "JetBrains Mono", "Cascadia Mono", Consolas, ui-monospace, monospace;

  --fc-radius-card: 28px;
  --fc-radius-block: 18px;
  --fc-radius-tab: 14px;
  --fc-radius-badge: 12px;
  --fc-radius-pill: 9999px;

  --fc-shadow-e1-light:
    0 0.5px 1px rgba(0, 0, 0, 0.05),
    0 2px 6px rgba(0, 0, 0, 0.04),
    0 12px 30px -6px rgba(0, 0, 0, 0.08);
  --fc-shadow-e1-dark:
    0 1px 2px rgba(0, 0, 0, 0.5),
    0 10px 28px -6px rgba(0, 0, 0, 0.55);
  --fc-shadow-e1: var(--fc-shadow-e1-light);

  --fc-shadow-e2-light:
    0 2px 6px rgba(0, 0, 0, 0.06),
    0 16px 36px -8px rgba(0, 0, 0, 0.18);
  --fc-shadow-e2-dark:
    0 2px 8px rgba(0, 0, 0, 0.55),
    0 24px 48px -10px rgba(0, 0, 0, 0.72);
  --fc-shadow-e2: var(--fc-shadow-e2-light);

  --fc-glass-bg: color-mix(in srgb, var(--fc-surface-floating) 76%, transparent);
  --fc-glass-blur: blur(22px) saturate(180%);
  --fc-glass-edge: color-mix(in srgb, #ffffff 28%, transparent);

  --fc-ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --fc-ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --fc-duration-fast: 160ms;
  --fc-duration-normal: 260ms;

  accent-color: var(--fc-primary);
  --fc-scrollbar-thumb: color-mix(in srgb, var(--fc-on-surface) 22%, transparent);
  --fc-scrollbar-track: transparent;
  scrollbar-color: var(--fc-scrollbar-thumb) var(--fc-scrollbar-track);
  scrollbar-width: thin;
}

:root:has(> head > meta[name="color-scheme"][content="dark"]) {
  color-scheme: dark;
  --fc-shadow-e1: var(--fc-shadow-e1-dark);
  --fc-shadow-e2: var(--fc-shadow-e2-dark);
  --fc-glass-bg: color-mix(in srgb, var(--fc-surface-inset) 68%, transparent);
  --fc-glass-edge: color-mix(in srgb, #ffffff 12%, transparent);
}
:root:has(> head > meta[name="color-scheme"][content="light"]) {
  color-scheme: light;
  --fc-shadow-e1: var(--fc-shadow-e1-light);
  --fc-shadow-e2: var(--fc-shadow-e2-light);
}

@media (prefers-color-scheme: dark) {
  :root:has(> head > meta[name="color-scheme"][content="light dark"]) {
    --fc-shadow-e1: var(--fc-shadow-e1-dark);
    --fc-shadow-e2: var(--fc-shadow-e2-dark);
    --fc-glass-bg: color-mix(in srgb, var(--fc-surface-inset) 68%, transparent);
    --fc-glass-edge: color-mix(in srgb, #ffffff 12%, transparent);
  }
}

:root[data-pure-black="true"]:has(> head > meta[name="color-scheme"][content="dark"]),
:root[data-pure-black="true"][data-resolved-theme="dark"] {
  --fc-surface-page-dark: #000000;
  --fc-surface-chrome-dark: #09090b;
  --fc-surface-card-dark: #141416;
  --fc-surface-block-dark: #202024;
  --fc-surface-inset-dark: #2b2b30;
}

@supports not (color: light-dark(white, black)) {
  :root {
    --fc-primary: var(--fc-primary-light);
    --fc-on-primary: #ffffff;
    --fc-surface-page: var(--fc-surface-page-light);
    --fc-surface-card: var(--fc-surface-card-light);
    --fc-surface-block: var(--fc-surface-block-light);
    --fc-surface-inset: var(--fc-surface-inset-light);
    --fc-surface-chrome: var(--fc-surface-chrome-light);
    --fc-surface-floating: var(--fc-surface-card-light);
    --fc-on-surface: var(--fc-on-surface-light);
    --fc-on-surface-variant: var(--fc-on-surface-variant-light);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --fc-primary: var(--fc-primary-dark);
      --fc-on-primary: #14110e;
      --fc-surface-page: var(--fc-surface-page-dark);
      --fc-surface-card: var(--fc-surface-card-dark);
      --fc-surface-block: var(--fc-surface-block-dark);
      --fc-surface-inset: var(--fc-surface-inset-dark);
      --fc-surface-chrome: var(--fc-surface-chrome-dark);
      --fc-surface-floating: var(--fc-surface-block-dark);
      --fc-on-surface: var(--fc-on-surface-dark);
      --fc-on-surface-variant: var(--fc-on-surface-variant-dark);
    }
  }
}

html, body, main, section, aside, article, header, nav, div, table, input, textarea, select, button {
  box-sizing: border-box;
}
[hidden] {
  display: none !important;
}

html, body {
  margin: 0;
  padding: 0;
  background-color: var(--fc-surface-page);
  color: var(--fc-on-surface);
  font-family: var(--fc-font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

button, input, select, textarea {
  font: inherit;
  color: inherit;
}

:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible {
  outline: 2px solid var(--fc-primary);
  outline-offset: 2px;
}

.fc-tabular {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}
.fc-mono {
  font-family: var(--fc-font-mono);
  font-variant-numeric: tabular-nums;
}
.fc-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

/* ---------- Shell & Navigation Chrome ---------- */
.fc-shell {
  display: flex;
  min-height: 100dvh;
  width: 100%;
  background-color: var(--fc-surface-page);
}

.fc-sidebar {
  width: 228px;
  flex: none;
  background-color: var(--fc-surface-chrome);
  border-inline-end: 1px solid var(--fc-divider);
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 0;
  height: 100dvh;
  transition: width 220ms var(--fc-ease-standard), padding 220ms var(--fc-ease-standard);
  z-index: 5;
}

.fc-shell.is-collapsed .fc-sidebar {
  width: 74px;
  padding: 16px 10px;
}

.fc-sidebar__top {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 2px 4px;
  min-height: 36px;
}

.fc-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--fc-on-surface);
  white-space: nowrap;
  overflow: hidden;
}

.fc-shell.is-collapsed .fc-sidebar__brand,
.fc-shell.is-collapsed .fc-nav-item span,
.fc-shell.is-collapsed .fc-sidebar__foot-text {
  display: none;
}

.fc-brand-dot {
  width: 24px;
  height: 24px;
  border-radius: 9px;
  background: var(--fc-primary);
  color: var(--fc-on-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.fc-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fc-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  height: 42px;
  padding: 0 12px 0 14px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: var(--fc-on-surface-variant);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  transition:
    background-color var(--fc-duration-fast) var(--fc-ease-standard),
    color var(--fc-duration-fast) var(--fc-ease-standard),
    scale var(--fc-duration-fast) var(--fc-ease-standard);
}

.fc-nav-item:hover {
  background-color: var(--fc-hover-overlay);
  color: var(--fc-on-surface);
}
.fc-nav-item:active {
  scale: 0.98;
}
.fc-nav-item[aria-current="page"] {
  background-color: color-mix(in srgb, var(--fc-on-surface) 7%, transparent);
  color: var(--fc-on-surface);
}
.fc-nav-item[aria-current="page"]::before {
  content: "";
  position: absolute;
  inset-inline-start: 3px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: var(--fc-radius-pill);
  background-color: var(--fc-primary);
}
.fc-nav-item[aria-current="page"] svg {
  color: var(--fc-primary);
}
.fc-nav-item svg {
  width: 19px;
  height: 19px;
  flex: none;
}

.fc-shell.is-collapsed .fc-nav-item {
  justify-content: center;
  padding: 0;
}

.fc-nav-badge {
  margin-inline-start: auto;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--fc-radius-pill);
  background: var(--fc-primary);
  color: var(--fc-on-primary);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.fc-nav-badge:empty {
  display: none;
}
.fc-shell.is-collapsed .fc-nav-badge {
  display: none;
}

.fc-sidebar__footer {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--fc-divider-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fc-lib-mini {
  padding: 10px 12px;
  border-radius: 16px;
  background-color: var(--fc-surface-block);
  font-size: 12px;
  color: var(--fc-on-surface-variant);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fc-lib-mini strong {
  color: var(--fc-on-surface);
  font-size: 13px;
}
.fc-shell.is-collapsed .fc-lib-mini {
  display: none;
}

/* ---------- Main Area & Sticky Topbar ---------- */
.fc-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.fc-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 26px 12px;
  position: sticky;
  top: 0;
  z-index: 4;
  background-color: color-mix(in srgb, var(--fc-surface-page) 86%, transparent);
  backdrop-filter: blur(12px);
}

.fc-topbar__title-wrap {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.fc-topbar__title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.fc-topbar__sub {
  font-size: 12.5px;
  color: var(--fc-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fc-topbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.fc-status-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background-color: var(--fc-success-container);
  color: var(--fc-on-success-container);
  cursor: pointer;
  transition: transform var(--fc-duration-fast) var(--fc-ease-spring);
}
.fc-status-circle:hover { transform: scale(1.06); }
.fc-status-circle:active { scale: 0.95; }
.fc-status-circle.is-busy {
  background-color: var(--fc-primary-tint-strong);
  color: var(--fc-primary);
}
.fc-status-circle.is-error {
  background-color: var(--fc-error-container);
  color: var(--fc-on-error-container);
}

/* ---------- Views Container ---------- */
.fc-view {
  padding: 4px 26px 40px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
}
.fc-view[hidden] {
  display: none;
}

/* ---------- 4-Level Borderless Surfaces ---------- */
.fc-card {
  position: relative;
  background-color: var(--fc-surface-card);
  border-radius: var(--fc-radius-card);
  box-shadow: var(--fc-shadow-e1);
  padding: 20px 22px;
  transition: background-color var(--fc-duration-fast) var(--fc-ease-standard);
}
.fc-card--clip { overflow: hidden; }
.fc-block {
  background-color: var(--fc-surface-block);
  border-radius: var(--fc-radius-block);
  padding: 12px 14px;
}

.fc-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 24px;
  margin-bottom: 12px;
}
.fc-card-header__start {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.fc-card-header__icon {
  width: 18px;
  height: 18px;
  color: var(--fc-on-surface-variant);
  flex: none;
}
.fc-card-header__title {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--fc-on-surface-variant);
  white-space: nowrap;
}
.fc-card-header__sub {
  font-size: 12px;
  color: var(--fc-on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- Bento Grids ---------- */
.fc-dash-row-1 {
  display: grid;
  grid-template-columns: minmax(320px, 1.5fr) 1fr 1fr;
  gap: 14px;
}
.fc-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 1080px) {
  .fc-dash-row-1 { grid-template-columns: 1fr 1fr; }
  .fc-dash-row-1 .fc-status-card { grid-column: 1 / -1; }
  .fc-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .fc-dash-row-1, .fc-kpi-row { grid-template-columns: 1fr; }
}

/* ---------- Hero Status Card ---------- */
.fc-status-card {
  min-height: 168px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 16px;
}
.fc-status-card__deco {
  position: absolute;
  right: -60px;
  top: -82px;
  width: 270px;
  height: 270px;
  color: var(--fc-surface-block);
  pointer-events: none;
  transition: transform 600ms var(--fc-ease-spring), color var(--fc-duration-normal);
}
.fc-status-card.is-running .fc-status-card__deco {
  color: var(--fc-primary-tint);
  transform: rotate(28deg) scale(1.1);
}
.fc-status-card__content {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
}
.fc-status-card__main {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fc-status-card__meta {
  display: flex;
  align-items: flex-end;
  gap: 22px;
  flex-wrap: wrap;
}
.fc-meta-item__label {
  font-size: 11.5px;
  color: var(--fc-on-surface-variant);
}
.fc-meta-item__value {
  font-size: 13px;
  font-weight: 700;
  margin-top: 2px;
}
.fc-status-card__action {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Material 3 12-petal Scalloped Cookie Button */
.fc-scallop-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 84px;
  height: 84px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--fc-on-primary);
  cursor: pointer;
  flex: none;
  transition: transform var(--fc-duration-normal) var(--fc-ease-spring);
}
.fc-scallop-btn:hover { transform: scale(1.05); }
.fc-scallop-btn:active { scale: 0.95; }
.fc-scallop-btn__shape {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  color: var(--fc-primary);
  filter: drop-shadow(0 6px 14px color-mix(in srgb, var(--fc-primary) 26%, transparent));
  transition: transform 420ms var(--fc-ease-spring), color var(--fc-duration-normal);
}
.fc-scallop-btn[aria-pressed="true"] .fc-scallop-btn__shape {
  transform: rotate(30deg);
}
.fc-scallop-btn[aria-pressed="false"] {
  color: var(--fc-on-surface);
}
.fc-scallop-btn[aria-pressed="false"] .fc-scallop-btn__shape {
  color: var(--fc-surface-inset);
  filter: none;
}
.fc-scallop-btn__icon {
  position: relative;
  z-index: 1;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* Stat Cards */
.fc-stat-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
}
.fc-stat-figure {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.fc-stat-num {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.fc-stat-unit {
  font-size: 13px;
  font-weight: 700;
  color: var(--fc-on-surface-variant);
}
.fc-stat-sub {
  font-size: 12px;
  color: var(--fc-on-surface-variant);
}

.fc-segmented-bar {
  display: flex;
  align-items: center;
  gap: 3px;
  width: 100%;
  height: 8px;
  border-radius: var(--fc-radius-pill);
  overflow: hidden;
  background-color: var(--fc-surface-inset);
}
.fc-segmented-bar__seg {
  height: 100%;
  border-radius: var(--fc-radius-pill);
  transition: width 360ms var(--fc-ease-standard);
}
.fc-segmented-bar__seg--primary { background-color: var(--fc-primary); }
.fc-segmented-bar__seg--secondary { background-color: var(--fc-series-2); }

.fc-wavy-meter {
  width: 100%;
  height: 12px;
  display: flex;
  align-items: center;
}
.fc-wavy-meter svg {
  width: 100%;
  height: 12px;
  display: block;
  overflow: visible;
}

/* ---------- Chips & Badges ---------- */
.fc-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: var(--fc-radius-pill);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  white-space: nowrap;
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface-variant);
}
.fc-chip--ok { background-color: var(--fc-success-container); color: var(--fc-on-success-container); }
.fc-chip--warn { background-color: var(--fc-warning-container); color: var(--fc-on-warning-container); }
.fc-chip--error { background-color: var(--fc-error-container); color: var(--fc-on-error-container); }
.fc-chip--primary { background-color: var(--fc-primary-tint-strong); color: var(--fc-primary); }
.fc-chip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}

/* ---------- Buttons, Inputs, Switches, Segmented ---------- */
.fc-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.fc-spacer { flex: 1; }

.fc-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: var(--fc-radius-pill);
  background: transparent;
  color: var(--fc-on-surface-variant);
  cursor: pointer;
  transition: background-color var(--fc-duration-fast), color var(--fc-duration-fast), scale var(--fc-duration-fast);
}
.fc-icon-btn:hover { background-color: var(--fc-hover-overlay); color: var(--fc-on-surface); }
.fc-icon-btn:active { scale: 0.94; }
.fc-icon-btn--tonal { background-color: var(--fc-surface-block); color: var(--fc-on-surface); }
.fc-icon-btn--tonal:hover { background-color: var(--fc-surface-inset); }
.fc-icon-btn svg { width: 17px; height: 17px; }

.fc-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 38px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--fc-radius-pill);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface);
  white-space: nowrap;
  transition: background-color var(--fc-duration-fast), opacity var(--fc-duration-fast), scale var(--fc-duration-fast);
}
.fc-btn:hover:not(:disabled) { background-color: var(--fc-surface-inset); }
.fc-btn:active:not(:disabled) { scale: 0.97; }
.fc-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.fc-btn--sm { height: 32px; padding: 0 13px; font-size: 12.5px; }
.fc-btn--primary { background-color: var(--fc-primary); color: var(--fc-on-primary); }
.fc-btn--primary:hover:not(:disabled) { opacity: 0.9; background-color: var(--fc-primary); }
.fc-btn--danger { background-color: var(--fc-error-container); color: var(--fc-on-error-container); }
.fc-btn--danger:hover:not(:disabled) { opacity: 0.9; background-color: var(--fc-error-container); }

.fc-input, .fc-textarea, .fc-select {
  border: 0;
  border-radius: 16px;
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface);
  padding: 10px 14px;
  transition: background-color var(--fc-duration-fast), box-shadow var(--fc-duration-fast);
}
.fc-input:focus, .fc-textarea:focus, .fc-select:focus {
  background-color: var(--fc-surface-inset);
  box-shadow: inset 0 0 0 2px var(--fc-primary);
  outline: none;
}
.fc-input { flex: 1; min-width: 240px; height: 42px; }
.fc-textarea { width: 100%; min-height: 98px; resize: vertical; line-height: 1.55; }
.fc-select { height: 34px; padding: 0 12px; border-radius: var(--fc-radius-pill); font-size: 13px; font-weight: 600; cursor: pointer; }

.fc-search {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.fc-search svg {
  position: absolute;
  inset-inline-start: 12px;
  width: 15px;
  height: 15px;
  color: var(--fc-on-surface-variant);
  pointer-events: none;
}
.fc-search input {
  height: 34px;
  padding: 0 14px 0 34px;
  border: 0;
  border-radius: var(--fc-radius-pill);
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface);
  font-size: 13px;
  min-width: 190px;
}

.fc-switch-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--fc-on-surface-variant);
  cursor: pointer;
}
.fc-switch {
  appearance: none;
  -webkit-appearance: none;
  position: relative;
  margin: 0;
  width: 44px;
  height: 26px;
  border-radius: var(--fc-radius-pill);
  background-color: var(--fc-surface-inset);
  cursor: pointer;
  flex: none;
  transition: background-color var(--fc-duration-fast) var(--fc-ease-standard);
}
.fc-switch::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: light-dark(#ffffff, #e6e3df);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.24);
  transition: transform var(--fc-duration-normal) var(--fc-ease-spring);
}
.fc-switch:checked { background-color: var(--fc-primary); }
.fc-switch:checked::after {
  transform: translateX(18px);
  background-color: var(--fc-on-primary);
}

.fc-segmented {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}
.fc-segmented__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--fc-radius-tab);
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color var(--fc-duration-fast), color var(--fc-duration-fast), scale var(--fc-duration-fast);
}
.fc-segmented__btn:hover:not([aria-pressed="true"]) { background-color: var(--fc-surface-inset); }
.fc-segmented__btn:active { scale: 0.97; }
.fc-segmented__btn[aria-pressed="true"] {
  background-color: var(--fc-primary);
  color: var(--fc-on-primary);
}

/* ---------- Tabs (遵循 modern-web-guidance `tabs`：单行、aria-selected、形状指示器) ---------- */
.fc-tablist {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-block: 2px;
}
.fc-tablist::-webkit-scrollbar { display: none; }
.fc-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--fc-radius-pill);
  background-color: var(--fc-surface-block);
  color: var(--fc-on-surface);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--fc-duration-fast), color var(--fc-duration-fast);
}
.fc-tab:hover:not([aria-selected="true"]) { background-color: var(--fc-surface-inset); }
.fc-tab[aria-selected="true"] {
  background-color: var(--fc-primary);
  color: var(--fc-on-primary);
}
.fc-tab[aria-selected="true"]::after {
  content: "";
  position: absolute;
  inset: auto 14px 3px;
  border-block-end: 2px solid currentColor;
  opacity: 0.65;
}
.fc-tabpanel-inner { padding-top: 2px; }

/* ---------- Responsive Zebra Table (无边框线，奇偶块级圆角铺垫) ---------- */
.fc-table-wrap {
  container-type: inline-size;
  overflow: auto;
  max-inline-size: 100%;
  max-block-size: min(440px, 60dvh);
  border-radius: 16px;
}
.fc-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}
.fc-table caption {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}
.fc-table thead th {
  position: sticky;
  inset-block-start: 0;
  z-index: 1;
  background-color: var(--fc-surface-card);
  padding: 8px 10px 10px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--fc-on-surface-variant);
  white-space: nowrap;
}
.fc-table thead th.is-num,
.fc-table tbody td.is-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
/* 新视图用 fc- 前缀的数字列等价类（is-num 为既有历史修饰类） */
.fc-table thead th.fc-num,
.fc-table tbody td.fc-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.fc-table tbody td {
  padding: 8px 10px;
  vertical-align: middle;
  max-width: 210px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fc-table tbody tr:nth-child(odd) td {
  background-color: var(--fc-surface-block);
}
.fc-table tbody tr:nth-child(odd) > :first-child {
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}
.fc-table tbody tr:nth-child(odd) > :last-child {
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
}
.fc-table tbody tr:hover td {
  background-color: color-mix(in srgb, var(--fc-surface-block) 82%, var(--fc-primary-tint));
}

@container (width < 520px) {
  .fc-table--responsive,
  .fc-table--responsive thead,
  .fc-table--responsive tbody,
  .fc-table--responsive tr,
  .fc-table--responsive td {
    display: block;
  }
  .fc-table--responsive thead { display: none; }
  .fc-table--responsive tbody tr {
    background-color: var(--fc-surface-block);
    border-radius: 16px;
    padding: 10px 14px;
    margin-block-end: 8px;
  }
  .fc-table--responsive tbody td {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: none;
    white-space: normal;
    padding: 4px 0;
    background: transparent !important;
    border-radius: 0 !important;
    text-align: right;
  }
  .fc-table--responsive tbody td::before {
    content: attr(data-label);
    color: var(--fc-on-surface-variant);
    font-size: 12px;
    font-weight: 500;
    margin-inline-end: 12px;
    flex: none;
  }
}

/* ---------- Jobs & Console Log ---------- */
.fc-job-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.fc-jobcard {
  width: 100%;
  text-align: left;
  border: 0;
  background-color: var(--fc-surface-block);
  border-radius: var(--fc-radius-block);
  padding: 14px 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: background-color var(--fc-duration-fast), box-shadow var(--fc-duration-fast), scale var(--fc-duration-fast);
}
.fc-jobcard:hover { background-color: var(--fc-surface-inset); }
.fc-jobcard:active { scale: 0.99; }
.fc-jobcard.is-selected {
  box-shadow: inset 0 0 0 2px var(--fc-primary);
}
.fc-jobcard__top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.fc-jobcard__name { font-weight: 700; font-size: 14px; }
.fc-jobcard__time { font-size: 12px; color: var(--fc-on-surface-variant); }
.fc-jobcard__sum { font-size: 12.5px; color: var(--fc-on-surface-variant); margin-inline-start: auto; }

.fc-log {
  background-color: var(--fc-surface-inset);
  color: var(--fc-on-surface);
  border-radius: var(--fc-radius-block);
  padding: 14px 16px;
  font-family: var(--fc-font-mono);
  font-size: 12.5px;
  line-height: 1.65;
  max-height: 340px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 0;
}
.fc-log-line { white-space: pre-wrap; word-break: break-word; padding: 2px 6px; border-radius: 6px; }
.fc-log-line.is-step { color: var(--fc-primary); font-weight: 600; background-color: color-mix(in srgb, var(--fc-primary) 10%, transparent); }
.fc-log-line.is-ok { color: var(--fc-success); }
.fc-log-line.is-warn { color: var(--fc-warning); }
.fc-log-line.is-err { color: var(--fc-error); background-color: color-mix(in srgb, var(--fc-error) 10%, transparent); }

.fc-empty {
  color: var(--fc-on-surface-variant);
  text-align: center;
  padding: 28px 12px;
  font-size: 13px;
}
.fc-hint {
  color: var(--fc-on-surface-variant);
  font-size: 12.5px;
  margin-top: 8px;
}

/* ---------- Library / Lyrics / Rename / Fingerprint 工具视图 ---------- */
.fc-page-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.fc-lyr-group > summary {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  list-style: none;
  font-size: 13px;
  font-weight: 600;
  min-height: 24px;
}
.fc-lyr-group > summary::-webkit-details-marker { display: none; }
.fc-lyr-group > summary::after {
  content: "▾";
  margin-inline-start: auto;
  color: var(--fc-on-surface-variant);
  transition: transform var(--fc-duration-fast) var(--fc-ease-standard);
}
.fc-lyr-group[open] > summary::after { transform: rotate(180deg); }
.fc-lyr-group.is-zero { opacity: 0.55; }
.fc-lyr-files {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}
.fc-lyr-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 10px;
  background-color: var(--fc-surface-block);
  font-size: 12.5px;
  cursor: pointer;
}
.fc-lyr-file:hover { background-color: var(--fc-surface-inset); }
.fc-lyr-file input { flex: none; }
.fc-lyr-file__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--fc-font-mono);
  font-size: 12px;
}
.fc-ren-item { flex-wrap: wrap; }
.fc-ren-path {
  font-family: var(--fc-font-mono);
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1 1 160px;
}
.fc-ren-arrow {
  color: var(--fc-primary);
  font-weight: 700;
  flex: none;
}
.fc-ren-result-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 12.5px;
  flex-wrap: wrap;
}
.fc-fp-md5 {
  flex: 1;
  min-width: 0;
  font-family: var(--fc-font-mono);
  font-size: 12.5px;
  word-break: break-all;
  overflow-wrap: anywhere;
  text-align: end;
}

/* ---------- Theme Popover & Toast ---------- */
.fc-popover {
  margin: auto;
  padding: 18px;
  border: 0;
  border-radius: 24px;
  background-color: var(--fc-surface-floating);
  color: var(--fc-on-surface);
  box-shadow: var(--fc-shadow-e2);
  width: min(90vw, 310px);
}
@supports ((anchor-name: --fc) and (position-area: top span-right)) {
  #btn-theme-menu { anchor-name: --theme-anchor; }
  #theme-popover {
    position-anchor: --theme-anchor;
    position-area: top span-right;
    inset: auto;
    margin: 0 0 10px 0;
  }
}
:root[data-liquid-glass="true"] .fc-popover,
:root[data-liquid-glass="true"] .fc-toast,
:root[data-liquid-glass="true"] .fc-dialog {
  background-color: var(--fc-glass-bg);
  backdrop-filter: var(--fc-glass-blur);
  box-shadow: inset 0 1px 0 var(--fc-glass-edge), var(--fc-shadow-e2);
}

.fc-dialog {
  margin: auto;
  padding: 20px;
  border: 0;
  border-radius: var(--fc-radius-card);
  background-color: var(--fc-surface-floating);
  color: var(--fc-on-surface);
  box-shadow: var(--fc-shadow-e2);
  width: min(92vw, 540px);
  max-height: 82vh;
}
.fc-dialog::backdrop {
  background: rgba(0, 0, 0, 0.48);
  backdrop-filter: blur(4px);
}
.fc-dir-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 300px;
  overflow-y: auto;
  padding: 6px;
  background-color: var(--fc-surface-inset);
  border-radius: var(--fc-radius-block);
}
.fc-dir-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--fc-on-surface);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.fc-dir-item:hover {
  background-color: var(--fc-surface-block);
}

.fc-swatch-row { display: flex; gap: 8px; flex-wrap: wrap; }
.fc-swatch {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 0;
  cursor: pointer;
  transition: transform var(--fc-duration-fast) var(--fc-ease-spring);
}
.fc-swatch:hover { transform: scale(1.08); }
.fc-swatch[aria-pressed="true"] {
  box-shadow: 0 0 0 2px var(--fc-surface-card), 0 0 0 4px var(--fc-primary);
}

.fc-toast-stack {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
}
.fc-toast {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: var(--fc-radius-pill);
  background-color: var(--fc-surface-floating);
  color: var(--fc-on-surface);
  box-shadow: var(--fc-shadow-e2);
  font-size: 13px;
  font-weight: 600;
  pointer-events: auto;
  animation: fc-toast-in 220ms var(--fc-ease-spring);
}
.fc-toast--err { background-color: var(--fc-error-container); color: var(--fc-on-error-container); }
@keyframes fc-toast-in {
  from { opacity: 0; transform: translateY(-10px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* ---------- Mobile Dock ---------- */
.fc-dock { display: none; }
@media (max-width: 760px) {
  .fc-sidebar { display: none; }
  .fc-topbar { padding: 14px 16px 8px; }
  .fc-view { padding: 4px 14px 96px; }
  .fc-dock {
    display: flex;
    position: fixed;
    left: 14px;
    right: 14px;
    bottom: 12px;
    padding: 6px;
    border-radius: 28px;
    background-color: var(--fc-surface-floating);
    box-shadow: var(--fc-shadow-e2);
    z-index: 20;
    justify-content: space-around;
  }
  :root[data-liquid-glass="true"] .fc-dock {
    background-color: var(--fc-glass-bg);
    backdrop-filter: var(--fc-glass-blur);
    box-shadow: inset 0 1px 0 var(--fc-glass-edge), var(--fc-shadow-e2);
  }
  .fc-dock__item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 50px;
    border: 0;
    border-radius: 22px;
    background: transparent;
    color: var(--fc-on-surface-variant);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .fc-dock__item[aria-current="page"] {
    background-color: var(--fc-surface-inset);
    color: var(--fc-primary);
  }
  .fc-dock__item svg { width: 19px; height: 19px; }
}

@media (forced-colors: active) {
  .fc-card, .fc-block, .fc-jobcard, .fc-segmented__btn, .fc-tab, .fc-popover {
    border: 1px solid CanvasText;
  }
  .fc-segmented__btn[aria-pressed="true"], .fc-tab[aria-selected="true"] {
    forced-color-adjust: none;
    background-color: Highlight;
    color: HighlightText;
    border: 2px solid Highlight;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute;pointer-events:none;" aria-hidden="true">
  <defs>
    <symbol id="fc-shape-cookie12" viewBox="0 0 100 100">
      <path fill="currentColor" d="M 44.53 3.86 Q 50.00 0.50 55.47 3.86 L 55.92 4.14 Q 61.39 7.50 67.80 7.32 L 68.34 7.31 Q 74.75 7.13 77.80 12.77 L 78.06 13.24 Q 81.11 18.89 86.76 21.94 L 87.23 22.20 Q 92.87 25.25 92.69 31.66 L 92.68 32.20 Q 92.50 38.61 95.86 44.08 L 96.14 44.53 Q 99.50 50.00 96.14 55.47 L 95.86 55.92 Q 92.50 61.39 92.68 67.80 L 92.69 68.34 Q 92.87 74.75 87.23 77.80 L 86.76 78.06 Q 81.11 81.11 78.06 86.76 L 77.80 87.23 Q 74.75 92.87 68.34 92.69 L 67.80 92.68 Q 61.39 92.50 55.92 95.86 L 55.47 96.14 Q 50.00 99.50 44.53 96.14 L 44.08 95.86 Q 38.61 92.50 32.20 92.68 L 31.66 92.69 Q 25.25 92.87 22.20 87.23 L 21.94 86.76 Q 18.89 81.11 13.24 78.06 L 12.77 77.80 Q 7.13 74.75 7.31 68.34 L 7.32 67.80 Q 7.50 61.39 4.14 55.92 L 3.86 55.47 Q 0.50 50.00 3.86 44.53 L 4.14 44.08 Q 7.50 38.61 7.32 32.20 L 7.31 31.66 Q 7.13 25.25 12.77 22.20 L 13.24 21.94 Q 18.89 18.89 21.94 13.24 L 22.20 12.77 Q 25.25 7.13 31.66 7.31 L 32.20 7.32 Q 38.61 7.50 44.08 4.14 Z"/>
    </symbol>
  </defs>
</svg>

<div id="fc-toast-stack" class="fc-toast-stack" aria-live="polite"></div>

<div id="fc-shell" class="fc-shell">
  <aside class="fc-sidebar" aria-label="主导航">
    <div class="fc-sidebar__top">
      <button id="btn-collapse" type="button" class="fc-icon-btn" aria-label="折叠侧边栏" title="折叠侧边栏" data-i18n-aria="sb.collapse" data-i18n-title="sb.collapse">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="3"/><line x1="9" y1="4" x2="9" y2="20"/>
        </svg>
      </button>
      <div class="fc-sidebar__brand">
        <span class="fc-brand-dot" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
          </svg>
        </span>
        <span>flac-hunter</span>
      </div>
    </div>

    <nav class="fc-nav" aria-label="功能视图">
      <button type="button" class="fc-nav-item" data-tab="import" aria-current="page">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <rect x="3" y="3" width="8" height="8" rx="2.5"/><rect x="13" y="3" width="8" height="8" rx="4"/>
          <rect x="3" y="13" width="8" height="8" rx="2.5"/><rect x="13" y="13" width="8" height="8" rx="2.5"/>
        </svg>
        <span data-i18n="nav.import">歌单导入</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="upgrade">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polygon points="12 2 15 9 22 9 16.5 14 18.5 21 12 17 5.5 21 7.5 14 2 9 9 9 12 2"/>
        </svg>
        <span data-i18n="nav.upgrade">无损升级</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="audit">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        </svg>
        <span data-i18n="nav.audit">质量审计</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="dedupe">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="13" height="13" rx="2"/><path d="M8 20h10a2 2 0 0 0 2-2V8"/>
        </svg>
        <span data-i18n="nav.dedupe">曲库查重</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="library">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M4 4h3v16H4z"/><path d="M10.5 4h3v16h-3z"/><path d="M17.2 4.4l2.9.8-3.3 14.6-2.9-.8z"/>
        </svg>
        <span data-i18n="nav.library">曲库浏览</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="lyrics">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
          <polyline points="14 3 14 9 20 9"/><line x1="8" y1="14" x2="16" y2="14"/><line x1="8" y1="17.5" x2="12.5" y2="17.5"/>
        </svg>
        <span data-i18n="nav.lyrics">歌词体检</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="rename">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/>
        </svg>
        <span data-i18n="nav.rename">改名工具</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="fingerprint">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 12a6 6 0 0 1 12 0c0 3.5-.9 5-.9 8"/><path d="M9.5 13.5A2.5 2.5 0 0 1 12 11a2.5 2.5 0 0 1 2.5 2.5c0 2-.5 3-.5 5.5"/><path d="M12 15v4"/>
        </svg>
        <span data-i18n="nav.fingerprint">指纹对比</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="jobs">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span data-i18n="nav.jobs">任务列表</span>
        <span id="nav-jobs-badge" class="fc-nav-badge fc-tabular"></span>
      </button>
    </nav>

    <div class="fc-sidebar__footer">
      <div class="fc-lib-mini">
        <div class="fc-row" style="justify-content:space-between;gap:6px;">
          <span id="sb-lib-total" class="fc-tabular"><strong>0</strong> 首曲目</span>
          <button type="button" id="btn-switch-lib" class="fc-btn fc-btn--sm fc-btn--tonal" style="padding:3px 9px;font-size:11px;" data-i18n="sb.switchLib">切换曲库</button>
        </div>
        <span id="sb-lib-sub" class="fc-tabular">FLAC 0 · MP3 0 · OGG 0</span>
        <span id="sb-lib-dir" class="fc-mono" style="font-size:11px;color:var(--fc-on-surface-variant);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
      </div>
      <div class="fc-row" style="gap:6px;">
        <button id="btn-theme-menu" type="button" class="fc-nav-item" popovertarget="theme-popover" style="height:36px;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
            <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
          </svg>
          <span data-i18n="sb.appearance">外观设置</span>
        </button>
      </div>
    </div>
  </aside>

  <main class="fc-main">
    <header class="fc-topbar">
      <div class="fc-topbar__title-wrap">
        <h1 id="topbar-title" class="fc-topbar__title">歌单导入</h1>
        <span id="topbar-sub" class="fc-topbar__sub fc-tabular"></span>
      </div>
      <div class="fc-topbar__actions">
        <span id="jobstat" class="fc-chip fc-tabular" data-i18n="common.idle">空闲</span>
        <button id="btn-lang" type="button" class="fc-btn fc-btn--sm fc-btn--tonal" aria-label="切换语言 / Switch Language" title="切换语言 / Switch Language" style="min-width:44px;font-weight:700;">EN</button>
        <button id="btn-quick-theme" type="button" class="fc-icon-btn fc-icon-btn--tonal" aria-label="切换浅色或深色主题" title="切换明暗主题" data-i18n-aria="topbar.toggleTheme" data-i18n-title="topbar.toggleTheme">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4"/>
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- VIEW 1: 歌单导入与总览 -->
    <section id="tab-import" class="fc-view" data-view="import">
      <div class="fc-dash-row-1">
        <article id="hero-card" class="fc-card fc-card--clip fc-status-card">
          <svg class="fc-status-card__deco" aria-hidden="true"><use href="#fc-shape-cookie12"></use></svg>
          <div class="fc-status-card__content">
            <div class="fc-card-header" style="margin-bottom:0;">
              <div class="fc-card-header__start">
                <svg class="fc-card-header__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <h2 class="fc-card-header__title" data-i18n="hero.title">引擎状态</h2>
                <span id="hero-chip" class="fc-chip fc-chip--ok"><span class="fc-chip__dot" aria-hidden="true"></span><span id="hero-chip-text" data-i18n="hero.ready">就绪</span></span>
              </div>
            </div>
            <div>
              <div id="hero-headline" class="fc-status-card__main" data-i18n="hero.headlineIdle">准备导入歌单或文本清单</div>
              <div class="fc-row" style="margin-top:6px;gap:8px;">
                <div id="hero-dir" class="fc-stat-sub fc-mono" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></div>
                <button type="button" id="btn-hero-switch-lib" class="fc-btn fc-btn--sm fc-btn--tonal" style="padding:2px 9px;font-size:11.5px;" data-i18n="hero.switchDefaultLib">切换默认曲库</button>
              </div>
            </div>
            <div class="fc-status-card__meta">
              <div>
                <div class="fc-meta-item__label" data-i18n="hero.jobProgress">作业进度</div>
                <div id="hero-progress" class="fc-meta-item__value fc-tabular" data-i18n="common.idle">空闲</div>
              </div>
              <div>
                <div class="fc-meta-item__label" data-i18n="hero.rateAndLock">限速与锁</div>
                <div class="fc-meta-item__value" data-i18n="hero.singleQueue">单队列串行</div>
              </div>
            </div>
          </div>
          <div class="fc-status-card__action">
            <button id="hero-action-btn" type="button" class="fc-scallop-btn" aria-pressed="false" aria-label="快捷操作" title="聚焦导入 / 暂停或继续下载" data-i18n-aria="hero.quickAction" data-i18n-title="hero.quickActionTitle">
              <svg class="fc-scallop-btn__shape" aria-hidden="true"><use href="#fc-shape-cookie12"></use></svg>
              <span id="hero-action-icon" class="fc-scallop-btn__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>
              </span>
            </button>
          </div>
        </article>

        <article class="fc-card fc-stat-card">
          <div class="fc-card-header" style="margin-bottom:0;">
            <div class="fc-card-header__start">
              <svg class="fc-card-header__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>
              </svg>
              <h2 class="fc-card-header__title" data-i18n="stat.losslessRate">本地曲库无损率</h2>
            </div>
            <span id="stat-flac-pct" class="fc-chip fc-chip--primary fc-tabular">0%</span>
          </div>
          <div>
            <div class="fc-stat-figure">
              <span id="stat-flac-num" class="fc-stat-num fc-tabular">0</span>
              <span class="fc-stat-unit">FLAC</span>
            </div>
            <div id="stat-lib-sub" class="fc-stat-sub fc-tabular">MP3 0 · OGG 0 · 共 0 首</div>
          </div>
          <div class="fc-segmented-bar" aria-label="曲库格式比例">
            <div id="bar-flac" class="fc-segmented-bar__seg fc-segmented-bar__seg--primary" style="width:0%"></div>
            <div id="bar-lossy" class="fc-segmented-bar__seg fc-segmented-bar__seg--secondary" style="width:0%"></div>
          </div>
        </article>

        <article class="fc-card fc-stat-card">
          <div class="fc-card-header" style="margin-bottom:0;">
            <div class="fc-card-header__start">
              <svg class="fc-card-header__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M9 11l3 3L22 4"/>
              </svg>
              <h2 class="fc-card-header__title" data-i18n="stat.recentAudit">最近质量审计</h2>
            </div>
            <button type="button" class="fc-btn fc-btn--sm" data-jump="audit" data-i18n="common.details">详情</button>
          </div>
          <div>
            <div class="fc-stat-figure">
              <span id="stat-audit-rate" class="fc-stat-num fc-tabular">—</span>
              <span class="fc-stat-unit" data-i18n="stat.passRate">通过率</span>
            </div>
            <div id="stat-audit-sub" class="fc-stat-sub fc-tabular" data-i18n="stat.noAuditYet">尚未加载审计记录</div>
          </div>
          <div class="fc-wavy-meter" aria-hidden="true">
            <svg viewBox="0 0 220 12" preserveAspectRatio="none">
              <line x1="0" y1="6" x2="220" y2="6" stroke="var(--fc-surface-inset)" stroke-width="3" stroke-linecap="round"/>
              <path id="wavy-audit-path" fill="none" stroke="var(--fc-primary)" stroke-width="3" stroke-linecap="round" d="M 0 6 L 0 6"/>
            </svg>
          </div>
        </article>
      </div>

      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="imp.step1Title">1 · 导入歌单与查重</h2>
            <span class="fc-card-header__sub" data-i18n="imp.step1Sub">拉元数据后与本地曲库三层比对</span>
          </div>
          <div class="fc-tablist" role="tablist" aria-label="导入方式">
            <button type="button" class="fc-tab" id="imp-tab-uri" role="tab" aria-selected="true" data-i18n="imp.tabUri">歌单链接 / URI</button>
            <button type="button" class="fc-tab" id="imp-tab-list" role="tab" aria-selected="false" data-i18n="imp.tabList">文本清单 (--list)</button>
          </div>
        </div>

        <div id="imp-panel-uri" role="tabpanel" aria-labelledby="imp-tab-uri" class="fc-tabpanel-inner">
          <div class="fc-row">
            <input type="text" class="fc-input" id="uri" aria-label="歌单链接或 URI" placeholder="粘贴歌单链接或 URI：B站收藏夹 / y.qq.com / 网易云 playlist / spotify: URI" data-i18n-ph="imp.uriPh">
            <button type="button" class="fc-btn fc-btn--primary" id="btn-uri" data-i18n="imp.btnUri">拉取并查重</button>
          </div>
          <div class="fc-hint" data-i18n="imp.uriHint">支持 bilibili.com 收藏夹、y.qq.com 歌单、网易云公开 playlist、spotify: URI。若为私密歌单，可切换「文本清单」。</div>
        </div>

        <div id="imp-panel-list" role="tabpanel" aria-labelledby="imp-tab-list" class="fc-tabpanel-inner" hidden>
          <textarea class="fc-textarea" id="listtext" aria-label="文本清单内容" placeholder="每行一首：歌名 - 歌手（也支持 歌名-歌手 或只写歌名；末尾可选加 | 时长秒）&#10;例：快晴 - Orangestar&#10;例：又三郎-ヨルシカ" data-i18n-ph="imp.listPh"></textarea>
          <div class="fc-row" style="margin-top:10px;">
            <button type="button" class="fc-btn fc-btn--primary" id="btn-list" data-i18n="imp.btnList">按文本清单查重</button>
            <span class="fc-hint" style="margin:0;" data-i18n="imp.listHint">只填歌名时自动联网展开多个歌手/版本供选择；填「歌名 - 歌手」直接本地查重。</span>
          </div>
        </div>

        <div class="fc-block" style="margin-top:14px;">
          <div class="fc-row" style="gap:8px;">
            <label class="fc-switch-label" for="dl-dir" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="imp.saveTo">本次下载保存到</label>
            <input type="text" id="dl-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则保存到默认曲库" data-i18n-ph="imp.dlDirPh">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-pick-dir" data-i18n="common.pickFolder">选择文件夹</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-reset-dir" data-i18n="common.resetDefault">恢复默认</button>
          </div>
          <div class="fc-hint" style="margin-top:6px;" data-i18n="imp.saveToHint">支持手动输入/粘贴路径或点击「选择文件夹」；留空则沿用默认曲库目录。</div>
        </div>
      </article>

      <article class="fc-card" id="tracks-card" hidden>
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="imp.step2Title">2 · 勾选要下载的曲目</h2>
            <span id="track-summary" class="fc-chip fc-tabular"></span>
          </div>
          <label class="fc-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="search" id="track-filter" placeholder="过滤歌名或歌手…" data-i18n-ph="imp.filterPh">
          </label>
        </div>

        <div class="fc-row" style="margin-bottom:12px;">
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selnew" data-i18n="imp.selNew">只选新曲</button>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selall" data-i18n="common.selAll">全选</button>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selnone" data-i18n="common.selNone">全不选</button>
          <span class="fc-spacer"></span>
          <label class="fc-switch-label" for="source"><span data-i18n="imp.source">下载源</span>
            <select id="source" class="fc-select">
              <option value="auto" data-i18n="imp.srcAuto">auto（无损优先）</option>
              <option value="gdstudio">gdstudio</option>
              <option value="netease">netease</option>
              <option value="musicdl">musicdl</option>
              <option value="bili">bili</option>
              <option value="youtube">youtube</option>
            </select>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="dl-cover" class="fc-switch" checked>
            <span data-i18n="imp.dlCover">下载封面</span>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="dl-lyrics" class="fc-switch">
            <span data-i18n="imp.dlLyrics">下载歌词</span>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="inc-ex" class="fc-switch">
            <span data-i18n="imp.incEx">含已有曲目重下</span>
          </label>
          <button type="button" class="fc-btn fc-btn--primary" id="btn-dl"><span data-i18n="imp.btnDl">开始下载</span> (<span id="sel-count" class="fc-tabular">0</span>)</button>
        </div>

        <div class="fc-table-wrap" tabindex="0" role="region" aria-label="歌单曲目查重列表">
          <table id="tracks" class="fc-table fc-table--responsive">
            <caption data-i18n="imp.tableCap">导入的歌单曲目及本地去重状态</caption>
            <thead>
              <tr>
                <th style="width:40px;"><input type="checkbox" id="chk-head" aria-label="切换全部勾选"></th>
                <th style="width:46px;" class="is-num">#</th>
                <th data-i18n="imp.colTitle">歌名</th>
                <th data-i18n="imp.colArtist">歌手</th>
                <th style="width:76px;" class="is-num" data-i18n="imp.colDur">时长</th>
                <th style="width:92px;" data-i18n="imp.colStatus">状态</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </article>
    </section>

    <!-- VIEW 2: 任务列表 -->
    <section id="tab-jobs" class="fc-view" data-view="jobs" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="jobs.title">任务列表</h2>
            <span class="fc-card-header__sub" data-i18n="jobs.sub">同一时间仅执行一个作业，共享限速与曲库锁</span>
          </div>
        </div>
        <div id="joblist" class="fc-job-list"><div class="fc-empty" data-i18n="jobs.empty">还没有任务 —— 前往「歌单导入」发起查重与下载</div></div>
      </article>

      <article class="fc-card" id="joblog-card" hidden>
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 id="joblog-title" class="fc-card-header__title" data-i18n="jobs.logTitle">作业日志</h2>
            <span id="dlpct" class="fc-chip fc-chip--primary fc-tabular"></span>
            <span id="job-cancelled-chip" class="fc-chip fc-chip--warn" hidden></span>
          </div>
          <div class="fc-row" style="gap:6px;">
            <button type="button" class="fc-btn fc-btn--sm" id="btn-copy-log" data-i18n="jobs.copyLog">复制日志</button>
            <button type="button" class="fc-btn fc-btn--sm" id="btn-pause" hidden>⏸ 暂停</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--danger" id="btn-skip" hidden data-i18n="jobs.skipTrack">⏭ 跳过这首</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--danger" id="btn-cancel" hidden data-i18n="jobs.cancel">⏹ 取消</button>
          </div>
        </div>
        <div class="fc-segmented-bar" id="dlbar-wrap" style="margin-bottom:10px;">
          <div id="dlbar" class="fc-segmented-bar__seg fc-segmented-bar__seg--primary" style="width:0%"></div>
        </div>
        <div id="job-stats-row" class="fc-row" style="gap:6px;margin-bottom:8px;flex-wrap:wrap;" hidden></div>
        <div id="cur-track" class="fc-block" style="margin:0 0 10px;padding:9px 12px;font-size:13px;" hidden></div>
        <div class="fc-log fc-mono" id="joblog" tabindex="0" aria-label="作业输出日志"></div>
      </article>
    </section>

    <!-- VIEW 3: 无损升级 -->
    <section id="tab-upgrade" class="fc-view" data-view="upgrade" hidden>
      <article class="fc-card" id="up-queue-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="up.step1Title">1 · 待升级清单</h2>
            <span id="up-queue-count" class="fc-chip fc-chip--primary fc-tabular">0 个文件</span>
          </div>
          <div class="fc-row" style="gap:6px;">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-selall" data-i18n="common.selAll">全选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-selnone" data-i18n="common.selNone">全不选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-clear-files" data-i18n="up.clearList">清空清单</button>
          </div>
        </div>

        <div class="fc-block" style="margin-bottom:12px;">
          <div class="fc-row" style="gap:8px;margin-bottom:10px;">
            <label class="fc-switch-label" for="up-dir" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="up.scanDir">扫描目录</label>
            <input type="text" id="up-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则扫描默认曲库" data-i18n-ph="common.scanDirPh">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-pick-dir" data-i18n="common.pickFolder">选择文件夹</button>
          </div>
          <div class="fc-row" style="gap:8px;justify-content:space-between;">
            <div class="fc-segmented" id="up-ext-seg" role="group" aria-label="扫描格式">
              <button type="button" class="fc-segmented__btn" data-ext="all" aria-pressed="true">MP3 + OGG</button>
              <button type="button" class="fc-segmented__btn" data-ext="mp3" aria-pressed="false" data-i18n="up.onlyMp3">仅 MP3</button>
              <button type="button" class="fc-segmented__btn" data-ext="ogg" aria-pressed="false" data-i18n="up.onlyOgg">仅 OGG</button>
              <button type="button" class="fc-segmented__btn" data-ext="flac" aria-pressed="false">FLAC</button>
            </div>
            <select id="up-ext" class="fc-sr-only" aria-hidden="true" tabindex="-1">
              <option value="all" selected>all</option>
              <option value="mp3">mp3</option>
              <option value="ogg">ogg</option>
              <option value="flac">flac</option>
            </select>
            <div class="fc-row" style="gap:8px;">
              <input type="search" id="up-queue-filter" class="fc-input" style="max-width:200px;padding:6px 10px;" placeholder="过滤清单文件名…" data-i18n-ph="up.filterPh">
              <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-up-scan" data-i18n="up.btnScan">扫描载入清单</button>
            </div>
          </div>
        </div>

        <div id="up-queue-list" class="fc-dir-list" style="max-height:260px;">
          <div class="fc-empty" data-i18n="up.empty">待升级清单为空 —— 请在上方选择目录「扫描载入清单」，或从「质量审计」传入不合格文件</div>
        </div>
      </article>

      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="up.step2Title">2 · 升级执行</h2>
            <span class="fc-card-header__sub" data-i18n="up.step2Sub">MP3/OGG 或假无损重拉真 FLAC；已是真 FLAC 仅就地补封面与标签（免重下）</span>
          </div>
        </div>

        <div class="fc-block" style="margin-bottom:14px;">
          <div class="fc-row" style="justify-content:space-between;">
            <div>
              <div style="font-weight:600;" data-i18n="up.retryTitle">清空跳名单全量重试</div>
              <div class="fc-stat-sub" data-i18n="up.retrySub">连续失败 ≥ 2 次的曲目默认记入跳名单；开启后会重置记录重新尝试</div>
            </div>
            <label class="fc-switch-label">
              <input type="checkbox" id="up-retry" class="fc-switch" aria-label="清空跳名单全量重试">
            </label>
          </div>
        </div>

        <div class="fc-row">
          <button type="button" class="fc-btn fc-btn--primary" id="btn-up"><span data-i18n="up.btnStart">开始无损升级</span> (<span id="up-sel-count" class="fc-tabular">0</span>)</button>
          <span class="fc-hint" style="margin:0;" data-i18n="up.hint">替换前自动备份旧文件并对比 PCM 指纹留证。</span>
        </div>
      </article>
    </section>

    <!-- VIEW 4: 质量审计 -->
    <section id="tab-audit" class="fc-view" data-view="audit" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="aud.title">四项质量门审计</h2>
            <span class="fc-card-header__sub" data-i18n="aud.sub">实测 ffprobe：时长偏差 / 缺标签 / 缺封面 / 伪 FLAC</span>
          </div>
          <div class="fc-row" style="gap:8px;">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-load-files" data-i18n="aud.pickFiles">选定文件列表</button>
            <button type="button" class="fc-btn fc-btn--primary" id="btn-audit" data-i18n="aud.btnStart">开始审计</button>
          </div>
        </div>
        <div class="fc-block" style="margin-bottom:10px;">
          <div class="fc-row" style="gap:8px;">
            <label class="fc-switch-label" for="aud-dir" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="aud.dirLabel">审计目录</label>
            <input type="text" id="aud-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则扫描默认曲库" data-i18n-ph="common.scanDirPh">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-dir" data-i18n="common.pickFolder">选择文件夹</button>
          </div>
        </div>
        <div id="aud-pick-box" class="fc-block" style="margin-bottom:10px;" hidden>
          <div class="fc-row" style="gap:8px;margin-bottom:8px;">
            <span id="aud-pick-summary" class="fc-chip fc-tabular">已选 0 个文件</span>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-all" data-i18n="common.selAll">全选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-none" data-i18n="common.clear">清空</button>
            <span class="fc-spacer"></span>
            <input type="search" id="aud-pick-filter" class="fc-input" style="max-width:220px;padding:6px 10px;" placeholder="过滤待审文件名…" data-i18n-ph="aud.pickFilterPh">
          </div>
          <div id="aud-pick-list" class="fc-dir-list" style="max-height:200px;"></div>
        </div>
        <div id="audit-empty-hint" class="fc-hint" style="margin-top:0;" data-i18n="aud.emptyHint">不选定具体文件时将扫描目录内全部 .flac；若有历史审计记录将自动回显在下方。</div>
      </article>

      <div id="audit-result" hidden>
        <div class="fc-kpi-row" id="audit-tiles" style="margin-bottom:14px;"></div>

        <article class="fc-card">
          <div class="fc-card-header">
            <div class="fc-card-header__start">
              <h2 class="fc-card-header__title" data-i18n="aud.detailTitle">不合格文件明细</h2>
              <span id="audit-when" class="fc-chip fc-tabular"></span>
            </div>
            <div class="fc-row" style="gap:8px;">
              <span id="audit-count" class="fc-stat-sub fc-tabular"></span>
              <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-send-sel"><span data-i18n="aud.sendSel">选中传入升级</span> (<span id="aud-sel-count" class="fc-tabular">0</span>)</button>
              <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-aud-send-all" data-i18n="aud.sendAll">全部不合格传入升级</button>
            </div>
          </div>

          <div class="fc-row" style="justify-content:space-between;margin-bottom:12px;">
            <div id="audit-chips" class="fc-tablist" role="tablist" aria-label="按问题分类筛选"></div>
            <label class="fc-search">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="search" id="audit-search" placeholder="按文件名搜索…" data-i18n-ph="aud.searchPh">
            </label>
          </div>

          <div class="fc-table-wrap" tabindex="0" role="region" aria-label="质量审计异常文件列表">
            <table id="audit-files" class="fc-table fc-table--responsive">
              <caption data-i18n="aud.tableCap">未通过四项质量门的 FLAC 文件列表</caption>
              <thead><tr><th style="width:40px;"><input type="checkbox" id="aud-chk-head" aria-label="全选当前不合格文件"></th><th data-i18n="aud.colFile">文件名</th><th style="width:240px;" data-i18n="aud.colIssues">触发问题</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>
        </article>
      </div>
    </section>

    <section data-view="dedupe" hidden>
      <article class="fc-card" style="margin-bottom:16px;">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="ded.step1Title">1 · 曲库查重扫描</h2>
            <span class="fc-card-header__sub" data-i18n="ded.step1Sub">按歌名、艺人别名与时长（±3s）聚类疑似重复文件，绝不自动删除，全权由你确认处理</span>
          </div>
          <span id="ded-summary" class="fc-chip fc-tabular" data-i18n="ded.notScanned">未扫描</span>
        </div>
        <div class="fc-block" style="margin-bottom:12px;">
          <div class="fc-row" style="gap:8px;flex-wrap:wrap;align-items:center;">
            <label class="fc-switch-label" for="ded-dir" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="ded.dirLabel">查重目录</label>
            <input type="text" id="ded-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则扫描当前默认曲库" data-i18n-ph="common.scanDirPh">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-pick-ded-dir" data-i18n="common.pickFolder">选择文件夹</button>
          </div>
        </div>
        <div class="fc-row" style="gap:10px;flex-wrap:wrap;">
          <button type="button" class="fc-btn fc-btn--primary" id="btn-ded-scan" data-i18n="ded.btnScan">开始扫描查重</button>
          <label class="fc-search" style="flex:1;min-width:180px;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="search" id="ded-filter" placeholder="过滤歌名、艺人或文件名…" data-i18n-ph="ded.filterPh">
          </label>
        </div>
      </article>

      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="ded.step2Title">2 · 疑似重复分组</h2>
            <span class="fc-card-header__sub" data-i18n="ded.step2Sub">请勾选确认要清理的冗余副本；操作会移入 staging/dedupe_trash 回收站</span>
          </div>
          <div class="fc-row" style="gap:6px;flex-wrap:wrap;">
            <button type="button" class="fc-btn fc-btn--sm" id="btn-ded-auto" data-i18n="ded.keepBest">保留最优（勾选其余）</button>
            <button type="button" class="fc-btn fc-btn--sm" id="btn-ded-none" data-i18n="ded.clearSel">清空勾选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--danger" id="btn-ded-del"><span data-i18n="ded.moveTrash">移入回收站</span> (<span id="ded-sel-count" class="fc-tabular">0</span>)</button>
          </div>
        </div>
        <div id="ded-groups" class="fc-dir-list" style="max-height:520px;">
          <div class="fc-empty" data-i18n="ded.empty">点击上方「开始扫描查重」列出曲库中可能重复的曲目分组</div>
        </div>
      </article>
    </section>

    <!-- VIEW 5: 曲库浏览 -->
    <section id="tab-library" class="fc-view" data-view="library" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="lib.title">曲库浏览</h2>
            <span class="fc-card-header__sub" data-i18n="lib.sub">按文件名与格式检索曲库音频文件</span>
          </div>
          <span id="lib-summary" class="fc-chip fc-tabular" data-i18n="lib.notLoaded">未载入</span>
        </div>
        <div class="fc-row" style="gap:8px;margin-bottom:12px;">
          <label class="fc-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="search" id="lib-q" placeholder="搜索文件名…" data-i18n-ph="lib.searchPh">
          </label>
          <select id="lib-ext" class="fc-select" aria-label="按格式筛选" data-i18n-aria="lib.extAria">
            <option value="" data-i18n="lib.extAll">全部格式</option>
            <option value="flac">flac</option>
            <option value="mp3">mp3</option>
            <option value="ogg">ogg</option>
            <option value="m4a">m4a</option>
            <option value="opus">opus</option>
            <option value="wav">wav</option>
          </select>
          <select id="lib-page-size" class="fc-select" aria-label="每页数量" data-i18n-aria="lib.pageSizeAria">
            <option value="50">50</option>
            <option value="100" selected>100</option>
            <option value="200">200</option>
          </select>
          <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-lib-load" data-i18n="lib.btnLoad">载入曲库</button>
        </div>
        <div class="fc-table-wrap" tabindex="0" role="region" aria-label="曲库文件列表" data-i18n-aria="lib.tableAria">
          <table id="lib-files" class="fc-table fc-table--responsive">
            <caption data-i18n="lib.tableCap">曲库音频文件索引</caption>
            <thead>
              <tr>
                <th data-i18n="lib.colName">文件名</th>
                <th style="width:84px;" data-i18n="lib.colExt">格式</th>
                <th style="width:110px;" class="fc-num" data-i18n="lib.colSize">大小 (MB)</th>
                <th style="width:150px;" data-i18n="lib.colMtime">修改时间</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="fc-page-bar">
          <button type="button" class="fc-btn fc-btn--sm" id="btn-lib-prev" disabled data-i18n="lib.prevPage">上一页</button>
          <span id="lib-page-info" class="fc-chip fc-tabular">—</span>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-lib-next" disabled data-i18n="lib.nextPage">下一页</button>
        </div>
      </article>
    </section>

    <!-- VIEW 6: 歌词体检 -->
    <section id="tab-lyrics" class="fc-view" data-view="lyrics" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="lyr.title">歌词体检</h2>
            <span class="fc-card-header__sub" data-i18n="lyr.sub">八类歌词问题分组体检，可勾选清理</span>
          </div>
          <span id="lyr-summary" class="fc-chip fc-tabular" data-i18n="lyr.notLoaded">未体检</span>
        </div>
        <div class="fc-row" style="gap:8px;margin-bottom:10px;">
          <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-lyr-reload" data-i18n="lyr.btnReload">重新体检</button>
          <button type="button" class="fc-btn fc-btn--sm fc-btn--danger" id="btn-lyr-del"><span data-i18n="lyr.btnDelete">删除所选</span> (<span id="lyr-sel-count" class="fc-tabular">0</span>)</button>
          <span class="fc-spacer"></span>
          <span id="lyr-dir" class="fc-chip fc-mono" hidden></span>
        </div>
        <div class="fc-hint" style="margin-top:0;" data-i18n="lyr.hint">体检只读不改动任何文件；「删除所选」仅把歌词移入回收目录 staging/lrc_trash/&lt;时间戳&gt;/，随时可手动移回，绝不直接销毁。</div>
        <div id="lyr-result" class="fc-block" style="margin-top:10px;" hidden></div>
        <div id="lyr-groups" class="fc-dir-list" style="max-height:520px;margin-top:10px;">
          <div class="fc-empty" data-i18n="lyr.empty">点击「重新体检」扫描曲库歌词问题</div>
        </div>
      </article>
    </section>

    <!-- VIEW 7: 改名工具 -->
    <section id="tab-rename" class="fc-view" data-view="rename" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="ren.title">改名工具</h2>
            <span class="fc-card-header__sub" data-i18n="ren.sub">按扫描建议批量规范曲库文件名</span>
          </div>
          <span id="ren-summary" class="fc-chip fc-tabular" data-i18n="ren.notScanned">未扫描</span>
        </div>
        <div class="fc-row" style="gap:8px;margin-bottom:10px;">
          <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-ren-scan" data-i18n="ren.btnScan">扫描改名建议</button>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-ren-apply"><span data-i18n="ren.btnApply">应用所选</span> (<span id="ren-sel-count" class="fc-tabular">0</span>)</button>
        </div>
        <div class="fc-hint" style="margin-top:0;" data-i18n="ren.hint">应用时服务端会自动同步同名 .jpg / .lrc 侧车文件一起改名；目标已存在时跳过并报告，绝不覆盖。</div>
        <div id="ren-result" class="fc-block" style="margin-top:10px;" hidden></div>
        <div id="ren-list" class="fc-dir-list" style="max-height:520px;margin-top:10px;">
          <div class="fc-empty" data-i18n="ren.empty">点击「扫描改名建议」检查曲库文件命名</div>
        </div>
      </article>
    </section>

    <!-- VIEW 8: 指纹对比 -->
    <section id="tab-fingerprint" class="fc-view" data-view="fingerprint" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title" data-i18n="fp.title">指纹对比</h2>
            <span class="fc-card-header__sub" data-i18n="fp.sub">对比两个音频文件的 PCM 指纹（MD5）判断是否同一音源</span>
          </div>
        </div>
        <div class="fc-block" style="margin-bottom:10px;">
          <div class="fc-row" style="gap:8px;">
            <label class="fc-switch-label" for="fp-a" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="fp.labelA">文件 A</label>
            <input type="text" id="fp-a" class="fc-input" placeholder="第一个音频文件的绝对路径…" data-i18n-ph="fp.pathPhA">
          </div>
          <div class="fc-row" style="gap:8px;margin-top:8px;">
            <label class="fc-switch-label" for="fp-b" style="font-weight:600;color:var(--fc-on-surface);" data-i18n="fp.labelB">文件 B</label>
            <input type="text" id="fp-b" class="fc-input" placeholder="第二个音频文件的绝对路径…" data-i18n-ph="fp.pathPhB">
          </div>
          <div class="fc-row" style="margin-top:12px;">
            <button type="button" class="fc-btn fc-btn--primary" id="btn-fp" data-i18n="fp.btnCompare">对比</button>
          </div>
        </div>
        <div id="fp-result" class="fc-block" hidden>
          <div class="fc-row" style="justify-content:space-between;">
            <span class="fc-chip" data-i18n="fp.resultA">A 指纹</span>
            <span id="fp-a-md5" class="fc-fp-md5">—</span>
          </div>
          <div class="fc-row" style="justify-content:space-between;margin-top:8px;">
            <span class="fc-chip" data-i18n="fp.resultB">B 指纹</span>
            <span id="fp-b-md5" class="fc-fp-md5">—</span>
          </div>
          <div style="margin-top:10px;">
            <span id="fp-match" class="fc-chip">—</span>
          </div>
        </div>
      </article>
    </section>
  </main>
</div>

<nav class="fc-dock" aria-label="移动端快捷导航">
  <button type="button" class="fc-dock__item" data-tab="import" aria-current="page">
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="4"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/></svg>
    <span data-i18n="dock.import">导入</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="upgrade">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polygon points="12 2 15 9 22 9 16.5 14 18.5 21 12 17 5.5 21 7.5 14 2 9 9 9 12 2"/></svg>
    <span data-i18n="dock.upgrade">升级</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="audit">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
    <span data-i18n="dock.audit">审计</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="dedupe">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="13" height="13" rx="2"/><path d="M8 20h10a2 2 0 0 0 2-2V8"/></svg>
    <span data-i18n="dock.dedupe">查重</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="library">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 4h3v16H4z"/><path d="M10.5 4h3v16h-3z"/><path d="M17.2 4.4l2.9.8-3.3 14.6-2.9-.8z"/></svg>
    <span data-i18n="dock.library">曲库</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="lyrics">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="14 3 14 9 20 9"/><line x1="8" y1="14" x2="16" y2="14"/><line x1="8" y1="17.5" x2="12.5" y2="17.5"/></svg>
    <span data-i18n="dock.lyrics">歌词</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="rename">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/></svg>
    <span data-i18n="dock.rename">改名</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="fingerprint">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 12a6 6 0 0 1 12 0c0 3.5-.9 5-.9 8"/><path d="M9.5 13.5A2.5 2.5 0 0 1 12 11a2.5 2.5 0 0 1 2.5 2.5c0 2-.5 3-.5 5.5"/><path d="M12 15v4"/></svg>
    <span data-i18n="dock.fingerprint">指纹</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="jobs">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    <span data-i18n="dock.jobs">任务</span>
  </button>
</nav>

<div id="theme-popover" popover="auto" class="fc-popover" aria-label="外观与主题设置">
  <div style="font-weight:700;font-size:14px;margin-bottom:12px;" data-i18n="theme.title">外观与主题引擎</div>
  <div style="font-size:12px;color:var(--fc-on-surface-variant);margin-bottom:6px;" data-i18n="theme.lang">界面语言</div>
  <div class="fc-segmented" style="margin-bottom:14px;width:100%;">
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-lang="zh" aria-pressed="true">中文</button>
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-lang="en" aria-pressed="false">English</button>
  </div>
  <div style="font-size:12px;color:var(--fc-on-surface-variant);margin-bottom:6px;" data-i18n="theme.mode">主题模式</div>
  <div class="fc-segmented" style="margin-bottom:14px;width:100%;">
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="light dark" aria-pressed="true" data-i18n="theme.auto">跟随系统</button>
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="light" aria-pressed="false" data-i18n="theme.light">浅色</button>
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="dark" aria-pressed="false" data-i18n="theme.dark">深色</button>
  </div>
  <div style="font-size:12px;color:var(--fc-on-surface-variant);margin-bottom:6px;" data-i18n="theme.seed">种子主题色</div>
  <div id="seed-swatches" class="fc-swatch-row" style="margin-bottom:14px;"></div>
  <div class="fc-row" style="justify-content:space-between;margin-bottom:8px;">
    <span style="font-size:13px;" data-i18n="theme.pureBlack">纯黑深色 (OLED)</span>
    <input type="checkbox" id="pref-pure-black" class="fc-switch" aria-label="纯黑深色模式">
  </div>
  <div class="fc-row" style="justify-content:space-between;">
    <span style="font-size:13px;" data-i18n="theme.glass">Liquid Glass 浮层</span>
    <input type="checkbox" id="pref-glass" class="fc-switch" aria-label="Liquid Glass 液态毛玻璃" checked>
  </div>
</div>

<dialog id="dir-dialog" class="fc-dialog" aria-labelledby="dir-dialog-title">
  <div class="fc-card-header" style="margin-bottom:10px;">
    <h3 id="dir-dialog-title" class="fc-card-header__title" style="font-size:15px;color:var(--fc-on-surface);" data-i18n="dir.title">选择下载保存目录</h3>
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-close" data-i18n="common.close">关闭</button>
  </div>
  <div id="dir-drives" class="fc-row" style="gap:6px;margin-bottom:8px;flex-wrap:wrap;"></div>
  <div class="fc-row" style="gap:8px;margin-bottom:10px;">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-up" data-i18n="dir.up">上一级</button>
    <input type="text" id="dir-current" class="fc-input" style="flex:1;padding:7px 10px;" aria-label="当前目录路径">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-go" data-i18n="dir.go">跳转</button>
  </div>
  <div id="dir-list" class="fc-dir-list" role="listbox" aria-label="子文件夹列表"></div>
  <div class="fc-row" style="justify-content:flex-end;gap:8px;margin-top:12px;">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-cancel" data-i18n="common.cancel">取消</button>
    <button type="button" class="fc-btn fc-btn--primary" id="dir-choose" data-i18n="dir.choose">选择此目录</button>
  </div>
</dialog>

<script>
"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const LANG_KEY = "fh-lang";
const I18N = {
  zh: {
    "nav.import": "歌单导入",
    "nav.upgrade": "无损升级",
    "nav.audit": "质量审计",
    "nav.dedupe": "曲库查重",
    "nav.jobs": "任务列表",
    "nav.library": "曲库浏览",
    "nav.lyrics": "歌词体检",
    "nav.rename": "改名工具",
    "nav.fingerprint": "指纹对比",
    "dock.import": "导入",
    "dock.upgrade": "升级",
    "dock.audit": "审计",
    "dock.dedupe": "查重",
    "dock.jobs": "任务",
    "dock.library": "曲库",
    "dock.lyrics": "歌词",
    "dock.rename": "改名",
    "dock.fingerprint": "指纹",
    "sb.collapse": "折叠侧边栏",
    "sb.switchLib": "切换曲库",
    "sb.appearance": "外观设置",
    "sb.tracksCount": "<strong>{n}</strong> 首曲目",
    "topbar.toggleTheme": "切换浅色或深色主题",
    "topbar.sub": "曲库 {total} 首 · FLAC {flac} ({pct}%)",
    "common.idle": "空闲",
    "common.details": "详情",
    "common.pickFolder": "选择文件夹",
    "common.resetDefault": "恢复默认",
    "common.selAll": "全选",
    "common.selNone": "全不选",
    "common.clear": "清空",
    "common.close": "关闭",
    "common.cancel": "取消",
    "hero.title": "引擎状态",
    "hero.ready": "就绪",
    "hero.paused": "已暂停",
    "hero.runningSuffix": "{type}中",
    "hero.runningFallback": "{type}执行中…",
    "hero.processing": "处理中",
    "hero.headlineIdle": "准备导入歌单或文本清单",
    "hero.headlineLoaded": "已加载歌单 ({n} 首)，随时可下载",
    "hero.switchDefaultLib": "切换默认曲库",
    "hero.jobProgress": "作业进度",
    "hero.historyJobs": "历史任务 {n} 条",
    "hero.rateAndLock": "限速与锁",
    "hero.singleQueue": "单队列串行",
    "hero.quickAction": "快捷操作",
    "hero.quickActionTitle": "聚焦导入 / 暂停或继续下载",
    "hero.dirPrefix": "曲库：{dir}",
    "hero.resumedToast": "已恢复下载任务",
    "hero.pausingToast": "将在当前曲目完成后暂停",
    "stat.losslessRate": "本地曲库无损率",
    "stat.libSub": "MP3 {mp3} · OGG {ogg} · 共 {total} 首",
    "stat.recentAudit": "最近质量审计",
    "stat.passRate": "通过率",
    "stat.noAuditYet": "尚未加载审计记录",
    "stat.auditSub": "通过 {pass} / 不合格 {fail}（共 {total} 个 FLAC）",
    "imp.step1Title": "1 · 导入歌单与查重",
    "imp.step1Sub": "拉元数据后与本地曲库三层比对",
    "imp.tabUri": "歌单链接 / URI",
    "imp.tabList": "文本清单 (--list)",
    "imp.uriPh": "粘贴歌单链接或 URI：B站收藏夹 / y.qq.com / 网易云 playlist / spotify: URI",
    "imp.btnUri": "拉取并查重",
    "imp.uriHint": "支持 bilibili.com 收藏夹、y.qq.com 歌单、网易云公开 playlist、spotify: URI。若为私密歌单，可切换「文本清单」。",
    "imp.listPh": "每行一首：歌名 - 歌手（也支持 歌名-歌手 或只写歌名；末尾可选加 | 时长秒）\n例：快晴 - Orangestar\n例：又三郎-ヨルシカ",
    "imp.btnList": "按文本清单查重",
    "imp.listHint": "只填歌名时自动联网展开多个歌手/版本供选择；填「歌名 - 歌手」直接本地查重。",
    "imp.saveTo": "本次下载保存到",
    "imp.dlDirPh": "留空则保存到默认曲库",
    "imp.dlDirPhWith": "留空则保存到默认曲库（{dir}）",
    "imp.saveToHint": "支持手动输入/粘贴路径或点击「选择文件夹」；留空则沿用默认曲库目录。",
    "imp.step2Title": "2 · 勾选要下载的曲目",
    "imp.filterPh": "过滤歌名或歌手…",
    "imp.selNew": "只选新曲",
    "imp.source": "下载源",
    "imp.srcAuto": "auto（无损优先）",
    "imp.dlCover": "下载封面",
    "imp.dlLyrics": "下载歌词",
    "imp.incEx": "含已有曲目重下",
    "imp.btnDl": "开始下载",
    "imp.tableCap": "导入的歌单曲目及本地去重状态",
    "imp.colTitle": "歌名",
    "imp.colArtist": "歌手",
    "imp.colDur": "时长",
    "imp.colStatus": "状态",
    "imp.colSelect": "选择",
    "imp.statusExisting": "已有",
    "imp.statusNew": "新曲",
    "imp.emptyTracks": "没有匹配的曲目",
    "imp.trackSummary": "共 {total} 首 · 新曲 {newCount} · 已有 {exists}",
    "imp.toastExpanded": "已展开 {n} 个版本候选，请勾选需要的版本",
    "imp.toastUriEmpty": "请先填入歌单链接或 URI",
    "imp.toastUriDone": "歌单元数据拉取与查重完成",
    "imp.toastListEmpty": "文本清单不能为空",
    "imp.toastListDone": "文本清单查重完成",
    "imp.toastNeedImport": "请先导入歌单",
    "imp.toastNeedTrack": "请至少勾选一首曲目再下载",
    "imp.unknownTrack": "未知曲目",
    "imp.existingTag": "（已有: {file}）",
    "imp.moreExisting": "\n…等共 {n} 首",
    "imp.confirmExisting": "曲库中已有类似曲目，是否继续下载？\n\n{samples}{more}",
    "jobs.title": "任务列表",
    "jobs.sub": "同一时间仅执行一个作业，共享限速与曲库锁",
    "jobs.empty": "还没有任务 —— 前往「歌单导入」发起查重与下载",
    "jobs.logTitle": "作业日志",
    "jobs.logTitleWith": "作业日志 · {type}",
    "jobs.copyLog": "复制日志",
    "jobs.pause": "⏸ 暂停",
    "jobs.resume": "▶ 继续",
    "jobs.skipTrack": "⏭ 跳过这首",
    "jobs.runningCount": "进行中 {n} · {type}",
    "jobs.stRunning": "进行中",
    "jobs.stQueued": "排队中",
    "jobs.stDone": "已完成",
    "jobs.stError": "失败",
    "jobs.pausingNote": "已暂停（当前曲目完成后停下）",
    "jobs.processing": "正在处理：{name}",
    "jobs.targetDir": "目标：{dir}",
    "jobs.failToast": "作业执行失败，请查看日志详情",
    "jobs.copyOk": "日志已复制到剪贴板",
    "jobs.copyErr": "复制失败",
    "jobs.skipToast": "已请求跳过当前曲目",
    "jobs.cancel": "⏹ 取消",
    "jobs.cancelConfirm": "确认取消当前作业？将停止发送新任务并终止进行中的操作，剩余条目会补记为「已取消」。",
    "jobs.cancelToast": "已请求取消作业",
    "jobs.cancelledBadge": "已取消",
    "jobs.cancelledRemaining": "剩余 {n}",
    "up.step1Title": "1 · 待升级清单",
    "up.queueCount": "{checked} / {total} 个文件",
    "up.clearList": "清空清单",
    "up.scanDir": "扫描目录",
    "up.onlyMp3": "仅 MP3",
    "up.onlyOgg": "仅 OGG",
    "up.filterPh": "过滤清单文件名…",
    "up.btnScan": "扫描载入清单",
    "up.empty": "待升级清单为空 —— 请在上方选择目录「扫描载入清单」，或从「质量审计」传入不合格文件",
    "up.emptyFilter": "没有匹配过滤关键词的待升级文件",
    "up.step2Title": "2 · 升级执行",
    "up.step2Sub": "MP3/OGG 或假无损重拉真 FLAC；已是真 FLAC 仅就地补封面与标签（免重下）",
    "up.retryTitle": "清空跳名单全量重试",
    "up.retrySub": "连续失败 ≥ 2 次的曲目默认记入跳名单；开启后会重置记录重新尝试",
    "up.btnStart": "开始无损升级",
    "up.hint": "替换前自动备份旧文件并对比 PCM 指纹留证。",
    "up.tagAudit": "审计导入",
    "up.toastNoFiles": "没有可传入升级的文件",
    "up.toastSent": "已将 {n} 个文件传入待升级清单",
    "up.toastCleared": "已清空待升级清单",
    "up.toastLoaded": "已载入 {n} 个待升级文件",
    "up.toastNeedFiles": "请先扫描载入或从质量审计传入待升级文件",
    "aud.title": "四项质量门审计",
    "aud.sub": "实测 ffprobe：时长偏差 / 缺标签 / 缺封面 / 伪 FLAC",
    "aud.pickFiles": "选定文件列表",
    "aud.btnStart": "开始审计",
    "aud.dirLabel": "审计目录",
    "aud.pickSummary": "已选 {sel} / {total} 个文件",
    "aud.pickFilterPh": "过滤待审文件名…",
    "aud.pickEmpty": "目录下没有匹配的 .flac 文件",
    "aud.emptyHint": "不选定具体文件时将扫描目录内全部 .flac；若有历史审计记录将自动回显在下方。",
    "aud.detailTitle": "不合格文件明细",
    "aud.recent": "最近",
    "aud.sendSel": "选中传入升级",
    "aud.sendAll": "全部不合格传入升级",
    "aud.searchPh": "按文件名搜索…",
    "aud.tableCap": "未通过四项质量门的 FLAC 文件列表",
    "aud.colFile": "文件名",
    "aud.colIssues": "触发问题",
    "aud.tileTotal": "扫描 FLAC",
    "aud.tilePass": "四项全过",
    "aud.tileFail": "存在异常",
    "aud.tileRate": "合格率",
    "aud.allFilter": "全部",
    "aud.countShown": "显示 {shown} / {total} 个不合格文件",
    "aud.emptyFilter": "没有符合当前筛选条件的不合格文件",
    "aud.toastDone": "曲库质量审计完成",
    "ded.step1Title": "1 · 曲库查重扫描",
    "ded.step1Sub": "按歌名、艺人别名与时长（±3s）聚类疑似重复文件，绝不自动删除，全权由你确认处理",
    "ded.notScanned": "未扫描",
    "ded.scanning": "扫描中…",
    "ded.scanFail": "扫描失败",
    "ded.dirLabel": "查重目录",
    "ded.btnScan": "开始扫描查重",
    "ded.filterPh": "过滤歌名、艺人或文件名…",
    "ded.step2Title": "2 · 疑似重复分组",
    "ded.step2Sub": "请勾选确认要清理的冗余副本；操作会移入 staging/dedupe_trash 回收站",
    "ded.keepBest": "保留最优（勾选其余）",
    "ded.clearSel": "清空勾选",
    "ded.moveTrash": "移入回收站",
    "ded.empty": "点击上方「开始扫描查重」列出曲库中可能重复的曲目分组",
    "ded.noGroups": "未发现疑似重复的曲目分组（或尚未扫描）",
    "ded.noMatch": "没有匹配过滤关键词的重复分组",
    "ded.unknownTitle": "未知标题",
    "ded.unknownArtist": "未知艺人",
    "ded.fileCount": "{n} 个文件",
    "ded.summary": "{groups} 组 · {files} 个文件",
    "ded.toastFound": "发现 {n} 组疑似重复",
    "ded.toastNone": "未发现重复曲目",
    "ded.toastAutoSel": "已按「FLAC / 高码率 / 大文件优先」勾选 {n} 个副本，请核对后操作",
    "ded.toastNeedSel": "请先勾选要清理的副本文件",
    "ded.confirmDel": "确认将选中的 {n} 个重复文件移入回收站（staging/dedupe_trash）？",
    "ded.toastMoved": "已移入回收站 {n} 个文件",
    "lib.title": "曲库浏览",
    "lib.sub": "按文件名与格式检索曲库音频文件",
    "lib.notLoaded": "未载入",
    "lib.summary": "共 {total} 个文件",
    "lib.searchPh": "搜索文件名…",
    "lib.extAll": "全部格式",
    "lib.extAria": "按格式筛选",
    "lib.pageSizeAria": "每页数量",
    "lib.btnLoad": "载入曲库",
    "lib.colName": "文件名",
    "lib.colExt": "格式",
    "lib.colSize": "大小 (MB)",
    "lib.colMtime": "修改时间",
    "lib.empty": "没有匹配的文件",
    "lib.prevPage": "上一页",
    "lib.nextPage": "下一页",
    "lib.pageInfo": "第 {page} / {pages} 页",
    "lib.tableCap": "曲库音频文件索引",
    "lib.tableAria": "曲库文件列表",
    "lyr.title": "歌词体检",
    "lyr.sub": "八类歌词问题分组体检，可勾选清理",
    "lyr.notLoaded": "未体检",
    "lyr.scanning": "体检中…",
    "lyr.summary": "共 {n} 个问题文件",
    "lyr.btnReload": "重新体检",
    "lyr.btnDelete": "删除所选",
    "lyr.hint": "体检只读不改动任何文件；「删除所选」仅把歌词移入回收目录 staging/lrc_trash/<时间戳>/，随时可手动移回，绝不直接销毁。",
    "lyr.empty": "点击「重新体检」扫描曲库歌词问题",
    "lyr.noIssues": "未发现歌词问题，曲库很干净",
    "lyr.noFiles": "该组当前没有文件",
    "lyr.kind_orphan": "孤儿歌词（无对应音频）",
    "lyr.kind_meta_title": "标题与元数据不符",
    "lyr.kind_meta_artist": "艺人与元数据不符",
    "lyr.kind_too_long": "歌词时长过长",
    "lyr.kind_too_short": "歌词时长过短",
    "lyr.kind_dup_content": "内容重复",
    "lyr.kind_empty": "空歌词文件",
    "lyr.kind_no_timestamps": "缺少时间戳",
    "lyr.toastNeedSel": "请先勾选要删除的歌词文件",
    "lyr.confirmDel": "确认删除所选的 {n} 个歌词文件？文件不会销毁，而是移入可恢复的回收目录 staging/lrc_trash/<时间戳>/，需要时可手动移回。",
    "lyr.toastMoved": "已移入回收目录 {n} 个，失败 {f} 个",
    "lyr.resultMoved": "已移入回收目录",
    "lyr.resultFailed": "删除失败",
    "ren.title": "改名工具",
    "ren.sub": "按扫描建议批量规范曲库文件名",
    "ren.notScanned": "未扫描",
    "ren.scanning": "扫描中…",
    "ren.summary": "{n} 个待改名建议",
    "ren.btnScan": "扫描改名建议",
    "ren.btnApply": "应用所选",
    "ren.hint": "应用时服务端会自动同步同名 .jpg / .lrc 侧车文件一起改名；目标已存在时跳过并报告，绝不覆盖。",
    "ren.empty": "点击「扫描改名建议」检查曲库文件命名",
    "ren.nothingFound": "未发现可改名文件",
    "ren.kind_junk": "垃圾标记",
    "ren.kind_no_separator": "缺少分隔符",
    "ren.kind_inverted": "顺序颠倒",
    "ren.kind_artist_junk": "艺人垃圾标记",
    "ren.toastNeedSel": "请先勾选要应用的改名项",
    "ren.confirmApply": "确认对选中的 {n} 个文件执行改名？同名 .jpg / .lrc 侧车文件会一并同步改名。",
    "ren.toastApplied": "改名完成：成功 {r} · 跳过 {s} · 失败 {f}",
    "ren.resultTitle": "应用结果",
    "ren.stRenamed": "已改名",
    "ren.stSkip": "已跳过",
    "ren.stFailed": "失败",
    "fp.title": "指纹对比",
    "fp.sub": "对比两个音频文件的 PCM 指纹（MD5）判断是否同一音源",
    "fp.labelA": "文件 A",
    "fp.labelB": "文件 B",
    "fp.pathPhA": "第一个音频文件的绝对路径…",
    "fp.pathPhB": "第二个音频文件的绝对路径…",
    "fp.btnCompare": "对比",
    "fp.toastNeedPaths": "请填写两个待对比文件的绝对路径",
    "fp.resultA": "A 指纹",
    "fp.resultB": "B 指纹",
    "fp.matchYes": "指纹一致（同一音源）",
    "fp.matchNo": "指纹不一致（不同音源）",
    "theme.title": "外观与主题引擎",
    "theme.lang": "界面语言",
    "theme.mode": "主题模式",
    "theme.auto": "跟随系统",
    "theme.light": "浅色",
    "theme.dark": "深色",
    "theme.seed": "种子主题色",
    "theme.seedAuto": "自动配对（浅蓝 / 深琥珀）",
    "theme.pureBlack": "纯黑深色 (OLED)",
    "theme.glass": "Liquid Glass 浮层",
    "dir.title": "选择下载保存目录",
    "dir.up": "上一级",
    "dir.go": "跳转",
    "dir.choose": "选择此目录",
    "dir.emptySub": "该目录下暂无子文件夹，可直接点击「选择此目录」",
    "dir.toastDefaultSaved": "默认曲库已切换并保存：{dir}",
    "dir.toastPicked": "已选定目录：{dir}",
    "dir.toastReset": "已恢复为默认曲库目录",
    "common.scanDirPh": "留空则扫描默认曲库",
    "common.scanDirPhWith": "留空则扫描默认曲库（{dir}）",
    "type.prepare": "歌单查重",
    "type.download": "下载",
    "type.upgrade": "无损升级",
    "type.audit": "质量审计",
    "type.custom": "自定义",
    "st.downloaded": "下载成功",
    "st.already_exists": "已存在跳过",
    "st.skipped": "手动跳过",
    "st.low_confidence": "未匹配(低置信度，未下载)",
    "st.no_result": "未搜到结果",
    "st.no_source": "无可用音源",
    "st.search_failed": "搜索失败",
    "st.failed": "下载失败",
  },
  en: {
    "nav.import": "Import",
    "nav.upgrade": "Upgrade",
    "nav.audit": "Quality Audit",
    "nav.dedupe": "Deduplicate",
    "nav.jobs": "Jobs",
    "nav.library": "Library",
    "nav.lyrics": "Lyrics Check",
    "nav.rename": "Rename Tool",
    "nav.fingerprint": "Fingerprint",
    "dock.import": "Import",
    "dock.upgrade": "Upgrade",
    "dock.audit": "Audit",
    "dock.dedupe": "Dedupe",
    "dock.jobs": "Jobs",
    "dock.library": "Library",
    "dock.lyrics": "Lyrics",
    "dock.rename": "Rename",
    "dock.fingerprint": "Print",
    "sb.collapse": "Collapse sidebar",
    "sb.switchLib": "Switch",
    "sb.appearance": "Appearance",
    "sb.tracksCount": "<strong>{n}</strong> tracks",
    "topbar.toggleTheme": "Toggle light/dark theme",
    "topbar.sub": "Library {total} tracks · FLAC {flac} ({pct}%)",
    "common.idle": "Idle",
    "common.details": "Details",
    "common.pickFolder": "Browse",
    "common.resetDefault": "Reset",
    "common.selAll": "Select All",
    "common.selNone": "Deselect All",
    "common.clear": "Clear",
    "common.close": "Close",
    "common.cancel": "Cancel",
    "hero.title": "Engine Status",
    "hero.ready": "Ready",
    "hero.paused": "Paused",
    "hero.runningSuffix": "{type}",
    "hero.runningFallback": "Running {type}…",
    "hero.processing": "Processing",
    "hero.headlineIdle": "Ready to import playlist or track list",
    "hero.headlineLoaded": "Playlist loaded ({n} tracks), ready to download",
    "hero.switchDefaultLib": "Switch Library",
    "hero.jobProgress": "Job Progress",
    "hero.historyJobs": "{n} history jobs",
    "hero.rateAndLock": "Queue & Lock",
    "hero.singleQueue": "Serial Queue",
    "hero.quickAction": "Quick Action",
    "hero.quickActionTitle": "Focus import / Pause or resume download",
    "hero.dirPrefix": "Library: {dir}",
    "hero.resumedToast": "Download resumed",
    "hero.pausingToast": "Will pause after current track finishes",
    "stat.losslessRate": "Lossless Ratio",
    "stat.libSub": "MP3 {mp3} · OGG {ogg} · {total} total",
    "stat.recentAudit": "Latest Audit",
    "stat.passRate": "Pass Rate",
    "stat.noAuditYet": "No audit record loaded yet",
    "stat.auditSub": "Passed {pass} / Failed {fail} ({total} FLACs)",
    "imp.step1Title": "1 · Import Playlist & Dedupe",
    "imp.step1Sub": "Fetch metadata and match against local library (3-tier)",
    "imp.tabUri": "Playlist URL / URI",
    "imp.tabList": "Text List (--list)",
    "imp.uriPh": "Paste playlist URL or URI: Bilibili / y.qq.com / NetEase / spotify: URI",
    "imp.btnUri": "Fetch & Check",
    "imp.uriHint": "Supports bilibili.com favorites, y.qq.com playlists, public NetEase playlists, and spotify: URIs. For private playlists, use Text List.",
    "imp.listPh": "One track per line: Title - Artist (or Title only; optional | duration_sec)\nExample: Kaisei - Orangestar\nExample: Matasaburo-Yorushika",
    "imp.btnList": "Check Text List",
    "imp.listHint": "Title-only lines automatically expand online artist/version candidates; 'Title - Artist' checks local library directly.",
    "imp.saveTo": "Save downloads to",
    "imp.dlDirPh": "Leave blank to save to default library",
    "imp.dlDirPhWith": "Leave blank to use default library ({dir})",
    "imp.saveToHint": "Enter/paste a path or click Browse; leave empty to use the default library folder.",
    "imp.step2Title": "2 · Select Tracks to Download",
    "imp.filterPh": "Filter by title or artist…",
    "imp.selNew": "New Only",
    "imp.source": "Source",
    "imp.srcAuto": "auto (Lossless First)",
    "imp.dlCover": "Cover Art",
    "imp.dlLyrics": "Lyrics",
    "imp.incEx": "Re-download Existing",
    "imp.btnDl": "Download",
    "imp.tableCap": "Imported playlist tracks and local dedupe status",
    "imp.colTitle": "Title",
    "imp.colArtist": "Artist",
    "imp.colDur": "Duration",
    "imp.colStatus": "Status",
    "imp.colSelect": "Select",
    "imp.statusExisting": "Exists",
    "imp.statusNew": "New",
    "imp.emptyTracks": "No matching tracks",
    "imp.trackSummary": "{total} total · {newCount} new · {exists} existing",
    "imp.toastExpanded": "Expanded {n} candidate versions; please select the ones you want",
    "imp.toastUriEmpty": "Please enter a playlist URL or URI first",
    "imp.toastUriDone": "Playlist metadata fetched & checked",
    "imp.toastListEmpty": "Text list cannot be empty",
    "imp.toastListDone": "Text list check complete",
    "imp.toastNeedImport": "Please import a playlist first",
    "imp.toastNeedTrack": "Select at least one track to download",
    "imp.unknownTrack": "Unknown Track",
    "imp.existingTag": " (Exists: {file})",
    "imp.moreExisting": "\n…and {n} more",
    "imp.confirmExisting": "Similar tracks already exist in your library. Continue downloading?\n\n{samples}{more}",
    "jobs.title": "Jobs",
    "jobs.sub": "Only one job runs at a time, sharing rate limit and library lock",
    "jobs.empty": "No jobs yet — go to Import to fetch & download a playlist",
    "jobs.logTitle": "Job Log",
    "jobs.logTitleWith": "Job Log · {type}",
    "jobs.copyLog": "Copy Log",
    "jobs.pause": "⏸ Pause",
    "jobs.resume": "▶ Resume",
    "jobs.skipTrack": "⏭ Skip Track",
    "jobs.runningCount": "Running {n} · {type}",
    "jobs.stRunning": "Running",
    "jobs.stQueued": "Queued",
    "jobs.stDone": "Done",
    "jobs.stError": "Failed",
    "jobs.pausingNote": "Paused (will stop after current track finishes)",
    "jobs.processing": "Processing: {name}",
    "jobs.targetDir": "Target: {dir}",
    "jobs.failToast": "Job failed — check the log for details",
    "jobs.copyOk": "Log copied to clipboard",
    "jobs.copyErr": "Copy failed",
    "jobs.skipToast": "Requested to skip current track",
    "jobs.cancel": "⏹ Cancel",
    "jobs.cancelConfirm": "Cancel this job? No new items will be started and the current one is terminated; remaining items are recorded as cancelled.",
    "jobs.cancelToast": "Cancellation requested",
    "jobs.cancelledBadge": "Cancelled",
    "jobs.cancelledRemaining": "{n} left",
    "up.step1Title": "1 · Upgrade Queue",
    "up.queueCount": "{checked} / {total} files",
    "up.clearList": "Clear Queue",
    "up.scanDir": "Scan Folder",
    "up.onlyMp3": "MP3 Only",
    "up.onlyOgg": "OGG Only",
    "up.filterPh": "Filter filenames…",
    "up.btnScan": "Scan & Load",
    "up.empty": "Upgrade queue is empty — select a folder above and click Scan & Load, or send failed files from Quality Audit",
    "up.emptyFilter": "No queued files match the filter",
    "up.step2Title": "2 · Run Upgrade",
    "up.step2Sub": "Re-fetch true FLAC for MP3/OGG or fake lossless; true FLACs get covers & tags repaired in-place",
    "up.retryTitle": "Clear skip list & retry all",
    "up.retrySub": "Tracks failing ≥ 2 consecutive times are skipped by default; enable to reset and retry",
    "up.btnStart": "Start Upgrade",
    "up.hint": "Old files are backed up and PCM-fingerprinted before replacement.",
    "up.tagAudit": "From Audit",
    "up.toastNoFiles": "No files to send to upgrade",
    "up.toastSent": "Sent {n} file(s) to upgrade queue",
    "up.toastCleared": "Upgrade queue cleared",
    "up.toastLoaded": "Loaded {n} file(s) for upgrade",
    "up.toastNeedFiles": "Scan a folder or send files from Quality Audit first",
    "aud.title": "4-Gate Quality Audit",
    "aud.sub": "ffprobe check: Duration / Tags / Cover Art / Fake FLAC",
    "aud.pickFiles": "Pick Files",
    "aud.btnStart": "Start Audit",
    "aud.dirLabel": "Audit Folder",
    "aud.pickSummary": "{sel} / {total} selected",
    "aud.pickFilterPh": "Filter filenames…",
    "aud.pickEmpty": "No matching .flac files in this folder",
    "aud.emptyHint": "Scans all .flac files in the folder unless specific files are picked; previous audit results load automatically below.",
    "aud.detailTitle": "Failed Files",
    "aud.recent": "Latest",
    "aud.sendSel": "Send Selected to Upgrade",
    "aud.sendAll": "Send All Failed to Upgrade",
    "aud.searchPh": "Search filename…",
    "aud.tableCap": "FLAC files that failed one or more quality gates",
    "aud.colFile": "Filename",
    "aud.colIssues": "Issues",
    "aud.tileTotal": "Scanned FLAC",
    "aud.tilePass": "All Passed",
    "aud.tileFail": "Issues Found",
    "aud.tileRate": "Pass Rate",
    "aud.allFilter": "All",
    "aud.countShown": "Showing {shown} / {total} failed files",
    "aud.emptyFilter": "No failed files match the current filter",
    "aud.toastDone": "Quality audit completed",
    "ded.step1Title": "1 · Duplicate Scan",
    "ded.step1Sub": "Cluster suspected duplicates by title, artist aliases & duration (±3s). Never auto-deletes.",
    "ded.notScanned": "Not Scanned",
    "ded.scanning": "Scanning…",
    "ded.scanFail": "Scan Failed",
    "ded.dirLabel": "Scan Folder",
    "ded.btnScan": "Start Scan",
    "ded.filterPh": "Filter by title, artist or filename…",
    "ded.step2Title": "2 · Duplicate Groups",
    "ded.step2Sub": "Select redundant copies to clean up; files are moved safely to staging/dedupe_trash",
    "ded.keepBest": "Keep Best (Select Others)",
    "ded.clearSel": "Clear Selection",
    "ded.moveTrash": "Move to Trash",
    "ded.empty": "Click Start Scan above to list potential duplicate groups in your library",
    "ded.noGroups": "No duplicate groups found (or not scanned yet)",
    "ded.noMatch": "No duplicate groups match the filter",
    "ded.unknownTitle": "Unknown Title",
    "ded.unknownArtist": "Unknown Artist",
    "ded.fileCount": "{n} files",
    "ded.summary": "{groups} groups · {files} files",
    "ded.toastFound": "Found {n} suspected duplicate group(s)",
    "ded.toastNone": "No duplicates found",
    "ded.toastAutoSel": "Selected {n} redundant copy/copies (keeping FLAC / higher bitrate / larger file)",
    "ded.toastNeedSel": "Select at least one duplicate file first",
    "ded.confirmDel": "Move {n} selected duplicate file(s) to trash (staging/dedupe_trash)?",
    "ded.toastMoved": "Moved {n} file(s) to trash",
    "lib.title": "Library Browser",
    "lib.sub": "Search library audio files by name and format",
    "lib.notLoaded": "Not loaded",
    "lib.summary": "{total} files",
    "lib.searchPh": "Search filename…",
    "lib.extAll": "All formats",
    "lib.extAria": "Filter by format",
    "lib.pageSizeAria": "Files per page",
    "lib.btnLoad": "Load Library",
    "lib.colName": "Filename",
    "lib.colExt": "Format",
    "lib.colSize": "Size (MB)",
    "lib.colMtime": "Modified",
    "lib.empty": "No matching files",
    "lib.prevPage": "Prev",
    "lib.nextPage": "Next",
    "lib.pageInfo": "Page {page} / {pages}",
    "lib.tableCap": "Library audio file index",
    "lib.tableAria": "Library file list",
    "lyr.title": "Lyrics Check",
    "lyr.sub": "Eight groups of lyric issues, selectable for cleanup",
    "lyr.notLoaded": "Not checked",
    "lyr.scanning": "Checking…",
    "lyr.summary": "{n} file(s) with issues",
    "lyr.btnReload": "Re-check",
    "lyr.btnDelete": "Delete Selected",
    "lyr.hint": "The check is read-only; Delete Selected only moves lyrics to the recoverable trash staging/lrc_trash/<timestamp>/, restore manually anytime — never destroyed.",
    "lyr.empty": "Click Re-check to scan lyric issues in the library",
    "lyr.noIssues": "No lyric issues found — library is clean",
    "lyr.noFiles": "No files in this group right now",
    "lyr.kind_orphan": "Orphan lyrics (no audio)",
    "lyr.kind_meta_title": "Title mismatch",
    "lyr.kind_meta_artist": "Artist mismatch",
    "lyr.kind_too_long": "Lyrics too long",
    "lyr.kind_too_short": "Lyrics too short",
    "lyr.kind_dup_content": "Duplicate content",
    "lyr.kind_empty": "Empty lyric file",
    "lyr.kind_no_timestamps": "Missing timestamps",
    "lyr.toastNeedSel": "Select lyric files to delete first",
    "lyr.confirmDel": "Delete {n} selected lyric file(s)? They are not destroyed — moved to the recoverable trash staging/lrc_trash/<timestamp>/ and can be restored manually.",
    "lyr.toastMoved": "Moved {n} to trash, {f} failed",
    "lyr.resultMoved": "Moved to trash",
    "lyr.resultFailed": "Failed to delete",
    "ren.title": "Rename Tool",
    "ren.sub": "Batch-normalize library filenames by suggestion",
    "ren.notScanned": "Not scanned",
    "ren.scanning": "Scanning…",
    "ren.summary": "{n} suggestion(s)",
    "ren.btnScan": "Scan Suggestions",
    "ren.btnApply": "Apply Selected",
    "ren.hint": "On apply, the server renames matching .jpg / .lrc sidecar files together; targets that already exist are skipped and reported — never overwritten.",
    "ren.empty": "Click Scan Suggestions to check library filenames",
    "ren.nothingFound": "No files need renaming",
    "ren.kind_junk": "Junk Tag",
    "ren.kind_no_separator": "No Separator",
    "ren.kind_inverted": "Inverted",
    "ren.kind_artist_junk": "Artist Junk",
    "ren.toastNeedSel": "Select items to apply first",
    "ren.confirmApply": "Rename {n} selected file(s)? Matching .jpg / .lrc sidecar files will be renamed together.",
    "ren.toastApplied": "Rename done: {r} renamed · {s} skipped · {f} failed",
    "ren.resultTitle": "Apply Result",
    "ren.stRenamed": "Renamed",
    "ren.stSkip": "Skipped",
    "ren.stFailed": "Failed",
    "fp.title": "Fingerprint Compare",
    "fp.sub": "Compare PCM fingerprints (MD5) of two audio files to tell if they share the same source",
    "fp.labelA": "File A",
    "fp.labelB": "File B",
    "fp.pathPhA": "Absolute path of the first audio file…",
    "fp.pathPhB": "Absolute path of the second audio file…",
    "fp.btnCompare": "Compare",
    "fp.toastNeedPaths": "Enter both absolute paths first",
    "fp.resultA": "A MD5",
    "fp.resultB": "B MD5",
    "fp.matchYes": "Fingerprints match (same source)",
    "fp.matchNo": "Fingerprints differ (different sources)",
    "theme.title": "Appearance & Theme",
    "theme.lang": "Language",
    "theme.mode": "Theme Mode",
    "theme.auto": "System",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.seed": "Accent Color",
    "theme.seedAuto": "Auto Pair (Azure / Amber)",
    "theme.pureBlack": "Pure Black (OLED)",
    "theme.glass": "Liquid Glass Overlay",
    "dir.title": "Select Folder",
    "dir.up": "Up",
    "dir.go": "Go",
    "dir.choose": "Select This Folder",
    "dir.emptySub": "No subfolders here; click Select This Folder to confirm",
    "dir.toastDefaultSaved": "Default library updated: {dir}",
    "dir.toastPicked": "Selected folder: {dir}",
    "dir.toastReset": "Reset to default library folder",
    "common.scanDirPh": "Leave blank to scan default library",
    "common.scanDirPhWith": "Leave blank to scan default library ({dir})",
    "type.prepare": "Playlist Check",
    "type.download": "Download",
    "type.upgrade": "Upgrade",
    "type.audit": "Quality Audit",
    "type.custom": "Custom",
    "st.downloaded": "Downloaded",
    "st.already_exists": "Already Exists",
    "st.skipped": "Skipped",
    "st.low_confidence": "Low Confidence (Skipped)",
    "st.no_result": "No Result",
    "st.no_source": "No Source",
    "st.search_failed": "Search Failed",
    "st.failed": "Failed",
  },
};

function getLang() {
  try {
    const qp = new URLSearchParams(location.search).get("lang");
    if (qp === "en" || qp === "zh") return qp;
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "en" || saved === "zh") return saved;
  } catch (_) {}
  return "zh";
}

let currentLang = getLang();
let currentView = "import";

function t(key, vars) {
  const dict = I18N[currentLang] || I18N.zh;
  let str = dict[key] ?? I18N.zh[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      str = str.replaceAll(`{${k}}`, String(v));
    }
  }
  return str;
}

function trType(type) {
  return t(`type.${type}`) !== `type.${type}` ? t(`type.${type}`) : (type || "");
}

function trIssue(issue) {
  if (currentLang !== "en") return issue;
  if (issue === "缺封面") return "Missing Cover";
  if (issue === "缺标签") return "Missing Tags";
  if (issue === "无法读取时长") return "Unreadable Duration";
  if (issue.startsWith("时长差")) return "Duration Diff " + issue.slice(3);
  if (issue.startsWith("编解码异常")) return "Codec Anomaly" + issue.slice(5);
  return issue;
}

function trDedupeReason(reason) {
  if (currentLang !== "en" || !reason) return reason || "";
  return reason
    .replaceAll("同长(≤4s)", "Similar Duration (≤4s)")
    .replaceAll("同艺人", "Same Artist")
    .replaceAll("同歌名", "Same Title");
}

function applyLang(lang, persist = true) {
  currentLang = lang === "en" ? "en" : "zh";
  if (persist) {
    try { localStorage.setItem(LANG_KEY, currentLang); } catch (_) {}
  }
  document.documentElement.lang = currentLang === "en" ? "en" : "zh-CN";
  document.documentElement.dataset.lang = currentLang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  document.querySelectorAll("[data-lang]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.lang === currentLang));
  });
  if ($("#btn-lang")) {
    $("#btn-lang").textContent = currentLang === "en" ? "中文" : "EN";
  }
  const autoSw = $('#seed-swatches [data-seed="auto"]');
  if (autoSw) {
    autoSw.title = t("theme.seedAuto");
    autoSw.setAttribute("aria-label", t("theme.seedAuto"));
  }
  $("#topbar-title").textContent = t(`nav.${currentView}`) || "flac-hunter";
  if (typeof refreshState === "function" && window._stateReady) {
    refreshState();
    if (loadedRecords.length) renderTracksTable();
    if (auditData) renderAudit();
    if (upgradeQueueItems.length) renderUpgradeQueue();
    if (dedupeGroups.length) renderDedupeGroups();
    if ($("#aud-pick-box") && !$("#aud-pick-box").hidden) renderAuditPickList();
  }
}

const SEEDS = [
  { id: "auto", label: "自动配对（浅蓝 / 深琥珀）", color: "linear-gradient(135deg,#0A7AFF 50%,#F59E3D 50%)" },
  { id: "azure", label: "Classic Blue", h: 212, s: 100, lL: 52, lD: 63, color: "#0A7AFF" },
  { id: "amber", label: "Warm Amber", h: 32, s: 90, lL: 48, lD: 62, color: "#F59E3D" },
  { id: "emerald", label: "Emerald", h: 160, s: 84, lL: 39, lD: 55, color: "#10B981" },
  { id: "violet", label: "Violet", h: 262, s: 83, lL: 58, lD: 69, color: "#7C3AED" },
  { id: "rose", label: "Rose", h: 350, s: 89, lL: 56, lD: 65, color: "#F43F5E" },
];

let tracksPath = null;
let loadedRecords = [];
let activeJobId = null;
let logOffset = 0;
const onDoneMap = {};
let auditData = null;
let auditFilter = "全部";
let lastJobs = [];
let latestPollTimer = null;

/* ---------- Toast ---------- */
function showToast(msg, kind = "ok") {
  const stack = $("#fc-toast-stack");
  if (!stack) return;
  const el = document.createElement("div");
  el.className = "fc-toast" + (kind === "err" ? " fc-toast--err" : "");
  el.setAttribute("role", "status");
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 180ms";
    setTimeout(() => el.remove(), 200);
  }, 2600);
}

/* ---------- Theme & Seed Engine (dark-mode / dark-mode-toggle) ---------- */
const mediaDark = window.matchMedia("(prefers-color-scheme: dark)");
const PREFS_KEY = "fh-ui-prefs";
const SCHEME_KEY = "fh-color-scheme";
let uiPrefs = { seed: "auto", pureBlack: false, glass: true };
try {
  const raw = localStorage.getItem(PREFS_KEY);
  if (raw) Object.assign(uiPrefs, JSON.parse(raw));
} catch (_) {}

function getScheme() {
  try {
    const v = localStorage.getItem(SCHEME_KEY);
    if (v === "light" || v === "dark") return v;
  } catch (_) {}
  return "light dark";
}

function applyTheme() {
  const scheme = getScheme();
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) meta.content = scheme;
  const resolved = scheme === "light dark" ? (mediaDark.matches ? "dark" : "light") : scheme;
  const root = document.documentElement;
  root.dataset.resolvedTheme = resolved;
  root.dataset.pureBlack = String(Boolean(uiPrefs.pureBlack));
  root.dataset.liquidGlass = String(Boolean(uiPrefs.glass));

  let seed;
  if (uiPrefs.seed === "auto") {
    seed = resolved === "dark" ? SEEDS[2] : SEEDS[1];
  } else {
    seed = SEEDS.find((x) => x.id === uiPrefs.seed) || SEEDS[1];
  }
  root.style.setProperty("--fc-seed-h", String(seed.h));
  root.style.setProperty("--fc-seed-s", seed.s + "%");
  root.style.setProperty("--fc-seed-l-light", seed.lL + "%");
  root.style.setProperty("--fc-seed-l-dark", seed.lD + "%");

  document.querySelectorAll("[data-scheme]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.scheme === scheme));
  });
  document.querySelectorAll("#seed-swatches .fc-swatch").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.seed === uiPrefs.seed));
  });
  $("#pref-pure-black").checked = Boolean(uiPrefs.pureBlack);
  $("#pref-glass").checked = Boolean(uiPrefs.glass);
}

function setScheme(mode) {
  try {
    if (mode === "light dark") localStorage.removeItem(SCHEME_KEY);
    else localStorage.setItem(SCHEME_KEY, mode);
  } catch (_) {}
  applyTheme();
}

$("#btn-quick-theme").onclick = () => {
  const cur = getScheme();
  const resolved = cur === "light dark" ? (mediaDark.matches ? "dark" : "light") : cur;
  const target = resolved === "dark" ? "light" : "dark";
  const sys = mediaDark.matches ? "dark" : "light";
  setScheme(target === sys ? "light dark" : target);
};

if ($("#btn-lang")) {
  $("#btn-lang").onclick = () => applyLang(currentLang === "en" ? "zh" : "en");
}
document.querySelectorAll("[data-lang]").forEach((b) => {
  b.onclick = () => applyLang(b.dataset.lang);
});

document.querySelectorAll("[data-scheme]").forEach((b) => {
  b.onclick = () => setScheme(b.dataset.scheme);
});

const swWrap = $("#seed-swatches");
SEEDS.forEach((s) => {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "fc-swatch";
  btn.dataset.seed = s.id;
  btn.title = s.label;
  btn.setAttribute("aria-label", s.label);
  btn.style.background = s.color;
  btn.onclick = () => {
    uiPrefs.seed = s.id;
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(uiPrefs)); } catch (_) {}
    applyTheme();
  };
  swWrap.appendChild(btn);
});
$("#pref-pure-black").onchange = (e) => {
  uiPrefs.pureBlack = e.target.checked;
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(uiPrefs)); } catch (_) {}
  applyTheme();
};
$("#pref-glass").onchange = (e) => {
  uiPrefs.glass = e.target.checked;
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(uiPrefs)); } catch (_) {}
  applyTheme();
};
mediaDark.addEventListener("change", applyTheme);
window.addEventListener("storage", (e) => {
  if (e.key === SCHEME_KEY || e.key === PREFS_KEY) applyTheme();
  if (e.key === LANG_KEY) applyLang(getLang(), false);
});

$("#btn-collapse").onclick = () => $("#fc-shell").classList.toggle("is-collapsed");

/* ---------- Navigation ---------- */
function showTab(name) {
  currentView = name;
  document.querySelectorAll("[data-tab]").forEach((b) => {
    if (b.dataset.tab === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  document.querySelectorAll("main section[data-view]").forEach((sec) => {
    sec.hidden = sec.dataset.view !== name;
  });
  $("#topbar-title").textContent = t(`nav.${name}`) || "flac-hunter";
}
document.querySelectorAll("[data-tab]").forEach((b) => {
  b.onclick = () => showTab(b.dataset.tab);
});
document.querySelectorAll("[data-jump]").forEach((b) => {
  b.onclick = () => showTab(b.dataset.jump);
});

/* ---------- Tablist Helper (tabs guide: aria-selected + arrow keys) ---------- */
function bindTablist(container, onSelect) {
  container.addEventListener("keydown", (e) => {
    const tabs = [...container.querySelectorAll('[role="tab"]')];
    const idx = tabs.indexOf(document.activeElement);
    if (idx < 0) return;
    let next = idx;
    if (e.key === "ArrowRight") next = (idx + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    tabs[next].focus();
    onSelect(tabs[next]);
  });
}

const impTabUri = $("#imp-tab-uri");
const impTabList = $("#imp-tab-list");
function selectImportTab(tabEl) {
  const isUri = tabEl === impTabUri;
  impTabUri.setAttribute("aria-selected", String(isUri));
  impTabList.setAttribute("aria-selected", String(!isUri));
  $("#imp-panel-uri").hidden = !isUri;
  $("#imp-panel-list").hidden = isUri;
}
impTabUri.onclick = () => selectImportTab(impTabUri);
impTabList.onclick = () => selectImportTab(impTabList);
bindTablist(impTabUri.parentElement, selectImportTab);

/* ---------- API Helper ---------- */
async function api(path, opts) {
  const r = await fetch(path, opts);
  const text = await r.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch (_) {}
  if (!r.ok) throw new Error(data.error || text || ("HTTP " + r.status));
  return data;
}

function fmtDur(ms) {
  if (!ms) return "—";
  const s = Math.round(ms / 1000);
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}

function buildWavyPath(pct, w = 220, mid = 6, amp = 3.2, freq = 0.28) {
  const endX = Math.max(0, Math.min(w, (w * pct) / 100));
  if (endX < 2) return `M 0 ${mid} L 0 ${mid}`;
  const pts = [];
  for (let x = 0; x <= endX; x += 3) {
    const y = mid + Math.sin(x * freq) * amp;
    pts.push((x === 0 ? "M " : "L ") + x.toFixed(1) + " " + y.toFixed(2));
  }
  return pts.join(" ");
}

/* ---------- Audit Dashboard ---------- */
function renderAudit() {
  if (!auditData) return;
  const A = auditData;
  const rate = A.total > 0 ? Math.round((A.pass * 100) / A.total) : 0;

  $("#stat-audit-rate").textContent = A.total > 0 ? rate + "%" : "—";
  $("#stat-audit-sub").textContent = t("stat.auditSub", { pass: A.pass, fail: A.fail, total: A.total });
  $("#wavy-audit-path").setAttribute("d", buildWavyPath(rate));

  $("#audit-tiles").innerHTML =
    `<div class="fc-card"><div class="fc-stat-num fc-tabular">${A.total}</div><div class="fc-stat-sub">${esc(t("aud.tileTotal"))}</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-success);">${A.pass}</div><div class="fc-stat-sub">${esc(t("aud.tilePass"))}</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-error);">${A.fail}</div><div class="fc-stat-sub">${esc(t("aud.tileFail"))}</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-primary);">${rate}%</div><div class="fc-stat-sub">${esc(t("aud.tileRate"))}</div></div>`;

  const chips = ["全部", ...Object.entries(A.by_issue || {}).sort((a, b) => b[1] - a[1]).map(([k]) => k)];
  const chipsEl = $("#audit-chips");
  chipsEl.innerHTML = chips.map((k) => {
    const n = k === "全部" ? A.fail : (A.by_issue[k] || 0);
    const label = k === "全部" ? t("aud.allFilter") : trIssue(k);
    return `<button type="button" class="fc-tab" role="tab" aria-selected="${k === auditFilter ? "true" : "false"}" data-k="${esc(k)}">${esc(label)} <span class="fc-tabular">${n}</span></button>`;
  }).join("");
  chipsEl.querySelectorAll('[role="tab"]').forEach((btn) => {
    btn.onclick = () => { auditFilter = btn.dataset.k; renderAudit(); };
  });

  const kw = ($("#audit-search").value || "").toLowerCase();
  const rows = (A.files || []).filter((f) =>
    (auditFilter === "全部" || (f.issues || []).includes(auditFilter)) &&
    (!kw || (f.name || "").toLowerCase().includes(kw)));
  $("#audit-count").textContent = t("aud.countShown", { shown: rows.length, total: A.fail });
  $("#audit-files tbody").innerHTML = rows.slice(0, 500).map((f) =>
    `<tr><td data-label="${esc(t("imp.colSelect"))}"><input type="checkbox" class="aud-sel" data-name="${esc(f.name)}" aria-label="${esc(t("imp.colSelect"))} ${esc(f.name)}"></td>` +
    `<td data-label="${esc(t("aud.colFile"))}" title="${esc(f.name)}">${esc(f.name)}</td>` +
    `<td data-label="${esc(t("aud.colIssues"))}">${(f.issues || []).map((i) => `<span class="fc-chip fc-chip--error" style="margin-inline-end:4px;">${esc(trIssue(i))}</span>`).join("")}</td></tr>`
  ).join("") || `<tr><td colspan="3" class="fc-empty">${esc(t("aud.emptyFilter"))}</td></tr>`;
  $("#aud-chk-head").checked = false;
  updateAuditSelCount();
}

function updateAuditSelCount() {
  const n = document.querySelectorAll("#audit-files .aud-sel:checked").length;
  if ($("#aud-sel-count")) $("#aud-sel-count").textContent = String(n);
}
$("#aud-chk-head").onchange = (e) => {
  document.querySelectorAll("#audit-files .aud-sel").forEach((cb) => { cb.checked = e.target.checked; });
  updateAuditSelCount();
};
$("#audit-files tbody").onchange = (e) => {
  if (e.target.classList.contains("aud-sel")) updateAuditSelCount();
};

bindTablist($("#audit-chips"), (btn) => {
  auditFilter = btn.dataset.k;
  renderAudit();
});
$("#audit-search").oninput = renderAudit;

function showAudit(A) {
  auditData = A;
  auditFilter = "全部";
  $("#audit-when").textContent = A.when || t("aud.recent");
  renderAudit();
  $("#audit-result").hidden = false;
  $("#audit-empty-hint").hidden = true;
}

/* ---------- Import & Track Selection ---------- */
$("#btn-uri").onclick = async () => {
  const uri = $("#uri").value.trim();
  if (!uri) return showToast(t("imp.toastUriEmpty"), "err");
  const dlDir = ($("#dl-dir")?.value || "").trim();
  const payload = dlDir ? { uri, music_dir: dlDir } : { uri };
  try {
    const j = await api("/api/prepare", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    watchJob(j.id, async () => {
      await loadTracks(j.tracks_path);
      showTab("import");
      showToast(t("imp.toastUriDone"));
    });
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

$("#btn-list").onclick = async () => {
  const list_text = $("#listtext").value.trim();
  if (!list_text) return showToast(t("imp.toastListEmpty"), "err");
  const dlDir = ($("#dl-dir")?.value || "").trim();
  const payload = dlDir ? { list_text, music_dir: dlDir } : { list_text };
  try {
    const j = await api("/api/prepare", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    watchJob(j.id, async () => {
      await loadTracks(j.tracks_path);
      showTab("import");
      showToast(t("imp.toastListDone"));
    });
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

function updateSelCount() {
  const all = [...document.querySelectorAll("#tracks .sel")];
  const checked = all.filter((c) => c.checked);
  $("#sel-count").textContent = String(checked.length);
  const head = $("#chk-head");
  if (head) {
    head.checked = all.length > 0 && checked.length === all.length;
    head.indeterminate = checked.length > 0 && checked.length < all.length;
  }
}

function renderTracksTable() {
  const kw = ($("#track-filter").value || "").trim().toLowerCase();
  const tb = document.querySelector("#tracks tbody");
  const prevState = new Map([...document.querySelectorAll("#tracks .sel")].map((c) => [c.dataset.key, c.checked]));
  tb.innerHTML = "";
  let exists = 0;
  let shown = 0;
  loadedRecords.forEach((r) => {
    if (r.existing) exists += 1;
    const art = (r.artists || []).join(" / ");
    if (kw && !`${r.name || ""} ${art}`.toLowerCase().includes(kw)) return;
    shown += 1;
    const rowKey = r.uri ? String(r.uri) : `pos:${r.position}`;
    const isChecked = prevState.has(rowKey) ? prevState.get(rowKey) : (!r.existing && !r.from_search);
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td data-label="${esc(t("imp.colSelect"))}"><input type="checkbox" class="sel" data-key="${esc(rowKey)}" data-uri="${esc(r.uri || "")}" data-existing="${r.existing ? "1" : "0"}" data-exfile="${esc(r.existing_file || "")}" data-title="${esc(r.name || "")}" ${isChecked ? "checked" : ""} aria-label="${esc(t("imp.colSelect"))} ${esc(r.name)}"></td>` +
      `<td data-label="#" class="is-num">${esc(r.position)}</td>` +
      `<td data-label="${esc(t("imp.colTitle"))}" title="${esc(r.name)}"><strong>${esc(r.name)}</strong></td>` +
      `<td data-label="${esc(t("imp.colArtist"))}" title="${esc(art)}">${esc(art || "—")}</td>` +
      `<td data-label="${esc(t("imp.colDur"))}" class="is-num">${fmtDur(r.duration_ms)}</td>` +
      `<td data-label="${esc(t("imp.colStatus"))}"><span class="fc-chip ${r.existing ? "fc-chip--ok" : "fc-chip--primary"}">${esc(r.existing ? t("imp.statusExisting") : t("imp.statusNew"))}</span></td>`;
    tb.appendChild(tr);
  });
  if (shown === 0) {
    tb.innerHTML = `<tr><td colspan="6" class="fc-empty">${esc(t("imp.emptyTracks"))}</td></tr>`;
  }
  $("#track-summary").textContent = t("imp.trackSummary", {
    total: loadedRecords.length,
    newCount: loadedRecords.length - exists,
    exists,
  });
  updateSelCount();
}

async function loadTracks(path) {
  tracksPath = path;
  const d = await api("/api/tracks?path=" + encodeURIComponent(path));
  loadedRecords = d.records || [];
  $("#tracks-card").hidden = false;
  $("#tracks tbody").innerHTML = "";
  renderTracksTable();
  if (loadedRecords.some((r) => r.from_search)) {
    showToast(t("imp.toastExpanded", { n: loadedRecords.length }), "ok");
  }
}

$("#track-filter").oninput = renderTracksTable;
document.querySelector("#tracks tbody").addEventListener("change", (e) => {
  if (e.target.classList.contains("sel")) updateSelCount();
});
$("#chk-head").onchange = (e) => {
  document.querySelectorAll("#tracks .sel").forEach((cb) => { cb.checked = e.target.checked; });
  updateSelCount();
};
$("#btn-selnew").onclick = () => {
  document.querySelectorAll("#tracks .sel").forEach((cb) => { cb.checked = cb.dataset.existing !== "1"; });
  updateSelCount();
};
$("#btn-selall").onclick = () => {
  document.querySelectorAll("#tracks .sel").forEach((cb) => { cb.checked = true; });
  updateSelCount();
};
$("#btn-selnone").onclick = () => {
  document.querySelectorAll("#tracks .sel").forEach((cb) => { cb.checked = false; });
  updateSelCount();
};

$("#btn-dl").onclick = async () => {
  if (!tracksPath) return showToast(t("imp.toastNeedImport"), "err");
  const allCbs = [...document.querySelectorAll("#tracks .sel")];
  const checkedCbs = allCbs.filter((c) => c.checked);
  if (checkedCbs.length === 0) return showToast(t("imp.toastNeedTrack"), "err");

  const existingCbs = checkedCbs.filter((c) => c.dataset.existing === "1");
  let includeExisting = $("#inc-ex").checked;
  if (!includeExisting && existingCbs.length > 0) {
    const samples = existingCbs.slice(0, 3).map((c) => {
      const title = c.dataset.title || c.dataset.key || t("imp.unknownTrack");
      const exf = c.dataset.exfile;
      return exf ? `${title}${t("imp.existingTag", { file: exf })}` : title;
    }).join("\n");
    const more = existingCbs.length > 3 ? t("imp.moreExisting", { n: existingCbs.length }) : "";
    if (!confirm(t("imp.confirmExisting", { samples, more }))) {
      return;
    }
    includeExisting = true;
  }
  const body = {
    tracks: tracksPath,
    source: $("#source").value,
    include_existing: includeExisting,
    download_cover: $("#dl-cover") ? $("#dl-cover").checked : true,
    download_lyrics: $("#dl-lyrics") ? $("#dl-lyrics").checked : false,
  };
  const dlDir = ($("#dl-dir")?.value || "").trim();
  if (dlDir) body.music_dir = dlDir;
  if (checkedCbs.length < loadedRecords.length) {
    body.only = checkedCbs.map((c) => c.dataset.key).filter(Boolean);
  }
  try {
    const j = await api("/api/download", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    watchJob(j.id);
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

let dirTargetInput = "#dl-dir";
let dirParent = "";
async function loadDirBrowser(targetPath) {
  try {
    const q = targetPath ? `?path=${encodeURIComponent(targetPath)}` : "";
    const d = await api(`/api/dirs${q}`);
    dirParent = d.parent || "";
    $("#dir-current").value = d.current || "";
    $("#dir-up").disabled = !dirParent;
    $("#dir-drives").innerHTML = (d.drives || [])
      .map((drv) => `<button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" data-drv="${esc(drv)}">${esc(drv)}</button>`)
      .join("");
    $("#dir-list").innerHTML = (d.dirs && d.dirs.length)
      ? d.dirs.map((item) => `<button type="button" class="fc-dir-item" data-path="${esc(item.path)}">📁 <span>${esc(item.name)}</span></button>`).join("")
      : `<div class="fc-hint" style="padding:12px;text-align:center;">${esc(t("dir.emptySub"))}</div>`;
  } catch (e) {
    showToast(e.message, "err");
  }
}
async function openDirPicker(targetSel, mode = "input") {
  dirTargetInput = targetSel;
  window._dirPickMode = mode;
  const dlg = $("#dir-dialog");
  if (dlg && typeof dlg.showModal === "function") dlg.showModal();
  const initial = mode === "defaultLib" ? (window._currentMusicDir || "") : (($(dirTargetInput)?.value || "").trim());
  await loadDirBrowser(initial);
}

$("#btn-pick-dir").onclick = () => openDirPicker("#dl-dir");
$("#btn-aud-pick-dir").onclick = () => openDirPicker("#aud-dir");
$("#btn-up-pick-dir").onclick = () => openDirPicker("#up-dir");
$("#btn-switch-lib").onclick = () => openDirPicker(null, "defaultLib");
$("#btn-hero-switch-lib").onclick = () => openDirPicker(null, "defaultLib");
$("#dir-drives").onclick = (e) => {
  const b = e.target.closest("[data-drv]");
  if (b) loadDirBrowser(b.dataset.drv);
};
$("#dir-list").onclick = (e) => {
  const b = e.target.closest(".fc-dir-item");
  if (b) loadDirBrowser(b.dataset.path);
};
$("#dir-up").onclick = () => { if (dirParent) loadDirBrowser(dirParent); };
$("#dir-go").onclick = () => loadDirBrowser($("#dir-current").value.trim());
$("#dir-current").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); $("#dir-go").click(); }
});
$("#dir-choose").onclick = async () => {
  const chosen = $("#dir-current").value.trim();
  if (!chosen) return $("#dir-dialog").close();
  if (window._dirPickMode === "defaultLib") {
    try {
      const res = await api("/api/config/music-dir", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ music_dir: chosen }),
      });
      $("#dir-dialog").close();
      await refreshState();
      showToast(t("dir.toastDefaultSaved", { dir: res.music_dir }), "ok");
    } catch (e) {
      showToast(e.message, "err");
    }
    return;
  }
  if (dirTargetInput && $(dirTargetInput)) {
    $(dirTargetInput).value = chosen;
    showToast(t("dir.toastPicked", { dir: chosen }), "ok");
  }
  $("#dir-dialog").close();
};
$("#dir-cancel").onclick = () => $("#dir-dialog").close();
$("#dir-close").onclick = () => $("#dir-dialog").close();
$("#btn-reset-dir").onclick = () => {
  $("#dl-dir").value = "";
  showToast(t("dir.toastReset"));
};

/* ---------- Jobs & Runner Polling ---------- */
$("#joblist").onclick = (e) => {
  const card = e.target.closest(".fc-jobcard");
  if (card) openJobLog(card.dataset.id);
};

function updateHero(d, running) {
  const card = $("#hero-card");
  const btn = $("#hero-action-btn");
  const icon = $("#hero-action-icon");
  const active = running[0];
  window._currentMusicDir = d.music_dir || "";
  $("#hero-dir").textContent = d.music_dir ? t("hero.dirPrefix", { dir: d.music_dir }) : "";
  if ($("#sb-lib-dir")) $("#sb-lib-dir").textContent = d.music_dir || "";
  if (d.music_dir && $("#dl-dir")) {
    $("#dl-dir").placeholder = t("imp.dlDirPhWith", { dir: d.music_dir });
  }
  if (d.music_dir && $("#aud-dir")) {
    $("#aud-dir").placeholder = t("common.scanDirPhWith", { dir: d.music_dir });
  }
  if (d.music_dir && $("#up-dir")) {
    $("#up-dir").placeholder = t("common.scanDirPhWith", { dir: d.music_dir });
  }

  if (active) {
    card.classList.add("is-running");
    $("#hero-chip").className = "fc-chip fc-chip--primary";
    const tName = trType(active.type);
    $("#hero-chip-text").textContent = active.paused ? t("hero.paused") : t("hero.runningSuffix", { type: tName });
    $("#hero-headline").textContent = active.current?.name || active.summary || t("hero.runningFallback", { type: tName });
    const pct = active.total > 0 ? Math.min(100, Math.round((active.progress.done * 100) / active.total)) : 0;
    $("#hero-progress").textContent = active.total > 0 ? `${active.progress.done} / ${active.total} (${pct}%)` : t("hero.processing");
    btn.setAttribute("aria-pressed", String(!active.paused));
    icon.innerHTML = active.paused
      ? `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>`
      : `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`;
  } else {
    card.classList.remove("is-running");
    $("#hero-chip").className = "fc-chip fc-chip--ok";
    $("#hero-chip-text").textContent = t("hero.ready");
    $("#hero-headline").textContent = tracksPath ? t("hero.headlineLoaded", { n: loadedRecords.length }) : t("hero.headlineIdle");
    $("#hero-progress").textContent = t("hero.historyJobs", { n: (d.jobs || []).length });
    btn.setAttribute("aria-pressed", "false");
    icon.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>`;
  }
}

$("#hero-action-btn").onclick = async () => {
  const running = lastJobs.find((j) => j.status === "running");
  if (running && running.type === "download") {
    try {
      await api(`/api/job/${running.id}/pause`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paused: !running.paused }),
      });
      showToast(running.paused ? t("hero.resumedToast") : t("hero.pausingToast"));
      refreshState();
    } catch (e) { showToast(e.message, "err"); }
  } else if (tracksPath) {
    $("#btn-dl").click();
  } else {
    showTab("import");
    $("#uri").focus();
  }
};

async function refreshState() {
  try {
    const d = await api("/api/state");
    window._stateReady = true;
    const L = d.library || { total: 0, flac: 0, mp3: 0, ogg: 0 };
    const flacPct = L.total > 0 ? Math.round((L.flac * 100) / L.total) : 0;
    const lossyPct = L.total > 0 ? Math.max(0, 100 - flacPct) : 0;

    $("#sb-lib-total").innerHTML = t("sb.tracksCount", { n: L.total });
    $("#sb-lib-sub").textContent = `FLAC ${L.flac} · MP3 ${L.mp3} · OGG ${L.ogg}`;
    $("#topbar-sub").textContent = t("topbar.sub", { total: L.total, flac: L.flac, pct: flacPct });
    $("#stat-flac-num").textContent = String(L.flac);
    $("#stat-flac-pct").textContent = flacPct + "%";
    $("#stat-lib-sub").textContent = t("stat.libSub", { mp3: L.mp3, ogg: L.ogg, total: L.total });
    $("#bar-flac").style.width = flacPct + "%";
    $("#bar-lossy").style.width = lossyPct + "%";

    lastJobs = d.jobs || [];
    const running = lastJobs.filter((j) => j.status === "running" || j.status === "queued");
    $("#nav-jobs-badge").textContent = running.length > 0 ? String(running.length) : "";
    $("#jobstat").textContent = running.length > 0
      ? t("jobs.runningCount", { n: running.length, type: trType(running[0].type) })
      : t("common.idle");
    $("#jobstat").className = "fc-chip fc-tabular" + (running.length > 0 ? " fc-chip--primary" : "");

    updateHero(d, running);
    renderJobs(lastJobs);
    if (activeJobId) pollJob();

    if (!auditData) {
      const lastAudit = lastJobs.find((j) => j.type === "audit" && j.status === "done");
      if (lastAudit) {
        const j = await api("/api/job/" + lastAudit.id);
        if (j.audit) showAudit({ ...j.audit, when: j.started_h });
      } else {
        const lastSaved = await api("/api/audit/last");
        if (lastSaved && lastSaved.audit) showAudit({ ...lastSaved.audit, when: lastSaved.when });
      }
    }
  } catch (_) {}
}

function renderJobs(jobs) {
  const box = $("#joblist");
  if (!jobs.length) {
    box.innerHTML = `<div class="fc-empty">${esc(t("jobs.empty"))}</div>`;
    return;
  }
  box.innerHTML = "";
  jobs.forEach((j) => {
    const chipCls = j.status === "running" ? "fc-chip--primary" : j.status === "done" ? "fc-chip--ok" :
                    j.status === "error" ? "fc-chip--error" : "";
    const st = j.status === "running" ? t("jobs.stRunning") : j.status === "queued" ? t("jobs.stQueued") :
               j.status === "done" ? t("jobs.stDone") : t("jobs.stError");
    const pct = j.total > 0 ? Math.min(100, Math.round((j.progress.done * 100) / j.total)) : 0;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fc-jobcard" + (j.id === activeJobId ? " is-selected" : "");
    btn.dataset.id = j.id;
    btn.innerHTML =
      `<div class="fc-jobcard__top">` +
      `<span class="fc-jobcard__name">${esc(trType(j.type))}</span>` +
      `<span class="fc-chip ${chipCls}">${esc(st)}</span>` +
      // snapshot.cancelled 防御式徽标：字段缺失时一律不显示（冻结契约 1）
      (j.cancelled ? `<span class="fc-chip fc-chip--warn">${esc(t("jobs.cancelledBadge"))}${Number(j.cancelled_remaining) > 0 ? ` · ${esc(t("jobs.cancelledRemaining", { n: j.cancelled_remaining }))}` : ""}</span>` : "") +
      `<span class="fc-jobcard__time fc-tabular">${esc(j.started_h)}</span>` +
      `<span class="fc-jobcard__sum">${esc(j.summary || "")}</span>` +
      `</div>` +
      (j.total > 0 ? `<div class="fc-segmented-bar"><div class="fc-segmented-bar__seg fc-segmented-bar__seg--primary" style="width:${pct}%"></div></div>` : "");
    box.appendChild(btn);
  });
}

function classifyLogLine(line) {
  if (/失败|错误|error|fail|异常|不存在/i.test(line)) return "is-err";
  if (/跳过|skip|警告|warn|暂停/i.test(line)) return "is-warn";
  if (/完成|通过|downloaded:\s*[1-9]|upgraded|PASS/i.test(line)) return "is-ok";
  if (/^\[runner\]\s*\(\d+\/\d+\)/.test(line) || /^\[audit\]/.test(line)) return "is-step";
  return "";
}

function openJobLog(id) {
  if (latestPollTimer) { clearTimeout(latestPollTimer); latestPollTimer = null; }
  activeJobId = id;
  logOffset = 0;
  $("#joblog").innerHTML = "";
  $("#job-stats-row").hidden = true;
  $("#cur-track").hidden = true;
  $("#joblog-card").hidden = false;
  pollJob();
}

async function pollJob() {
  if (!activeJobId) return;
  const curId = activeJobId;
  try {
    const j = await api("/api/job/" + curId);
    if (curId !== activeJobId) return;
    $("#joblog-title").textContent = t("jobs.logTitleWith", { type: trType(j.type) });
    if (j.progress && j.progress.total > 0) {
      const pct = Math.min(100, Math.round((j.progress.done * 100) / j.progress.total));
      $("#dlbar").style.width = pct + "%";
      $("#dlpct").textContent = `${j.progress.done} / ${j.progress.total} (${pct}%)`;
      $("#dlpct").hidden = false;
    } else {
      $("#dlbar").style.width = "0";
      $("#dlpct").hidden = true;
    }
    const sc = j.status_counts || {};
    const scEntries = Object.entries(sc);
    if (scEntries.length) {
      const scHtml = scEntries.map(([k, v]) => {
        const cls = /fail|err/i.test(k)
          ? "fc-chip--error"
          : (k === "downloaded" || k === "upgraded" || k === "ok" || k === "pass" ? "fc-chip--ok" : "fc-chip--warn");
        const lbl = t(`st.${k}`) !== `st.${k}` ? t(`st.${k}`) : k;
        return `<span class="fc-chip ${cls} fc-tabular">${esc(lbl)}: ${v}</span>`;
      }).join("");
      $("#job-stats-row").innerHTML = scHtml + (j.music_dir ? `<span class="fc-chip fc-mono">${esc(t("jobs.targetDir", { dir: j.music_dir }))}</span>` : "");
      $("#job-stats-row").hidden = false;
    } else if (j.music_dir) {
      $("#job-stats-row").innerHTML = `<span class="fc-chip fc-mono">${esc(t("jobs.targetDir", { dir: j.music_dir }))}</span>`;
      $("#job-stats-row").hidden = false;
    } else {
      $("#job-stats-row").hidden = true;
    }
    const tail = j.log_tail || [];
    if (tail.length > logOffset) {
      const frag = tail.slice(logOffset).map((ln) => {
        const cls = classifyLogLine(ln);
        return `<div class="fc-log-line ${cls}">${esc(ln)}</div>`;
      }).join("");
      $("#joblog").insertAdjacentHTML("beforeend", frag);
      logOffset = tail.length;
      $("#joblog").scrollTop = $("#joblog").scrollHeight;
    }
    const showCtl = j.type === "download" && j.status === "running" && j.current !== undefined;
    $("#btn-pause").hidden = !showCtl;
    $("#btn-skip").hidden = !showCtl;
    // 取消按钮：作业 queued/running 时可用（冻结契约 1）
    $("#btn-cancel").hidden = !(j.status === "running" || j.status === "queued");
    const ccChip = $("#job-cancelled-chip");
    if (j.cancelled) {
      ccChip.textContent = Number(j.cancelled_remaining) > 0
        ? `${t("jobs.cancelledBadge")} · ${t("jobs.cancelledRemaining", { n: j.cancelled_remaining })}`
        : t("jobs.cancelledBadge");
      ccChip.hidden = false;
    } else {
      ccChip.hidden = true;
      ccChip.textContent = "";
    }
    if (showCtl) {
      $("#btn-pause").textContent = j.paused ? t("jobs.resume") : t("jobs.pause");
      $("#btn-pause").dataset.paused = j.paused ? "1" : "";
      const txt = j.current && j.current.name
        ? (j.paused ? t("jobs.pausingNote") : t("jobs.processing", { name: j.current.name }))
        : "";
      $("#cur-track").textContent = txt;
      $("#cur-track").hidden = !txt;
    } else {
      $("#cur-track").textContent = j.summary || "";
      $("#cur-track").hidden = !(j.summary);
    }
    if (j.status !== "running" && j.status !== "queued") {
      const cb = onDoneMap[curId];
      if (cb) {
        delete onDoneMap[curId];
        if (j.status === "done") cb();
        else showToast(t("jobs.failToast"), "err");
      }
    } else {
      latestPollTimer = setTimeout(pollJob, 1500);
    }
  } catch (_) {
    if (curId === activeJobId) latestPollTimer = setTimeout(pollJob, 2500);
  }
}

function watchJob(id, onDone) {
  if (onDone) onDoneMap[id] = onDone;
  openJobLog(id);
}

$("#btn-copy-log").onclick = () => {
  const txt = $("#joblog").textContent || "";
  navigator.clipboard?.writeText(txt).then(
    () => showToast(t("jobs.copyOk")),
    () => showToast(t("jobs.copyErr"), "err")
  );
};

$("#btn-pause").onclick = async () => {
  if (!activeJobId) return;
  const paused = $("#btn-pause").dataset.paused === "1";
  try {
    await api(`/api/job/${activeJobId}/pause`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paused: !paused }),
    });
    pollJob();
  } catch (e) { showToast(e.message, "err"); }
};

$("#btn-skip").onclick = async () => {
  if (!activeJobId) return;
  try {
    await api(`/api/job/${activeJobId}/skip`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    showToast(t("jobs.skipToast"));
  } catch (e) { showToast(e.message, "err"); }
};

$("#btn-cancel").onclick = async () => {
  if (!activeJobId) return;
  if (!confirm(t("jobs.cancelConfirm"))) return;
  try {
    await api(`/api/job/${activeJobId}/cancel`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    showToast(t("jobs.cancelToast"));
    pollJob();
    refreshState();
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Upgrade & Audit ---------- */
let upgradeQueueItems = []; // [{ name, tag, fromAudit, checked }]
let auditCandidateFiles = [];
let auditSelectedFiles = new Set();

function renderUpgradeQueue() {
  const kw = ($("#up-queue-filter")?.value || "").toLowerCase();
  const checkedCount = upgradeQueueItems.filter((x) => x.checked).length;
  $("#up-queue-count").textContent = t("up.queueCount", { checked: checkedCount, total: upgradeQueueItems.length });
  $("#up-sel-count").textContent = String(checkedCount);

  const shown = upgradeQueueItems.filter((x) => !kw || x.name.toLowerCase().includes(kw));
  if (!upgradeQueueItems.length) {
    $("#up-queue-list").innerHTML = `<div class="fc-empty">${esc(t("up.empty"))}</div>`;
    return;
  }
  if (!shown.length) {
    $("#up-queue-list").innerHTML = `<div class="fc-hint" style="padding:12px;text-align:center;">${esc(t("up.emptyFilter"))}</div>`;
    return;
  }
  $("#up-queue-list").innerHTML = shown.map((item) => {
    const tagText = item.fromAudit ? t("up.tagAudit") : item.tag;
    return `<div class="fc-dir-item" style="justify-content:space-between;">` +
      `<label class="fc-row" style="gap:8px;flex:1;min-width:0;cursor:pointer;">` +
        `<input type="checkbox" class="up-q-cb" data-name="${esc(item.name)}" ${item.checked ? "checked" : ""}>` +
        `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(item.name)}">${esc(item.name)}</span>` +
      `</label>` +
      `<div class="fc-row" style="gap:6px;flex:none;">` +
        `<span class="fc-chip">${esc(tagText)}</span>` +
        `<button type="button" class="fc-btn fc-btn--sm fc-btn--tonal up-q-del" data-name="${esc(item.name)}" aria-label="Remove ${esc(item.name)}">×</button>` +
      `</div>` +
    `</div>`;
  }).join("");
}

function setUpgradeExtUI(extVal) {
  if ($("#up-ext")) $("#up-ext").value = extVal;
  document.querySelectorAll("#up-ext-seg .fc-segmented__btn").forEach((x) => {
    x.setAttribute("aria-pressed", String(x.dataset.ext === extVal));
  });
}

function sendAuditFilesToUpgrade(names) {
  if (!names.length) return showToast(t("up.toastNoFiles"), "err");
  const seen = new Set();
  upgradeQueueItems = [];
  for (const n of names) {
    if (n && !seen.has(n)) {
      seen.add(n);
      upgradeQueueItems.push({ name: n, fromAudit: true, tag: t("up.tagAudit"), checked: true });
    }
  }
  const srcDir = (auditData && auditData.music_dir) || ($("#aud-dir")?.value || "").trim();
  if (srcDir && $("#up-dir")) $("#up-dir").value = srcDir;
  setUpgradeExtUI("flac");
  renderUpgradeQueue();
  showTab("upgrade");
  showToast(t("up.toastSent", { n: upgradeQueueItems.length }), "ok");
}

$("#up-queue-filter").oninput = renderUpgradeQueue;
$("#up-queue-list").onchange = (e) => {
  if (!e.target.classList.contains("up-q-cb")) return;
  const item = upgradeQueueItems.find((x) => x.name === e.target.dataset.name);
  if (item) item.checked = e.target.checked;
  const checkedCount = upgradeQueueItems.filter((x) => x.checked).length;
  $("#up-queue-count").textContent = t("up.queueCount", { checked: checkedCount, total: upgradeQueueItems.length });
  $("#up-sel-count").textContent = String(checkedCount);
};
$("#up-queue-list").onclick = (e) => {
  const del = e.target.closest(".up-q-del");
  if (!del) return;
  upgradeQueueItems = upgradeQueueItems.filter((x) => x.name !== del.dataset.name);
  renderUpgradeQueue();
};
$("#btn-up-selall").onclick = () => {
  const kw = ($("#up-queue-filter")?.value || "").toLowerCase();
  upgradeQueueItems.forEach((x) => { if (!kw || x.name.toLowerCase().includes(kw)) x.checked = true; });
  renderUpgradeQueue();
};
$("#btn-up-selnone").onclick = () => {
  const kw = ($("#up-queue-filter")?.value || "").toLowerCase();
  upgradeQueueItems.forEach((x) => { if (!kw || x.name.toLowerCase().includes(kw)) x.checked = false; });
  renderUpgradeQueue();
};
$("#btn-up-clear-files").onclick = () => {
  upgradeQueueItems = [];
  renderUpgradeQueue();
  showToast(t("up.toastCleared"));
};
async function scanUpgradeFiles(silent = false) {
  try {
    const dir = ($("#up-dir")?.value || "").trim();
    const ext = $("#up-ext").value;
    const params = new URLSearchParams();
    if (dir) params.set("dir", dir);
    if (ext) params.set("ext", ext);
    const res = await api(`/api/upgrade/files?${params.toString()}`);
    if (res.music_dir && $("#up-dir") && !dir) $("#up-dir").value = res.music_dir;
    upgradeQueueItems = (res.files || []).map((f) => ({
      name: f.name, tag: (f.ext || "").toUpperCase(), checked: true,
    }));
    renderUpgradeQueue();
    if (!silent) {
      showToast(t("up.toastLoaded", { n: upgradeQueueItems.length }), upgradeQueueItems.length ? "ok" : "");
    }
  } catch (e) { showToast(e.message, "err"); }
}

$("#btn-up-scan").onclick = () => scanUpgradeFiles(false);

$("#btn-aud-send-sel").onclick = () => {
  const picked = [...document.querySelectorAll("#audit-files .aud-sel:checked")].map((c) => c.dataset.name).filter(Boolean);
  sendAuditFilesToUpgrade(picked);
};
$("#btn-aud-send-all").onclick = () => {
  const allNames = (auditData?.files || []).map((f) => f.name).filter(Boolean);
  sendAuditFilesToUpgrade(allNames);
};

function renderAuditPickList() {
  const kw = ($("#aud-pick-filter").value || "").toLowerCase();
  const shown = auditCandidateFiles.filter((f) => !kw || f.toLowerCase().includes(kw));
  $("#aud-pick-summary").textContent = t("aud.pickSummary", { sel: auditSelectedFiles.size, total: auditCandidateFiles.length });
  $("#aud-pick-list").innerHTML = shown.map((name) => {
    const chk = auditSelectedFiles.has(name) ? "checked" : "";
    return `<label class="fc-dir-item"><input type="checkbox" class="aud-pick-cb" data-name="${esc(name)}" ${chk}> <span>${esc(name)}</span></label>`;
  }).join("") || `<div class="fc-hint" style="padding:10px;text-align:center;">${esc(t("aud.pickEmpty"))}</div>`;
}

$("#btn-aud-load-files").onclick = async () => {
  const box = $("#aud-pick-box");
  if (!box.hidden) { box.hidden = true; return; }
  try {
    const dir = ($("#aud-dir")?.value || "").trim();
    const q = dir ? `?dir=${encodeURIComponent(dir)}` : "";
    const res = await api(`/api/audit/files${q}`);
    auditCandidateFiles = res.files || [];
    auditSelectedFiles = new Set();
    box.hidden = false;
    renderAuditPickList();
  } catch (e) { showToast(e.message, "err"); }
};
$("#aud-pick-filter").oninput = renderAuditPickList;
$("#aud-pick-list").onchange = (e) => {
  if (!e.target.classList.contains("aud-pick-cb")) return;
  const nm = e.target.dataset.name;
  if (e.target.checked) auditSelectedFiles.add(nm);
  else auditSelectedFiles.delete(nm);
  $("#aud-pick-summary").textContent = t("aud.pickSummary", { sel: auditSelectedFiles.size, total: auditCandidateFiles.length });
};
$("#btn-aud-pick-all").onclick = () => {
  const kw = ($("#aud-pick-filter").value || "").toLowerCase();
  auditCandidateFiles.filter((f) => !kw || f.toLowerCase().includes(kw)).forEach((f) => auditSelectedFiles.add(f));
  renderAuditPickList();
};
$("#btn-aud-pick-none").onclick = () => {
  auditSelectedFiles.clear();
  renderAuditPickList();
};

document.querySelectorAll("#up-ext-seg .fc-segmented__btn").forEach((b) => {
  b.onclick = () => {
    setUpgradeExtUI(b.dataset.ext);
    scanUpgradeFiles(true);
  };
});

$("#btn-up").onclick = async () => {
  const picked = upgradeQueueItems.filter((x) => x.checked).map((x) => x.name);
  if (!picked.length) return showToast(t("up.toastNeedFiles"), "err");
  try {
    const extVal = $("#up-ext").value;
    const dir = ($("#up-dir")?.value || "").trim();
    const body = {
      ext: extVal === "flac" ? "all" : extVal,
      full_retry: $("#up-retry").checked,
      files: picked,
    };
    if (dir) body.music_dir = dir;
    const j = await api("/api/upgrade", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    watchJob(j.id);
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

$("#btn-audit").onclick = async () => {
  try {
    const body = {};
    const dir = ($("#aud-dir")?.value || "").trim();
    if (dir) body.music_dir = dir;
    if (auditSelectedFiles.size > 0) body.files = [...auditSelectedFiles];
    const j = await api("/api/audit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    watchJob(j.id, async () => {
      const full = await api("/api/job/" + j.id);
      if (full.audit) showAudit({ ...full.audit, when: full.started_h });
      showTab("audit");
      showToast(t("aud.toastDone"));
    });
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Dedupe View ---------- */
let dedupeGroups = [];
let dedupeMusicDir = "";
const dedupeSelected = new Set();

function fmtSizeMB(bytes) {
  if (!bytes) return "-";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function renderDedupeGroups() {
  const kw = ($("#ded-filter")?.value || "").toLowerCase();
  $("#ded-sel-count").textContent = String(dedupeSelected.size);
  if (!dedupeGroups.length) {
    $("#ded-groups").innerHTML = `<div class="fc-empty">${esc(t("ded.noGroups"))}</div>`;
    return;
  }
  const shown = dedupeGroups.filter((g) => {
    if (!kw) return true;
    const hay = [g.title_key, g.artist_key, ...(g.members || []).map((m) => m.file)].join(" ").toLowerCase();
    return hay.includes(kw);
  });
  if (!shown.length) {
    $("#ded-groups").innerHTML = `<div class="fc-hint" style="padding:12px;text-align:center;">${esc(t("ded.noMatch"))}</div>`;
    return;
  }
  $("#ded-groups").innerHTML = shown.map((g, gi) => {
    const rows = (g.members || []).map((m) => {
      const checked = dedupeSelected.has(m.file) ? "checked" : "";
      const meta = [
        (m.ext || "").toUpperCase(),
        m.bitrate_kbps ? `${m.bitrate_kbps} kbps` : "",
        m.duration ? fmtDur(Math.round(m.duration * 1000)) : "",
        fmtSizeMB(m.size),
      ].filter(Boolean).join(" · ");
      return `<label class="fc-dir-item" style="justify-content:space-between;cursor:pointer;">` +
        `<span class="fc-row" style="gap:8px;flex:1;min-width:0;">` +
          `<input type="checkbox" class="ded-cb" data-file="${esc(m.file)}" ${checked}>` +
          `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(m.file)}">${esc(m.file)}</span>` +
        `</span>` +
        `<span class="fc-chip fc-tabular" style="flex:none;">${esc(meta)}</span>` +
      `</label>`;
    }).join("");
    return `<div class="fc-block" style="margin-bottom:10px;padding:10px 12px;">` +
      `<div class="fc-row" style="justify-content:space-between;margin-bottom:8px;">` +
        `<strong style="font-size:13px;">#${gi + 1} · ${esc(g.title_key || t("ded.unknownTitle"))} — ${esc(g.artist_key || t("ded.unknownArtist"))}</strong>` +
        `<div class="fc-row" style="gap:6px;">` +
          (g.reason ? `<span class="fc-chip">${esc(trDedupeReason(g.reason))}</span>` : "") +
          `<span class="fc-chip fc-tabular">${esc(t("ded.fileCount", { n: (g.members || []).length }))}</span>` +
        `</div>` +
      `</div>` +
      rows +
    `</div>`;
  }).join("");
}

async function scanDedupe() {
  try {
    $("#btn-ded-scan").disabled = true;
    $("#ded-summary").textContent = t("ded.scanning");
    const dir = ($("#ded-dir")?.value || "").trim();
    const q = dir ? `?dir=${encodeURIComponent(dir)}` : "";
    const res = await api("/api/dedupe" + q);
    dedupeMusicDir = res.music_dir || dir;
    if (res.music_dir && $("#ded-dir") && !dir) $("#ded-dir").value = res.music_dir;
    dedupeGroups = res.groups || [];
    dedupeSelected.clear();
    $("#ded-summary").textContent = t("ded.summary", { groups: res.total_groups || 0, files: res.total_files || 0 });
    renderDedupeGroups();
    showToast(dedupeGroups.length ? t("ded.toastFound", { n: dedupeGroups.length }) : t("ded.toastNone"), dedupeGroups.length ? "" : "ok");
  } catch (e) {
    $("#ded-summary").textContent = t("ded.scanFail");
    showToast(e.message, "err");
  } finally {
    $("#btn-ded-scan").disabled = false;
  }
}

$("#btn-ded-scan").onclick = scanDedupe;
if ($("#btn-pick-ded-dir")) $("#btn-pick-ded-dir").onclick = () => openDirPicker("#ded-dir");
$("#ded-filter").oninput = renderDedupeGroups;
$("#ded-groups").onchange = (e) => {
  if (!e.target.classList.contains("ded-cb")) return;
  const f = e.target.dataset.file;
  if (!f) return;
  if (e.target.checked) dedupeSelected.add(f);
  else dedupeSelected.delete(f);
  $("#ded-sel-count").textContent = String(dedupeSelected.size);
};
$("#btn-ded-auto").onclick = () => {
  dedupeSelected.clear();
  for (const g of dedupeGroups) {
    const sorted = [...(g.members || [])].sort((a, b) => {
      const fa = a.ext === "flac" ? 1 : 0;
      const fb = b.ext === "flac" ? 1 : 0;
      if (fb !== fa) return fb - fa;
      if ((b.bitrate_kbps || 0) !== (a.bitrate_kbps || 0)) return (b.bitrate_kbps || 0) - (a.bitrate_kbps || 0);
      return (b.size || 0) - (a.size || 0);
    });
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i]?.file) dedupeSelected.add(sorted[i].file);
    }
  }
  renderDedupeGroups();
  showToast(t("ded.toastAutoSel", { n: dedupeSelected.size }));
};
$("#btn-ded-none").onclick = () => {
  dedupeSelected.clear();
  renderDedupeGroups();
};
$("#btn-ded-del").onclick = async () => {
  const files = [...dedupeSelected];
  if (!files.length) return showToast(t("ded.toastNeedSel"), "err");
  if (!confirm(t("ded.confirmDel", { n: files.length }))) return;
  try {
    const res = await api("/api/dedupe/delete", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ music_dir: dedupeMusicDir || ($("#ded-dir")?.value || "").trim(), files }),
    });
    showToast(t("ded.toastMoved", { n: (res.moved || []).length }), "ok");
    await scanDedupe();
    refreshState();
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Library Browser（冻结契约 2：/api/library/files） ---------- */
let libPage = 1;
let libTotal = 0;
let libLoading = false;
let libSearchTimer = null;

async function loadLibraryFiles(resetPage = false) {
  if (libLoading) return;
  if (resetPage) libPage = 1;
  libLoading = true;
  $("#btn-lib-load").disabled = true;
  try {
    const pageSize = Number($("#lib-page-size").value) || 50;
    const params = new URLSearchParams({ page: String(libPage), page_size: String(pageSize) });
    const q = ($("#lib-q").value || "").trim();
    const ext = $("#lib-ext").value || "";
    if (q) params.set("q", q);
    if (ext) params.set("ext", ext);
    const res = await api("/api/library/files?" + params.toString());
    libTotal = Number(res.total) || 0;
    libPage = Number(res.page) || libPage;
    const pages = Math.max(1, Math.ceil(libTotal / pageSize));
    if (libPage > pages) { libPage = pages; libLoading = false; return loadLibraryFiles(); }
    $("#lib-summary").textContent = t("lib.summary", { total: libTotal });
    $("#lib-page-info").textContent = t("lib.pageInfo", { page: libPage, pages });
    $("#btn-lib-prev").disabled = libPage <= 1;
    $("#btn-lib-next").disabled = libPage >= pages;
    $("#lib-files tbody").innerHTML = (res.files || []).map((f) =>
      `<tr>` +
      `<td data-label="${esc(t("lib.colName"))}" title="${esc(f.name)}">${esc(f.name)}</td>` +
      `<td data-label="${esc(t("lib.colExt"))}"><span class="fc-chip">${esc((f.ext || "").toUpperCase())}</span></td>` +
      `<td data-label="${esc(t("lib.colSize"))}" class="is-num">${esc(f.size_mb)}</td>` +
      `<td data-label="${esc(t("lib.colMtime"))}" class="fc-tabular">${esc(f.mtime_h)}</td>` +
      `</tr>`
    ).join("") || `<tr><td colspan="4" class="fc-empty">${esc(t("lib.empty"))}</td></tr>`;
  } catch (e) {
    $("#lib-summary").textContent = t("lib.notLoaded");
    showToast(e.message, "err");
  } finally {
    libLoading = false;
    $("#btn-lib-load").disabled = false;
  }
}

$("#btn-lib-load").onclick = () => loadLibraryFiles(true);
$("#btn-lib-prev").onclick = () => { if (libPage > 1) { libPage -= 1; loadLibraryFiles(); } };
$("#btn-lib-next").onclick = () => { libPage += 1; loadLibraryFiles(); };
$("#lib-ext").onchange = () => loadLibraryFiles(true);
$("#lib-page-size").onchange = () => loadLibraryFiles(true);
$("#lib-q").oninput = () => {
  if (libSearchTimer) clearTimeout(libSearchTimer);
  libSearchTimer = setTimeout(() => loadLibraryFiles(true), 320);
};
$("#lib-q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); loadLibraryFiles(true); }
});

/* ---------- Lyrics Check（冻结契约 3：/api/lyrics/report + /api/lyrics/delete） ---------- */
const LYR_KINDS = ["orphan", "meta_title", "meta_artist", "too_long", "too_short", "dup_content", "empty", "no_timestamps"];
let lyrReport = null;
const lyrSelected = new Set();

function lyrKindLabel(kind) {
  return t(`lyr.kind_${kind}`) !== `lyr.kind_${kind}` ? t(`lyr.kind_${kind}`) : kind;
}

// 绝对路径 = music_dir + name（按 music_dir 的分隔符拼接，契约 3 约定）
function lyrAbsPath(name) {
  const dir = (lyrReport && lyrReport.music_dir) || "";
  if (!dir) return name;
  const sep = dir.includes("\\") && !dir.includes("/") ? "\\" : "/";
  const withSep = dir.endsWith("/") || dir.endsWith("\\") ? dir : dir + sep;
  return withSep + name;
}

async function loadLyricsReport() {
  const btn = $("#btn-lyr-reload");
  btn.disabled = true;
  $("#lyr-summary").textContent = t("lyr.scanning");
  try {
    const res = await api("/api/lyrics/report");
    lyrReport = res;
    lyrSelected.clear();
    renderLyricsReport();
    renderLyricsResult(null, null);
    $("#lyr-summary").textContent = t("lyr.summary", { n: Number(res.total) || 0 });
    if (res.music_dir) {
      $("#lyr-dir").textContent = res.music_dir;
      $("#lyr-dir").hidden = false;
    }
  } catch (e) {
    $("#lyr-summary").textContent = t("lyr.notLoaded");
    showToast(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

function renderLyricsReport() {
  $("#lyr-sel-count").textContent = String(lyrSelected.size);
  const groups = (lyrReport && lyrReport.groups) || [];
  if (!groups.length) {
    $("#lyr-groups").innerHTML = `<div class="fc-empty">${esc(t("lyr.noIssues"))}</div>`;
    return;
  }
  // 固定八类顺序渲染，报告里缺失的 kind 补空组置灰（契约 3）
  const byKind = new Map(groups.map((g) => [g.kind || "", g]));
  const ordered = LYR_KINDS.map((k) => byKind.get(k) || { kind: k, count: 0, files: [] });
  $("#lyr-groups").innerHTML = ordered.map((g) => {
    const files = g.files || [];
    const count = Number(g.count ?? files.length) || 0;
    const isZero = count === 0;
    const rows = files.map((f) => {
      const nm = f.name || "";
      const checked = lyrSelected.has(nm) ? "checked" : "";
      return `<label class="fc-lyr-file">` +
        `<input type="checkbox" class="lyr-cb" data-name="${esc(nm)}" ${checked}>` +
        `<span class="fc-lyr-file__name" title="${esc(nm)}">${esc(nm)}</span>` +
        `<span class="fc-chip">${esc(f.issue || "")}</span>` +
      `</label>`;
    }).join("") || `<div class="fc-hint" style="margin-top:6px;">${esc(t("lyr.noFiles"))}</div>`;
    return `<details class="fc-block fc-lyr-group${isZero ? " is-zero" : ""}">` +
      `<summary>` +
        `<span class="fc-chip">${esc(lyrKindLabel(g.kind || ""))}</span>` +
        `<span class="fc-chip fc-tabular">${count}</span>` +
      `</summary>` +
      `<div class="fc-lyr-files">${rows}</div>` +
    `</details>`;
  }).join("");
}

function renderLyricsResult(moved, failed) {
  const box = $("#lyr-result");
  const mv = moved || [];
  const fl = failed || [];
  if (!mv.length && !fl.length) { box.hidden = true; box.innerHTML = ""; return; }
  const fmtFail = (x) => (typeof x === "string" ? x : JSON.stringify(x));
  box.innerHTML =
    `<div class="fc-row" style="gap:6px;flex-wrap:wrap;">` +
      (mv.length ? `<span class="fc-chip fc-chip--ok fc-tabular">${esc(t("lyr.resultMoved"))} ${mv.length}</span>` : "") +
      (fl.length ? `<span class="fc-chip fc-chip--error fc-tabular">${esc(t("lyr.resultFailed"))} ${fl.length}</span>` : "") +
    `</div>` +
    (mv.length ? `<div class="fc-hint fc-mono" style="word-break:break-all;margin-top:6px;">${esc(mv.map(String).join(" ; "))}</div>` : "") +
    (fl.length ? `<div class="fc-hint fc-mono" style="word-break:break-all;margin-top:6px;">${esc(fl.map(fmtFail).join(" ; "))}</div>` : "");
  box.hidden = false;
}

$("#btn-lyr-reload").onclick = () => loadLyricsReport();
$("#lyr-groups").addEventListener("change", (e) => {
  if (!e.target.classList.contains("lyr-cb")) return;
  const nm = e.target.dataset.name;
  if (!nm) return;
  if (e.target.checked) lyrSelected.add(nm);
  else lyrSelected.delete(nm);
  $("#lyr-sel-count").textContent = String(lyrSelected.size);
});
$("#btn-lyr-del").onclick = async () => {
  const files = [...lyrSelected].map(lyrAbsPath);
  if (!files.length) return showToast(t("lyr.toastNeedSel"), "err");
  if (!confirm(t("lyr.confirmDel", { n: files.length }))) return;
  try {
    const res = await api("/api/lyrics/delete", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files }),
    });
    const moved = res.moved || [];
    const failed = res.failed || [];
    renderLyricsResult(moved, failed);
    showToast(t("lyr.toastMoved", { n: moved.length, f: failed.length }), failed.length ? "err" : "ok");
    await loadLyricsReport();
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Rename Tool（冻结契约 4/5：/api/rename/scan + /api/rename/apply） ---------- */
let renameItems = [];
const renSelected = new Set();

function renKey(it) { return `${it.old}\n=>\n${it.new}`; }

function renKindLabel(kind) {
  return t(`ren.kind_${kind}`) !== `ren.kind_${kind}` ? t(`ren.kind_${kind}`) : kind;
}

async function scanRename() {
  const btn = $("#btn-ren-scan");
  btn.disabled = true;
  $("#ren-summary").textContent = t("ren.scanning");
  try {
    const res = await api("/api/rename/scan");
    renameItems = Array.isArray(res) ? res : [];
    renSelected.clear();
    renderRenameList();
    $("#ren-summary").textContent = t("ren.summary", { n: renameItems.length });
  } catch (e) {
    $("#ren-summary").textContent = t("ren.notScanned");
    showToast(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

function renderRenameList() {
  $("#ren-sel-count").textContent = String(renSelected.size);
  if (!renameItems.length) {
    $("#ren-list").innerHTML = `<div class="fc-empty">${esc(t("ren.nothingFound"))}</div>`;
    return;
  }
  $("#ren-list").innerHTML = renameItems.map((it) => {
    const badges = (it.kinds || []).map((k) =>
      `<span class="fc-chip fc-chip--warn">${esc(renKindLabel(k))}</span>`).join("");
    const checked = renSelected.has(renKey(it)) ? "checked" : "";
    return `<label class="fc-dir-item fc-ren-item">` +
      `<span class="fc-row" style="gap:8px;flex:1;min-width:0;">` +
        `<input type="checkbox" class="ren-cb" data-key="${esc(renKey(it))}" ${checked}>` +
        `<span class="fc-ren-path" title="${esc(it.old)}">${esc(it.old)}</span>` +
        `<span class="fc-ren-arrow" aria-hidden="true">→</span>` +
        `<span class="fc-ren-path" title="${esc(it.new)}">${esc(it.new)}</span>` +
      `</span>` +
      `<span class="fc-row" style="gap:4px;flex:none;">${badges}</span>` +
    `</label>`;
  }).join("");
}

function renderRenameResult(records) {
  const box = $("#ren-result");
  const recs = records || [];
  if (!recs.length) { box.hidden = true; box.innerHTML = ""; return; }
  const nR = recs.filter((r) => r.status === "renamed").length;
  const nS = recs.filter((r) => r.status === "skip").length;
  const nF = recs.filter((r) => r.status === "failed").length;
  const cls = { renamed: "fc-chip--ok", skip: "fc-chip--warn", failed: "fc-chip--error" };
  const lbl = { renamed: t("ren.stRenamed"), skip: t("ren.stSkip"), failed: t("ren.stFailed") };
  box.innerHTML =
    `<div class="fc-row" style="gap:6px;margin-bottom:6px;flex-wrap:wrap;">` +
      `<strong style="font-size:13px;">${esc(t("ren.resultTitle"))}</strong>` +
      `<span class="fc-chip fc-chip--ok fc-tabular">${esc(lbl.renamed)} ${nR}</span>` +
      `<span class="fc-chip fc-chip--warn fc-tabular">${esc(lbl.skip)} ${nS}</span>` +
      `<span class="fc-chip fc-chip--error fc-tabular">${esc(lbl.failed)} ${nF}</span>` +
    `</div>` +
    recs.map((r) => {
      const c = cls[r.status] || "";
      const l = lbl[r.status] || r.status || "";
      return `<div class="fc-ren-result-line">` +
        `<span class="fc-chip ${c}">${esc(l)}</span>` +
        `<span class="fc-ren-path" title="${esc(r.old || "")}">${esc(r.old || "")} → ${esc(r.new || "")}</span>` +
        (r.detail ? `<span class="fc-hint" style="margin:0;">${esc(r.detail)}</span>` : "") +
      `</div>`;
    }).join("");
  box.hidden = false;
}

$("#btn-ren-scan").onclick = () => scanRename();
$("#ren-list").addEventListener("change", (e) => {
  if (!e.target.classList.contains("ren-cb")) return;
  const key = e.target.dataset.key;
  if (!key) return;
  if (e.target.checked) renSelected.add(key);
  else renSelected.delete(key);
  $("#ren-sel-count").textContent = String(renSelected.size);
});
$("#btn-ren-apply").onclick = async () => {
  const items = renameItems
    .filter((it) => renSelected.has(renKey(it)))
    .map((it) => ({ old: it.old, new: it.new }));
  if (!items.length) return showToast(t("ren.toastNeedSel"), "err");
  if (!confirm(t("ren.confirmApply", { n: items.length }))) return;
  try {
    const res = await api("/api/rename/apply", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    const records = res.records || [];
    renderRenameResult(records);
    showToast(t("ren.toastApplied", {
      r: records.filter((x) => x.status === "renamed").length,
      s: records.filter((x) => x.status === "skip").length,
      f: records.filter((x) => x.status === "failed").length,
    }), "ok");
    await scanRename();
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Fingerprint Compare（冻结契约 5：/api/fingerprint?a=&b=） ---------- */
$("#btn-fp").onclick = async () => {
  const a = ($("#fp-a").value || "").trim();
  const b = ($("#fp-b").value || "").trim();
  if (!a || !b) return showToast(t("fp.toastNeedPaths"), "err");
  const btn = $("#btn-fp");
  btn.disabled = true;
  try {
    const q = `?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`;
    const res = await api("/api/fingerprint" + q);
    $("#fp-result").hidden = false;
    $("#fp-a-md5").textContent = res.a_md5 || "—";
    $("#fp-b-md5").textContent = res.b_md5 || "—";
    const m = $("#fp-match");
    if (res.match === true) {
      m.className = "fc-chip fc-chip--ok";
      m.textContent = t("fp.matchYes");
    } else {
      m.className = "fc-chip fc-chip--error";
      m.textContent = t("fp.matchNo");
    }
  } catch (e) { showToast(e.message, "err"); }
  finally { btn.disabled = false; }
};

applyTheme();
applyLang(currentLang, false);
refreshState();
setInterval(refreshState, 2500);
</script>
</body>
</html>
"""
