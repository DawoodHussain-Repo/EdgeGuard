# UI Context - EdgeGuard-AI Monitoring Dashboard

## Theme

Dark industrial command-center workspace (`#0b0f19` base). Low eye-strain, high-contrast visual hierarchy designed for security and safety operation control centers. Glassmorphism panel styling with vivid status indicators.

## Colors

All UI components use custom CSS variables for consistency:

| Role | CSS Variable | Value |
| ---- | ------------ | ----- |
| Page Background | `--bg-base` | `#080b11` |
| Surface Panel | `--bg-surface` | `#111827` |
| Surface Card/Header | `--bg-surface-elevated` | `#1f293d` |
| Primary Text | `--text-primary` | `#f3f4f6` |
| Muted Text | `--text-muted` | `#9ca3af` |
| Primary Accent (Cyan/Emerald) | `--accent-primary` | `#06b6d4` |
| Safety Success (Green) | `--state-success` | `#10b981` |
| Violation Error (Red) | `--state-error` | `#ef4444` |
| Warning / PPE Missing (Amber) | `--state-warning` | `#f59e0b` |
| Border Default | `--border-default` | `#1f2937` |
| Border Highlight | `--border-highlight` | `#374151` |

## Typography

| Role | Font | Variable |
| ---- | ---- | -------- |
| UI Header / Body | Inter, system-ui, sans-serif | `--font-sans` |
| Telemetry / Code / FPS | JetBrains Mono, monospace | `--font-mono` |

## Border Radius

| Context | Class | Value |
| ------- | ----- | ----- |
| Badges / Pills | `rounded-full` | `9999px` |
| Metrics Cards | `rounded-lg` | `8px` |
| Main Video Player | `rounded-xl` | `12px` |
| Control Panels | `rounded-xl` | `12px` |

## Layout Patterns

- **Top Navigation**: Fixed dark header with live status pulse dot, system metrics indicator (FPS, Latency), and quick action buttons.
- **Main Dashboard Grid**: 
  - Left Column (70%): Live Annotated Video Feed Player (`/api/v1/stream`) with HUD overlay toggles & Interactive ROI polygon drawer canvas.
  - Right Column (30%): Real-Time Telemetry Stats Cards (Active Workers, Compliant Count, Non-Compliant Count, Violations), Live Violation Alert Stream feed, ROI configuration panel.
- **Responsive**: Mobile and desktop responsive layout with dynamic grid column collapse.

## Icons

Lucide SVG icons for clean vector rendering (Shield, AlertTriangle, Users, Activity, Eye, Settings, Video).
