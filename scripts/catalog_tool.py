#!/usr/bin/env python3
"""Build, refresh, and render the Open Source Catalog."""

from __future__ import annotations

import html
import json
import math
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "cache"
HK = ZoneInfo("Asia/Hong_Kong")
DEFAULT_EMAIL = "sunny3131831@gmail.com"
# Hourly updates always publish to this GitHub Pages site.
PAGES_ROOT = "https://titanothereyik.github.io/Open-Source-Catalog/"
# Each update keeps calling GitHub until this share of the core REST quota is used.
CORE_USAGE_TARGET = 0.80

CATEGORIES = [
    {
        "id": "gaussian-splatting",
        "dir": "gaussian-splatting",
        "title": "Gaussian Splatting",
        "blurb": "用三維高斯重建場景、即時渲染、編輯同 SLAM，包括 3DGS、4D 動態場景同瀏覽器檢視器。",
    },
    {
        "id": "world-model",
        "dir": "world-model",
        "title": "World Model",
        "blurb": "學識預測下一個畫面或狀態嘅世界模型，用喺影片、自動駕駛、機械人同可探索嘅三維世界。",
    },
    {
        "id": "image-to-3d",
        "dir": "image-to-3d",
        "title": "Image to 3D",
        "blurb": "由一張圖或一段文字生成三維模型，包括網格、高斯同多視角幾何重建。",
    },
    {
        "id": "ai-agent",
        "dir": "ai-agent",
        "title": "AI Agent",
        "blurb": "會規劃、調用工具、同其他 agent 一齊做嘢嘅開源框架同程式。",
    },
    {
        "id": "image",
        "dir": "image",
        "title": "圖像",
        "blurb": "圖像生成、編輯、放大、識別同影像處理。",
    },
    {
        "id": "video",
        "dir": "video",
        "title": "影片",
        "blurb": "影片生成、剪接、播放、轉碼同處理。",
    },
    {
        "id": "vfx-cg-blender",
        "dir": "vfx-cg-blender",
        "title": "VFX / CG / Blender",
        "blurb": "三維、合成、渲染、材質同 Blender 生態。",
    },
    {
        "id": "stock-trading",
        "dir": "stock-trading",
        "title": "Stock Trading",
        "blurb": "股票同量化研究、回測、行情數據同交易框架。",
    },
    {
        "id": "crypto-trading",
        "dir": "crypto-trading",
        "title": "Crypto Trading",
        "blurb": "加密貨幣交易所 API、交易機械人同回測工具。",
    },
]

QUERIES = {
    "gaussian-splatting": [
        "topic:gaussian-splatting",
        "topic:3d-gaussian-splatting",
        "3d gaussian splatting stars:>80",
    ],
    "world-model": [
        '"world model" stars:>80',
        '"world models" stars:>60',
    ],
    "image-to-3d": [
        '"image to 3d" OR "image-to-3d" OR "text-to-3d" OR "text to 3d" stars:>40',
        "triposr OR hunyuan3d OR trellis OR dust3r OR vggt stars:>40",
    ],
    "ai-agent": [
        "topic:ai-agent",
        "topic:ai-agents",
        "topic:autonomous-agents",
        "topic:agent-framework",
    ],
    "image": [
        "topic:stable-diffusion",
        "topic:image-generation",
        "topic:comfyui",
        "topic:diffusion-models",
    ],
    "video": [
        "topic:video-generation",
        "topic:text-to-video",
        "topic:video-editing",
        "topic:ai-video",
    ],
    "vfx-cg-blender": [
        "topic:blender",
        "topic:computer-graphics",
        "topic:vfx",
    ],
    "stock-trading": [
        "topic:algorithmic-trading",
        "topic:quantitative-finance",
        "topic:stock-trading",
        "topic:backtesting",
    ],
    "crypto-trading": [
        "topic:crypto-trading",
        "topic:trading-bot",
        "topic:cryptocurrency-trading",
        "freqtrade OR hummingbot OR ccxt in:name stars:>80",
    ],
}

MIN_NEW = {
    "gaussian-splatting": 800,
    "world-model": 600,
    "image-to-3d": 800,
    "ai-agent": 5000,
    "image": 4000,
    "video": 3000,
    "vfx-cg-blender": 2500,
    "stock-trading": 1500,
    "crypto-trading": 1200,
}

PAPER_LINKS = {
    "CompVis/stable-diffusion": {
        "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
        "url": "https://arxiv.org/abs/2112.10752",
    },
    "CompVis/latent-diffusion": {
        "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
        "url": "https://arxiv.org/abs/2112.10752",
    },
    "lllyasviel/ControlNet": {
        "title": "Adding Conditional Control to Text-to-Image Diffusion Models",
        "url": "https://arxiv.org/abs/2302.05543",
    },
    "guoyww/AnimateDiff": {
        "title": "AnimateDiff",
        "url": "https://arxiv.org/abs/2307.04725",
    },
    "Stability-AI/generative-models": {
        "title": "Stable Video Diffusion",
        "url": "https://arxiv.org/abs/2311.15127",
    },
    "zai-org/CogVideo": {
        "title": "CogVideo",
        "url": "https://arxiv.org/abs/2205.15868",
    },
    "Tencent-Hunyuan/HunyuanVideo": {
        "title": "HunyuanVideo",
        "url": "https://arxiv.org/abs/2412.03603",
    },
    "graphdeco-inria/gaussian-splatting": {
        "title": "3D Gaussian Splatting for Real-Time Radiance Field Rendering",
        "url": "https://arxiv.org/abs/2308.04079",
    },
    "naver/dust3r": {
        "title": "DUSt3R: Geometric 3D Vision Made Easy",
        "url": "https://arxiv.org/abs/2312.14132",
    },
    "facebookresearch/vggt": {
        "title": "VGGT: Visual Geometry Grounded Transformer",
        "url": "https://arxiv.org/abs/2503.11651",
    },
    "VAST-AI-Research/TripoSR": {
        "title": "TripoSR: Fast 3D Object Reconstruction from a Single Image",
        "url": "https://arxiv.org/abs/2403.02151",
    },
    "microsoft/TRELLIS": {
        "title": "Structured 3D Latents for Scalable and Versatile 3D Generation",
        "url": "https://arxiv.org/abs/2412.01506",
    },
    "danijar/dreamerv3": {
        "title": "Mastering Diverse Domains through World Models",
        "url": "https://arxiv.org/abs/2301.04104",
    },
    "dreamgaussian/dreamgaussian": {
        "title": "DreamGaussian: Generative Gaussian Splatting for Efficient 3D Content Creation",
        "url": "https://arxiv.org/abs/2309.16653",
    },
    "NVlabs/instant-ngp": {
        "title": "Instant Neural Graphics Primitives",
        "url": "https://arxiv.org/abs/2201.05989",
    },
    "AI4Finance-Foundation/FinRL": {
        "title": "FinRL",
        "url": "https://arxiv.org/abs/2011.09607",
    },
}

