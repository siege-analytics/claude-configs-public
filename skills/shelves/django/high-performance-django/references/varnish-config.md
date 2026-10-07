# Varnish Configuration Reference

Extracted from High Performance Django, Chapter 3 (The Deployment).
Varnish 4.x syntax. Update version-specific syntax for current releases.

## Backend definition

```vcl
backend mysite {
    .host = "127.0.0.1";
    .port = "8080";
}
```

Multiple backends load-balanced using directors.

## vcl_recv -- request routing

Cache based on URL + Vary headers. Bypass cache for authenticated users,
strip cookies for anonymous:

```vcl
sub vcl_recv {
    if (req.http.cookie ~ "sessionid") {
        return (pass);
    } else {
        unset req.http.Cookie;
    }
    return (hash);
}
```

### Cache bypass for debugging

```vcl
if (req.url ~ "(\\?|&)flush-the-cache") {
    return(pass);
}
```

### Drop requests for non-existent static files

```vcl
if (req.method == "GET" &&
    req.url ~ "\\.(jpg|jpeg|png|gif|ico|js|css)$") {
    return (synth(404, "Not Found"));
}
```

## Personalized content strategies

**AJAX approach:** cache the anonymized page, fetch personalized bits
via a second AJAX request. Faster initial page load, delayed
personalization.

**ESI (Edge Side Includes):** Varnish assembles pages from personalized
content blocks. More complex but avoids the visible delay of AJAX.

## Grace periods -- serve stale content during outages

```vcl
vcl 4.0;
import std;

backend default {
    .host = "127.0.0.1";
    .port = "8080";
    .probe = {
        .url = "/";
        .interval = 5s;
        .timeout = 1s;
        .window = 5;
        .threshold = 3;
    }
}

sub vcl_hit {
    if (obj.ttl >= 0s) {
        return (deliver);
    }
    if (!std.healthy(req.backend_hint) ||
        (obj.ttl + obj.grace > 0s)) {
        return (deliver);
    }
    return (fetch);
}

sub vcl_backend_response {
    set beresp.grace = 6h;
    set beresp.ttl = 20s;
    return (deliver);
}
```

Backend health probes: every 5 seconds, 3 of 5 failures marks unhealthy.

## Custom error page

```vcl
sub vcl_backend_error {
    set beresp.http.Content-Type = "text/html; charset=utf-8";
    synthetic(std.fileread("/var/www/error.html"));
    return(deliver);
}
```

Generate from Django template:

```python
from django.core.management.base import BaseCommand
from django.shortcuts import render
from django.test import RequestFactory

class Command(BaseCommand):
    help = "Generate HTML for 500 page"
    def handle(self, *args, **options):
        request = RequestFactory().get('/')
        print(render(request, '500.html').content)
```

Run: `manage.py generate_500_html > /var/www/error.html`

## Redirects in Varnish

```vcl
sub vcl_recv {
    if (req.method == "GET" &&
        req.http.host == "example.com") {
        return (synth(801, "http://www.example.com" + req.url));
    }
    return (hash);
}

sub vcl_synth {
    if (resp.status == 801) {
        set resp.http.Content-Type = "text/html; charset=utf-8";
        set resp.http.Location = resp.reason;
        set resp.status = 301;
    }
    return (deliver);
}
```

Use 802 for temporary 302 redirects.

## Cache purging

```vcl
acl purge {
    "127.0.0.1";
}

sub vcl_recv {
    if (req.method == "PURGE") {
        if (!client.ip ~ purge) {
            return(synth(405, "Not allowed."));
        }
        return (purge);
    }
}
```

Execute: `curl -I -XPURGE http://localhost:6081/`

**Security:** strictly limit ACL addresses. Unrestricted PURGE enables
DDoS via cache flushing.
