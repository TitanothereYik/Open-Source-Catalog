# Open Source Catalog

九個方向嘅開源項目同相關論文，用深色頁面瀏覽。開源項目按 GitHub stars 由多至少排列。而家最前三頁聚焦 Gaussian Splatting、World Model 同 Image to 3D。

分類次序：

1. Gaussian Splatting
2. World Model
3. Image to 3D
4. AI Agent
5. 圖像
6. 影片
7. VFX / CG / Blender
8. Stock Trading
9. Crypto Trading

第一版收錄 200 個開源項目，之後再加入 Gaussian Splatting、World Model 同 Image to 3D。每個項目有大約一百字嘅中文說明。已經收錄嘅 repo 唔會再加入。之後每小時檢查一次，只加入未見過、而且符合分類嘅新項目，同時更新 stars 同最近推送。

## 本地瀏覽

```bash
python3 -m http.server 43123
```

然後開 [http://127.0.0.1:43123](http://127.0.0.1:43123)。

根目錄 `index.html` 係九個分類嘅入口，每個分類係獨立一頁，例如 `gaussian-splatting/`、`world-model/`、`image-to-3d/`。搜尋可以喺目錄頁搵全部項目，或者喺分類頁入面篩選。

## 更新

```bash
python3 scripts/catalog_tool.py update
```

`bootstrap` 只用嚟由 `data/allowlist.json` 同 `data/summaries.json` 重建第一版。日常更新唔好加 `--force`，否則會覆蓋而家嘅目錄。

檢查：

```bash
python3 scripts/catalog_tool.py validate
```

## GitHub

公開網站同每小時更新都放喺 [TitanothereYik/Open-Source-Catalog](https://github.com/TitanothereYik/Open-Source-Catalog)，唔係 Cursor 嘅 codebase。頁面標題係 **Open Source Catalog**。Repo 要公開，免費 GitHub Pages 先用到。

網站網址：

```text
https://titanothereyik.github.io/Open-Source-Catalog/
```

根目錄 `index.html` 就係 Pages 嘅內容。推上 GitHub `main` 之後，`.github/workflows/pages.yml` 會部署。每小時嘅更新根網址固定係上面呢個 GitHub Pages 網址，寫入目錄、canonical 同電郵連結，然後 push 去呢個 repo 嘅 `main`。

## 每小時

`.github/workflows/update.yml` 喺每小時整點運行（UTC 同香港時間都係 xx:00）。每次會讀取 workflow token 嘅 GitHub REST core 配額，並繼續查公開 repo，直到用咗最少 80%。搜尋配額係另一個每分鐘上限，程式會自己放慢，避免搜尋被截斷。

每次完成會：

- 更新 `index.html` 同九個分類子目錄
- commit 並 push 去 `main`，Pages 會跟住更新
- 喺 issue「Open Source Catalog updates」留一則通知
- 如果設定咗 SMTP，寄出 `email/latest.html`

電郵收件人預設係帳號電郵。可以喺 repository secret 用 `NOTIFY_EMAIL` 覆蓋。

要真係寄出精美 HTML 電郵，請喺 repository secrets 加上：

| Secret | 例子 |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com`（可選，預設就係呢個） |
| `SMTP_PORT` | `587`（可選） |
| `SMTP_USERNAME` | 你嘅電郵 |
| `SMTP_PASSWORD` | 電郵供應商嘅 app password |
| `NOTIFY_EMAIL` | 收件地址（可選） |

Gmail 要用 app password，唔係平時登入密碼。未設定 SMTP 時，電郵 HTML 仍然會寫入 `email/latest.html`，GitHub issue 通知會照常建立。
