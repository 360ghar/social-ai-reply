from ddgs import DDGS

sites = {
    "reddit": "site:reddit.com/r",
    "linkedin": "site:linkedin.com/posts",
    "instagram": "site:instagram.com/p",
    "indiehackers": "site:indiehackers.com",
    "hackernews": "site:news.ycombinator.com",
    "github": "site:github.com"
}

keyword = "flipkart"

for name, site in sites.items():
    print(f"\n--- {name.upper()} ---")
    try:
        results = list(DDGS().text(f'{site} "{keyword}"', max_results=10))
        print(f"Found {len(results)} results")
        for r in results[:2]:
            print(f"- {r['title']} ({r['href']})")
    except Exception as e:
        print(f"Error: {e}")
