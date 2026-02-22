import { fetchObservation, fetchWcsParams, getTileUrl } from "@/lib/api";
import ViewerClient from "./ViewerClient";

interface ViewerPageProps {
  params: Promise<{ uuid: string }>;
}

/**
 * Server component for the sky viewer page at /viewer/[uuid].
 *
 * Fetches observation data and WCS parameters from the FastAPI backend
 * on the server, then passes them as props to the client-side ViewerClient
 * which renders the OpenSeadragon viewer and coordinate overlay.
 */
export default async function ViewerPage({ params }: ViewerPageProps) {
  const { uuid } = await params;

  try {
    const [observation, wcsParams] = await Promise.all([
      fetchObservation(uuid),
      fetchWcsParams(uuid),
    ]);

    if (!observation.tile_metadata) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-semibold mb-2">Tiles Not Ready</h1>
            <p className="text-zinc-400">
              Tile generation has not completed for observation{" "}
              <code className="text-sm bg-zinc-800 px-2 py-0.5 rounded font-mono">
                {uuid}
              </code>
            </p>
            <p className="text-zinc-500 text-sm mt-2">
              Status: {observation.pipeline_status}
            </p>
          </div>
        </div>
      );
    }

    const tileBaseUrl = getTileUrl(uuid);

    return (
      <ViewerClient
        observationUuid={uuid}
        wcsParams={wcsParams}
        tileMetadata={observation.tile_metadata}
        tileBaseUrl={tileBaseUrl}
        observationDetail={observation}
      />
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error";
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-2">
            Observation Not Found
          </h1>
          <p className="text-zinc-400">{message}</p>
          <p className="text-zinc-500 text-sm mt-4">
            UUID:{" "}
            <code className="bg-zinc-800 px-2 py-0.5 rounded font-mono">
              {uuid}
            </code>
          </p>
        </div>
      </div>
    );
  }
}