STANDALONE_PAPERS = [
    {
        "id": "arxiv:2210.03629",
        "category": "ai-agent",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2210.03629",
        "code_url": "https://github.com/ysymyth/ReAct",
        "summary": "呢篇論文提出推理同行動要交替進行。語言模型先寫低自己嘅思考，再決定調用邊個工具，然後讀取觀察結果，繼續下一步。後來好多 agent 框架都跟住呢個「諗、做、再諗」嘅循環。",
    },
    {
        "id": "arxiv:2304.03442",
        "category": "ai-agent",
        "title": "Generative Agents: Interactive Simulacra of Human Behavior",
        "year": 2023,
        "url": "https://arxiv.org/abs/2304.03442",
        "code_url": "https://github.com/joonspk-research/generative_agents",
        "summary": "用記憶、反思同計劃，模擬小鎮入面多個 AI 角色點樣自己過日常。每個角色會記住發生過嘅事、整理成較高層嘅看法，再決定同邊個傾偈、做咩活動，從而互相影響。",
    },
    {
        "id": "arxiv:2303.11366",
        "category": "ai-agent",
        "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "year": 2023,
        "url": "https://arxiv.org/abs/2303.11366",
        "code_url": "https://github.com/noahshinn/reflexion",
        "summary": "Agent 做完一次嘗試之後，用自然語言寫低自己點解失敗，將呢段教訓放入記憶，下次再試就避開同一啲錯。重點係靠文字反思改進，而唔係重新訓練模型權重。",
    },
    {
        "id": "arxiv:2305.16291",
        "category": "ai-agent",
        "title": "Voyager: An Open-Ended Embodied Agent with Large Language Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2305.16291",
        "code_url": "https://github.com/MineDojo/Voyager",
        "summary": "一個喺 Minecraft 入面自己寫程式、累積技能庫嘅 agent。佢會探索地圖、將成功嘅程式存低做技能，之後遇到新任務可以重用，所以可以持續學新嘢而唔使每次由零開始。",
    },
    {
        "id": "arxiv:2307.01952",
        "category": "image",
        "title": "SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis",
        "year": 2023,
        "url": "https://arxiv.org/abs/2307.01952",
        "code_url": "https://github.com/Stability-AI/generative-models",
        "summary": "Stable Diffusion 嘅較大版本，針對高解像圖像生成。佢改善構圖、提示詞跟隨同整體畫質，尤其係人物同文字細節。研究同產品都常用佢做比第一代更清楚嘅出圖底子。",
    },
    {
        "id": "arxiv:2211.09800",
        "category": "image",
        "title": "InstructPix2Pix: Learning to Follow Image Editing Instructions",
        "year": 2023,
        "url": "https://arxiv.org/abs/2211.09800",
        "code_url": "https://github.com/timothybrooks/instruct-pix2pix",
        "summary": "用一句自然語言指令直接改一張現有圖像，例如換背景、加物件或者轉風格。模型要同時睇住原圖同指示，所以改動跟住你講嘅嘢，而唔係由文字重新生成成張新圖。",
    },
    {
        "id": "arxiv:2003.08934",
        "category": "vfx-cg-blender",
        "title": "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis",
        "year": 2020,
        "url": "https://arxiv.org/abs/2003.08934",
        "code_url": "https://github.com/bmild/nerf",
        "summary": "用神經網路表示一個立體場景，由多張相片合成未拍過嘅新視角。場景被寫成連續嘅輻射場，沿光線取樣就可以渲染。後來大量新視角合成同神經渲染工作都由呢篇論文開始。",
    },
]


def now_hk() -> datetime:
    return datetime.now(HK)


def iso_hk(moment: datetime | None = None) -> str:
    moment = moment or now_hk()
    return moment.strftime("%Y-%m-%dT%H:%M:%S%z")[:-2] + ":" + moment.strftime("%z")[-2:]


def format_hk(iso: str) -> str:
    text = iso.replace("Z", "+00:00")
    moment = datetime.fromisoformat(text).astimezone(HK)
    return moment.strftime("%Y年%m月%d日 %H:%M（香港時間）")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def hk_day(value: str) -> str:
    """Calendar date in Hong Kong for a GitHub timestamp."""
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) == 10 and text[4] == "-" and "T" not in text:
        return text
    normalized = text.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(normalized)
    except ValueError:
        return text[:10]
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(HK).date().isoformat()


def token() -> str:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


class RateLimitExceeded(RuntimeError):
    pass


# Latest core REST quota (resources.core), updated from /rate_limit and response headers.
# spent counts requests made by this run and does not reset when the hourly window rolls.
RATE = {"limit": 0, "remaining": 0, "reset": 0, "spent": 0}
FETCHED: set[str] = set()


def gh_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "open-source-catalog",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token():
        headers["Authorization"] = f"Bearer {token()}"
    return headers


def cache_file(kind: str, key: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in key)[:180]
    return CACHE / kind / f"{safe}.json"


def note_rate_headers(headers) -> None:
    if (headers.get("X-RateLimit-Resource") or "") != "core":
        return
    try:
        limit = int(headers.get("X-RateLimit-Limit") or 0)
        remaining = int(headers.get("X-RateLimit-Remaining") or 0)
        reset = int(headers.get("X-RateLimit-Reset") or 0)
    except ValueError:
        return
    previous = int(RATE["remaining"] or 0)
    previous_reset = int(RATE["reset"] or 0)
    before_spent = int(RATE["spent"] or 0)
    if previous and previous_reset and reset == previous_reset and remaining < previous:
        RATE["spent"] = before_spent + (previous - remaining)
    RATE["limit"] = limit
    RATE["remaining"] = remaining
    RATE["reset"] = reset
    spent = int(RATE["spent"])
    if limit and spent // 100 != before_spent // 100:
        print(f"core rate {spent}/{limit}", flush=True)


def core_quota_met() -> bool:
    limit = int(RATE["limit"] or 0)
    if limit <= 0:
        return False
    target = math.ceil(limit * CORE_USAGE_TARGET)
    spent = int(RATE["spent"] or 0)
    window_used = max(0, limit - int(RATE["remaining"] or 0))
    return max(spent, window_used) >= target


def read_core_quota() -> None:
    req = urllib.request.Request("https://api.github.com/rate_limit", headers=gh_headers())
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode())
    core = payload["resources"]["core"]
    RATE["limit"] = int(core["limit"])
    RATE["remaining"] = int(core["remaining"])
    RATE["reset"] = int(core["reset"])
    print(
        f"core rate remaining {RATE['remaining']}/{RATE['limit']} "
        f"(target {math.ceil(RATE['limit'] * CORE_USAGE_TARGET)})",
        flush=True,
    )


def wait_for_core_budget() -> None:
    """Wait out a spent window so this run can still use 80% of the quota."""
    if not token():
        print("no GitHub token, skip rate-limit target")
        return
    read_core_quota()
    limit = int(RATE["limit"] or 0)
    if limit <= 0:
        return
    target = math.ceil(limit * CORE_USAGE_TARGET)
    if int(RATE["remaining"]) >= target:
        return
    wait = RATE["reset"] - time.time() + 2
    if wait <= 0:
        read_core_quota()
        return
    if wait > 45 * 60:
        print("rate window is already spent and resets in over 45 minutes; using what is left")
        return
    print(f"only {RATE['remaining']} core requests left, waiting {int(wait)}s for reset", flush=True)
    time.sleep(wait)
    read_core_quota()


def pause_after(kind: str) -> None:
    if kind == "search":
        time.sleep(2.1 if token() else 6.5)
    elif kind == "repos":
        time.sleep(0.09 if token() else 0.4)
    else:
        time.sleep(0.2 if token() else 1.0)


def fetch_json(url: str, cache_key: str, kind: str, use_cache: bool) -> dict:
    path = cache_file(kind, cache_key)
    if use_cache and path.exists():
        return json.loads(path.read_text())
    last_error = "unknown"
    for attempt in range(5):
        req = urllib.request.Request(url, headers=gh_headers())
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                note_rate_headers(resp.headers)
                data = json.loads(resp.read().decode())
            if isinstance(data, list):
                data = {"items": data}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
            pause_after(kind)
            return data
        except urllib.error.HTTPError as exc:
            note_rate_headers(exc.headers)
            body = exc.read().decode()[:300]
            last_error = f"{exc.code} {body}"
            lowered = body.lower()
            if exc.code == 404:
                return {"message": "Not Found"}
            if exc.code in (403, 429) and "secondary rate" in lowered:
                retry_after = exc.headers.get("Retry-After")
                time.sleep(int(retry_after) if str(retry_after or "").isdigit() else 20)
                continue
            resource = exc.headers.get("X-RateLimit-Resource") or ""
            if exc.code in (403, 429) and resource == "search":
                reset = int(exc.headers.get("X-RateLimit-Reset") or 0)
                time.sleep(max(2, min(65, reset - time.time() + 1)))
                continue
            if exc.code in (403, 429) and resource == "core" and "rate limit" in lowered:
                RATE["remaining"] = 0
                raise RateLimitExceeded(body)
            time.sleep(4 + attempt * 2)
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = str(exc)
            time.sleep(4 + attempt * 2)
    raise RuntimeError(f"GitHub request failed for {cache_key}: {last_error}")


