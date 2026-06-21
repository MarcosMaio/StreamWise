"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError } from "@/lib/api-client";
import { register } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await register(email, password, displayName);
      router.push("/");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("This email is already registered.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Please check your details. Password must be at least 8 characters.");
      } else {
        setError("Unable to create account. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6 rounded-xl border border-white/10 bg-streamwise-surface p-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Create account</h1>
        <p className="text-sm text-streamwise-muted">Join StreamWise to discover what to watch next.</p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block space-y-1">
          <span className="text-sm text-streamwise-muted">Display name</span>
          <input
            type="text"
            required
            autoComplete="name"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2 outline-none focus:border-streamwise-accent"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-streamwise-muted">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2 outline-none focus:border-streamwise-accent"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-streamwise-muted">Password</span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2 outline-none focus:border-streamwise-accent"
          />
        </label>

        {error ? <p className="text-sm text-red-400">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-streamwise-accent px-4 py-2 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p className="text-sm text-streamwise-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-streamwise-accent hover:underline">
          Sign in
        </Link>
      </p>
    </section>
  );
}
