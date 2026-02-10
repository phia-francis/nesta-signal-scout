from __future__ import annotations

import json
import logging
import random
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

import keywords as kw
from models import PolicyRequest, RadarRequest, ResearchRequest, UpdateSignalRequest
from services import (
    CrunchbaseService,
    GatewayResearchService,
    HorizonAnalyticsService,
    SearchService,
    ServiceError,
    SheetService,
    TopicModellingService,
)

app = FastAPI()

# ---------------------------------------------------------
# SECURITY CONFIGURATION: Explicit Allowed Origins
# ---------------------------------------------------------
origins = [
    "http://localhost:8000",  # Local Development
    "http://127.0.0.1:8000",  # Local Development (IP)
    "https://phia-francis.github.io",  # Your GitHub Pages Frontend
    "https://phia-francis.github.io/",  # Your GitHub Pages Frontend (Trailing slash)
    "https://nesta-signal-backend.onrender.com",  # Your Production Backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # STRICT LIST (No more "*")
    allow_credentials=True,  # Allowed because origins are explicit
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
app.mount("/static", StaticFiles(directory="static"), name="static")

search_svc = SearchService()
sheet_svc = SheetService()
analytics_svc = HorizonAnalyticsService()
gtr_svc = GatewayResearchService()
cb_svc = CrunchbaseService()
topic_svc = TopicModellingService()

MISSION_KEYWORDS = kw.MISSION_KEYWORDS
CROSS_CUTTING_KEYWORDS = kw.CROSS_CUTTING_KEYWORDS


@lru_cache(maxsize=32)
def build_allowed_keywords_menu(mission: str) -> str:
    lines = []
    for mission_name, terms in MISSION_KEYWORDS.items():
        if mission != "All Missions" and mission_name != mission:
            continue
        if terms:
            lines.append(f"- {mission_name}: {', '.join(terms)}")

    if mission == "All Missions" and CROSS_CUTTING_KEYWORDS:
        lines.append(f"- Cross-cutting: {', '.join(CROSS_CUTTING_KEYWORDS)}")

    if not lines:
        return "Error: Could not load keywords.py variables."

    return "\n".join(lines)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"status": "System Operational", "message": "Signal Scout Backend is Running"}


@app.exception_handler(ServiceError)
async def service_error_handler(request, exc):
    logging.error("Service error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"status": "error", "msg": "Service unavailable. Please try again later."},
    )


