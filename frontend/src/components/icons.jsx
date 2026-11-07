const PATHS = {
  ring: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></>,
  undo: <><path d="M9 14L4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 010 11H11" /></>,
  check: <path d="M5 12l4 4 10-10" />,
  plus: <path d="M12 5v14M5 12h14" />,
  list: <path d="M4 6h16M4 12h10M4 18h16" />,
  menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  chevronLeft: <path d="M15 6l-6 6 6 6" />,
  chevronRight: <path d="M9 6l6 6-6 6" />,
  doc: <><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5" /></>,
  flask: <><path d="M9 3h6M10 3v6l-5 9a2 2 0 001.8 3h10.4a2 2 0 001.8-3l-5-9V3" /><path d="M7.5 15h9" /></>,
  layers: <><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
  shield: <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></>,
  chart: <path d="M4 20V10M10 20V4M16 20v-8M22 20H2" />,
  alert: <><path d="M12 3l10 18H2L12 3z" /><path d="M12 10v5M12 18v.01" /></>,
  bang: <path d="M12 7v6M12 17v.01" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.01" /></>,
  fish: <path d="M3 12h14M17 12l4-5M17 12l4 5M7 12L4 7M7 12l-3 5" />,
  clip: <path d="M21 11l-9 9a5 5 0 01-7-7l9-9a3.5 3.5 0 015 5l-9 9a2 2 0 01-3-3l8-8" />,
  send: <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />,
  sparkle: <path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6z" />,
  chat: <path d="M21 12a8 8 0 01-11.6 7.1L4 20l1-4.6A8 8 0 1121 12z" />,
}

/** Small inline icon set. Decorative by default: pair with a text label or aria-label on the parent. */
export function Icon({ name, size = 16, stroke = 2, fill = 'none' }) {
  return (
    <svg
      aria-hidden="true" width={size} height={size} viewBox="0 0 24 24"
      fill={fill} stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
    >
      {PATHS[name]}
    </svg>
  )
}
