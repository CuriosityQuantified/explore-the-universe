"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { fetchObjectTypes, searchByName } from "@/lib/api";

type Tab = "name" | "coordinates" | "type";

export function SearchBar() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("name");

  // Name tab state
  const [nameInput, setNameInput] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);

  // Coordinates tab state
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [radius, setRadius] = useState("60");
  const [coordError, setCoordError] = useState<string | null>(null);

  // Type tab state
  const [types, setTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [typesLoading, setTypesLoading] = useState(false);

  // Load object types when type tab is first activated
  useEffect(() => {
    if (activeTab === "type" && types.length === 0) {
      setTypesLoading(true);
      fetchObjectTypes()
        .then((t) => {
          setTypes(t);
          if (t.length > 0) setSelectedType(t[0]);
        })
        .catch(() => {
          // Silent — empty dropdown is a valid degraded state
        })
        .finally(() => setTypesLoading(false));
    }
  }, [activeTab, types.length]);

  // --- Name search submit ---
  async function handleNameSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = nameInput.trim();
    if (!trimmed) return;

    setNameError(null);
    setNameLoading(true);
    try {
      const result = await searchByName(trimmed, 50, 0);
      if (result.results.length === 1) {
        router.push(`/objects/${result.results[0].object_uuid}`);
      } else {
        router.push(`/search?name=${encodeURIComponent(trimmed)}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setNameError(msg);
    } finally {
      setNameLoading(false);
    }
  }

  // --- Coordinates submit ---
  function handleConeSubmit(e: FormEvent) {
    e.preventDefault();
    setCoordError(null);
    const raNum = parseFloat(ra);
    const decNum = parseFloat(dec);
    const radNum = parseFloat(radius);
    if (isNaN(raNum) || isNaN(decNum) || isNaN(radNum)) {
      setCoordError("Please enter valid numbers for RA, Dec, and radius.");
      return;
    }
    if (raNum < 0 || raNum >= 360) {
      setCoordError("RA must be between 0 and 360 degrees.");
      return;
    }
    if (decNum < -90 || decNum > 90) {
      setCoordError("Dec must be between -90 and 90 degrees.");
      return;
    }
    if (radNum <= 0) {
      setCoordError("Radius must be a positive number.");
      return;
    }
    router.push(`/search?ra=${raNum}&dec=${decNum}&radius_arcsec=${radNum}`);
  }

  // --- Type submit ---
  function handleTypeSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedType) return;
    router.push(`/search?type=${encodeURIComponent(selectedType)}`);
  }

  const tabClass = (tab: Tab) =>
    `px-4 py-2 text-sm font-medium rounded-t border-b-2 transition-colors ${
      activeTab === tab
        ? "border-indigo-400 text-indigo-300 bg-zinc-800"
        : "border-transparent text-zinc-400 hover:text-zinc-200 bg-zinc-900"
    }`;

  return (
    <div className="w-full max-w-xl">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-700 mb-0">
        <button className={tabClass("name")} onClick={() => setActiveTab("name")}>
          Name
        </button>
        <button className={tabClass("coordinates")} onClick={() => setActiveTab("coordinates")}>
          Coordinates
        </button>
        <button className={tabClass("type")} onClick={() => setActiveTab("type")}>
          Type
        </button>
      </div>

      {/* Tab panels */}
      <div className="bg-zinc-800 rounded-b rounded-tr p-4">

        {/* Name tab */}
        {activeTab === "name" && (
          <form onSubmit={handleNameSubmit} className="flex flex-col gap-3">
            <label className="text-xs text-zinc-400 uppercase tracking-wide">
              Object name (e.g. NGC 1300, M87, Andromeda)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder="NGC 1300"
                className="flex-1 rounded bg-zinc-900 border border-zinc-600 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-400"
                disabled={nameLoading}
              />
              <button
                type="submit"
                disabled={nameLoading || !nameInput.trim()}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {nameLoading ? "Searching…" : "Search"}
              </button>
            </div>
            {nameError && (
              <p className="text-xs text-red-400">{nameError}</p>
            )}
          </form>
        )}

        {/* Coordinates tab */}
        {activeTab === "coordinates" && (
          <form onSubmit={handleConeSubmit} className="flex flex-col gap-3">
            <label className="text-xs text-zinc-400 uppercase tracking-wide">
              Sky coordinates + radius
            </label>
            <div className="grid grid-cols-3 gap-2">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-zinc-500">RA (deg)</span>
                <input
                  type="number"
                  step="any"
                  value={ra}
                  onChange={(e) => setRa(e.target.value)}
                  placeholder="49.92"
                  className="rounded bg-zinc-900 border border-zinc-600 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-400"
                />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-zinc-500">Dec (deg)</span>
                <input
                  type="number"
                  step="any"
                  value={dec}
                  onChange={(e) => setDec(e.target.value)}
                  placeholder="-19.41"
                  className="rounded bg-zinc-900 border border-zinc-600 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-400"
                />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-zinc-500">Radius (arcsec)</span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={radius}
                  onChange={(e) => setRadius(e.target.value)}
                  placeholder="60"
                  className="rounded bg-zinc-900 border border-zinc-600 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-400"
                />
              </div>
            </div>
            {coordError && (
              <p className="text-xs text-red-400">{coordError}</p>
            )}
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 self-end"
            >
              Search
            </button>
          </form>
        )}

        {/* Type tab */}
        {activeTab === "type" && (
          <form onSubmit={handleTypeSubmit} className="flex flex-col gap-3">
            <label className="text-xs text-zinc-400 uppercase tracking-wide">
              Object type
            </label>
            {typesLoading ? (
              <p className="text-sm text-zinc-500">Loading types…</p>
            ) : types.length === 0 ? (
              <p className="text-sm text-zinc-500">No classified objects in catalog yet.</p>
            ) : (
              <div className="flex gap-2">
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="flex-1 rounded bg-zinc-900 border border-zinc-600 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-indigo-400"
                >
                  {types.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button
                  type="submit"
                  disabled={!selectedType}
                  className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Browse
                </button>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
