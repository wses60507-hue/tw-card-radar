import datetime, json, os, re
from google import genai
from google.genai import types

with open("cards.json", "r", encoding="utf-8") as f:
    current_data = json.load(f)

today = datetime.date.today().isoformat()
card_list = "、".join(f"{c['bank']}{c['name']}" for c in current_data.get("cards", []))

prompt = f"""今天是 {today}。請使用 Google 搜尋查詢台灣以下信用卡最新的官方回饋權益：{card_list}。
請嚴格依照原本 JSON 的結構與欄位名稱更新（保留原 id、bank、name、color、tierKey 等欄位，只更新最新回饋率 rate、加碼上限 bonusCap、活動到期日 validUntil、條件 condition、通路關鍵字 keywords 與官方網址 officialUrl）。
只輸出純 JSON 物件（包含 version、updatedAt: "{today}"、cards 陣列），不要任何多餘文字或說明。
原本 JSON 參考：
{json.dumps(current_data, ensure_ascii=False)}"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
resp = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    ),
)

text = resp.text.strip()
match = re.search(r"\{[\s\S]*\}", text)
if not match:
    raise ValueError("無法從回應解析 JSON")
updated = json.loads(match.group(0))
assert isinstance(updated.get("cards"), list) and len(updated["cards"]) > 0

with open("cards.json", "w", encoding="utf-8") as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)
print(f"已更新 {len(updated['cards'])} 張信用卡權益 ({today})")