def load_repo_index() -> dict[str, dict]:
    repos: dict[str, dict] = {}
    if not CACHE.exists():
        return repos
    for path in CACHE.rglob("*.json"):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("full_name"):
                    repos[item["full_name"].lower()] = item
        elif isinstance(data, dict) and data.get("full_name"):
            repos[data["full_name"].lower()] = data
    return repos


def license_of(repo: dict) -> str:
    lic = repo.get("license") or {}
    spdx = lic.get("spdx_id") or ""
    if spdx in ("NOASSERTION", "NONE", "OTHER"):
        return ""
    return spdx


def project_from_repo(repo: dict, category: str, summary: str, locked: bool, added_at: str) -> dict:
    paper = PAPER_LINKS.get(repo["full_name"], {})
    homepage = repo.get("homepage") or ""
    if not str(homepage).startswith("http"):
        homepage = ""
    return {
        "id": "github:" + repo["full_name"].lower(),
        "type": "github",
        "category": category,
        "name": repo["name"],
        "full_name": repo["full_name"],
        "url": repo.get("html_url") or f"https://github.com/{repo['full_name']}",
        "homepage": homepage,
        "description": (repo.get("description") or "").strip(),
        "summary": summary.strip(),
        "summary_locked": locked,
        "stars": int(repo.get("stargazers_count") or 0),
        "language": repo.get("language") or "",
        "license": license_of(repo),
        "topics": list(repo.get("topics") or [])[:8],
        "archived": bool(repo.get("archived")),
        "pushed_at": hk_day(repo.get("pushed_at") or ""),
        "paper_title": paper.get("title", ""),
        "paper_url": paper.get("url", ""),
        "added_at": added_at,
    }


def base_url() -> str:
    """Site root for HTML, notifications, and email. Always the GitHub Pages host."""
    env = os.environ.get("SITE_BASE_URL", "").strip()
    if not env:
        return PAGES_ROOT
    normalized = env if env.endswith("/") else env + "/"
    if normalized.lower() != PAGES_ROOT.lower():
        raise SystemExit(f"SITE_BASE_URL must be the GitHub Pages root {PAGES_ROOT}")
    return PAGES_ROOT


def repo_web_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo:
        return f"https://github.com/{repo}"
    return ""


def bootstrap(force: bool = False) -> dict:
    catalog_path = DATA / "catalog.json"
    if catalog_path.exists() and not force:
        raise SystemExit("catalog.json already exists. Use update, or bootstrap --force.")
    allow = load_json(DATA / "allowlist.json", {})
    summaries = load_json(DATA / "summaries.json", {})
    repos = load_repo_index()
    added_at = iso_hk()
    projects = []
    missing = []
    for category in CATEGORIES:
        for name in allow.get(category["id"], []):
            repo = repos.get(name.lower())
            if not repo:
                missing.append(name)
                continue
            summary = summaries.get(name) or summaries.get(repo["full_name"])
            if not summary:
                missing.append(name + " (no summary)")
                continue
            projects.append(project_from_repo(repo, category["id"], summary, True, added_at))
    if missing:
        raise SystemExit("missing metadata:\n" + "\n".join(missing))
    seen = set()
    for project in projects:
        if project["id"] in seen:
            raise SystemExit(f"duplicate {project['id']}")
        seen.add(project["id"])
    catalog = {
        "title": "Open Source Catalog",
        "updated_at": added_at,
        "base_url": base_url(),
        "projects": projects,
        "papers": STANDALONE_PAPERS,
        "last_new_ids": [project["id"] for project in projects],
    }
    save_json(catalog_path, catalog)
    render(catalog)
    write_outputs(catalog, projects, "bootstrap")
    return catalog


def category_map() -> dict[str, dict]:
    return {item["id"]: item for item in CATEGORIES}


def projects_by_category(catalog: dict) -> dict[str, list[dict]]:
    grouped = {item["id"]: [] for item in CATEGORIES}
    for project in catalog["projects"]:
        grouped.setdefault(project["category"], []).append(project)
    for items in grouped.values():
        items.sort(key=lambda project: (-int(project.get("stars") or 0), project["full_name"].lower()))
    return grouped


def papers_by_category(catalog: dict) -> dict[str, list[dict]]:
    grouped = {item["id"]: [] for item in CATEGORIES}
    for paper in catalog.get("papers", []):
        grouped.setdefault(paper["category"], []).append(paper)
    for items in grouped.values():
        items.sort(key=lambda paper: (-int(paper.get("year") or 0), paper["title"]))
    return grouped


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def fmt_stars(value: int) -> str:
    return f"{int(value):,}"


