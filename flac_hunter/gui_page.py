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
.fc-table tbody td {
  padding: 8px 10px;
  vertical-align: middle;
  max-width: 340px;
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
      <button id="btn-collapse" type="button" class="fc-icon-btn" aria-label="折叠侧边栏" title="折叠侧边栏">
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
        <span>歌单导入</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="upgrade">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polygon points="12 2 15 9 22 9 16.5 14 18.5 21 12 17 5.5 21 7.5 14 2 9 9 9 12 2"/>
        </svg>
        <span>无损升级</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="audit">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        </svg>
        <span>质量审计</span>
      </button>
      <button type="button" class="fc-nav-item" data-tab="jobs">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span>任务列表</span>
        <span id="nav-jobs-badge" class="fc-nav-badge fc-tabular"></span>
      </button>
    </nav>

    <div class="fc-sidebar__footer">
      <div class="fc-lib-mini">
        <div class="fc-row" style="justify-content:space-between;gap:6px;">
          <span id="sb-lib-total" class="fc-tabular"><strong>0</strong> 首曲目</span>
          <button type="button" id="btn-switch-lib" class="fc-btn fc-btn--sm fc-btn--tonal" style="padding:3px 9px;font-size:11px;">切换曲库</button>
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
          <span>外观设置</span>
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
        <span id="jobstat" class="fc-chip fc-tabular">空闲</span>
        <button id="btn-quick-theme" type="button" class="fc-icon-btn fc-icon-btn--tonal" aria-label="切换浅色或深色主题" title="切换明暗主题">
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
                <h2 class="fc-card-header__title">引擎状态</h2>
                <span id="hero-chip" class="fc-chip fc-chip--ok"><span class="fc-chip__dot" aria-hidden="true"></span><span id="hero-chip-text">就绪</span></span>
              </div>
            </div>
            <div>
              <div id="hero-headline" class="fc-status-card__main">准备导入歌单或文本清单</div>
              <div class="fc-row" style="margin-top:6px;gap:8px;">
                <div id="hero-dir" class="fc-stat-sub fc-mono" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></div>
                <button type="button" id="btn-hero-switch-lib" class="fc-btn fc-btn--sm fc-btn--tonal" style="padding:2px 9px;font-size:11.5px;">切换默认曲库</button>
              </div>
            </div>
            <div class="fc-status-card__meta">
              <div>
                <div class="fc-meta-item__label">作业进度</div>
                <div id="hero-progress" class="fc-meta-item__value fc-tabular">空闲</div>
              </div>
              <div>
                <div class="fc-meta-item__label">限速与锁</div>
                <div class="fc-meta-item__value">单队列串行</div>
              </div>
            </div>
          </div>
          <div class="fc-status-card__action">
            <button id="hero-action-btn" type="button" class="fc-scallop-btn" aria-pressed="false" aria-label="快捷操作" title="聚焦导入 / 暂停或继续下载">
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
              <h2 class="fc-card-header__title">本地曲库无损率</h2>
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
              <h2 class="fc-card-header__title">最近质量审计</h2>
            </div>
            <button type="button" class="fc-btn fc-btn--sm" data-jump="audit">详情</button>
          </div>
          <div>
            <div class="fc-stat-figure">
              <span id="stat-audit-rate" class="fc-stat-num fc-tabular">—</span>
              <span class="fc-stat-unit">通过率</span>
            </div>
            <div id="stat-audit-sub" class="fc-stat-sub fc-tabular">尚未加载审计记录</div>
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
            <h2 class="fc-card-header__title">1 · 导入歌单与查重</h2>
            <span class="fc-card-header__sub">拉元数据后与本地曲库三层比对</span>
          </div>
          <div class="fc-tablist" role="tablist" aria-label="导入方式">
            <button type="button" class="fc-tab" id="imp-tab-uri" role="tab" aria-selected="true">歌单链接 / URI</button>
            <button type="button" class="fc-tab" id="imp-tab-list" role="tab" aria-selected="false">文本清单 (--list)</button>
          </div>
        </div>

        <div id="imp-panel-uri" role="tabpanel" aria-labelledby="imp-tab-uri" class="fc-tabpanel-inner">
          <div class="fc-row">
            <input type="text" class="fc-input" id="uri" aria-label="歌单链接或 URI" placeholder="粘贴歌单链接或 URI：B站收藏夹 / y.qq.com / 网易云 playlist / spotify: URI">
            <button type="button" class="fc-btn fc-btn--primary" id="btn-uri">拉取并查重</button>
          </div>
          <div class="fc-hint">支持 bilibili.com 收藏夹、y.qq.com 歌单、网易云公开 playlist、spotify: URI。若为私密歌单，可切换「文本清单」。</div>
        </div>

        <div id="imp-panel-list" role="tabpanel" aria-labelledby="imp-tab-list" class="fc-tabpanel-inner" hidden>
          <textarea class="fc-textarea" id="listtext" aria-label="文本清单内容" placeholder="每行一首：歌名 - 歌手（也支持 歌名-歌手 或只写歌名；末尾可选加 | 时长秒）&#10;例：快晴 - Orangestar&#10;例：又三郎-ヨルシカ"></textarea>
          <div class="fc-row" style="margin-top:10px;">
            <button type="button" class="fc-btn fc-btn--primary" id="btn-list">按文本清单查重</button>
            <span class="fc-hint" style="margin:0;">不访问网络，直接解析并与本地曲库对比去重。</span>
          </div>
        </div>

        <div class="fc-block" style="margin-top:14px;">
          <div class="fc-row" style="gap:8px;">
            <label class="fc-switch-label" for="dl-dir" style="font-weight:600;color:var(--fc-on-surface);">本次下载保存到</label>
            <input type="text" id="dl-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则保存到默认曲库">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-pick-dir">选择文件夹</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-reset-dir">恢复默认</button>
          </div>
          <div class="fc-hint" style="margin-top:6px;">支持手动输入/粘贴路径或点击「选择文件夹」；留空则沿用默认曲库目录。</div>
        </div>
      </article>

      <article class="fc-card" id="tracks-card" hidden>
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title">2 · 勾选要下载的曲目</h2>
            <span id="track-summary" class="fc-chip fc-tabular"></span>
          </div>
          <label class="fc-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="search" id="track-filter" placeholder="过滤歌名或歌手…">
          </label>
        </div>

        <div class="fc-row" style="margin-bottom:12px;">
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selnew">只选新曲</button>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selall">全选</button>
          <button type="button" class="fc-btn fc-btn--sm" id="btn-selnone">全不选</button>
          <span class="fc-spacer"></span>
          <label class="fc-switch-label" for="source">下载源
            <select id="source" class="fc-select">
              <option value="auto">auto（无损优先）</option>
              <option value="gdstudio">gdstudio</option>
              <option value="netease">netease</option>
              <option value="musicdl">musicdl</option>
              <option value="bili">bili</option>
              <option value="youtube">youtube</option>
            </select>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="dl-cover" class="fc-switch" checked>
            <span>下载封面</span>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="dl-lyrics" class="fc-switch">
            <span>下载歌词</span>
          </label>
          <label class="fc-switch-label">
            <input type="checkbox" id="inc-ex" class="fc-switch">
            <span>含已有曲目重下</span>
          </label>
          <button type="button" class="fc-btn fc-btn--primary" id="btn-dl">开始下载 (<span id="sel-count" class="fc-tabular">0</span>)</button>
        </div>

        <div class="fc-table-wrap" tabindex="0" role="region" aria-label="歌单曲目查重列表">
          <table id="tracks" class="fc-table fc-table--responsive">
            <caption>导入的歌单曲目及本地去重状态</caption>
            <thead>
              <tr>
                <th style="width:40px;"><input type="checkbox" id="chk-head" aria-label="切换全部勾选"></th>
                <th style="width:46px;" class="is-num">#</th>
                <th>歌名</th>
                <th>歌手</th>
                <th style="width:76px;" class="is-num">时长</th>
                <th style="width:92px;">状态</th>
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
            <h2 class="fc-card-header__title">任务列表</h2>
            <span class="fc-card-header__sub">同一时间仅执行一个作业，共享限速与曲库锁</span>
          </div>
        </div>
        <div id="joblist" class="fc-job-list"><div class="fc-empty">还没有任务 —— 前往「歌单导入」发起查重与下载</div></div>
      </article>

      <article class="fc-card" id="joblog-card" hidden>
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 id="joblog-title" class="fc-card-header__title">作业日志</h2>
            <span id="dlpct" class="fc-chip fc-chip--primary fc-tabular"></span>
          </div>
          <div class="fc-row" style="gap:6px;">
            <button type="button" class="fc-btn fc-btn--sm" id="btn-copy-log">复制日志</button>
            <button type="button" class="fc-btn fc-btn--sm" id="btn-pause" hidden>⏸ 暂停</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--danger" id="btn-skip" hidden>⏭ 跳过这首</button>
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
            <h2 class="fc-card-header__title">1 · 待升级清单</h2>
            <span id="up-queue-count" class="fc-chip fc-chip--primary fc-tabular">0 个文件</span>
          </div>
          <div class="fc-row" style="gap:6px;">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-selall">全选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-selnone">全不选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-clear-files">清空清单</button>
          </div>
        </div>

        <div class="fc-block" style="margin-bottom:12px;">
          <div class="fc-row" style="gap:8px;margin-bottom:10px;">
            <label class="fc-switch-label" for="up-dir" style="font-weight:600;color:var(--fc-on-surface);">扫描目录</label>
            <input type="text" id="up-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则扫描默认曲库">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-up-pick-dir">选择文件夹</button>
          </div>
          <div class="fc-row" style="gap:8px;justify-content:space-between;">
            <div class="fc-segmented" id="up-ext-seg" role="group" aria-label="扫描格式">
              <button type="button" class="fc-segmented__btn" data-ext="all" aria-pressed="true">MP3 + OGG</button>
              <button type="button" class="fc-segmented__btn" data-ext="mp3" aria-pressed="false">仅 MP3</button>
              <button type="button" class="fc-segmented__btn" data-ext="ogg" aria-pressed="false">仅 OGG</button>
              <button type="button" class="fc-segmented__btn" data-ext="flac" aria-pressed="false">FLAC</button>
            </div>
            <select id="up-ext" class="fc-sr-only" aria-hidden="true" tabindex="-1">
              <option value="all" selected>all</option>
              <option value="mp3">mp3</option>
              <option value="ogg">ogg</option>
              <option value="flac">flac</option>
            </select>
            <div class="fc-row" style="gap:8px;">
              <input type="search" id="up-queue-filter" class="fc-input" style="max-width:200px;padding:6px 10px;" placeholder="过滤清单文件名…">
              <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-up-scan">扫描载入清单</button>
            </div>
          </div>
        </div>

        <div id="up-queue-list" class="fc-dir-list" style="max-height:260px;">
          <div class="fc-empty">待升级清单为空 —— 请在上方选择目录「扫描载入清单」，或从「质量审计」传入不合格文件</div>
        </div>
      </article>

      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title">2 · 升级执行</h2>
            <span class="fc-card-header__sub">仅替换 ffprobe 实测真 FLAC 的无损源，绝不有损硬转</span>
          </div>
        </div>

        <div class="fc-block" style="margin-bottom:14px;">
          <div class="fc-row" style="justify-content:space-between;">
            <div>
              <div style="font-weight:600;">清空跳名单全量重试</div>
              <div class="fc-stat-sub">连续失败 ≥ 2 次的曲目默认记入跳名单；开启后会重置记录重新尝试</div>
            </div>
            <label class="fc-switch-label">
              <input type="checkbox" id="up-retry" class="fc-switch" aria-label="清空跳名单全量重试">
            </label>
          </div>
        </div>

        <div class="fc-row">
          <button type="button" class="fc-btn fc-btn--primary" id="btn-up">开始无损升级 (<span id="up-sel-count" class="fc-tabular">0</span>)</button>
          <span class="fc-hint" style="margin:0;">替换前自动备份旧文件并对比 PCM 指纹留证。</span>
        </div>
      </article>
    </section>

    <!-- VIEW 4: 质量审计 -->
    <section id="tab-audit" class="fc-view" data-view="audit" hidden>
      <article class="fc-card">
        <div class="fc-card-header">
          <div class="fc-card-header__start">
            <h2 class="fc-card-header__title">四项质量门审计</h2>
            <span class="fc-card-header__sub">实测 ffprobe：时长偏差 / 缺标签 / 缺封面 / 伪 FLAC</span>
          </div>
          <div class="fc-row" style="gap:8px;">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-load-files">选定文件列表</button>
            <button type="button" class="fc-btn fc-btn--primary" id="btn-audit">开始审计</button>
          </div>
        </div>
        <div class="fc-block" style="margin-bottom:10px;">
          <div class="fc-row" style="gap:8px;">
            <label class="fc-switch-label" for="aud-dir" style="font-weight:600;color:var(--fc-on-surface);">审计目录</label>
            <input type="text" id="aud-dir" class="fc-input" style="flex:1;min-width:200px;" placeholder="留空则扫描默认曲库">
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-dir">选择文件夹</button>
          </div>
        </div>
        <div id="aud-pick-box" class="fc-block" style="margin-bottom:10px;" hidden>
          <div class="fc-row" style="gap:8px;margin-bottom:8px;">
            <span id="aud-pick-summary" class="fc-chip fc-tabular">已选 0 个文件</span>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-all">全选</button>
            <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-pick-none">清空</button>
            <span class="fc-spacer"></span>
            <input type="search" id="aud-pick-filter" class="fc-input" style="max-width:220px;padding:6px 10px;" placeholder="过滤待审文件名…">
          </div>
          <div id="aud-pick-list" class="fc-dir-list" style="max-height:200px;"></div>
        </div>
        <div id="audit-empty-hint" class="fc-hint" style="margin-top:0;">不选定具体文件时将扫描目录内全部 .flac；若有历史审计记录将自动回显在下方。</div>
      </article>

      <div id="audit-result" hidden>
        <div class="fc-kpi-row" id="audit-tiles" style="margin-bottom:14px;"></div>

        <article class="fc-card">
          <div class="fc-card-header">
            <div class="fc-card-header__start">
              <h2 class="fc-card-header__title">不合格文件明细</h2>
              <span id="audit-when" class="fc-chip fc-tabular"></span>
            </div>
            <div class="fc-row" style="gap:8px;">
              <span id="audit-count" class="fc-stat-sub fc-tabular"></span>
              <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="btn-aud-send-sel">选中传入升级 (<span id="aud-sel-count" class="fc-tabular">0</span>)</button>
              <button type="button" class="fc-btn fc-btn--sm fc-btn--primary" id="btn-aud-send-all">全部不合格传入升级</button>
            </div>
          </div>

          <div class="fc-row" style="justify-content:space-between;margin-bottom:12px;">
            <div id="audit-chips" class="fc-tablist" role="tablist" aria-label="按问题分类筛选"></div>
            <label class="fc-search">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="search" id="audit-search" placeholder="按文件名搜索…">
            </label>
          </div>

          <div class="fc-table-wrap" tabindex="0" role="region" aria-label="质量审计异常文件列表">
            <table id="audit-files" class="fc-table fc-table--responsive">
              <caption>未通过四项质量门的 FLAC 文件列表</caption>
              <thead><tr><th style="width:40px;"><input type="checkbox" id="aud-chk-head" aria-label="全选当前不合格文件"></th><th>文件名</th><th style="width:240px;">触发问题</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>
        </article>
      </div>
    </section>
  </main>
</div>

<nav class="fc-dock" aria-label="移动端快捷导航">
  <button type="button" class="fc-dock__item" data-tab="import" aria-current="page">
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="4"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/></svg>
    <span>导入</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="upgrade">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polygon points="12 2 15 9 22 9 16.5 14 18.5 21 12 17 5.5 21 7.5 14 2 9 9 9 12 2"/></svg>
    <span>升级</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="audit">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
    <span>审计</span>
  </button>
  <button type="button" class="fc-dock__item" data-tab="jobs">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    <span>任务</span>
  </button>
</nav>

<div id="theme-popover" popover="auto" class="fc-popover" aria-label="外观与主题设置">
  <div style="font-weight:700;font-size:14px;margin-bottom:12px;">外观与主题引擎</div>
  <div style="font-size:12px;color:var(--fc-on-surface-variant);margin-bottom:6px;">主题模式</div>
  <div class="fc-segmented" style="margin-bottom:14px;width:100%;">
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="light dark" aria-pressed="true">跟随系统</button>
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="light" aria-pressed="false">浅色</button>
    <button type="button" class="fc-segmented__btn" style="flex:1;" data-scheme="dark" aria-pressed="false">深色</button>
  </div>
  <div style="font-size:12px;color:var(--fc-on-surface-variant);margin-bottom:6px;">种子主题色</div>
  <div id="seed-swatches" class="fc-swatch-row" style="margin-bottom:14px;"></div>
  <div class="fc-row" style="justify-content:space-between;margin-bottom:8px;">
    <span style="font-size:13px;">纯黑深色 (OLED)</span>
    <input type="checkbox" id="pref-pure-black" class="fc-switch" aria-label="纯黑深色模式">
  </div>
  <div class="fc-row" style="justify-content:space-between;">
    <span style="font-size:13px;">Liquid Glass 浮层</span>
    <input type="checkbox" id="pref-glass" class="fc-switch" aria-label="Liquid Glass 液态毛玻璃" checked>
  </div>
</div>

<dialog id="dir-dialog" class="fc-dialog" aria-labelledby="dir-dialog-title">
  <div class="fc-card-header" style="margin-bottom:10px;">
    <h3 id="dir-dialog-title" class="fc-card-header__title" style="font-size:15px;color:var(--fc-on-surface);">选择下载保存目录</h3>
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-close">关闭</button>
  </div>
  <div id="dir-drives" class="fc-row" style="gap:6px;margin-bottom:8px;flex-wrap:wrap;"></div>
  <div class="fc-row" style="gap:8px;margin-bottom:10px;">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-up">上一级</button>
    <input type="text" id="dir-current" class="fc-input" style="flex:1;padding:7px 10px;" aria-label="当前目录路径">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-go">跳转</button>
  </div>
  <div id="dir-list" class="fc-dir-list" role="listbox" aria-label="子文件夹列表"></div>
  <div class="fc-row" style="justify-content:flex-end;gap:8px;margin-top:12px;">
    <button type="button" class="fc-btn fc-btn--sm fc-btn--tonal" id="dir-cancel">取消</button>
    <button type="button" class="fc-btn fc-btn--primary" id="dir-choose">选择此目录</button>
  </div>
</dialog>

<script>
"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const TYPE_NAME = { prepare: "歌单查重", download: "下载", upgrade: "无损升级", audit: "质量审计", custom: "自定义" };
const VIEW_TITLE = { import: "歌单导入", jobs: "任务列表", upgrade: "无损升级", audit: "质量审计" };
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
});

