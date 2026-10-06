# HW1-Taiwan-Weather：台灣天氣預報網站

使用 **交通部中央氣象署（CWA）開放資料 API** 製作的台灣天氣預報網站。
使用者可以在網頁上選擇任一縣市，立即查看未來 36 小時的天氣狀況、最低溫、
最高溫與降雨機率。

> 資料集：`F-C0032-001`「一般天氣預報-今明 36 小時天氣預報」、`W-C0033-001`「天氣特報-各別縣市地區目前之天氣警特報情形」

---

## 功能

- 連接 CWA 開放資料 API，一次取得全台 **22 縣市** 的 36 小時預報
- 頁首選單切換縣市，切換時不需重新呼叫 API（資料快取 10 分鐘）
- **主卡片**：所選縣市目前時段的天氣狀況、最低溫、最高溫、降雨機率與體感，底色與圖示隨天氣變化
- **天氣特報橫幅**：所選縣市有大雨、強風、颱風等特報時，頁面上方顯示醒目提示（警報與豪雨、颱風以紅色顯示）；地圖上以橘色虛線框標出有特報的縣市
- **出門建議**：把預報翻譯成口語提醒，例如「記得帶傘：今晚降雨機率 70%」「早晚溫差大：相差 9 度，建議洋蔥式穿搭」，並依特報給出對應建議（規則見 `src/advice.py`）
- **未來 36 小時**：三個時段以「今天白天／今晚／明天白天」等口語名稱並排顯示
- **趨勢圖**：氣溫以浮動長條呈現「最低溫～最高溫」區間，另有降雨機率長條圖
- **完整預報表格**：放在可展開區塊中
- **全台概況**：縣市地圖依最高溫上色並標示各縣市溫度；旁邊為北、中、南、東四區平均溫度卡片（依國發會區域劃分，金門、連江為離島不列入）
- 自訂佈景主題（Noto Sans TC 字型、線條天氣圖示），手機版面自動改為單欄
- 完整錯誤處理：金鑰未設定、金鑰錯誤、連線逾時、欄位缺漏都會顯示友善訊息
- API 金鑰一律從環境變數或 Streamlit secrets 讀取，**不寫在原始碼中**

## 技術

