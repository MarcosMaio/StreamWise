export type TimeBudget = "short" | "medium" | "long";
export type Mood = "funny" | "intense" | "cozy" | "thoughtful";
export type Company = "solo" | "date" | "family";

export type TonightContext = {
  time_budget?: TimeBudget;
  mood?: Mood;
  company?: Company;
};

export const TONIGHT_CONTEXT_KEY = "streamwise_tonight_context";

export function saveTonightContext(context: TonightContext): void {
  sessionStorage.setItem(TONIGHT_CONTEXT_KEY, JSON.stringify(context));
}

export function loadTonightContext(): TonightContext | null {
  const raw = sessionStorage.getItem(TONIGHT_CONTEXT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TonightContext;
  } catch {
    return null;
  }
}

export function clearTonightContext(): void {
  sessionStorage.removeItem(TONIGHT_CONTEXT_KEY);
}
