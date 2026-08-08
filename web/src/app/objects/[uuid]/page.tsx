import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchObjectDetail } from "@/lib/api";
import { GraphPanel } from "./GraphPanel";
import { MaskOverlay } from "./MaskOverlay";

interface ObjectPageProps {
  params: Promise<{ uuid: string }>;
}

export default async function ObjectPage({ params }: ObjectPageProps) {
  const { uuid } = await params;

  let object;
  try {
    object = await fetchObjectDetail(uuid);
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    if (msg === "NOT_FOUND") {
      notFound();
    }
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-2">Error Loading Object</h1>
          <p className="text-zinc-400">{msg}</p>
        </div>
      </div>
    );
  }

  const clf = object.latest_classification;

  return (
    <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold font-mono break-all">
          {object.catalog_object_name ?? object.object_uuid}
        </h1>
        {object.classified_object_type && (
          <p className="text-zinc-400 mt-1 capitalize">
            {object.classified_object_type.replace(/_/g, " ")}
          </p>
        )}
      </div>

      {/* Cutout image + segmentation mask overlay */}
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Cutout</h2>
        <div
          style={{ position: "relative", display: "inline-block" }}
          className="rounded overflow-hidden bg-zinc-900"
        >
          {object.cutout_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={object.cutout_url}
              alt={`Cutout of ${object.catalog_object_name ?? object.object_uuid}`}
              className="block max-w-full"
            />
          ) : (
            <div className="w-64 h-64 flex items-center justify-center text-zinc-500 text-sm">
              No cutout available
            </div>
          )}
          {object.segmentation_mask_rle && (
            <MaskOverlay rle={object.segmentation_mask_rle} />
          )}
        </div>
      </section>

      {/* Classification panel */}
      {clf && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Classification</h2>
          <div className="bg-zinc-900 rounded p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-400">Predicted type</span>
              <span className="capitalize">{clf.predicted_object_type.replace(/_/g, " ")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Confidence</span>
              <span>{(clf.classification_confidence_score * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Model version</span>
              <span className="font-mono">{clf.ml_model_version}</span>
            </div>
            {clf.classified_at && (
              <div className="flex justify-between">
                <span className="text-zinc-400">Classified</span>
                <span>{new Date(clf.classified_at).toLocaleString()}</span>
              </div>
            )}
          </div>
          {clf.is_anomaly_flagged && clf.anomaly_explanation && (
            <div
              role="alert"
              className="border border-amber-500 bg-amber-950/40 rounded p-3 text-sm text-amber-200"
            >
              <span className="font-semibold">Anomaly flagged: </span>
              {clf.anomaly_explanation}
            </div>
          )}
        </section>
      )}

      {/* Catalog cross-matches */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Catalog Cross-matches</h2>
        {object.cross_matches.length === 0 ? (
          <p className="text-zinc-500 text-sm">No cross-matches found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-zinc-700">
                  <th className="text-left py-2 pr-4 text-zinc-400 font-medium">Catalog</th>
                  <th className="text-left py-2 pr-4 text-zinc-400 font-medium">Source ID</th>
                  <th className="text-right py-2 pr-4 text-zinc-400 font-medium">Sep. (arcsec)</th>
                  <th className="text-left py-2 text-zinc-400 font-medium">External link</th>
                </tr>
              </thead>
              <tbody>
                {object.cross_matches.map((m) => (
                  <tr key={m.match_uuid} className="border-b border-zinc-800">
                    <td className="py-2 pr-4">{m.catalog_name}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{m.catalog_source_id}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {m.angular_separation_arcseconds.toFixed(3)}
                    </td>
                    <td className="py-2">
                      {m.external_url ? (
                        <a
                          href={m.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:underline"
                        >
                          View in {m.catalog_name} ↗
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Physical properties */}
      {object.physical_properties &&
        Object.keys(object.physical_properties).length > 0 && (
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Physical Properties</h2>
            <dl className="bg-zinc-900 rounded p-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {Object.entries(object.physical_properties)
                .filter(([, v]) => v !== null && v !== undefined)
                .map(([key, value]) => (
                  <div key={key} className="flex justify-between col-span-1">
                    <dt className="text-zinc-400 font-mono">{key}</dt>
                    <dd className="tabular-nums">{String(value)}</dd>
                  </div>
                ))}
            </dl>
          </section>
        )}

      {/* Observation context */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Observation Context</h2>
        <div className="bg-zinc-900 rounded p-4 text-sm space-y-2">
          <div className="flex justify-between">
            <span className="text-zinc-400">RA</span>
            <span className="font-mono tabular-nums">
              {object.sky_coordinate_ra_degrees.toFixed(6)}°
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Dec</span>
            <span className="font-mono tabular-nums">
              {object.sky_coordinate_dec_degrees.toFixed(6)}°
            </span>
          </div>
          {object.catalog_magnitude !== null && (
            <div className="flex justify-between">
              <span className="text-zinc-400">Magnitude</span>
              <span className="tabular-nums">{object.catalog_magnitude.toFixed(2)}</span>
            </div>
          )}
          {object.catalog_redshift !== null && (
            <div className="flex justify-between">
              <span className="text-zinc-400">Redshift</span>
              <span className="font-mono tabular-nums">{object.catalog_redshift}</span>
            </div>
          )}
        </div>
        <Link
          href={`/viewer/${object.source_observation_uuid}`}
          className="inline-block text-sm text-blue-400 hover:underline"
        >
          ← View parent observation in sky viewer
        </Link>
      </section>

      {/* Export Data */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Export Data</h2>
        <div className="flex flex-wrap gap-3">
          <a
            href={`/api/objects/${object.object_uuid}/export/fits`}
            download={`${object.catalog_object_name ?? object.object_uuid}.fits`}
            className="inline-block rounded bg-zinc-800 px-4 py-2 text-sm hover:bg-zinc-700 transition-colors"
          >
            Download FITS
          </a>
          <a
            href={`/api/objects/${object.object_uuid}/export/csv`}
            download={`${object.catalog_object_name ?? object.object_uuid}.csv`}
            className="inline-block rounded bg-zinc-800 px-4 py-2 text-sm hover:bg-zinc-700 transition-colors"
          >
            Download CSV
          </a>
          <a
            href={`/api/objects/${object.object_uuid}/export/votable`}
            download={`${object.catalog_object_name ?? object.object_uuid}.votable`}
            className="inline-block rounded bg-zinc-800 px-4 py-2 text-sm hover:bg-zinc-700 transition-colors"
          >
            Download VOTable
          </a>
        </div>
      </section>

      {/* Knowledge graph */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">In the knowledge graph</h2>
        <GraphPanel uuid={uuid} />
      </section>
    </main>
  );
}
