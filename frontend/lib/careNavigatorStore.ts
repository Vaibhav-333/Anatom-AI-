// sessionStorage bridge for passing specialist auto-search context
// from the Results page to the Care Navigator page.

const STORAGE_KEY = "care_navigator_specialist";

export interface SpecialistSearchContext {
  specialist: string;
  condition: string;
}

export function saveSpecialistSearch(context: SpecialistSearchContext): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  } catch {
    // sessionStorage may be unavailable in SSR context; ignore
  }
}

export function loadSpecialistSearch(): SpecialistSearchContext | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SpecialistSearchContext) : null;
  } catch {
    return null;
  }
}

export function clearSpecialistSearch(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