def page_css() -> str:
    return """
:root {
  --bg: #0c0d11;
  --bg-raise: #15171e;
  --line: rgba(244, 236, 224, 0.12);
  --text: #f6f1e8;
  --muted: #b7b0a4;
  --faint: #8d867c;
  --gold: #e4b15a;
  --ink: #1c140c;
  --shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(228, 177, 90, 0.14), transparent 55%),
    radial-gradient(900px 420px at 100% 0%, rgba(143, 208, 196, 0.08), transparent 50%),
    var(--bg);
  color: var(--text);
  font-family: Outfit, "Avenir Next", "Segoe UI", sans-serif;
  font-size: 16px;
  line-height: 1.55;
}
a { color: inherit; }
.skip {
  position: absolute;
  left: 12px;
  top: -40px;
  background: var(--gold);
  color: var(--ink);
  padding: 8px 12px;
  z-index: 5;
}
.skip:focus { top: 12px; }
.wrap { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
header.hero { padding: 36px 0 18px; }
.kicker {
  margin: 0 0 8px;
  color: var(--gold);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 12px;
}
h1 {
  margin: 0;
  font-family: Fraunces, Georgia, serif;
  font-weight: 560;
  font-size: clamp(40px, 6vw, 68px);
  letter-spacing: -0.045em;
  line-height: 0.95;
}
.lede { max-width: 680px; color: var(--muted); font-size: 18px; margin: 14px 0 0; }
.stats { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.stat {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px 14px;
  min-width: 120px;
}
.stat b { display: block; font-family: Fraunces, Georgia, serif; font-size: 22px; font-weight: 560; }
.stat span { color: var(--faint); font-size: 13px; }
.stickybar {
  position: sticky;
  top: 0;
  z-index: 3;
  padding: 8px 0 12px;
  background: linear-gradient(var(--bg) 72%, rgba(12, 13, 17, 0.94) 88%, transparent);
}
nav.pages {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
}
nav.pages a {
  text-decoration: none;
  color: var(--muted);
  border: 1px solid var(--line);
  background: rgba(21, 23, 30, 0.92);
  border-radius: 999px;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  white-space: nowrap;
}
nav.pages a:hover { color: var(--text); border-color: var(--gold); }
nav.pages a[aria-current="page"] {
  background: var(--gold);
  color: var(--ink);
  border-color: var(--gold);
}
nav.pages .count { color: var(--faint); font-variant-numeric: tabular-nums; }
nav.pages a[aria-current="page"] .count { color: var(--ink); }
.search { padding: 0; }
.hub { display: grid; grid-template-columns: 1fr; gap: 14px; }
.hub[hidden], #results[hidden] { display: none !important; }
.tile {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 196px;
  text-decoration: none;
  background: rgba(21, 23, 30, 0.92);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 22px 22px 18px;
  box-shadow: var(--shadow);
}
.tile:hover { border-color: var(--gold); }
.tile-top { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.tile h2 {
  margin: 0;
  font-family: Fraunces, Georgia, serif;
  font-size: clamp(28px, 4vw, 36px);
  font-weight: 560;
  letter-spacing: -0.04em;
}
.tile .count { color: var(--gold); font-family: Fraunces, Georgia, serif; font-size: 28px; line-height: 1; }
.tile p { margin: 0; color: var(--muted); }
.tile .top { color: var(--text); }
.tile .go { margin-top: auto; color: var(--gold); }
.hero-sub { padding-top: 22px; }
.hero-sub h1 { font-size: clamp(36px, 5vw, 56px); }
.kicker a { text-decoration: none; }
main.page { padding-bottom: 72px; }
.search input {
  width: 100%;
  background: var(--bg-raise);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px;
  font: inherit;
  outline: none;
}
.search input:focus { border-color: var(--gold); }
.section { margin: 8px 0 36px; scroll-margin-top: 72px; }
.section h2 {
  font-family: Fraunces, Georgia, serif;
  font-size: 34px;
  font-weight: 560;
  letter-spacing: -0.04em;
  margin: 0;
}
.section .blurb { color: var(--muted); margin: 6px 0 16px; }
.grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
.card {
  background: rgba(21, 23, 30, 0.92);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px 16px 14px;
  box-shadow: var(--shadow);
  min-width: 0;
}
.card header { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
.rank { color: var(--faint); font-variant-numeric: tabular-nums; font-size: 13px; margin-right: 8px; }
.card h3 { margin: 0; font-size: 18px; letter-spacing: -0.02em; }
.card h3 a { text-decoration: none; }
.card h3 a:hover { color: var(--gold); }
.stars { color: var(--gold); font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 650; }
.meta { color: var(--faint); font-size: 13px; margin: 6px 0 8px; overflow-wrap: anywhere; }
.summary { margin: 0; color: #ebe4d8; }
.links { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.links a, .badge {
  text-decoration: none;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 13px;
  color: var(--muted);
}
.links a:hover { color: var(--text); border-color: var(--gold); }
.badge.arch { color: #e7b8a4; }
.topics { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.topics span { color: var(--faint); font-size: 12px; }
.papers { margin-top: 16px; }
.papers h3 { margin: 0 0 10px; font-size: 15px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--faint); }
#empty { display: none; color: var(--muted); padding: 12px 0 24px; }
footer.site { color: var(--faint); font-size: 13px; padding: 8px 0 28px; }
@media (min-width: 800px) {
  .hub { grid-template-columns: 1fr 1fr; }
}
@media (min-width: 980px) {
  .grid { grid-template-columns: 1fr 1fr; }
}
""".strip()


def project_anchor(project: dict) -> str:
    slug = project["full_name"].lower().replace("/", "-")
    return "p-" + "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in slug)


def card_html(project: dict, rank: int, category_href: str = "", category_title: str = "") -> str:
    bits = [project["full_name"]]
    if project.get("language"):
        bits.append(project["language"])
    if project.get("license"):
        bits.append(project["license"])
    pushed = project.get("pushed_at") or ""
    search = " ".join(
        [
            project.get("name", ""),
            project.get("full_name", ""),
            project.get("summary", ""),
            project.get("description", ""),
            project.get("language", ""),
            " ".join(project.get("topics") or []),
        ]
    ).lower()
    links = [f'<a href="{esc(project["url"])}">GitHub</a>']
    if project.get("homepage"):
        links.append(f'<a href="{esc(project["homepage"])}">主頁</a>')
    if project.get("paper_url"):
        links.append(f'<a href="{esc(project["paper_url"])}">論文</a>')
    if category_title and category_href:
        links.append(f'<a href="{esc(category_href)}#{project_anchor(project)}">{esc(category_title)}</a>')
    badges = ""
    if project.get("archived"):
        badges = '<span class="badge arch">已封存</span>'
    topics = "".join(f"<span>#{esc(topic)}</span>" for topic in (project.get("topics") or [])[:3])
    topic_html = f'<div class="topics">{topics}</div>' if topics else ""
    meta_parts = [esc(bit) for bit in bits]
    label = esc(pushed) if pushed else "…"
    meta_parts.append(f'<time class="pushed" datetime="{esc(pushed)}">最近推送 {label}</time>')
    return f"""
<article class="card" id="{esc(project_anchor(project))}" data-repo="{esc(project["full_name"])}" data-search="{esc(search)}">
  <header>
    <h3><span class="rank">{rank:02d}</span><a href="{esc(project["url"])}">{esc(project["name"])}</a></h3>
    <div class="stars">★ {fmt_stars(project.get("stars") or 0)}</div>
  </header>
  <p class="meta">{" · ".join(meta_parts)}</p>
  <p class="summary">{esc(project.get("summary"))}</p>
  <div class="links">{''.join(links)}{badges}</div>
  {topic_html}
</article>
""".strip()


def paper_html(paper: dict) -> str:
    search = " ".join([paper["title"], paper.get("summary", ""), "paper", "arxiv"]).lower()
    links = [f'<a href="{esc(paper["url"])}">arXiv</a>']
    if paper.get("code_url"):
        links.append(f'<a href="{esc(paper["code_url"])}">程式</a>')
    return f"""
<article class="card" data-search="{esc(search)}">
  <header>
    <h3><a href="{esc(paper["url"])}">{esc(paper["title"])}</a></h3>
    <div class="stars">{esc(paper.get("year"))}</div>
  </header>
  <p class="meta">論文 · arXiv</p>
  <p class="summary">{esc(paper.get("summary"))}</p>
  <div class="links">{''.join(links)}<span class="badge">論文</span></div>
</article>
""".strip()


def page_nav(grouped: dict[str, list[dict]], active: str | None) -> str:
    if active is None:
        links = ['<a href="./" aria-current="page">目錄</a>']
    else:
        links = ['<a href="../">目錄</a>']
    for category in CATEGORIES:
        count = len(grouped.get(category["id"], []))
        if active == category["id"]:
            href = "./"
            current = ' aria-current="page"'
        elif active is None:
            href = f'{category["dir"]}/'
            current = ""
        else:
            href = f'../{category["dir"]}/'
            current = ""
        links.append(
            f'<a href="{href}"{current}>{esc(category["title"])}<span class="count">{count}</span></a>'
        )
    return f'<nav class="pages" aria-label="分類">{"".join(links)}</nav>'


def hub_html(grouped: dict[str, list[dict]]) -> str:
    tiles = []
    for category in CATEGORIES:
        items = grouped.get(category["id"], [])
        top = items[0] if items else None
        top_line = ""
        if top:
            top_line = f'<p class="top">星數最高 · {esc(top["name"])} ★ {fmt_stars(top.get("stars") or 0)}</p>'
        tiles.append(
            f"""
<a class="tile" href="{esc(category["dir"])}/">
  <div class="tile-top"><h2>{esc(category["title"])}</h2><span class="count">{len(items)}</span></div>
  <p>{esc(category["blurb"])}</p>
  {top_line}
  <span class="go">打開呢一頁</span>
</a>
""".strip()
        )
    return f'<div class="hub" id="hub">{"".join(tiles)}</div>'