def ndjson_line(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _build_search_term(req: RadarRequest) -> tuple[str, str]:
    priorities = kw.MISSION_PRIORITIES.get(req.mission, [])
    signal_terms = kw.SIGNAL_TYPES.get(req.mode, kw.SIGNAL_TYPES["radar"])

    if req.mode == "research":
        base_query = req.query if req.query else f"{req.mission} {req.topic or 'innovation'}"
        joined_signals = " OR ".join([f'"{term}"' for term in signal_terms])
        return "🔬 RESEARCH MODE: Global Academic Scan...", f"{base_query} ({joined_signals}) filetype:pdf -site:.com"

    if req.mode == "policy":
        joined_signals = " OR ".join([f'"{term}"' for term in signal_terms])
        return (
            "⚖️ POLICY MODE: International Policy & Strategy...",
            f"{req.mission} {req.topic or 'policy'} ({joined_signals}) (site:.gov OR site:.int OR site:.org)",
        )

    joined_blacklist = " ".join([f"-{word}" for word in kw.BLACKLIST])
    joined_signals = " OR ".join([f'"{term}"' for term in signal_terms])
    topic_value = (req.topic or "innovation").strip()
    if topic_value.lower() in kw.GENERIC_TOPICS:
        pillars = " OR ".join([f'"{pillar}"' for pillar in priorities[:3]])
        return (
            "📡 RADAR MODE: Full Spectrum Scan (Industry + Policy + Academic)...",
            f"{req.mission} ({topic_value} AND ({pillars})) ({joined_signals}) {joined_blacklist}",
        )

    return (
        "📡 RADAR MODE: Full Spectrum Scan (Industry + Policy + Academic)...",
        f"{req.mission} {topic_value} ({joined_signals}) {joined_blacklist}",
    )


async def _calculate_scores(
    topic: str,
    gtr_projects: List[Dict[str, Any]],
    cb_data: List[Dict[str, Any]],
    web_results: List[Dict[str, Any]],
) -> tuple[float, float, str, List[str], List[str]]:
    abstracts = [p.get("abstract", "") for p in gtr_projects if p.get("abstract")]
    refined_keywords = topic_svc.perform_lda(abstracts)
    top2vec_seeds = topic_svc.recommend_top2vec_seeds(abstracts)

    total_research = sum(p.get("fund_val", 0) for p in gtr_projects)
    total_investment = sum(d.get("amount", 0) for d in cb_data)
    activity_score = analytics_svc.calculate_activity_score(total_research, total_investment)

    niche_results = await search_svc.search_niche(topic)
    mainstream_count = len(web_results)
    niche_count = len([item for item in niche_results if item.get("is_niche")])
    attention_score = analytics_svc.calculate_attention_score(mainstream_count, niche_count)

    typology = analytics_svc.classify_sweet_spot(activity_score, attention_score)
    return activity_score, attention_score, typology, refined_keywords, top2vec_seeds


@app.post("/api/mode/radar")
async def radar_scan(req: RadarRequest) -> StreamingResponse:
    async def generator() -> AsyncGenerator[str, None]:
        try:
            topic = req.topic or "innovation"
            mission = req.mission or "All Missions"

            # STEP 1: SHEET SYNC
            yield json.dumps({"status": "info", "msg": "Authenticating with Google Sheets..."}) + "\n"
            existing_urls = await sheet_svc.get_existing_urls()
            yield (
                json.dumps(
                    {
                        "status": "success",
                        "msg": f"Database Connected. {len(existing_urls)} existing records loaded.",
                    }
                )
                + "\n"
            )

            # STEP 2: UKRI API
            yield (
                json.dumps(
                    {"status": "info", "msg": f"GET https://gtr.ukri.org/gtr/api/projects?q={topic}..."}
                )
                + "\n"
            )
            gtr_projects = await gtr_svc.fetch_projects(topic)
            yield (
                json.dumps(
                    {
                        "status": "success",
                        "msg": f"Received {len(gtr_projects)} objects from UKRI GtR.",
                    }
                )
                + "\n"
            )

            # STEP 3: CRUNCHBASE API
            yield (
                json.dumps(
                    {"status": "info", "msg": f"GET https://api.crunchbase.com/v4/entities?query={topic}..."}
                )
                + "\n"
            )
            cb_data = await cb_svc.fetch_deals(topic)
            yield (
                json.dumps(
                    {
                        "status": "success",
                        "msg": f"Received {len(cb_data)} objects from Crunchbase.",
                    }
                )
                + "\n"
            )

            mode_msg, search_term = _build_search_term(req)
            yield json.dumps({"status": "info", "msg": mode_msg}) + "\n"

            # STEP 4: GOOGLE SEARCH API
            yield json.dumps(
                {"status": "info", "msg": f"🔍 Executing Search: {search_term[:80]}..."}
            ) + "\n"
            web_results = await search_svc.search(search_term)
            yield (
                json.dumps(
                    {
                        "status": "success",
                        "msg": f"Received {len(web_results)} objects from Google Search.",
                    }
                )
                + "\n"
            )

            # STEP 5: PROCESSING LOOP
            yield (
                json.dumps(
                    {
                        "status": "info",
                        "msg": "Processing signals & calculating Sweet Spot scores...",
                    }
                )
                + "\n"
            )

            activity_score, attention_score, typology, refined_keywords, top2vec_seeds = (
                await _calculate_scores(topic, gtr_projects, cb_data, web_results)
            )

            for project in gtr_projects[:6]:
                url_ref = project.get("grantReference") or project.get("title", "")
                project_signal = {
                    "mode": "Radar",
                    "title": project.get("title", f"GtR: {topic}"),
                    "summary": project.get("abstract", ""),
                    "url": f"https://gtr.ukri.org/projects?ref={url_ref}",
                    "mission": mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(attention_score, 1),
                    "typology": typology,
                    "sparkline": analytics_svc.generate_sparkline(activity_score, attention_score),
                    "refined_keywords": refined_keywords,
                    "topic_seeds": top2vec_seeds,
                    "source": "UKRI GtR",
                }

                if project_signal["url"] in existing_urls:
                    continue

                try:
                    await sheet_svc.save_signal(project_signal, existing_urls)
                    yield json.dumps({"status": "blip", "blip": project_signal}) + "\n"
                except Exception:
                    logging.exception(
                        "Failed to save signal '%s' to sheet.", project_signal.get("title")
                    )
                    yield json.dumps(
                        {"status": "error", "msg": "Write Failed: Could not persist signal."}
                    ) + "\n"

            for item in web_results[:6]:
                if item.get("link") in existing_urls:
                    yield (
                        json.dumps(
                            {
                                "status": "warning",
                                "msg": f"Skipping Duplicate: {item['title'][:20]}...",
                            }
                        )
                        + "\n"
                    )
                    continue

                signal = {
                    "mode": "Radar",
                    "title": item.get("title", "Untitled Signal"),
                    "summary": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "mission": mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(attention_score, 1),
                    "typology": typology,
                    "sparkline": analytics_svc.generate_sparkline(activity_score, attention_score),
                    "refined_keywords": refined_keywords,
                    "topic_seeds": top2vec_seeds,
                    "source": "Google Search",
                }

                try:
                    await sheet_svc.save_signal(signal, existing_urls)
                    yield json.dumps({"status": "blip", "blip": signal}) + "\n"
                    yield (
                        json.dumps(
                            {
                                "status": "info",
                                "msg": f"→ Wrote row to Sheet: {signal['title'][:20]}...",
                            }
                        )
                        + "\n"
                    )
                except Exception:
                    logging.exception("Failed to save signal '%s' to sheet.", signal.get("title"))
                    yield json.dumps(
                        {"status": "error", "msg": "Write Failed: Could not persist signal."}
                    ) + "\n"

            yield json.dumps({"status": "complete", "msg": "Scan Routine Finished."}) + "\n"

        except ServiceError as exc:
            logging.error("Service error in radar_scan generator: %s", exc)
            yield json.dumps({"status": "error", "msg": "Service unavailable. Please try again later."}) + "\n"
        except Exception as exc:
            logging.exception("Unexpected failure in radar_scan generator: %s", exc)
            yield json.dumps(
                {"status": "error", "msg": "CRITICAL FAILURE: Unexpected system error."}
            ) + "\n"

    return StreamingResponse(generator(), media_type="application/x-ndjson")


@app.post("/api/intelligence/cluster")
async def cluster_signals(signals: List[dict]):
    """
    Takes a raw list of signals and groups them into 'Narratives'
    using TF-IDF Vectorization and K-Means Clustering.
    """
    if len(signals) < 3:
        return []

    texts = [f"{signal['title']} {signal['summary']}" for signal in signals]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    matrix = vectorizer.fit_transform(texts)

    k = max(2, len(signals) // 5)
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42).fit(matrix)

    clusters: Dict[str, Dict[str, Any]] = {}
    for index, label in enumerate(kmeans.labels_):
        lbl = str(label)
        if lbl not in clusters:
            clusters[lbl] = {"id": lbl, "signals": [], "keywords": []}
        clusters[lbl]["signals"].append(signals[index])

    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
    terms = vectorizer.get_feature_names_out()

    results = []
    for cluster_id in clusters:
        centroid_index = int(cluster_id)
        top_terms = [terms[ind] for ind in order_centroids[centroid_index, :3]]
        cluster_title = f"Narrative: {', '.join(top_terms).title()}"

        results.append(
            {
                "title": cluster_title,
                "count": len(clusters[cluster_id]["signals"]),
                "signals": clusters[cluster_id]["signals"],
                "keywords": top_terms,
            }
        )

    return results


@app.post("/api/mode/research")
async def research_scan(req: ResearchRequest) -> StreamingResponse:
    async def generator() -> AsyncGenerator[str, None]:
        try:
            yield ndjson_line(
                {"status": "searching", "msg": f"Deep researching '{req.query}'..."}
            )

            existing_urls = await sheet_svc.get_existing_urls()
            results = await search_svc.search(f"{req.query} whitepaper report pdf", num=5)

            yield ndjson_line({"status": "processing", "msg": "Extracting insights..."})

            for item in results:
                activity = random.uniform(7, 10)
                attention = random.uniform(2, 6)

                signal = {
                    "mode": "Research",
                    "title": item.get("title", "Untitled"),
                    "summary": item.get("snippet", "No summary"),
                    "url": item.get("link", "#"),
                    "mission": "Targeted Research",
                    "typology": "Evidence",
                    "score_activity": round(activity, 1),
                    "score_attention": round(attention, 1),
                    "sparkline": analytics_svc.generate_sparkline(activity, attention),
                    "source": "Google Search",
                }

                try:
                    await sheet_svc.save_signal(signal, existing_urls)
                except Exception as exc:
                    logging.error("Failed to save research signal: %s", exc)


                yield ndjson_line({"status": "blip", "blip": signal})

            yield ndjson_line({"status": "complete"})
        except ServiceError as exc:
            logging.error("Service error in research_scan generator: %s", exc)
            yield ndjson_line({"status": "error", "msg": "Service unavailable. Please try again later."})
        except Exception:
            yield ndjson_line({"status": "error", "msg": "Unexpected System Error"})

    return StreamingResponse(generator(), media_type="application/x-ndjson")


@app.post("/api/mode/policy")
async def policy_mode(req: PolicyRequest) -> Dict[str, Any]:
    query = f"(site:gov.uk OR site:parliament.uk) {req.topic}"
    results = await search_svc.search(query)
    return {"status": "success", "data": {"results": results}}


@app.get("/api/saved")
async def get_saved() -> Dict[str, Any]:
    try:
        return {"signals": await sheet_svc.get_all()}
    except ServiceError as exc:
        logging.error("Service error in get_saved: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service unavailable. Please try again later.",
        ) from exc


@app.post("/api/update_signal")
async def update_signal(req: UpdateSignalRequest) -> Dict[str, str]:
    await sheet_svc.update_status(req.url, req.status)
    return {"status": "success"}


@app.post("/api/feedback")
async def feedback(payload: Dict[str, Any]) -> Dict[str, str]:
    return {"status": "recorded"}
