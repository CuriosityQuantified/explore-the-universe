"use client";

import { useEffect, useState } from "react";

export function CatalogSummary() {
  const [counts, setCounts] = useState<{ objects: number; images_ready: number } | null>(null);
  useEffect(() => {
    fetch("/api/catalog/summary").then(r => r.ok ? r.json() : null).then(setCounts).catch(() => {});
  }, []);
  return (
    <div className="text-sm text-zinc-400 max-w-xl space-y-2">
      {counts && <p>{counts.objects.toLocaleString()} catalog objects · {counts.images_ready.toLocaleString()} survey images ready. More images are being added.</p>}
      <p>Catalog: <a className="text-blue-400 hover:underline" href="https://github.com/mattiaverga/OpenNGC">OpenNGC, Mattia Verga and contributors</a> (<a className="text-blue-400 hover:underline" href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>). Imagery: DSS2 / STScI, served through CDS Strasbourg.</p>
    </div>
  );
}
