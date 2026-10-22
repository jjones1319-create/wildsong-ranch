/** Fills `{placeholders}` in a player-facing template. Missing values are left as they are, so a typo shows up in testing. */
export function fill(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) => (key in vars ? String(vars[key]) : whole))
}
