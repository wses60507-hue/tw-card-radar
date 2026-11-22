import datetime
import html
import json
import os
import re
import time
import urllib.request
from google import genai
from google.genai import types


def fetch_page_text(url, max_chars=3500):
    if not url:
        return ""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        raw = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw)
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print(f"略過抓取 {url}: {e}")
        return ""


with open("cards.json", "r", encoding="utf-8") as f:
    current_data = json.load(f)

today = datetime.date.today().isoformat()
snippets = []
for c in current_data.get("cards", []):
    page_text = fetch_page_text(c.get("officialUrl", ""))
    if page_text:
        snippets.append(f"【{c['bank']} {c['name']} 官網最新文字】\n{page_text}")

fetched_context = (
    "\n\n".join(snippets)
    if snippets
    else "（本次未抓到新網頁文字，請保留原資料並更新日期）"
)

prompt = f"""今天是 {today}。請根據以下即時抓取到的台灣各銀行信用卡官網文字，核對並更新原本的 cards.json。
規則：
1. 嚴格保留原本 JSON 結構與所有欄位名稱（id, bank, name, color, rewardType, baseRate, validUntil, officialUrl, owned, notes, rules 及其 tierKey/tierRate/tierOffRate/holidayOnly/excludeKeywords）。
2. 若官網文字中有明確出現更新後的回饋率、活動到期日(validUntil)、上限或條件，請更新對應欄位；若某張卡未抓到官網文字或官網未提及變動，請完整保留該張卡原本的資料不要刪減。
3. 將最外層 updatedAt 更新為 "{today}"，只輸出純 JSON。

=== 原本 cards.json ===
{json.dumps(current_data, ensure_ascii=False)}

=== 即時抓取的銀行官網文字 ===
{fetched_context}
"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
resp = None
for model_name in [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]:
    try:
        print(f"嘗試使用模型：{model_name}")
        resp = client.models.generate_content(
