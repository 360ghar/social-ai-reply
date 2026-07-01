from ddgs import DDGS

try:
    results = DDGS().text('site:reddit.com/r "real estate"', max_results=5)
    for r in results:
        print(f"Title: {r['title']}\nURL: {r['href']}\nBody: {r['body']}\n")
except Exception as e:
    print("Error:", e)
