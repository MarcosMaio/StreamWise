"use client";

import { useEffect, useState } from "react";

import {
  clearTonightContext,
  loadTonightContext,
  saveTonightContext,
  type Company,
  type Mood,
  type TimeBudget,
  type TonightContext,
} from "@/lib/tonight-context";

type TonightModePromptProps = {
  onChange: (context: TonightContext | null) => void;
};

export function TonightModePrompt({ onChange }: TonightModePromptProps) {
  const [enabled, setEnabled] = useState(false);
  const [timeBudget, setTimeBudget] = useState<TimeBudget>("medium");
  const [mood, setMood] = useState<Mood | "">("");
  const [company, setCompany] = useState<Company>("solo");

  useEffect(() => {
    const saved = loadTonightContext();
    if (saved) {
      setEnabled(true);
      if (saved.time_budget) setTimeBudget(saved.time_budget);
      if (saved.mood) setMood(saved.mood);
      if (saved.company) setCompany(saved.company);
      onChange(saved);
    }
  }, [onChange]);

  function applyContext(active: boolean) {
    setEnabled(active);
    if (!active) {
      clearTonightContext();
      onChange(null);
      return;
    }

    const context: TonightContext = {
      time_budget: timeBudget,
      company,
      ...(mood ? { mood } : {}),
    };
    saveTonightContext(context);
    onChange(context);
  }

  return (
    <section className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Tonight mode</h2>
          <p className="text-sm text-streamwise-muted">
            Tailor your For You feed to how much time you have and who is watching.
          </p>
        </div>
        <button
          type="button"
          onClick={() => applyContext(!enabled)}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            enabled
              ? "bg-streamwise-accent text-white"
              : "border border-white/10 text-streamwise-muted hover:text-white"
          }`}
        >
          {enabled ? "Active" : "Enable"}
        </button>
      </div>

      {enabled ? (
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-1 text-sm">
            <span className="text-streamwise-muted">Time budget</span>
            <select
              value={timeBudget}
              onChange={(event) => {
                const value = event.target.value as TimeBudget;
                setTimeBudget(value);
                const context: TonightContext = {
                  time_budget: value,
                  company,
                  ...(mood ? { mood } : {}),
                };
                saveTonightContext(context);
                onChange(context);
              }}
              className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
            >
              <option value="short">Short (movie)</option>
              <option value="medium">Flexible</option>
              <option value="long">Long (series)</option>
            </select>
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-streamwise-muted">Mood</span>
            <select
              value={mood}
              onChange={(event) => {
                const value = event.target.value as Mood | "";
                setMood(value);
                const context: TonightContext = {
                  time_budget: timeBudget,
                  company,
                  ...(value ? { mood: value } : {}),
                };
                saveTonightContext(context);
                onChange(context);
              }}
              className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
            >
              <option value="">Any</option>
              <option value="funny">Funny</option>
              <option value="intense">Intense</option>
              <option value="cozy">Cozy</option>
              <option value="thoughtful">Thoughtful</option>
            </select>
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-streamwise-muted">Company</span>
            <select
              value={company}
              onChange={(event) => {
                const value = event.target.value as Company;
                setCompany(value);
                const context: TonightContext = {
                  time_budget: timeBudget,
                  company: value,
                  ...(mood ? { mood } : {}),
                };
                saveTonightContext(context);
                onChange(context);
              }}
              className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
            >
              <option value="solo">Solo</option>
              <option value="date">Date night</option>
              <option value="family">Family</option>
            </select>
          </label>
        </div>
      ) : null}
    </section>
  );
}
