with open("app/services/infrastructure/platforms/native_multi.py", "r") as f:
    code = f.read()

if "query_encoded =" not in code:
    code = code.replace(
        'query = " OR ".join(keywords)\n        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage={limit}"',
        'query = " OR ".join(keywords)\n        import urllib.parse\n        query_encoded = urllib.parse.quote_plus(query)\n        url = f"https://hn.algolia.com/api/v1/search_by_date?query={query_encoded}&tags=story&hitsPerPage={limit}"'
    )
    code = code.replace(
        'query = " ".join(keywords) + " is:issue"\n        url = f"https://api.github.com/search/issues?q={query}&per_page={limit}&sort=created"',
        'query = " ".join(keywords) + " is:issue"\n        import urllib.parse\n        query_encoded = urllib.parse.quote_plus(query)\n        url = f"https://api.github.com/search/issues?q={query_encoded}&per_page={limit}&sort=created"'
    )
    with open("app/services/infrastructure/platforms/native_multi.py", "w") as f:
        f.write(code)
    print("Patched HN and GitHub")
else:
    print("Already patched")