def render_document(catalog: dict, active: str | None) -> str:
    grouped = projects_by_category(catalog)
    papers = papers_by_category(catalog)
    site = catalog.get("base_url") or base_url()
    title = "Open Source Catalog"
    if active:
        title = f"{category_map()[active]['title']} · Open Source Catalog"
    canonical = ""
    if site:
        path = "" if active is None else category_map()[active]["dir"] + "/"
        canonical = f'<link rel="canonical" href="{esc(site + path)}">'
    nav = page_nav(grouped, active)
    if active is None:
        result_cards = []
        for category in CATEGORIES:
            href = f'{category["dir"]}/'
            for rank, project in enumerate(grouped.get(category["id"], []), 1):
                result_cards.append(card_html(project, rank, href, category["title"]))
            for paper in papers.get(category["id"], []):
                result_cards.append(paper_html(paper))
        body = f"""
{hub_html(grouped)}
<div id="results" hidden>
  <div class="grid">{''.join(result_cards)}</div>
</div>
""".strip()
    else:
        category = category_map()[active]
        cards = [
            card_html(project, rank)
            for rank, project in enumerate(grouped.get(category["id"], []), 1)
        ]
        paper_cards = [paper_html(paper) for paper in papers.get(category["id"], [])]
        paper_block = ""
        if paper_cards:
            paper_block = '<div class="papers"><h3>相關論文</h3><div class="grid">' + "".join(paper_cards) + "</div></div>"
        body = f"""
<section class="section" id="{esc(category["id"])}" data-section>
  <div class="grid">{''.join(cards)}</div>
  {paper_block}
</section>
""".strip()
    project_count = len(catalog["projects"])
    paper_count = len(catalog.get("papers", []))
    if active is None:
        hero = f"""
<header class="hero">
    <p class="kicker">每兩小時更新</p>
    <h1>Open Source Catalog</h1>
    <p class="lede">九個分類各自一頁。而家聚焦 Gaussian Splatting、World Model 同 Image to 3D。開源項目按 stars 由多至少排，已收錄嘅項目唔會重複加入。</p>
    <div class="stats">
      <div class="stat"><b>{project_count}</b><span>開源項目</span></div>
      <div class="stat"><b>{paper_count}</b><span>未另列 repo 嘅論文</span></div>
      <div class="stat"><b>{esc(format_hk(catalog["updated_at"]).split(" ")[0])}</b><span>{esc(format_hk(catalog["updated_at"]).split(" ", 1)[1])}</span></div>
    </div>
  </header>
"""
    else:
        category = category_map()[active]
        hero = f"""
<header class="hero hero-sub">
    <p class="kicker"><a href="../">Open Source Catalog</a></p>
    <h1>{esc(category["title"])}</h1>
    <p class="lede">{esc(category["blurb"])} 開源項目按 GitHub stars 由多至少。</p>
    <div class="stats">
      <div class="stat"><b>{len(grouped.get(active, []))}</b><span>開源項目</span></div>
      <div class="stat"><b>{len(papers.get(active, []))}</b><span>相關論文</span></div>
      <div class="stat"><b>{esc(format_hk(catalog["updated_at"]).split(" ")[0])}</b><span>{esc(format_hk(catalog["updated_at"]).split(" ", 1)[1])}</span></div>
    </div>
  </header>
"""
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0c0d11">
<meta name="description" content="Open Source Catalog：AI Agent、圖像、影片、VFX/CG/Blender、Stock Trading、Crypto Trading 嘅開源項目同相關論文。">
<title>{esc(title)}</title>
{canonical}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,650&family=Outfit:wght@400;520;650&display=swap" rel="stylesheet">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect fill='%230c0d11' width='64' height='64' rx='14'/%3E%3Ccircle cx='32' cy='32' r='16' fill='none' stroke='%23e4b15a' stroke-width='4'/%3E%3C/svg%3E">
<style>
{page_css()}
</style>
</head>
<body>
<a class="skip" href="#content">跳到項目</a>
<div class="wrap">
  {hero}
  <div class="stickybar">
    {nav}
    <form class="search" role="search" onsubmit="return false">
      <label class="sr" for="q" style="position:absolute;left:-999px">搜尋</label>
      <input id="q" type="search" placeholder="搜尋名稱、摘要、語言或主題" autocomplete="off">
    </form>
  </div>
  <main class="page" id="content">
    <p id="empty">沒有符合呢個搜尋嘅項目。</p>
    {body}
  </main>
  <footer class="site">Open Source Catalog · 資料來自 GitHub 公開資料同 arXiv · 排序以 stars 為準 · 重複項目只保留一次 · 最近推送會喺你睇到嗰張卡時向 GitHub 更新</footer>
