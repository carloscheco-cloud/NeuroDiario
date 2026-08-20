from __future__ import annotations

import hashlib
import os
from typing import Dict, List

import requests

from ..config import StudyConfig


def _id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class YouTubeCollector:
    """Collects public YouTube video metadata and top-level public comments via API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        self.base = "https://www.googleapis.com/youtube/v3"

    def _get(self, endpoint: str, params: Dict) -> Dict:
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY is not configured")
        params = dict(params)
        params["key"] = self.api_key
        response = requests.get(f"{self.base}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def collect(self, study: StudyConfig) -> List[Dict]:
        cfg = study.sources.get("youtube", {})
        if cfg is False or cfg.get("enabled", True) is False:
            return []
        query = " OR ".join(study.search_terms[:6])
        payload = self._get("search", {
            "part": "snippet",
            "q": query,
            "type": "video",
            "regionCode": "DO",
            "relevanceLanguage": "es",
            "maxResults": min(int(cfg.get("max_videos", 25)), 50),
            "publishedAfter": f"{study.period_start}T00:00:00Z",
            "publishedBefore": f"{study.period_end}T23:59:59Z"
        })
        records: List[Dict] = []
        for item in payload.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id:
                continue
            video_url = "https://www.youtube.com/watch?v=" + video_id
            records.append({
                "id": _id("video:" + video_id), "study": study.slug,
                "source_type": "youtube_video", "platform": "youtube",
                "source_name": snippet.get("channelTitle", "YouTube"),
                "url": video_url, "title": snippet.get("title", ""),
                "text": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"), "video_id": video_id
            })
            try:
                comments = self._get("commentThreads", {
                    "part": "snippet", "videoId": video_id,
                    "maxResults": min(int(cfg.get("comments_per_video", 100)), 100),
                    "textFormat": "plainText", "order": "relevance"
                })
            except requests.HTTPError:
                continue
            for thread in comments.get("items", []):
                top = thread.get("snippet", {}).get("topLevelComment", {})
                cs = top.get("snippet", {})
                comment_id = top.get("id")
                if comment_id:
                    records.append({
                        "id": _id("comment:" + comment_id), "study": study.slug,
                        "source_type": "youtube_comment", "platform": "youtube",
                        "source_name": snippet.get("channelTitle", "YouTube"),
                        "url": video_url, "title": snippet.get("title", ""),
                        "text": cs.get("textDisplay", ""),
                        "published_at": cs.get("publishedAt"),
                        "video_id": video_id, "like_count": cs.get("likeCount", 0)
                    })
        return records
