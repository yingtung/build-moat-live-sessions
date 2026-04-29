# QR Code Generator Prototype

## System Requirements

Build a dynamic QR code system where:
- Users submit a long URL and get back a short URL token + QR code image
- The QR code encodes a short URL that redirects (302) to the original URL via your server
- Users can modify the target URL after QR code creation
- Users can delete a QR code (soft delete)
- Users can optionally set an expiration timestamp on create or update
- Deleted or expired links return appropriate HTTP status codes
- URL validation: format check, normalization, malicious URL blocking

## Design Questions

Answer these before you start coding:

1. **Static vs Dynamic QR Code:** Why does this system use dynamic QR codes (encode short URL) instead of static (encode original URL directly)? When would you choose static instead?

    Ans: Since the target URL can be modified, expired or soft-deleted by the user, a dynamic solution is required. If the target URL remains unchanged, a static QR code is sufficient. Static QR codes are also suitable for offline environments where server redirection is unavailable, or for senarios that require extreme reliability.

2. **Token Generation:** How will you generate short URL tokens? What happens when two different URLs produce the same token? How does collision probability change as the number of tokens grows?

    Ans: 
    1. Hash the target url with a nounce (current timestamp) and truncate it to 48 bits to ensure a fixed the length.
    2. Encode the resulting hashed string with Base62.
    3. Check for duplicates in the database.
    4. if a dulplicate exists, retry the process with a new timestamp.
3. **Redirect Strategy:** Why 302 (temporary) instead of 301 (permanent)? What are the trade-offs for analytics, URL modification, and latency?

    Ans:
    1. Browser Caching
        - 301(Moved Permanently): Browsers cache this response permanently. If a user modifies the target URL after the QR code is generated, anyone who previously canned it will be redirected to the old URL stored in their cache, bypassing your server entirely.
        - 302(Found/ Temporary Redirect): This ensures the browser checks with your server on every scan. It allows the system to verify the current target URL and status(e.g., whether it's expired or deleted), which is essential for dynamic QR code.
    2. Analytics & Tracking:
        - 301(Moved Permanently): Since the browser only hits the QR server once and uses the cache thereafter, you lose the ability to track repeat scans. Your analytics will be significantly understated.
        - 302(Found/ Temporary Redirect): Because every scan forces a network request to your server, you have 100% visibility. You can log the timestamp, users agent, IP address, and geolocation for every single interaction, enabling granular analytics.
    3. URL modification:
        - 301(Moved Permanently): Using 301 violates the core requirement of a dynamic system. Once a target URL is cached, the server cannot force the browser to update to the new destination.
        - 302(Found/ Temporary Redirect): The server maintains full control. Each scan hits the QR server first, which then resolves ,the latest mapping and redirects the user to the correct, updated URL.
    4. Latency:
        - 301(Moved Permanently): Offers lower latency for repeat visitors because the redirect happens locally within the browser cache.
        - 302(Found/ Temporary Redirect): Incurs slightly higher latency because every scan requires a round-trip to the QR sesrver before reaching the final destination. However, this is a necessary trade-off for data accuracy and flexibility.

4. **URL Normalization:** What normalization rules do you need? Why is `http://Example.com/` and `https://example.com` potentially the same URL?
    1. Case Insensitivity of the Host: DNS is case-insensitive. Therefore, Example.com and example.com will resolve to the exact same IP address.
    2. Implicit Root Path: If a URL contains no apth components, browsers and HTTP clients implicitly assume the root path `/`. Therefore, example.com and example.com/ are functionally identical.
    3. Practical Protocal Upgrades:In the real world, almost all legitimate web servers running HTTP (port 80) will instantly issue a 301 redirect to their HTTPS (port 443) counterpart to enforce security. Because of this, business logic often strips the protocol or treats http:// and https:// as identical to prevent users from bypassing spam filters simply by changing the scheme.

5. **Error Semantics:** What should happen when someone scans a deleted link vs a non-existent link? Should the HTTP status codes be different?
   - Non-existed link: 404 not found
   - deleted link: 410 Gone
   - expired link: 410 Gone/ 403 Forbidden
   - token blocked: 451 Unavailable

## Verification

Your prototype should pass all of these:

```bash
# Create a QR code
curl -X POST http://localhost:8000/api/qr/create \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# → 200, returns {"token": "...", "short_url": "...", "qr_code_url": "...", "original_url": "..."}

# Redirect
curl -o /dev/null -w "%{http_code}" http://localhost:8000/r/{token}
# → 302

# Get info
curl http://localhost:8000/api/qr/{token}
# → 200, returns token metadata

# Update target URL
curl -X PATCH http://localhost:8000/api/qr/{token} \
  -H "Content-Type: application/json" \
  -d '{"url": "https://new-url.com"}'
# → 200

# Redirect now goes to new URL
curl -o /dev/null -w "%{redirect_url}" http://localhost:8000/r/{token}
# → https://new-url.com

# Delete
curl -X DELETE http://localhost:8000/api/qr/{token}
# → 200

# Redirect after delete
curl -o /dev/null -w "%{http_code}" http://localhost:8000/r/{token}
# → 410

# Non-existent token
curl -o /dev/null -w "%{http_code}" http://localhost:8000/r/INVALID
# → 404

# QR code image
# (create a new one first, then)
curl -o /dev/null -w "%{http_code} %{content_type}" http://localhost:8000/api/qr/{token}/image
# → 200 image/png

# Analytics
curl http://localhost:8000/api/qr/{token}/analytics
# → 200, returns {"token": "...", "total_scans": N, "scans_by_day": [...]}
```

## Suggested Tech Stack

Python + FastAPI recommended, but you may use any language/framework.
