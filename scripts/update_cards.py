import datetime, html, json, os, re, time, urllib.request
from google import genai
from google.genai import types

def fetch_text(url):
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        raw = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()[:3000]
    except Exception as e:
        print("略過網址：", url, e)
        return ""

with open("cards.json", "r", encoding="utf-8") as f:
    data = json.load(f)

today = datetime.date.today().isoformat()
pages = [f"【{c['bank']} {c['name']}】\n{t}" for c in data.get("cards", []) if (t := fetch_text(c.get("officialUrl", "")))]
ctx = "\n\n".join(pages) if pages else "無新網頁文字，請保留原資料並更新日期"

prompt = f"""今天是 {today}。請依據以下官網文字核對並更新 cards.json：
1. 保留原本所有欄位結構（id, bank, name, color, rewardType, baseRate, validUntil, officialUrl, owned, notes, rules 及其子欄位）。
2. 有明確新權益就更新，未抓到官網文字的卡片請完整保留原資料。
3. 最外層 updatedAt 改為 "{today}"，只輸出純 JSON。

=== 原 cards.json ===
{json.dumps(data, ensure_ascii=False)}

=== 官網文字 ===
{ctx}"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
resp = None
for m in ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]:
    try:
        print("嘗試模型：", m)
        resp = client.models.generate_content(model=m, contents=prompt, config=cfg)
        print("成功：", m)
        break
    except Exception as e:
        print("暫時失敗：", m, e)
        time.sleep(3)

if resp is None:
    raise RuntimeError("所有備援模型目前忙碌中")

m = re.search(r"\{[\s\S]*\}", resp.text.strip())
updated = json.loads(m.group(0))
assert isinstance(updated.get("cards"), list) and len(updated["cards"]) > 0

with open("cards.json", "w", encoding="utf-8") as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)

print("完成更新", len(updated["cards"]))
