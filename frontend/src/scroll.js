/** Smooth-scrolls the form pane to a section (used by the KPI cards and the view tabs). */
export function goTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
