import os
import time
import logging
from concurrent import futures

import grpc
import pandas as pd
from pyrosm import OSM
from postal.expand import expand_address
from postal.parser import parse_address
from autocorrect import Speller
import bm25s

import geocode_pb2
import geocode_pb2_grpc

# -----------------------------------------------------------------------------
# Basic logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Address / BM25 helpers
# -----------------------------------------------------------------------------

ADDR_COLS = [
    "addr:country",
    "addr:postcode",
    "addr:city",
    "addr:place",
    "addr:street",
    "addr:housenumber",
    "addr:housename",
]


def build_address(row: pd.Series) -> str | None:
    """Build a human-readable address string from OSM address tags."""
    if pd.notnull(row.get("addr:full")):
        return str(row["addr:full"])

    parts = []
    for col in ADDR_COLS:
        val = row.get(col)
        if pd.notnull(val) and val != "":
            parts.append(str(val))

    return ", ".join(parts) if parts else None


def normalized_forms(text: str) -> list[str]:
    """Libpostal expansions limited to Russian; fallback to original text."""
    if not isinstance(text, str):
        return []
    try:
        expansions = expand_address(text, languages=["ru"]) or []
    except Exception:
        expansions = []
    if not expansions:
        expansions = [text]
    return expansions


def parse_libpostal_components(text: str) -> dict:
    """
    Convert libpostal parse_address result into a dict:
    {label: component}.
    """
    try:
        parts = parse_address(text)
    except Exception:
        return {}

    # parse_address returns list of (component, label)
    return {label: component for component, label in parts}


def setup_geocoder(pbf_path: str):
    """
    Setup function:
    - loads OSM PBF
    - extracts buildings
    - builds address index
    - builds BM25 retriever
    Returns: (index_df, retriever, spell)
    """
    logger.info("Loading OSM data from %s", pbf_path)
    osm = OSM(pbf_path)
    buildings = osm.get_buildings()

    df = buildings.copy()
    # Primary key
    df["building_pk"] = df.index

    # Geometry → lon/lat
    df["lon"] = df.geometry.centroid.x
    df["lat"] = df.geometry.centroid.y

    # Build raw address
    df["raw_address"] = df.apply(build_address, axis=1)
    df = df[df["raw_address"].notna()].reset_index(drop=True)

    # Build index table: one row per (building, normalized_string)
    index_rows = []
    for idx, row in df.iterrows():
        expansions = normalized_forms(row["raw_address"])
        for norm in set(expansions):
            index_rows.append(
                {
                    "building_pk": idx,
                    "norm_address": norm,
                    "lon": row["lon"],
                    "lat": row["lat"],
                }
            )

    index_df = pd.DataFrame(index_rows)

    # BM25 index
    corpus = index_df["norm_address"].tolist()
    corpus_tokens = bm25s.tokenize(corpus)

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    spell = Speller("ru")

    logger.info("Geocoder index built: %d documents", len(index_df))
    return index_df, retriever, spell


def process_query(
    query: str,
    index_df: pd.DataFrame,
    retriever: bm25s.BM25,
    spell: Speller,
    limit: int = 10,
):
    """
    Process function:
    - expands & spell-corrects query
    - runs BM25 retrieval
    - returns list of matches with normalized scores [0,1]
    Each match: {
        "rank", "score", "norm_address", "building_pk", "lon", "lat"
    }
    """
    if not query:
        return []

    try:
        expansions = expand_address(query, languages=["ru"]) or []
    except Exception:
        expansions = []

    if not expansions:
        expansions = [query]

    q_norms = [spell(text) for text in expansions]

    # Use first normalized variant for now
    query_str = q_norms[0]
    query_tokens = bm25s.tokenize(query_str)

    # Retrieve
    k = max(limit, 1)
    results, scores = retriever.retrieve(query_tokens, k=k)

    if results.size == 0:
        return []

    raw_scores = scores[0]
    max_score = float(raw_scores.max()) if raw_scores.size > 0 else 0.0

    matches = []
    n_results = results.shape[1]
    for i in range(n_results):
        doc_id = int(results[0, i])
        raw_score = float(raw_scores[i])
        norm_score = raw_score / max_score if max_score > 0 else 0.0

        row = index_df.iloc[doc_id]
        matches.append(
            {
                "rank": i + 1,
                "score": norm_score,
                "norm_address": row["norm_address"],
                "building_pk": int(row["building_pk"]),
                "lon": float(row["lon"]),
                "lat": float(row["lat"]),
            }
        )

    return matches


