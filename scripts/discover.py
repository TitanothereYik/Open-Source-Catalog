#!/usr/bin/env python3
"""Collect high-star open-source candidates for Open Source Catalog."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
OUT = Path("/tmp/catalog-review.txt")
SELECTION = ROOT / "data" / "selection.json"

CATEGORIES = [
    "ai-agent",
    "image",
    "video",
    "vfx-cg-blender",
    "stock-trading",
    "crypto-trading",
]

QUOTA = {
    "ai-agent": 42,
    "image": 36,
    "video": 32,
    "vfx-cg-blender": 32,
    "stock-trading": 30,
    "crypto-trading": 28,
}

MIN_STARS = {
    "ai-agent": 400,
    "image": 400,
    "video": 300,
    "vfx-cg-blender": 300,
    "stock-trading": 120,
    "crypto-trading": 150,
}

QUERIES = {
    "ai-agent": [
        "topic:ai-agent",
        "topic:ai-agents",
        "topic:autonomous-agents",
        "topic:llm-agent",
        "topic:multi-agent",
        "topic:agent-framework",
    ],
    "image": [
        "topic:stable-diffusion",
        "topic:image-generation",
        "topic:comfyui",
        "topic:super-resolution",
        "topic:diffusion-models",
        "topic:image-processing stars:>700",
    ],
    "video": [
        "topic:video-generation",
        "topic:text-to-video",
        "topic:video-editing",
        "topic:video-processing stars:>300",
        "topic:text2video",
        "topic:ai-video",
    ],
    "vfx-cg-blender": [
        "topic:blender",
        "topic:computer-graphics",
        "topic:vfx",
        "topic:gaussian-splatting",
        "topic:3d-graphics",
        "topic:rendering",
    ],
    "stock-trading": [
        "topic:algorithmic-trading",
        "topic:quantitative-finance",
        "topic:stock-trading",
        "topic:backtesting",
        "topic:stock-market stars:>80",
        "topic:quant stars:>80",
    ],
    "crypto-trading": [
        "topic:crypto-trading",
        "topic:cryptocurrency-trading",
        "topic:trading-bot",
        "topic:bitcoin-trading",
        "topic:algorithmic-trading topic:cryptocurrency",
        "freqtrade OR hummingbot OR ccxt in:name stars:>50",
    ],
}

SEEDS = {
    "ai-agent": [
        "Significant-Gravitas/AutoGPT",
        "langchain-ai/langchain",
        "run-llama/llama_index",
        "microsoft/autogen",
        "crewAIInc/crewAI",
        "langgenius/dify",
        "All-Hands-AI/OpenHands",
        "FoundationAgents/MetaGPT",
        "langchain-ai/langgraph",
        "microsoft/semantic-kernel",
        "deepset-ai/haystack",
        "FlowiseAI/Flowise",
        "browser-use/browser-use",
        "assafelovic/gpt-researcher",
        "yoheinakajima/babyagi",
        "OpenBMB/ChatDev",
        "princeton-nlp/SWE-agent",
        "OpenInterpreter/open-interpreter",
        "Aider-AI/aider",
        "continuedev/continue",
        "cline/cline",
        "huggingface/smolagents",
        "pydantic/pydantic-ai",
        "mastra-ai/mastra",
        "letta-ai/letta",
        "mem0ai/mem0",
        "openai/openai-agents-python",
        "openai/swarm",
        "TransformerOptimus/SuperAGI",
        "reworkd/AgentGPT",
        "agno-agi/agno",
        "camel-ai/camel",
        "skyvern-ai/skyvern",
        "browserbase/stagehand",
        "microsoft/magentic-ui",
        "stanfordnlp/dspy",
        "langflow-ai/langflow",
        "ComposioHQ/composio",
        "e2b-dev/E2B",
        "block/goose",
        "gptme/gptme",
        "lavague-ai/LaVague",
        "KillianLucas/open-interpreter",
        "joshpxyne/gpt-migrate",
        "modelcontextprotocol/python-sdk",
        "lastmile-ai/mcp-agent",
    ],
    "image": [
        "AUTOMATIC1111/stable-diffusion-webui",
        "comfyanonymous/ComfyUI",
        "huggingface/diffusers",
        "invoke-ai/InvokeAI",
        "lllyasviel/Fooocus",
        "lllyasviel/ControlNet",
        "lllyasviel/stable-diffusion-webui-forge",
        "vladmandic/automatic",
        "bmaltais/kohya_ss",
        "kohya-ss/sd-scripts",
        "Stability-AI/stablediffusion",
        "black-forest-labs/flux",
        "CompVis/stable-diffusion",
        "CompVis/latent-diffusion",
        "apple/ml-stable-diffusion",
        "mcmonkeyprojects/SwarmUI",
        "xinntao/Real-ESRGAN",
        "upscayl/upscayl",
        "TencentARC/GFPGAN",
        "openai/CLIP",
        "NVlabs/stylegan3",
        "NVlabs/stylegan2",
        "ImageMagick/ImageMagick",
        "python-pillow/Pillow",
        "lovell/sharp",
        "libvips/libvips",
        "darktable-org/darktable",
        "opencv/opencv",
        "Sanster/IOPaint",
        "Acly/krita-ai-diffusion",
        "lllyasviel/IC-Light",
        "instantX-research/InstantID",
        "cubiq/ComfyUI_IPAdapter_plus",
        "chaiNNer-org/chaiNNer",
        "huggingface/pytorch-image-models",
        "JingyunLiang/SwinIR",
        "timothybrooks/instruct-pix2pix",
        "bghira/SimpleTuner",
        "tesseract-ocr/tesseract",
        "JaidedAI/EasyOCR",
        "PaddlePaddle/PaddleOCR",
        "Beep6581/RawTherapee",
    ],
    "video": [
        "FFmpeg/FFmpeg",
        "mpv-player/mpv",
        "obsproject/obs-studio",
        "OpenShot/openshot-qt",
        "mltframework/shotcut",
        "Zulko/moviepy",
        "remotion-dev/remotion",
        "Lightricks/LTX-Video",
        "hpcaitech/Open-Sora",
        "THUDM/CogVideo",
        "Wan-Video/Wan2.1",
        "lllyasviel/FramePack",
        "guoyww/AnimateDiff",
        "genmoai/mochi",
        "AILab-CVC/VideoCrafter",
        "HumanAIGC/AnimateAnyone",
        "Tencent-Hunyuan/HunyuanVideo",
        "Kosinkadink/ComfyUI-AnimateDiff-Evolved",
        "Stability-AI/generative-models",
        "numz/ComfyUI-SeedVR2_VideoUpscaler",
        "openai/consistency_models",
        "showlab/Tune-A-Video",
        "Magic-Research/magic-animate",
        "MooreThreads/Moore-AnimateAnyone",
        "open-mmlab/mmaction2",
        "mifi/editly",
        "jellyfin/jellyfin",
        "yt-dlp/yt-dlp",
        "k4yt3x/video2x",
        "HandBrake/HandBrake",
    ],
    "vfx-cg-blender": [
        "blender/blender",
        "AcademySoftwareFoundation/openvdb",
        "AcademySoftwareFoundation/MaterialX",
        "AcademySoftwareFoundation/OpenColorIO",
        "AcademySoftwareFoundation/openexr",
        "AcademySoftwareFoundation/OpenImageIO",
        "AcademySoftwareFoundation/OpenShadingLanguage",
        "PixarAnimationStudios/OpenUSD",
        "PixarAnimationStudios/OpenSubdiv",
        "alembic/alembic",
        "NatronGitHub/Natron",
        "opentoonz/opentoonz",
        "synfig/synfig",
        "mitsuba-renderer/mitsuba3",
        "mmp/pbrt-v4",
        "embree/embree",
        "ospray/ospray",
        "google/filament",
        "mrdoob/three.js",
        "pmndrs/react-three-fiber",
        "BabylonJS/Babylon.js",
        "godotengine/godot",
        "assimp/assimp",
        "graphdeco-inria/gaussian-splatting",
        "NVlabs/instant-ngp",
        "nerfstudio-project/nerfstudio",
        "facebookresearch/pytorch3d",
        "isl-org/Open3D",
        "cnr-isti-vclab/meshlab",
        "alicevision/Meshroom",
        "armorpaint/armorpaint",
        "pixijs/pixijs",
        "armory3d/armory",
        "UPBGE/upbge",
        "carson-katri/dream-textures",
        "pencil2d/pencil",
        "tahoma2d/tahoma2d",
        "libigl/libigl",
        "wjakob/instant-meshes",
        "shader-slang/slang",
        "playcanvas/engine",
        "luxcorerender/luxcorerender",
        "appleseedhq/appleseed",
        "KhronosGroup/glTF",
        "bulletphysics/bullet3",
    ],
    "stock-trading": [
        "microsoft/qlib",
        "vnpy/vnpy",
        "quantopian/zipline",
        "mementum/backtrader",
        "kernc/backtesting.py",
        "polakowo/vectorbt",
        "TA-Lib/ta-lib",
        "bukosabino/ta",
        "twopirllc/pandas-ta",
        "ranaroussi/yfinance",
        "akfamily/akshare",
        "waditu/tushare",
        "quantconnect/Lean",
        "nautechsystems/nautilus_trader",
        "ranaroussi/quantstats",
        "pmorissette/ffn",
        "pmorissette/bt",
        "quantopian/alphalens",
        "quantopian/pyfolio",
        "AI4Finance-Foundation/FinRL",
        "AI4Finance-Foundation/FinGPT",
        "ricequant/rqalpha",
        "shidenggui/easytrader",
        "fasiondog/hikyuu",
        "lballabio/QuantLib",
        "google/tf-quant-finance",
        "dcajasn/Riskfolio-Lib",
        "robertmartin8/PyPortfolioOpt",
        "erdewit/ib_insync",
        "alpacahq/alpaca-py",
        "DaveSkender/Stock.Indicators",
        "peerchemist/finta",
        "jealous/stockstats",
        "edtechre/pybroker",
        "kieran-mackle/AutoTrader",
        "robcarver17/pysystemtrade",
        "tradingview/lightweight-charts",
        "Lumiwealth/lumibot",
        "stefan-jansen/machine-learning-for-trading",
        "blankly-finance/blankly",
    ],
    "crypto-trading": [
        "freqtrade/freqtrade",
        "ccxt/ccxt",
        "hummingbot/hummingbot",
        "Drakkar-Software/OctoBot",
        "jesse-ai/jesse",
        "Superalgos/Superalgos",
        "askmike/gekko",
        "DeviaVir/zenbot",
        "bmoscon/cryptofeed",
        "sammchardy/python-binance",
        "enarjord/passivbot",
        "tensortrade-org/tensortrade",
        "freqtrade/freqtrade-strategies",
        "nkaz001/hftbacktest",
        "rotki/rotki",
        "whittlem/pycryptobot",
        "CyberPunkMetalHead/Binance-volatility-trading-bot",
        "ccxt/binance-trade-bot",
        "edeng23/binance-trade-bot",
        "blankly-finance/blankly",
        "jesse-ai/jesse",
        "smallevilbeast/binance-quant",
        "CryptoSignal/Crypto-Signal",
        "kivancozbilgic/Binance-Trading-Bot",
        "mementum/bbroker",
        "aschleg/cryptos",
        "ccxt/ccxt",
        "bmoscon/cryptostore",
        "tardis-dev/tardis-python",
        "solidquant/whirlpool",
        "freqtrade/frequi",
        "iterativv/NostalgiaForInfinity",
    ],
}

PAPERS = [
    {
        "id": "arxiv:2210.03629",
        "category": "ai-agent",
        "repo": "ysymyth/ReAct",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2210.03629",
        "summary": "提出推理同行動交替進行：語言模型先寫低自己嘅思考，再調用工具，然後按觀察結果繼續推理。",
    },
    {
        "id": "arxiv:2304.03442",
        "category": "ai-agent",
        "repo": "joonspk-research/generative_agents",
        "title": "Generative Agents: Interactive Simulacra of Human Behavior",
        "year": 2023,
        "url": "https://arxiv.org/abs/2304.03442",
        "summary": "用記憶、反思同計劃，模擬小鎮入面多個 AI 角色點樣自己過日常、互相影響。",
    },
    {
        "id": "arxiv:2303.11366",
        "category": "ai-agent",
        "repo": "noahshinn/reflexion",
        "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "year": 2023,
        "url": "https://arxiv.org/abs/2303.11366",
        "summary": "Agent 用自然語言總結自己嘅失敗，記住教訓再試，而唔係靠更新模型權重。",
    },
    {
        "id": "arxiv:2305.16291",
        "category": "ai-agent",
        "repo": "MineDojo/Voyager",
        "title": "Voyager: An Open-Ended Embodied Agent with Large Language Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2305.16291",
        "summary": "一個喺 Minecraft 入面自己寫程式、累積技能庫，可以持續探索同完成新任務嘅 agent。",
    },
    {
        "id": "arxiv:2112.10752",
        "category": "image",
        "repo": "CompVis/latent-diffusion",
        "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
        "year": 2022,
        "url": "https://arxiv.org/abs/2112.10752",
        "summary": "喺壓縮後嘅潛在空間做擴散，用文字生成高解像圖像，係後來大量開源圖像工具嘅基礎。",
    },
    {
        "id": "arxiv:2307.01952",
        "category": "image",
        "repo": "Stability-AI/generative-models",
        "title": "SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis",
        "year": 2023,
        "url": "https://arxiv.org/abs/2307.01952",
        "summary": "Stable Diffusion 嘅較大版本，改善構圖、文字同整體畫質，適合高解像生成。",
    },
    {
        "id": "arxiv:2302.05543",
        "category": "image",
        "repo": "lllyasviel/ControlNet",
        "title": "Adding Conditional Control to Text-to-Image Diffusion Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2302.05543",
        "summary": "用邊緣、姿勢、深度等條件圖控制擴散模型，生成時可以跟住指定結構行。",
    },
    {
        "id": "arxiv:2211.09800",
        "category": "image",
        "repo": "timothybrooks/instruct-pix2pix",
        "title": "InstructPix2Pix: Learning to Follow Image Editing Instructions",
        "year": 2023,
        "url": "https://arxiv.org/abs/2211.09800",
        "summary": "用自然語言指令直接改一張現有圖像，例如換背景、改物件或者轉風格。",
    },
    {
        "id": "arxiv:2307.04725",
        "category": "video",
        "repo": "guoyww/AnimateDiff",
        "title": "AnimateDiff: Animate Your Personalized Text-to-Image Diffusion Models without Specific Tuning",
        "year": 2023,
        "url": "https://arxiv.org/abs/2307.04725",
        "summary": "畀靜態擴散模型加一個時間模組，唔使逐個模型再訓練，都可以生成短片同動畫。",
    },
    {
        "id": "arxiv:2311.15127",
        "category": "video",
        "repo": "Stability-AI/generative-models",
        "title": "Stable Video Diffusion: Scaling Latent Video Diffusion Models to Large Datasets",
        "year": 2023,
        "url": "https://arxiv.org/abs/2311.15127",
        "summary": "Stability AI 將潛在擴散擴到影片，用大規模數據做圖像到影片同短片生成。",
    },
    {
        "id": "arxiv:2205.15868",
        "category": "video",
        "repo": "THUDM/CogVideo",
        "title": "CogVideo: Large-scale Pretraining for Text-to-Video Generation via Transformers",
        "year": 2022,
        "url": "https://arxiv.org/abs/2205.15868",
        "summary": "清華提出嘅大型文字到影片模型，用 transformer 做預訓練，並公開程式同權重。",
    },
    {
        "id": "arxiv:2412.03603",
        "category": "video",
        "repo": "Tencent-Hunyuan/HunyuanVideo",
        "title": "HunyuanVideo: A Systematic Framework For Large Video Generative Models",
        "year": 2024,
        "url": "https://arxiv.org/abs/2412.03603",
        "summary": "騰訊混元嘅大型開源影片生成框架，涵蓋數據、訓練同推理，用來做高質文字到影片。",
    },
    {
        "id": "arxiv:2308.04079",
        "category": "vfx-cg-blender",
        "repo": "graphdeco-inria/gaussian-splatting",
        "title": "3D Gaussian Splatting for Real-Time Radiance Field Rendering",
        "year": 2023,
        "url": "https://arxiv.org/abs/2308.04079",
        "summary": "用大量 3D Gaussian 表示場景，可以由相片重建立體場景，並做到即時渲染。",
    },
    {
        "id": "arxiv:2003.08934",
        "category": "vfx-cg-blender",
        "repo": "bmild/nerf",
        "title": "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis",
        "year": 2020,
        "url": "https://arxiv.org/abs/2003.08934",
        "summary": "用神經網路表示一個立體場景，由多張相片合成新視角，係後來大量新視角合成工作嘅起點。",
    },
    {
        "id": "arxiv:2201.05989",
        "category": "vfx-cg-blender",
        "repo": "NVlabs/instant-ngp",
        "title": "Instant Neural Graphics Primitives with a Multiresolution Hash Encoding",
        "year": 2022,
        "url": "https://arxiv.org/abs/2201.05989",
        "summary": "NVIDIA 用多解析度 hash 編碼大幅加快神經圖形基元，NeRF 一類場景可以近乎即時訓練同渲染。",
    },
    {
        "id": "arxiv:2011.09607",
        "category": "stock-trading",
        "repo": "AI4Finance-Foundation/FinRL",
        "title": "FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance",
        "year": 2020,
        "url": "https://arxiv.org/abs/2011.09607",
        "summary": "用深度強化學習做自動股票交易嘅開源庫，提供市場環境、訓練流程同回測。",
    },
]


def gh_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "open-source-catalog",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def cache_path(kind: str, key: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in key)[:180]
    return CACHE / kind / f"{safe}.json"


def fetch_json(url: str, cache_key: str, kind: str) -> dict:
    path = cache_path(kind, cache_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text())
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        delay = 2.1
    elif kind == "repos":
        delay = 0.35
    else:
        delay = 6.4
    last_error = None
    for attempt in range(6):
        req = urllib.request.Request(url, headers=gh_headers())
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode())
            path.write_text(json.dumps(data))
            time.sleep(delay)
            return data
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()[:400]
            last_error = f"{exc.code} {body}"
            if exc.code == 404:
                path.write_text(json.dumps({"message": "Not Found"}))
                return {"message": "Not Found"}
            if exc.code == 422:
                print(f"invalid query {cache_key[:80]}", flush=True)
                return {"message": "Invalid"}
            if exc.code in (403, 429):
                wait = 20 + attempt * 15
                print(f"rate limit, sleep {wait}s ({cache_key[:60]})", flush=True)
                time.sleep(wait)
                continue
            print(f"http {exc.code} {cache_key[:80]}", flush=True)
            time.sleep(5)
        except urllib.error.URLError as exc:
            last_error = str(exc)
            time.sleep(5)
    raise SystemExit(f"failed {cache_key}: {last_error}")


def fetch_repo(full_name: str) -> dict | None:
    data = fetch_json(
        f"https://api.github.com/repos/{full_name}",
        f"repo-{full_name}",
        "repos",
    )
    if "full_name" not in data:
        print(f"missing repo {full_name}", flush=True)
        return None
    print(f"repo {data['stargazers_count']:7d} {data['full_name']}", flush=True)
    return data


def search(query: str, page: int = 1) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": page}
    )
    data = fetch_json(
        f"https://api.github.com/search/repositories?{params}",
        f"search-{query}-p{page}",
        "search",
    )
    if "items" not in data:
        print(f"search miss: {query} -> {str(data)[:160]}", flush=True)
        return []
    print(f"search {data.get('total_count')} :: {query}", flush=True)
    return data["items"]


def slim(repo: dict, category: str, seeded: bool) -> dict:
    lic = repo.get("license") or {}
    spdx = lic.get("spdx_id")
    if spdx in (None, "NOASSERTION"):
        spdx = None
    return {
        "full_name": repo["full_name"],
        "name": repo["name"],
        "url": repo["html_url"],
        "homepage": repo.get("homepage") or "",
        "description": (repo.get("description") or "").strip(),
        "stars": int(repo.get("stargazers_count") or 0),
        "language": repo.get("language") or "",
        "license": spdx or "",
        "topics": repo.get("topics") or [],
        "archived": bool(repo.get("archived")),
        "pushed_at": repo.get("pushed_at") or "",
        "category": category,
        "seeded": seeded,
    }


def text_of(repo: dict) -> str:
    return " ".join(
        [
            repo["full_name"],
            repo["name"],
            repo.get("description") or "",
            " ".join(repo.get("topics") or []),
        ]
    ).lower()


def is_list_repo(repo: dict) -> bool:
    name = repo["name"].lower()
    desc = (repo.get("description") or "").lower()
    if name.startswith("awesome"):
        return True
    if "awesome list" in desc or "curated list" in desc or desc.startswith("a list of"):
        return True
    return False


def spammy(repo: dict) -> bool:
    blob = text_of(repo)
    needles = (
        "airdrop",
        "guaranteed profit",
        "1000x",
        "signal group",
        "pump and dump",
        "mev bot drain",
    )
    return any(n in blob for n in needles)


def relevant(category: str, repo: dict) -> bool:
    if repo.get("fork"):
        return False
    if not repo.get("description"):
        return False
    if is_list_repo(repo) or spammy(repo):
        return False
    blob = text_of(repo)
    if category == "ai-agent":
        agentish = any(
            k in blob
            for k in (
                "agent",
                "autogen",
                "langchain",
                "langgraph",
                "crewai",
                "multi-agent",
                "tool call",
                "autonomous",
                "computer use",
                "browser use",
                "workflow",
                "orchestr",
            )
        )
        blocked = any(
            k in repo["name"].lower()
            for k in ("llama.cpp", "ollama", "stable-diffusion", "comfyui")
        )
        return agentish and not blocked
    if category == "image":
        keys = (
            "image",
            "diffusion",
            "photo",
            "vision",
            "upscal",
            "ocr",
            "pixel",
            "gan",
            "inpaint",
            "graphics",
        )
        return any(k in blob for k in keys)
    if category == "video":
        keys = ("video", "film", "ffmpeg", "movie", "animation", "editor", "frame")
        blocked = ("video game", "game engine")
        return any(k in blob for k in keys) and not any(k in blob for k in blocked)
    if category == "vfx-cg-blender":
        keys = (
            "blender",
            "render",
            "vfx",
            "3d",
            "graphics",
            "composit",
            "shader",
            "gaussian",
            "nerf",
            "scene",
            "geometry",
            "animation",
        )
        return any(k in blob for k in keys)
    if category == "stock-trading":
        keys = (
            "trad",
            "quant",
            "stock",
            "backtest",
            "portfolio",
            "finance",
            "market",
            "broker",
            "alpha",
            "indicator",
        )
        if not any(k in blob for k in keys):
            return False
        name = repo["name"].lower()
        topics = set(repo.get("topics") or [])
        if "crypto-trading" in topics or "cryptocurrency" in topics:
            return False
        if any(k in name for k in ("crypto", "bitcoin", "binance", "freqtrade", "ethereum")):
            return False
        return True
    if category == "crypto-trading":
        keys = (
            "trad",
            "exchange",
            "bot",
            "backtest",
            "freqtrade",
            "ccxt",
            "order",
            "arbitrage",
            "market",
            "strategy",
            "portfolio",
        )
        return any(k in blob for k in keys)
    return False


def merge_items(items: list[dict]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for repo in items:
        if "full_name" not in repo:
            continue
        key = repo["full_name"].lower()
        current = found.get(key)
        if current is None or repo.get("stargazers_count", 0) > current.get("stargazers_count", 0):
            found[key] = repo
    return found


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    by_cat: dict[str, dict[str, dict]] = {c: {} for c in CATEGORIES}
    for category, queries in QUERIES.items():
        for query in queries:
            for repo in search(query):
                by_cat[category][repo["full_name"].lower()] = repo
    # Seed lookup via OR queries, assigned to their category.
    for category, names in SEEDS.items():
        for name in names:
            if name.lower() in by_cat[category]:
                continue
            repo = fetch_repo(name)
            if repo:
                by_cat[category][repo["full_name"].lower()] = repo

    selected: dict[str, list[dict]] = {}
    lines = []
    for category in CATEGORIES:
        repos = list(by_cat[category].values())
        slimmed = []
        for repo in repos:
            seeded = repo["full_name"].lower() in {n.lower() for n in SEEDS[category]}
            item = slim(repo, category, seeded)
            if item["stars"] < (80 if seeded else MIN_STARS[category]) and not seeded:
                continue
            if not relevant(category, item) and not seeded:
                continue
            if not item["description"]:
                continue
            slimmed.append(item)
        # Global dedupe later: a repo kept in the earliest category wins.
        slimmed.sort(key=lambda r: (-r["stars"], r["full_name"].lower()))
        picked = slimmed[: QUOTA[category] + 25]
        selected[category] = picked
        lines.append(f"\n## {category} candidates={len(slimmed)} showing={len(picked)} quota={QUOTA[category]}")
        for i, item in enumerate(picked, 1):
            flag = "SEED" if item["seeded"] else "    "
            arch = " ARCH" if item["archived"] else ""
            desc = item["description"].replace("\n", " ")[:140]
            lines.append(
                f"{i:02d} {flag} {item['stars']:7d}{arch} {item['full_name']} | {desc}"
            )
    report = "\n".join(lines)
    OUT.write_text(report)
    SELECTION.write_text(json.dumps({"candidates": selected, "papers": PAPERS}, indent=2))
    print(report)
    print(f"\nwrote {SELECTION}")


if __name__ == "__main__":
    main()
