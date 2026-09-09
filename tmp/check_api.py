import json, sys
d = json.load(sys.stdin)
for path, methods in d["paths"].items():
    for m in ["post", "patch"]:
        if m in methods:
            body = methods[m].get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            reqd = body.get("required", [])
            if reqd:
                print(f"{m.upper()} {path}: required={reqd}")