</div>
<script>
(function () {{
  const input = document.querySelector("#q");
  const hub = document.querySelector("#hub");
  const results = document.querySelector("#results");
  const cards = Array.from(document.querySelectorAll("#results [data-search], section [data-search]"));
  const sections = Array.from(document.querySelectorAll("[data-section]"));
  const empty = document.querySelector("#empty");
  function apply() {{
    const q = input.value.trim().toLowerCase();
    if (hub && results) {{
      const browsing = q.length === 0;
      hub.hidden = !browsing;
      results.hidden = browsing;
      if (browsing) {{
        empty.hidden = true;
        empty.style.display = "none";
        refreshPushed();
        return;
      }}
    }}
    let shown = 0;
    cards.forEach((card) => {{
      const ok = !q || card.dataset.search.includes(q);
      card.hidden = !ok;
      if (ok) shown += 1;
    }});
    sections.forEach((section) => {{
      section.hidden = !Array.from(section.querySelectorAll("[data-search]")).some((card) => !card.hidden);
    }});
    empty.hidden = shown !== 0;
    empty.style.display = shown === 0 ? "block" : "none";
    refreshPushed();
  }}
  const cacheKey = "osc-pushed-v1";
  const pending = new Set();
  const failed = new Set();
  const queue = [];
  let active = 0;
  let blocked = false;
  function readCache() {{
    try {{ return JSON.parse(localStorage.getItem(cacheKey) || "{{}}"); }}
    catch (error) {{ return {{}}; }}
  }}
  function writeCache(cache) {{
    try {{ localStorage.setItem(cacheKey, JSON.stringify(cache)); }}
    catch (error) {{}}
  }}
  function hkDay(iso) {{
    const moment = new Date(iso);
    if (Number.isNaN(moment.getTime())) return String(iso || "").slice(0, 10);
    return new Intl.DateTimeFormat("en-CA", {{
      timeZone: "Asia/Hong_Kong",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }}).format(moment);
  }}
  function paint(name, day) {{
    document.querySelectorAll("article.card[data-repo]").forEach((card) => {{
      if (card.dataset.repo !== name) return;
      const node = card.querySelector("time.pushed");
      if (!node) return;
      node.dateTime = day;
      node.textContent = "最近推送 " + day;
    }});
  }}
  function cachedDay(name) {{
    const hit = readCache()[name];
    if (!hit || !hit.day || Date.now() - hit.at > 6 * 60 * 60 * 1000) return "";
    return hit.day;
  }}
  function pump() {{
    if (blocked) return;
    while (active < 4 && queue.length) {{
      const name = queue.shift();
      active += 1;
      fetch("https://api.github.com/repos/" + name, {{
        headers: {{ Accept: "application/vnd.github+json" }}
      }}).then((response) => {{
        if (response.status === 403 || response.status === 429) {{
          blocked = true;
          queue.length = 0;
          return null;
        }}
        if (!response.ok) {{
          failed.add(name);
          return null;
        }}
        return response.json();
      }}).then((data) => {{
        if (!data || !data.pushed_at) return;
        const day = hkDay(data.pushed_at);
        const cache = readCache();
        cache[name] = {{ day: day, at: Date.now() }};
        writeCache(cache);
        paint(name, day);
      }}).catch(() => {{
        failed.add(name);
      }}).finally(() => {{
        active -= 1;
        pending.delete(name);
        pump();
      }});
    }}
  }}
  function enqueue(name) {{
    if (!name || blocked || pending.has(name) || failed.has(name)) return;
    const day = cachedDay(name);
    if (day) {{
      paint(name, day);
      return;
    }}
    pending.add(name);
    queue.push(name);
    pump();
  }}
  function refreshPushed() {{
    document.querySelectorAll("article.card[data-repo]").forEach((card) => {{
      if (card.hidden || card.closest("[hidden]")) return;
      const rect = card.getBoundingClientRect();
      if (rect.bottom < -240 || rect.top > window.innerHeight + 240) return;
      enqueue(card.dataset.repo);
    }});
  }}
  document.querySelectorAll("article.card[data-repo]").forEach((card) => {{
    const day = cachedDay(card.dataset.repo);
    if (day) paint(card.dataset.repo, day);
  }});
  let ticking = false;
  function schedulePushed() {{
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {{
      ticking = false;
      refreshPushed();
    }});
  }}
  window.addEventListener("scroll", schedulePushed, {{ passive: true }});
  window.addEventListener("resize", schedulePushed);
  input.addEventListener("input", apply);
  refreshPushed();
  document.addEventListener("keydown", (event) => {{
    if (event.key === "/" && document.activeElement !== input) {{
      event.preventDefault();
      input.focus();
    }}
  }});
}})();
</script>
</body>
</html>
"""


def render(catalog: dict) -> None:
    catalog["base_url"] = base_url() or catalog.get("base_url") or ""
    root_html = render_document(catalog, None)
    (ROOT / "index.html").write_text(root_html)
    for category in CATEGORIES:
        folder = ROOT / category["dir"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(render_document(catalog, category["id"]))
    (ROOT / ".nojekyll").write_text("")
    save_json(DATA / "catalog.json", catalog)


def write_outputs(catalog: dict, new_projects: list[dict], mode: str) -> None:
    note = notification_text(catalog, new_projects, mode)
    (ROOT / "notifications").mkdir(exist_ok=True)
    (ROOT / "notifications" / "latest.md").write_text(note)
    (ROOT / "email").mkdir(exist_ok=True)
    (ROOT / "email" / "latest.html").write_text(email_html(catalog, new_projects, mode))
    send_email(note)


def notification_text(catalog: dict, new_projects: list[dict], mode: str) -> str:
    grouped = projects_by_category(catalog)
    counts = " · ".join(f"{category['title']} {len(grouped[category['id']])}" for category in CATEGORIES)
    url = catalog.get("base_url") or PAGES_ROOT
    headline = "Open Source Catalog 已建立基礎目錄" if mode == "bootstrap" else "Open Source Catalog 已更新"
    lines = [
        f"# {headline}",
        "",
        f"- 時間：{format_hk(catalog['updated_at'])}",
        f"- 今次新增：{len(new_projects)} 個開源項目",
        f"- 目錄總數：{len(catalog['projects'])} 個開源項目",
        f"- 分類：{counts}",
        f"- 瀏覽：{url}",
        "",
    ]
    rate = catalog.get("rate_limit") or {}
    if rate.get("limit"):
        lines.insert(
            6,
            f"- GitHub 請求配額：已用 {rate['used']}/{rate['limit']}（{rate['percent']}%，目標 80%）",
        )
    if new_projects:
        lines.append("## 新增")
        lines.append("")
        ordered = sorted(new_projects, key=lambda project: (-int(project.get("stars") or 0), project["full_name"].lower()))
        for project in ordered[:30]:
            lines.append(
                f"- {project['full_name']} · ★ {fmt_stars(project.get('stars') or 0)} · {project['category']} · {project['url']}"
            )
        if len(ordered) > 30:
            lines.append(f"- 另外 {len(ordered) - 30} 個見完整目錄")
    else:
        lines.append("今次沒有新項目。已同步現有項目嘅 stars，排序保持由多至少。已收錄項目冇重複加入。")
    lines.append("")
    return "\n".join(lines)


def email_html(catalog: dict, new_projects: list[dict], mode: str) -> str:
    url = catalog.get("base_url") or repo_web_url()
    grouped = projects_by_category(catalog)
    new_ids = {project["id"] for project in new_projects}
    blocks = []
    for category in CATEGORIES:
        if mode == "bootstrap" or len(new_projects) > 18:
            picks = grouped[category["id"]][:3]
        else:
            picks = [project for project in grouped[category["id"]] if project["id"] in new_ids]
        if not picks:
            continue
        rows = []
        for project in picks:
            rows.append(
                f"""
<tr>
  <td style="padding:14px 0;border-top:1px solid #2a261f;">
    <div style="font-size:16px;font-weight:650;color:#f6f1e8;">{esc(project["name"])}</div>
    <div style="color:#e4b15a;font-size:13px;margin-top:2px;">★ {fmt_stars(project.get("stars") or 0)} · {esc(project["full_name"])}</div>
    <div style="color:#d9d1c5;font-size:14px;line-height:1.5;margin-top:6px;">{esc(project.get("summary"))}</div>
    <div style="margin-top:8px;"><a href="{esc(project["url"])}" style="color:#e4b15a;text-decoration:none;">GitHub</a></div>
  </td>
</tr>
""".strip()
            )
        blocks.append(
            f"""
<tr><td style="padding:22px 8px 0;">
  <div style="font-family:Georgia,'Times New Roman',serif;font-size:22px;color:#f6f1e8;">{esc(category["title"])}</div>
  <div style="color:#b7b0a4;font-size:13px;margin-top:2px;">{len(grouped[category["id"]])} 個項目</div>
