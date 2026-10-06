# HW1-Taiwan-Weather：台灣天氣預報網站

使用 **交通部中央氣象署（CWA）開放資料 API** 製作的台灣天氣預報網站。
使用者可以在網頁上選擇任一縣市，立即查看未來 36 小時的天氣狀況、最低溫、
最高溫與降雨機率。

> 資料集：`F-C0032-001`「一般天氣預報-今明 36 小時天氣預報」

---

## 功能

- 連接 CWA 開放資料 API 取得台灣天氣預報
- 下拉選單可切換全台 **22 個縣市**
- 以 **metric 卡片** 顯示最近時段的天氣狀況、最低溫、最高溫、降雨機率
- 以 **表格** 列出完整三個預報時段（共 36 小時）的明細
- 以 **浮動長條圖** 呈現各時段的氣溫區間（最低溫 ~ 最高溫），以及降雨機率
- 以 **全台縣市地圖** 呈現 22 縣市氣溫：顏色代表最高溫，標籤為「最低~最高」溫度，滑鼠移上去可看天氣與降雨機率
- 一次 API 呼叫取得全部縣市資料，切換縣市不需重新查詢
- 查詢結果快取 10 分鐘，減少不必要的 API 呼叫
- 完整的錯誤處理：金鑰未設定、金鑰錯誤、連線逾時、欄位缺漏都會顯示友善訊息
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
├── app.py                        # Streamlit 使用者介面
├── src/
│   ├── __init__.py
│   └── cwa_api.py                # CWA API 呼叫與資料解析（與 UI 分離）
├── tests/
│   ├── sample_response.json      # 測試用的 API 回應範例
│   └── test_cwa_api.py           # 解析邏輯的測試
├── .streamlit/
│   └── secrets.toml.example      # Streamlit secrets 範本
├── .env.example                  # 環境變數範本
├── requirements.txt
├── .gitignore
└── README.md
```

程式刻意分成兩層：

- `src/cwa_api.py`：只負責呼叫 API、處理錯誤、把 JSON 整理成 `ForecastPeriod` 物件。
- `app.py`：只負責畫面呈現，不直接處理 JSON。

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

解析邏輯使用 `tests/sample_response.json` 當作假資料，不需要 API 金鑰也能測試：

```bash
python3 tests/test_cwa_api.py
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
