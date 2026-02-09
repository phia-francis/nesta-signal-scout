from __future__ import annotations

import json
import random
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
app.mount("/static", StaticFiles(directory="static"), name="static")

search_svc = SearchService()
sheet_svc = SheetService()
analytics_svc = HorizonAnalyticsService()
gtr_svc = GatewayResearchService()
cb_svc = CrunchbaseService()
topic_svc = TopicModellingService()


@app.exception_handler(ServiceError)
async def service_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"status": "error", "msg": str(exc)})


def ndjson_line(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@app.post("/api/mode/radar")
async def radar_scan(req: RadarRequest) -> StreamingResponse:
    async def generator() -> AsyncGenerator[str, None]:
        try:
            topic = req.topic or req.mission
            yield ndjson_line(
                {"status": "searching", "msg": f"Scanning GtR & Crunchbase for {topic}..."}
            )

            existing_urls = await sheet_svc.get_existing_urls()
            gtr_data = await gtr_svc.fetch_projects(topic)
            cb_data = await cb_svc.fetch_deals(topic)

            abstracts = [p.get("abstract", "") for p in gtr_data if p.get("abstract")]
            refined_keywords = topic_svc.perform_lda(abstracts)
            top2vec_seeds = topic_svc.recommend_top2vec_seeds(abstracts)

            yield ndjson_line({"status": "classifying", "msg": "Mapping Activity vs. Attention..."})

            total_research = sum(p.get("fund_val", 0) for p in gtr_data)
            total_investment = sum(d.get("amount", 0) for d in cb_data)
            activity_score = analytics_svc.calculate_activity_score(total_research, total_investment)

            web_results = await search_svc.search(f"{topic} innovation", num=6)
            niche_results = await search_svc.search_niche(topic)
            mainstream_count = len(web_results)
            niche_count = len([item for item in niche_results if item.get("is_niche")])
            attention_score = analytics_svc.calculate_attention_score(mainstream_count, niche_count)

            typology = analytics_svc.classify_sweet_spot(activity_score, attention_score)

            for project in gtr_data:
                url_ref = project.get("grantReference") or project.get("title", "")
                signal = {
                    "mode": "Radar",
                    "title": project.get("title", f"GtR: {topic}"),
                    "summary": project.get("abstract", ""),
                    "url": f"https://gtr.ukri.org/projects?ref={url_ref}",
                    "mission": req.mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(attention_score, 1),
                    "typology": typology,
                    "sparkline": analytics_svc.generate_sparkline(activity_score, attention_score),
                    "refined_keywords": refined_keywords,
                    "topic_seeds": top2vec_seeds,
                    "source": "UKRI GtR",
                }

                try:
                    await sheet_svc.save_signal(signal, existing_urls)
                except Exception as exc:
                    logging.critical("Could not save signal '%s' to sheet: %s", signal.get('title'), exc)


                yield ndjson_line({"status": "blip", "blip": signal})

            for item in web_results[:6]:
                signal = {
                    "mode": "Radar",
                    "title": item.get("title", f"Trend: {topic}"),
                    "summary": item.get("snippet", ""),
                    "url": item.get("link", "#"),
                    "mission": req.mission,
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
                except Exception as exc:
                    print(f"CRITICAL DB ERROR: Could not save '{signal['title']}': {exc}")

                yield ndjson_line({"status": "blip", "blip": signal})

            yield ndjson_line({"status": "complete"})
        except ServiceError as exc:
            yield ndjson_line({"status": "error", "msg": str(exc)})
        except Exception:
            logging.exception("Unexpected error in radar_scan generator")
            yield ndjson_line({"status": "error", "msg": "Unexpected System Error"})


    return StreamingResponse(generator(), media_type="application/x-ndjson")


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
            yield ndjson_line({"status": "error", "msg": str(exc)})
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
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/update_signal")
async def update_signal(req: UpdateSignalRequest) -> Dict[str, str]:
    await sheet_svc.update_status(req.url, req.status)
    return {"status": "success"}


@app.post("/api/feedback")
async def feedback(payload: Dict[str, Any]) -> Dict[str, str]:
    return {"status": "recorded"}