</td></tr>
{''.join(rows)}
""".strip()
        )
    if url:
        button = f'<a href="{esc(url)}" style="display:inline-block;background:#e4b15a;color:#1c140c;text-decoration:none;font-weight:700;padding:12px 22px;border-radius:999px;">打開完整目錄</a>'
    else:
        button = '<span style="color:#d9d1c5;">完整目錄喺 repo 根目錄嘅 index.html。啟用 GitHub Pages 之後，呢封信會帶網站連結。</span>'
    intro = (
        "第一版收錄 200 個開源項目，另外附上幾篇相關論文。下面係每個分類 stars 最高嘅幾個。"
        if mode == "bootstrap"
        else (
            f"今次新增 {len(new_projects)} 個未收錄項目。"
            if new_projects
            else "今次沒有新項目。現有項目嘅 stars 已同步，已收錄項目冇重複加入。"
        )
    )
    counts = "".join(
        f'<td style="padding:8px;color:#f6f1e8;font-size:13px;">{esc(category["title"])}<br><b>{len(grouped[category["id"]])}</b></td>'
        for category in CATEGORIES
    )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<body style="margin:0;padding:0;background:#090a0d;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#090a0d;">
    <tr><td align="center" style="padding:28px 12px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:640px;max-width:640px;background:#12141a;border-radius:20px;overflow:hidden;">
        <tr><td style="padding:32px 28px 8px;background:#12141a;">
          <div style="letter-spacing:0.16em;text-transform:uppercase;color:#e4b15a;font-size:12px;font-family:Georgia,serif;">Open Source Catalog</div>
          <div style="font-family:Georgia,'Times New Roman',serif;font-size:36px;line-height:1.05;color:#f6f1e8;margin-top:8px;">開源目錄更新</div>
          <div style="color:#d9d1c5;font-size:15px;line-height:1.6;margin-top:12px;">{esc(intro)}</div>
          <div style="color:#b7b0a4;font-size:13px;margin-top:8px;">{esc(format_hk(catalog["updated_at"]))}</div>
        </td></tr>
        <tr><td style="padding:8px 20px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{counts}</tr></table>
        </td></tr>
        <tr><td style="padding:8px 20px 8px;">{''.join(f'<table role="presentation" width="100%">{block}</table>' for block in blocks)}</td></tr>
        <tr><td align="center" style="padding:28px 24px 12px;">{button}</td></tr>
        <tr><td style="padding:8px 28px 28px;color:#8d867c;font-size:12px;line-height:1.5;">分類次序：Gaussian Splatting、World Model、Image to 3D、AI Agent、圖像、影片、VFX / CG / Blender、Stock Trading、Crypto Trading。開源項目按 stars 由多至少。已收錄項目唔會再加入。</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_email(note: str) -> bool:
    user = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("NOTIFY_EMAIL", "").strip() or DEFAULT_EMAIL
    if not user or not password:
        print(f"email saved at email/latest.html; SMTP not configured, not sent to {recipient}")
        return False
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    subject_line = note.splitlines()[0].lstrip("# ").strip()
    message = MIMEMultipart("alternative")
    message["Subject"] = subject_line
    message["From"] = user
    message["To"] = recipient
    message.attach(MIMEText(note, "plain", "utf-8"))
    message.attach(MIMEText((ROOT / "email" / "latest.html").read_text(), "html", "utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        smtp.sendmail(user, [recipient], message.as_string())
    print(f"email sent to {recipient}")
    return True


def text_blob(repo: dict) -> str:
    return " ".join(
        [
            repo.get("full_name") or "",
            repo.get("name") or "",
            repo.get("description") or "",
            " ".join(repo.get("topics") or []),
        ]
    ).lower()


def blocked(repo: dict) -> bool:
    name = (repo.get("name") or "").lower()
    blob = text_blob(repo)
    bad_name = (
        "awesome",
        "checklist",
        "leak",
        "best-practice",
        "best_practice",
        "skill",
        "cheatsheet",
        "paper-list",
        "papers-with",
        "for-beginners",
        "from-scratch",
        "-guide",
        "tutorial",
    )
    if any(part in name for part in bad_name):
        return True
    bad_text = ("curated list", "awesome list", "system prompt", "leaked prompt", "job search")
    return any(part in blob for part in bad_text)


def relevant(category: str, repo: dict) -> bool:
    if repo.get("fork") or repo.get("archived"):
        return False
    if not (repo.get("description") or "").strip():
        return False
    if blocked(repo):
        return False
    blob = text_blob(repo)
    name = (repo.get("name") or "").lower()
    if category == "gaussian-splatting":
        if any(part in name for part in ("comfyui", "awesome", "notes", "survey")):
            return False
        return any(key in blob for key in ("gaussian", "splat", "3dgs"))
    if category == "world-model":
        if any(part in name for part in ("awesome", "comfyui", "agentworld")):
            return False
        if "code world model" in blob or "enterprise world model" in blob:
            return False
        return "world model" in blob or "world models" in blob
    if category == "image-to-3d":
        if any(part in name for part in ("comfyui", "winportable", "awesome", "benchmark", "wrapper")):
            return False
        keys = (
            "image-to-3d",
            "image to 3d",
            "text-to-3d",
            "text to 3d",
            "3d generation",
            "3d reconstruction",
            "single image",
            "triposr",
            "trellis",
            "hunyuan3d",
            "dust3r",
            "vggt",
        )
        return any(key in blob for key in keys)
    if category == "ai-agent":
        keys = ("agent", "autogen", "langchain", "langgraph", "multi-agent", "tool call", "autonomous")
        banned = ("stable-diffusion", "comfyui", "llama.cpp")
        return any(key in blob for key in keys) and not any(key in (repo.get("name") or "").lower() for key in banned)
    if category == "image":
        return any(key in blob for key in ("image", "diffusion", "photo", "vision", "ocr", "upscal"))
    if category == "video":
        return any(key in blob for key in ("video", "film", "ffmpeg", "movie", "editor"))
    if category == "vfx-cg-blender":
        return any(key in blob for key in ("blender", "render", "vfx", "3d", "graphics", "gaussian", "shader", "composit"))
    if category == "stock-trading":
        name = (repo.get("name") or "").lower()
        topics = set(repo.get("topics") or [])
        if "crypto-trading" in topics or any(part in name for part in ("crypto", "bitcoin", "binance", "freqtrade")):
            return False
        return any(key in blob for key in ("trad", "quant", "stock", "backtest", "portfolio", "finance", "market"))
    if category == "crypto-trading":
        return any(key in blob for key in ("trad", "exchange", "bot", "backtest", "freqtrade", "ccxt", "arbitrage"))
    return False


def search_repos(query: str, page: int) -> tuple[list[dict], bool]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": page}
    )
    data = fetch_json(
        f"https://api.github.com/search/repositories?{params}",
        f"update-{query}-p{page}",
        "search",
        use_cache=False,
    )
    items = data.get("items") or []
    total = min(int(data.get("total_count") or 0), 1000)
    more = bool(items) and page * 100 < total and len(items) == 100 and page < 10
    return items, more


def graphql(query: str) -> dict:
    if not token():
        return {}
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={**gh_headers(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def apply_repo_payload(project: dict, repo: dict) -> bool:
    stars = int(repo.get("stargazers_count") or 0)
    changed = stars != project.get("stars")
    project["stars"] = stars
    project["archived"] = bool(repo.get("archived"))
    project["pushed_at"] = hk_day(repo.get("pushed_at") or "")
    if repo.get("language"):
        project["language"] = repo["language"]
    license_name = license_of(repo)
    if license_name:
        project["license"] = license_name
    homepage = repo.get("homepage") or ""
    if str(homepage).startswith("http"):
        project["homepage"] = homepage
    description = (repo.get("description") or "").strip()
    if description:
        project["description"] = description
        if not project.get("summary_locked"):
            project["summary"] = description
    if repo.get("topics"):
        project["topics"] = list(repo.get("topics") or [])[:8]
    return changed


def fetch_repo_live(full_name: str) -> dict | None:
    key = full_name.lower()
    if key in FETCHED or core_quota_met():
        return None
    FETCHED.add(key)
    try:
        repo = fetch_json(
            f"https://api.github.com/repos/{full_name}",
            f"live-{full_name}",
            "repos",
            use_cache=False,
        )
    except RateLimitExceeded as exc:
        print(exc)
        RATE["remaining"] = 0
        return None
    if not repo or repo.get("message"):
        return None
    return repo


def refresh_stars(catalog: dict) -> int:
    if not token():
        print("no GitHub token, skip star refresh")
        return 0
    changed = 0
    for project in catalog["projects"]:
        if project.get("type") != "github":
            continue
        repo = fetch_repo_live(project["full_name"])
        if not repo:
            if core_quota_met():
                break
            continue
        if apply_repo_payload(project, repo):
            changed += 1
    return changed


def discover_new(catalog: dict) -> tuple[list[dict], list[str]]:
    existing = {project["full_name"].lower() for project in catalog["projects"]}
    denylist = {name.lower() for name in load_json(DATA / "denylist.json", [])}
    found: dict[str, tuple[str, dict]] = {}
    pool: list[str] = []
    seen_pool = set(FETCHED)
    queries = [(category, query) for category in CATEGORIES for query in QUERIES[category["id"]]]
    more_pages = {id(query): True for _, query in queries}

    def remember(full_name: str) -> None:
        key = full_name.lower()
        if key and key not in seen_pool:
            seen_pool.add(key)
            pool.append(full_name)

    def consider(category_id: str, repo: dict) -> None:
        key = (repo.get("full_name") or "").lower()
        full_name = repo.get("full_name") or ""
        if full_name:
            remember(full_name)
        if not key or key in existing or key in denylist:
            return
        threshold = MIN_NEW[category_id]
        if len(catalog["projects"]) < 200:
            threshold = max(200, threshold // 4)
        if int(repo.get("stargazers_count") or 0) < threshold:
            return
        if not relevant(category_id, repo):
            return
        current = found.get(key)
        if current is None or repo.get("stargazers_count", 0) > current[1].get("stargazers_count", 0):
            found[key] = (category_id, repo)

    def drain() -> None:
        while pool and not core_quota_met():
            full_name = pool.pop(0)
            repo = fetch_repo_live(full_name)
            if not repo:
                continue
            current = found.get(full_name.lower())
            if current:
                found[full_name.lower()] = (current[0], repo)

    for page in range(1, 11):
        progressed = False
        for category, query in queries:
            if not more_pages.get(id(query), False):
                continue
            try:
                items, more = search_repos(query, page)
            except (RuntimeError, RateLimitExceeded) as exc:
                print(exc)
                more_pages[id(query)] = False
                continue
            more_pages[id(query)] = more
            progressed = progressed or bool(items)
            for repo in items:
                consider(category["id"], repo)
        drain()
        if core_quota_met() or not progressed:
            break
    ranked = sorted(found.values(), key=lambda item: -int(item[1].get("stargazers_count") or 0))
    per_category: dict[str, int] = {category["id"]: 0 for category in CATEGORIES}
    chosen = []
    limit = 24 if len(catalog["projects"]) < 200 else 8
    per_limit = 8 if len(catalog["projects"]) < 200 else 2
    added_at = iso_hk()
    for category_id, repo in ranked:
        if len(chosen) >= limit or per_category[category_id] >= per_limit:
            continue
        summary = (repo.get("description") or "").strip()
        project = project_from_repo(repo, category_id, summary, False, added_at)
        chosen.append(project)
        per_category[category_id] += 1
        existing.add(project["full_name"].lower())
    return chosen, list(seen_pool)


def spend_core_quota(names: list[str]) -> None:
    """Keep reading public repo metadata until 80% of the core quota is used."""
    names = [name for name in names if name]
    if not token() or not names or core_quota_met():
        return
    suffixes = ("/languages", "/commits?per_page=1", "/releases?per_page=1", "/stargazers?per_page=1")
    guard = 0
    stalls = 0
    while not core_quota_met() and guard < 20000:
        name = names[guard % len(names)]
        suffix = suffixes[(guard // len(names)) % len(suffixes)]
        page = guard // (len(names) * len(suffixes))
        url = f"https://api.github.com/repos/{name}{suffix}"
        if page:
            url += ("&" if "?" in suffix else "?") + f"page={page + 1}"
        before = int(RATE["remaining"])
        try:
            fetch_json(url, f"spend-{guard}-{name}", "repos", use_cache=False)
        except RateLimitExceeded as exc:
            print(exc)
            RATE["remaining"] = 0
            return
        except RuntimeError as exc:
            print(exc)
        guard += 1
        if int(RATE["remaining"]) == before:
            stalls += 1
            if stalls > 8:
                print("core quota stopped decreasing; leaving the rest unused")
                return
        else:
            stalls = 0


def record_rate_usage(catalog: dict) -> None:
    limit = int(RATE["limit"] or 0)
    remaining = int(RATE["remaining"] or 0)
    window_used = max(0, limit - remaining)
    used = max(window_used, int(RATE["spent"] or 0))
    percent = round(100 * used / limit, 1) if limit else 0
    catalog["rate_limit"] = {"used": used, "limit": limit, "remaining": remaining, "percent": percent}
    print(f"GitHub core requests used {used}/{limit} ({percent}%)", flush=True)
    if limit and used < math.ceil(limit * CORE_USAGE_TARGET):
        print("warning: this run used less than 80% of the GitHub core rate limit", flush=True)


def update() -> dict:
    catalog_path = DATA / "catalog.json"
    if not catalog_path.exists():
        return bootstrap(force=False)
    catalog = load_json(catalog_path, {})
    FETCHED.clear()
    RATE["spent"] = 0
    wait_for_core_budget()
    refresh_stars(catalog)
    new_projects, seen_names = discover_new(catalog)
    spend_core_quota(seen_names)
    record_rate_usage(catalog)
    catalog["projects"].extend(new_projects)
    catalog["updated_at"] = iso_hk()
    catalog["last_new_ids"] = [project["id"] for project in new_projects]
    catalog["base_url"] = base_url() or catalog.get("base_url") or ""
    save_json(catalog_path, catalog)
    render(catalog)
    write_outputs(catalog, new_projects, "update")
    validate(catalog)
    return catalog


def validate(catalog: dict | None = None) -> None:
    catalog = catalog or load_json(DATA / "catalog.json", {})
    projects = catalog.get("projects") or []
    if len(projects) < 200:
        raise SystemExit(f"expected at least 200 projects, found {len(projects)}")
    ids = [project["id"] for project in projects]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate project ids")
    names = [project["full_name"].lower() for project in projects]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate repository names")
    grouped = projects_by_category(catalog)
    order = [category["id"] for category in CATEGORIES]
    if list(grouped) != order:
        raise SystemExit("category order mismatch")
    for category in CATEGORIES:
        stars = [int(project.get("stars") or 0) for project in grouped[category["id"]]]
        if stars != sorted(stars, reverse=True):
            raise SystemExit(f"stars not sorted in {category['id']}")
        if not grouped[category["id"]]:
            raise SystemExit(f"empty category {category['id']}")
        for project in grouped[category["id"]]:
            for field in ("summary", "url", "name", "full_name"):
                if not project.get(field):
                    raise SystemExit(f"missing {field} on {project.get('full_name')}")
    if (catalog.get("base_url") or "").rstrip("/") + "/" != PAGES_ROOT:
        raise SystemExit(f"base_url must be the GitHub Pages root {PAGES_ROOT}")
    html_text = (ROOT / "index.html").read_text()
    if PAGES_ROOT not in html_text:
        raise SystemExit("index canonical is not the GitHub Pages root")
    if 'href="ai-agent/"' not in html_text or 'href="#ai-agent"' in html_text:
        raise SystemExit("home must link to category pages instead of scrolling")
    for project in projects:
        if project["full_name"] not in html_text:
            raise SystemExit(f"index missing {project['full_name']}")
        if project.get("summary_locked"):
            length = len(project.get("summary") or "")
            if length < 80 or length > 150:
                raise SystemExit(f"summary for {project['full_name']} is {length} chars, want about 100")
    for category in CATEGORIES:
        page = (ROOT / category["dir"] / "index.html").read_text()
        if category["title"] not in page:
            raise SystemExit(f"subpage missing title {category['title']}")
        if 'href="../"' not in page:
            raise SystemExit(f"{category['dir']} does not link back to the catalog")
        page_root = f"{PAGES_ROOT}{category['dir']}/"
        if page_root not in page:
            raise SystemExit(f"{category['dir']} canonical is not {page_root}")
        for project in grouped[category["id"]]:
            if project["full_name"] not in page:
                raise SystemExit(f"{category['dir']} missing {project['full_name']}")
    print(f"validated {len(projects)} projects across {len(CATEGORIES)} categories")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "bootstrap"
    force = "--force" in sys.argv
    if command == "bootstrap":
        catalog = bootstrap(force=force)
        validate(catalog)
    elif command == "update":
        update()
    elif command == "render":
        catalog = load_json(DATA / "catalog.json", {})
        render(catalog)
        validate(catalog)
    elif command == "validate":
        validate()
    elif command == "send-email":
        note = (ROOT / "notifications" / "latest.md").read_text()
        if not send_email(note):
            raise SystemExit(1)
    else:
        raise SystemExit("use bootstrap, update, render, validate, or send-email")


if __name__ == "__main__":
    main()