# -----------------------------------------------------------------------------
# gRPC servicer
# -----------------------------------------------------------------------------

class GeocodeServicer(geocode_pb2_grpc.GeocodeServiceServicer):
    """
    BM25-based geocoder backed by OSM buildings.
    Uses the API scheme from the provided prototype (SearchAddress, HealthCheck).
    """

    def __init__(self, pbf_path: str | None = None):
        self.start_time = time.time()
        self.pbf_path = pbf_path or os.environ.get("PBF_PATH", "10-moscow.osm.pbf")

        self.index_df, self.retriever, self.spell = setup_geocoder(self.pbf_path)

    def SearchAddress(self, request, context):
        start_time = time.time()

        # Prefer normalized_query, fallback to original_query
        query = request.normalized_query or request.original_query
        query = query.strip()

        if not query:
            exec_ms = int((time.time() - start_time) * 1000)
            return geocode_pb2.SearchAddressResponse(
                status=geocode_pb2.ResponseStatus(
                    code=geocode_pb2.StatusCode.OK,
                    message="Empty query",
                ),
                searched_address="",
                objects=[],
                total_found=0,
                metadata=geocode_pb2.ResponseMetadata(
                    execution_time_ms=exec_ms,
                    timestamp=int(time.time()),
                    engine_version="bm25-osm-1.0",
                ),
            )

        limit = request.limit if request.limit > 0 else 10
        matches = process_query(
            query,
            self.index_df,
            self.retriever,
            self.spell,
            limit=limit,
        )

        # Convert BM25 matches to AddressObject list
        objects = []
        for m in matches:
            components = parse_libpostal_components(m["norm_address"])

            locality = components.get("city", "")
            street = components.get("road", "")
            number = components.get("house_number", "")
            postal_code = components.get("postcode", "")
            district = components.get("suburb", "") or components.get(
                "city_district", ""
            )

            additional_info = geocode_pb2.AdditionalInfo(
                postal_code=postal_code,
                district=district,
                full_address=m["norm_address"],
                object_id=str(m["building_pk"]),
            )

            obj = geocode_pb2.AddressObject(
                locality=locality,
                street=street,
                number=number,
                lon=m["lon"],
                lat=m["lat"],
                score=m["score"],
                additional_info=additional_info,
            )
            objects.append(obj)

        # Apply options (basic)
        if request.options:
            # Min score threshold
            if request.options.min_score_threshold > 0:
                thr = request.options.min_score_threshold
                objects = [o for o in objects if o.score >= thr]

            # Locality filter (simple substring match)
            if request.options.locality_filter:
                lf = request.options.locality_filter.strip().lower()
                if lf:
                    objects = [
                        o for o in objects if lf in o.locality.lower()
                    ]

            # enable_fuzzy_search is currently ignored; BM25 already does fuzzy-ish matching.

        # Enforce limit again after filtering
        if request.limit > 0:
            objects = objects[: request.limit]

        exec_ms = int((time.time() - start_time) * 1000)
        logger.info("SearchAddress '%s' -> %d results in %d ms", query, len(objects), exec_ms)

        return geocode_pb2.SearchAddressResponse(
            status=geocode_pb2.ResponseStatus(
                code=geocode_pb2.StatusCode.OK,
                message="OK",
            ),
            searched_address=request.normalized_query or query,
            objects=objects,
            total_found=len(objects),
            metadata=geocode_pb2.ResponseMetadata(
                execution_time_ms=exec_ms,
                timestamp=int(time.time()),
                engine_version="bm25-osm-1.0",
            ),
        )

    def HealthCheck(self, request, context):
        uptime = int(time.time() - self.start_time)
        return geocode_pb2.HealthCheckResponse(
            status=geocode_pb2.HealthStatus.HEALTHY,
            version="bm25-osm-1.0",
            uptime_seconds=uptime,
        )


# -----------------------------------------------------------------------------
# Server bootstrap
# -----------------------------------------------------------------------------

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    geocode_pb2_grpc.add_GeocodeServiceServicer_to_server(
        GeocodeServicer(), server
    )

    port = os.environ.get("GRPC_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info("gRPC geocoder server started on port %s", port)

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