$("#btn-collapse").onclick = () => $("#fc-shell").classList.toggle("is-collapsed");

/* ---------- Navigation ---------- */
function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach((b) => {
    if (b.dataset.tab === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  document.querySelectorAll("main section[data-view]").forEach((sec) => {
    sec.hidden = sec.dataset.view !== name;
  });
  $("#topbar-title").textContent = VIEW_TITLE[name] || "flac-hunter";
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
  $("#stat-audit-sub").textContent = `通过 ${A.pass} / 不合格 ${A.fail}（共 ${A.total} 个 FLAC）`;
  $("#wavy-audit-path").setAttribute("d", buildWavyPath(rate));

  $("#audit-tiles").innerHTML =
    `<div class="fc-card"><div class="fc-stat-num fc-tabular">${A.total}</div><div class="fc-stat-sub">扫描 FLAC</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-success);">${A.pass}</div><div class="fc-stat-sub">四项全过</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-error);">${A.fail}</div><div class="fc-stat-sub">存在异常</div></div>` +
    `<div class="fc-card"><div class="fc-stat-num fc-tabular" style="color:var(--fc-primary);">${rate}%</div><div class="fc-stat-sub">合格率</div></div>`;

  const chips = ["全部", ...Object.entries(A.by_issue || {}).sort((a, b) => b[1] - a[1]).map(([k]) => k)];
  const chipsEl = $("#audit-chips");
  chipsEl.innerHTML = chips.map((k) => {
    const n = k === "全部" ? A.fail : (A.by_issue[k] || 0);
    return `<button type="button" class="fc-tab" role="tab" aria-selected="${k === auditFilter ? "true" : "false"}" data-k="${esc(k)}">${esc(k)} <span class="fc-tabular">${n}</span></button>`;
  }).join("");
  chipsEl.querySelectorAll('[role="tab"]').forEach((btn) => {
    btn.onclick = () => { auditFilter = btn.dataset.k; renderAudit(); };
  });

  const kw = ($("#audit-search").value || "").toLowerCase();
  const rows = (A.files || []).filter((f) =>
    (auditFilter === "全部" || (f.issues || []).includes(auditFilter)) &&
    (!kw || (f.name || "").toLowerCase().includes(kw)));
  $("#audit-count").textContent = `显示 ${rows.length} / ${A.fail} 个不合格文件`;
  $("#audit-files tbody").innerHTML = rows.slice(0, 500).map((f) =>
    `<tr><td data-label="选择"><input type="checkbox" class="aud-sel" data-name="${esc(f.name)}" aria-label="选择 ${esc(f.name)}"></td>` +
    `<td data-label="文件名" title="${esc(f.name)}">${esc(f.name)}</td>` +
    `<td data-label="触发问题">${(f.issues || []).map((i) => `<span class="fc-chip fc-chip--error" style="margin-inline-end:4px;">${esc(i)}</span>`).join("")}</td></tr>`
  ).join("") || `<tr><td colspan="3" class="fc-empty">没有符合当前筛选条件的不合格文件</td></tr>`;
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
  $("#audit-when").textContent = A.when || "最近";
  renderAudit();
  $("#audit-result").hidden = false;
  $("#audit-empty-hint").hidden = true;
}

/* ---------- Import & Track Selection ---------- */
$("#btn-uri").onclick = async () => {
  const uri = $("#uri").value.trim();
  if (!uri) return showToast("请先填入歌单链接或 URI", "err");
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
      showToast("歌单元数据拉取与查重完成");
    });
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

$("#btn-list").onclick = async () => {
  const list_text = $("#listtext").value.trim();
  if (!list_text) return showToast("文本清单不能为空", "err");
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
      showToast("文本清单查重完成");
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
    const isChecked = prevState.has(rowKey) ? prevState.get(rowKey) : !r.existing;
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td data-label="选择"><input type="checkbox" class="sel" data-key="${esc(rowKey)}" data-uri="${esc(r.uri || "")}" data-existing="${r.existing ? "1" : "0"}" ${isChecked ? "checked" : ""} aria-label="选择 ${esc(r.name)}"></td>` +
      `<td data-label="#" class="is-num">${esc(r.position)}</td>` +
      `<td data-label="歌名" title="${esc(r.name)}"><strong>${esc(r.name)}</strong></td>` +
      `<td data-label="歌手" title="${esc(art)}">${esc(art || "—")}</td>` +
      `<td data-label="时长" class="is-num">${fmtDur(r.duration_ms)}</td>` +
      `<td data-label="状态"><span class="fc-chip ${r.existing ? "fc-chip--ok" : "fc-chip--primary"}">${r.existing ? "已有" : "新曲"}</span></td>`;
    tb.appendChild(tr);
  });
  if (shown === 0) {
    tb.innerHTML = `<tr><td colspan="6" class="fc-empty">没有匹配的曲目</td></tr>`;
  }
  $("#track-summary").textContent = `共 ${loadedRecords.length} 首 · 新曲 ${loadedRecords.length - exists} · 已有 ${exists}`;
  updateSelCount();
}

async function loadTracks(path) {
  tracksPath = path;
  const d = await api("/api/tracks?path=" + encodeURIComponent(path));
  loadedRecords = d.records || [];
  $("#tracks-card").hidden = false;
  $("#tracks tbody").innerHTML = "";
  renderTracksTable();
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
  if (!tracksPath) return showToast("请先导入歌单", "err");
  const allCbs = [...document.querySelectorAll("#tracks .sel")];
  const checkedCbs = allCbs.filter((c) => c.checked);
  if (checkedCbs.length === 0) return showToast("请至少勾选一首曲目再下载", "err");

  const body = {
    tracks: tracksPath,
    source: $("#source").value,
    include_existing: $("#inc-ex").checked,
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
      : '<div class="fc-hint" style="padding:12px;text-align:center;">该目录下暂无子文件夹，可直接点击「选择此目录」</div>';
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
      showToast(`默认曲库已切换并保存：${res.music_dir}`, "ok");
    } catch (e) {
      showToast(e.message, "err");
    }
    return;
  }
  if (dirTargetInput && $(dirTargetInput)) {
    $(dirTargetInput).value = chosen;
    showToast(`已选定目录：${chosen}`, "ok");
  }
  $("#dir-dialog").close();
};
$("#dir-cancel").onclick = () => $("#dir-dialog").close();
$("#dir-close").onclick = () => $("#dir-dialog").close();
$("#btn-reset-dir").onclick = () => {
  $("#dl-dir").value = "";
  showToast("已恢复为默认曲库目录");
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
  $("#hero-dir").textContent = d.music_dir ? `曲库：${d.music_dir}` : "";
  if ($("#sb-lib-dir")) $("#sb-lib-dir").textContent = d.music_dir || "";
  if (d.music_dir && $("#dl-dir")) {
    $("#dl-dir").placeholder = `留空则保存到默认曲库（${d.music_dir}）`;
  }
  if (d.music_dir && $("#aud-dir")) {
    $("#aud-dir").placeholder = `留空则扫描默认曲库（${d.music_dir}）`;
  }
  if (d.music_dir && $("#up-dir")) {
    $("#up-dir").placeholder = `留空则扫描默认曲库（${d.music_dir}）`;
  }

  if (active) {
    card.classList.add("is-running");
    $("#hero-chip").className = "fc-chip fc-chip--primary";
    $("#hero-chip-text").textContent = active.paused ? "已暂停" : `${TYPE_NAME[active.type] || active.type}中`;
    $("#hero-headline").textContent = active.current?.name || active.summary || `${TYPE_NAME[active.type] || active.type}执行中…`;
    const pct = active.total > 0 ? Math.min(100, Math.round((active.progress.done * 100) / active.total)) : 0;
    $("#hero-progress").textContent = active.total > 0 ? `${active.progress.done} / ${active.total} (${pct}%)` : "处理中";
    btn.setAttribute("aria-pressed", String(!active.paused));
    icon.innerHTML = active.paused
      ? `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>`
      : `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`;
  } else {
    card.classList.remove("is-running");
    $("#hero-chip").className = "fc-chip fc-chip--ok";
    $("#hero-chip-text").textContent = "就绪";
    $("#hero-headline").textContent = tracksPath ? `已加载歌单 (${loadedRecords.length} 首)，随时可下载` : "准备导入歌单或文本清单";
    $("#hero-progress").textContent = `历史任务 ${(d.jobs || []).length} 条`;
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
      showToast(running.paused ? "已恢复下载任务" : "将在当前曲目完成后暂停");
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
    const L = d.library || { total: 0, flac: 0, mp3: 0, ogg: 0 };
    const flacPct = L.total > 0 ? Math.round((L.flac * 100) / L.total) : 0;
    const lossyPct = L.total > 0 ? Math.max(0, 100 - flacPct) : 0;

    $("#sb-lib-total").innerHTML = `<strong>${L.total}</strong> 首曲目`;
    $("#sb-lib-sub").textContent = `FLAC ${L.flac} · MP3 ${L.mp3} · OGG ${L.ogg}`;
    $("#topbar-sub").textContent = `曲库 ${L.total} 首 · FLAC ${L.flac} (${flacPct}%)`;
    $("#stat-flac-num").textContent = String(L.flac);
    $("#stat-flac-pct").textContent = flacPct + "%";
    $("#stat-lib-sub").textContent = `MP3 ${L.mp3} · OGG ${L.ogg} · 共 ${L.total} 首`;
    $("#bar-flac").style.width = flacPct + "%";
    $("#bar-lossy").style.width = lossyPct + "%";

    lastJobs = d.jobs || [];
    const running = lastJobs.filter((j) => j.status === "running" || j.status === "queued");
    $("#nav-jobs-badge").textContent = running.length > 0 ? String(running.length) : "";
    $("#jobstat").textContent = running.length > 0
      ? `进行中 ${running.length} · ${TYPE_NAME[running[0].type] || running[0].type}`
      : "空闲";
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
    box.innerHTML = `<div class="fc-empty">还没有任务 —— 前往「歌单导入」发起查重与下载</div>`;
    return;
  }
  box.innerHTML = "";
  jobs.forEach((j) => {
    const chipCls = j.status === "running" ? "fc-chip--primary" : j.status === "done" ? "fc-chip--ok" :
                    j.status === "error" ? "fc-chip--error" : "";
    const st = j.status === "running" ? "进行中" : j.status === "queued" ? "排队中" :
               j.status === "done" ? "已完成" : "失败";
    const pct = j.total > 0 ? Math.min(100, Math.round((j.progress.done * 100) / j.total)) : 0;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fc-jobcard" + (j.id === activeJobId ? " is-selected" : "");
    btn.dataset.id = j.id;
    btn.innerHTML =
      `<div class="fc-jobcard__top">` +
      `<span class="fc-jobcard__name">${esc(TYPE_NAME[j.type] || j.type)}</span>` +
      `<span class="fc-chip ${chipCls}">${st}</span>` +
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
    $("#joblog-title").textContent = `作业日志 · ${TYPE_NAME[j.type] || j.type}`;
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
    const STATUS_LABEL = {
      downloaded: "下载成功",
      already_exists: "已存在跳过",
      skipped: "手动跳过",
      low_confidence: "未匹配(低置信度，未下载)",
      no_result: "未搜到结果",
      no_source: "无可用音源",
      search_failed: "搜索失败",
      failed: "下载失败",
    };
    if (scEntries.length) {
      const scHtml = scEntries.map(([k, v]) => {
        const cls = /fail|err/i.test(k)
          ? "fc-chip--error"
          : (k === "downloaded" || k === "upgraded" || k === "ok" || k === "pass" ? "fc-chip--ok" : "fc-chip--warn");
        return `<span class="fc-chip ${cls} fc-tabular">${esc(STATUS_LABEL[k] || k)}：${v}</span>`;
      }).join("");
      $("#job-stats-row").innerHTML = scHtml + (j.music_dir ? `<span class="fc-chip fc-mono">目标：${esc(j.music_dir)}</span>` : "");
      $("#job-stats-row").hidden = false;
    } else if (j.music_dir) {
      $("#job-stats-row").innerHTML = `<span class="fc-chip fc-mono">目标：${esc(j.music_dir)}</span>`;
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
    if (showCtl) {
      $("#btn-pause").textContent = j.paused ? "▶ 继续" : "⏸ 暂停";
      $("#btn-pause").dataset.paused = j.paused ? "1" : "";
      const txt = j.current && j.current.name
        ? (j.paused ? "已暂停（当前曲目完成后停下）" : "正在处理：" + j.current.name)
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
        else showToast("作业执行失败，请查看日志详情", "err");
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
    () => showToast("日志已复制到剪贴板"),
    () => showToast("复制失败", "err")
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
    showToast("已请求跳过当前曲目");
  } catch (e) { showToast(e.message, "err"); }
};

/* ---------- Upgrade & Audit ---------- */
let upgradeQueueItems = []; // [{ name, tag, checked }]
let auditCandidateFiles = [];
let auditSelectedFiles = new Set();

function renderUpgradeQueue() {
  const kw = ($("#up-queue-filter")?.value || "").toLowerCase();
  const checkedCount = upgradeQueueItems.filter((x) => x.checked).length;
  $("#up-queue-count").textContent = `${checkedCount} / ${upgradeQueueItems.length} 个文件`;
  $("#up-sel-count").textContent = String(checkedCount);

  const shown = upgradeQueueItems.filter((x) => !kw || x.name.toLowerCase().includes(kw));
  if (!upgradeQueueItems.length) {
    $("#up-queue-list").innerHTML = '<div class="fc-empty">待升级清单为空 —— 请在上方选择目录「扫描载入清单」，或从「质量审计」传入不合格文件</div>';
    return;
  }
  if (!shown.length) {
    $("#up-queue-list").innerHTML = '<div class="fc-hint" style="padding:12px;text-align:center;">没有匹配过滤关键词的待升级文件</div>';
    return;
  }
  $("#up-queue-list").innerHTML = shown.map((item) =>
    `<div class="fc-dir-item" style="justify-content:space-between;">` +
      `<label class="fc-row" style="gap:8px;flex:1;min-width:0;cursor:pointer;">` +
        `<input type="checkbox" class="up-q-cb" data-name="${esc(item.name)}" ${item.checked ? "checked" : ""}>` +
        `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(item.name)}">${esc(item.name)}</span>` +
      `</label>` +
      `<div class="fc-row" style="gap:6px;flex:none;">` +
        `<span class="fc-chip">${esc(item.tag)}</span>` +
        `<button type="button" class="fc-btn fc-btn--sm fc-btn--tonal up-q-del" data-name="${esc(item.name)}" aria-label="移除 ${esc(item.name)}">×</button>` +
      `</div>` +
    `</div>`
  ).join("");
}