| 項目 | 使用工具 |
| --- | --- |
| 程式語言 | Python 3.9+ |
| 網頁框架 | Streamlit |
| HTTP 請求 | requests |
| 資料處理 | pandas |
| 圖表與地圖 | Altair（Streamlit 內建） |
| 資料來源 | CWA 氣象開放資料平臺 API |
| 縣市邊界 | [taiwan-atlas](https://github.com/dkaoster/taiwan-atlas)（TopoJSON，經 jsDelivr CDN 載入） |
| 版本控制 | Git / GitHub |

## 專案結構

```
HW1-Taiwan-Weather/
├── app.py                        # 頁面流程：要顯示哪些區塊、放在哪裡
├── src/
│   ├── __init__.py
│   ├── cwa_api.py                # CWA API 呼叫、預報與特報解析、區域平均（不含 UI）
│   ├── advice.py                 # 出門建議的判斷規則（不含 UI）
│   └── ui.py                     # 外觀：CSS、天氣圖示、自訂 HTML 卡片
├── tests/
│   ├── sample_response.json      # 預報 API 回應範例
│   ├── sample_hazards.json       # 特報 API 回應範例
│   ├── test_cwa_api.py           # 預報解析的測試
│   └── test_hazards_advice.py    # 特報解析與出門建議規則的測試
├── .streamlit/
│   ├── config.toml               # 佈景主題（顏色、字型），可上傳
│   └── secrets.toml.example      # Streamlit secrets 範本
├── .env.example                  # 環境變數範本
├── requirements.txt
├── .gitignore
└── README.md
```

程式分成三層：

- `src/cwa_api.py`：只負責呼叫 API、處理錯誤、把 JSON 整理成 `ForecastPeriod` / `Hazard` 物件，以及計算區域平均。
- `src/advice.py`：出門建議的規則，門檻值集中在檔案開頭，方便調整。
- `src/ui.py`：只負責外觀，把資料轉成 HTML 卡片與樣式。
- `app.py`：決定頁面上有哪些區塊與排列方式，不直接處理 JSON。

這樣解析邏輯可以單獨測試（見 `tests/`），不需要啟動 Streamlit。

---

## 安裝

```bash
# 1. 取得專案
git clone https://github.com/<你的帳號>/HW1-Taiwan-Weather.git
cd HW1-Taiwan-Weather

# 2. 建立並啟動虛擬環境
python3 -m venv venv
source venv/bin/activate          # Windows：venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt
```

## 如何申請 CWA API 金鑰

1. 前往 [氣象開放資料平臺](https://opendata.cwa.gov.tw/)。
2. 點右上角「登入/註冊」，以 Email 註冊會員並完成信箱驗證（免費）。
3. 登入後進入「[取得授權碼](https://opendata.cwa.gov.tw/user/authkey)」頁面。
4. 複製畫面上的授權碼，格式類似 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`。

## 如何設定 API 金鑰

**金鑰不可寫在 Python 程式碼裡**，請任選以下一種方式（程式會依序尋找）：

### 方式 1：環境變數

```bash
export CWA_API_KEY="CWA-你的金鑰"       # Windows PowerShell：$env:CWA_API_KEY="CWA-你的金鑰"
```

### 方式 2：`.env` 檔（建議，開發最方便）

```bash
cp .env.example .env
```

編輯 `.env`：

```
CWA_API_KEY=CWA-你的金鑰
```

### 方式 3：Streamlit secrets（部署到 Streamlit Community Cloud 時使用）

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

編輯 `.streamlit/secrets.toml`：

```toml
CWA_API_KEY = "CWA-你的金鑰"
```

`.env` 與 `.streamlit/secrets.toml` 都已寫在 `.gitignore` 中，不會被上傳到 GitHub。

## 執行

```bash
streamlit run app.py
```

瀏覽器會自動開啟 <http://localhost:8501>。若沒有自動開啟，手動輸入該網址即可。

## 執行測試

測試使用 `tests/` 裡的範例回應當作假資料，不需要 API 金鑰也能執行：

```bash
python3 tests/test_cwa_api.py
python3 tests/test_hazards_advice.py
```

---

## 上傳到 GitHub

先在 GitHub 建立一個名為 `HW1-Taiwan-Weather` 的空白儲存庫（不要勾選 README），再執行：

```bash
git init
git add .
git commit -m "HW1: Taiwan CWA weather forecast website"
git branch -M main
git remote add origin https://github.com/<你的帳號>/HW1-Taiwan-Weather.git
git push -u origin main
```

之後要更新：

```bash
git add .
git commit -m "Update: 說明這次修改了什麼"
git push
```

> 推送前請確認 `git status` 中 **沒有** `.env` 或 `.streamlit/secrets.toml`，
> 避免把 API 金鑰上傳到公開儲存庫。

## 疑難排解

| 畫面訊息 | 原因與處理方式 |
| --- | --- |
| 找不到 CWA API 金鑰 | 尚未設定 `CWA_API_KEY`，請參考「如何設定 API 金鑰」 |
| API 金鑰無效或已失效（HTTP 401） | 金鑰打錯或已重新產生，請到授權碼頁面重新複製 |
| 連線 CWA API 逾時 | 網路不通或 CWA 服務忙碌，稍後按「重新取得資料」再試 |
| 查不到某縣市的預報資料 | CWA 使用「臺」而非「台」，程式已自動轉換；若仍無資料代表該時段 API 尚未提供 |

## 授權與資料來源

天氣資料由 **交通部中央氣象署** 提供，依
[政府資料開放授權條款](https://data.gov.tw/license) 使用。
本專案為大學課程作業，僅供學習用途。
