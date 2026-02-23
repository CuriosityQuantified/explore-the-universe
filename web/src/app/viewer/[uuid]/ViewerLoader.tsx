"use client";

import dynamic from "next/dynamic";
import type {
  WcsParams,
  TileMetadata,
  ObservationDetail,
} from "@/types/observation";

const ViewerClient = dynamic(() => import("./ViewerClient"), { ssr: false });

interface ViewerLoaderProps {
  observationUuid: string;
  wcsParams: WcsParams;
  tileMetadata: TileMetadata;
  tileBaseUrl: string;
  observationDetail: ObservationDetail;
}

export default function ViewerLoader(props: ViewerLoaderProps) {
  return <ViewerClient {...props} />;
}