function sendAuditFilesToUpgrade(names) {
  if (!names.length) return showToast("没有可传入升级的文件", "err");
  const seen = new Set();
  upgradeQueueItems = [];
  for (const n of names) {
    if (n && !seen.has(n)) {
      seen.add(n);
      upgradeQueueItems.push({ name: n, tag: "审计导入", checked: true });
    }
  }
  const srcDir = (auditData && auditData.music_dir) || ($("#aud-dir")?.value || "").trim();
  if (srcDir && $("#up-dir")) $("#up-dir").value = srcDir;
  renderUpgradeQueue();
  showTab("upgrade");
  showToast(`已将 ${upgradeQueueItems.length} 个文件传入待升级清单`, "ok");
}

$("#up-queue-filter").oninput = renderUpgradeQueue;
$("#up-queue-list").onchange = (e) => {
  if (!e.target.classList.contains("up-q-cb")) return;
  const item = upgradeQueueItems.find((x) => x.name === e.target.dataset.name);
  if (item) item.checked = e.target.checked;
  const checkedCount = upgradeQueueItems.filter((x) => x.checked).length;
  $("#up-queue-count").textContent = `${checkedCount} / ${upgradeQueueItems.length} 个文件`;
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
  showToast("已清空待升级清单");
};
$("#btn-up-scan").onclick = async () => {
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
    showToast(`已载入 ${upgradeQueueItems.length} 个待升级文件`, upgradeQueueItems.length ? "ok" : "");
  } catch (e) { showToast(e.message, "err"); }
};

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
  $("#aud-pick-summary").textContent = `已选 ${auditSelectedFiles.size} / ${auditCandidateFiles.length} 个文件`;
  $("#aud-pick-list").innerHTML = shown.map((name) => {
    const chk = auditSelectedFiles.has(name) ? "checked" : "";
    return `<label class="fc-dir-item"><input type="checkbox" class="aud-pick-cb" data-name="${esc(name)}" ${chk}> <span>${esc(name)}</span></label>`;
  }).join("") || '<div class="fc-hint" style="padding:10px;text-align:center;">目录下没有匹配的 .flac 文件</div>';
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
  $("#aud-pick-summary").textContent = `已选 ${auditSelectedFiles.size} / ${auditCandidateFiles.length} 个文件`;
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
    document.querySelectorAll("#up-ext-seg .fc-segmented__btn").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    $("#up-ext").value = b.dataset.ext;
  };
});

$("#btn-up").onclick = async () => {
  const picked = upgradeQueueItems.filter((x) => x.checked).map((x) => x.name);
  if (!picked.length) return showToast("请先扫描载入或从质量审计传入待升级文件", "err");
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
      showToast("曲库质量审计完成");
    });
    showTab("jobs");
  } catch (e) { showToast(e.message, "err"); }
};

applyTheme();
refreshState();
setInterval(refreshState, 2500);
</script>
</body>
</html>
"""
