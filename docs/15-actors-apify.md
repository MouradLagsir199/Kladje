# Apify Actor Reference — Social Media Extraction

Documentation of Apify actors used to retrieve video transcripts and metadata from
social platforms. Pinterest is the exception: it resolves a Pin to its destination
URL rather than extracting content.

## Authentication

```bash
export APIFY_API_TOKEN="apify_api_..."
```

```python
import os
from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_API_TOKEN"])
```

---

## TikTok

- **Actor ID:** `509El6cODefVZLx2W`
- **Approx cost:** ~$0.001 per video
- **Approx runtime:** ~8–9 sec

### Input

```python
run_input = {
    "videoUrl": "https://www.tiktok.com/t/ZP8gXqkBM/"
}
run = client.actor("509El6cODefVZLx2W").call(run_input=run_input)
```

### Output shape (per item)

Top-level fields: `url`, `title`, `createTime`, `playCount`, `commentCount`,
`diggCount`, `shareCount`, `collectCount`, `duration`, `nickname`, `avatarUri`,
`signature`, `secUid`, `followerCount`, `followingCount`, `heartCount`, `text`,
`segments` (list of `{start, end, text}`), `errMsg`, `videoUrl`, `timestamp`.

- Title/caption: `title`
- Transcript: `text` (full text), `segments` (timestamped)

---

## Instagram

- **Actor ID:** `S9A11NvceWaGorwwh`
- **Approx cost:** ~$0.006 per video
- **Approx runtime:** ~4 sec

### Input

```python
run_input = {
    "videoUrl": "https://www.instagram.com/p/DULBkEngpxg",
    "bulkUrls": [],
    "usernames": ["bbcnews"],
    "resultsLimit": 12,
    "onlyPostsNewerThan": None,
    "skipPinnedPosts": False,
    "includeSharesCount": False,
}
run = client.actor("S9A11NvceWaGorwwh").call(run_input=run_input)
```

Supports either a single `videoUrl`, a `bulkUrls` list, or `usernames` (to pull a
user's recent posts, bounded by `resultsLimit`).

### Output shape (per item)

`url`, `code`, `pk`, `id`, `title`, `img`, `videoUrl`, `audioUrl`, `duration`,
`createTime`, `likeCount`, `commentCount`, `userPk`, `userName`, `userFullName`,
`avatarUri`, `text`, `segments` (list of `{start, end, text}`), `errMsg`, `timestamp`.

- Title/caption: `title`
- Transcript: `text` (full text), `segments` (timestamped)

---

## YouTube

- **Actor ID:** `yPVke6lPnfMmRZUX6`
- **Approx cost:** ~$0.024 for an 8-minute video
- **Approx runtime:** ~38 sec for an 8-minute video

### Input (Node.js client)

```javascript
const input = {
    "youtubeUrl": [
        { "url": "https://www.youtube.com/watch?v=hz9tSv3CP6k" }
    ],
    "transcriptOnly": false,
    "extractcomments": false,
    "sortBy": "top",
    "maxComments": 10,
    "maxRepliesPerComment": 0
};
const run = await client.actor("yPVke6lPnfMmRZUX6").call(input);
```

Accepts multiple URL formats in the same `youtubeUrl` array: `watch?v=`, `youtu.be/`,
and `/live/`. Set `transcriptOnly: true` to skip metadata/comments if only the
transcript is needed (cheaper/faster).

### Output shape (per item)

`thumbnail`, `VideoURL`, `Video_title`, `published_Date`, `Views`, `likes`,
`Description`, `transcriptText`, `timestamps` (list of `{time, text}` — `time` as
`"m:ss"` string, not seconds), `channel` (`{name, id, url, subscribers, verified}`),
`videoId`, `embedUrl`, `hasTranscript`, `commentsExtracted`, `commentCount`,
`comments`.

- Title/caption: `Video_title` (title), `Description` (caption/description text)
- Transcript: `transcriptText` (full text), `timestamps` (timestamped, `"m:ss"` string)

---

## Pinterest

Different in kind from the three above: Pinterest is not a transcript source. A Pin is a *pointer*
to a real recipe page, and that page is a far better source than the Pin (see `docs/03`, Stage 0).
So this actor is used for one thing only — resolving a Pin to its **destination URL**, which is then
fed back through URL normalisation and handled as a blog.

- **Actor ID:** `tseqJicQpIxyFdHNB`
- **Approx cost:** not yet measured — **measure on the first real run before enabling this path.**
  It uses residential proxy, which is the expensive tier, and unlike the others it buys us a URL
  rather than content
- **Approx runtime:** not yet measured

### Input

The published example scrapes a search page for up to 50 000 pins. That is the wrong shape for us
entirely — we resolve a single Pin:

```python
run_input = {
    "startUrls": ["https://www.pinterest.com/pin/123456789012345678/"],
    "type": "all-pins",
    "limit": 1,
    "sentinent_analysis": False,
    "content_analysis": False,
    "proxyConfiguration": {
        "useApifyProxy": True,
        "apifyProxyGroups": ["RESIDENTIAL"],
    },
}
run = client.actor("tseqJicQpIxyFdHNB").call(run_input=run_input)
```

- **`limit` must be 1.** The example's `50000` is a search-scraping default; copying it into a
  per-import call would be a runaway cost bug, not a slow request
- `sentinent_analysis` (sic — the typo is in the actor's own input schema, don't "fix" it) and
  `content_analysis` stay `False`. Both are extra spend for output we don't use
- Residential proxy is required: Pinterest blocks datacenter IPs

### Output shape (per item)

**Unverified.** Every other entry in this file documents a shape observed from a real run; this one
has not been run yet. Capture a raw payload into `api/tests/fixtures/apify/` the same way task M6
does for the other platforms, then fill this in — do not code against a guessed field name.

What we need from it is the outbound destination link of the Pin (plus the Pin's own image URL as a
fallback thumbnail). Confirm what that field is actually called before wiring it up.

### Key fields for Kladje

| Field | Purpose |
|---|---|
| destination/outbound URL (name TBC) | Re-normalised via `services/url_norm.py`, then imported as a blog |
| image URL (name TBC) | Fallback thumbnail if the destination page has none |

### Notes

- A Pin with no outbound destination (image-only, or one pointing at another Pin) has no better
  source than itself. Treat that as a normal failure with its own copy in the taxonomy, not as an
  error — the user pasted something we genuinely cannot import
- This is a **paid call**, so it sits behind the same server-side quota check as every other paid
  call (non-negotiable 7). It also means a Pinterest import costs strictly more than the same recipe
  pasted as a blog URL: pin resolution *plus* synthesis
- Not wired up yet. `services/url_norm.py` currently normalises `pin.it/{code}` and
  `pinterest.com/pin/{id}` to a canonical Pin URL and stops there

---

## Cross-platform field mapping

| Field | TikTok | Instagram | YouTube |
|---|---|---|---|
| `source_url` | `url` | `url` | `VideoURL` |
| `caption_text` | `title` | `title` | `Description` |
| `transcript_text` | `text` | `text` | `transcriptText` |
| `transcript_segments` | `segments` (start/end in sec, float) | `segments` (start/end in sec, float) | `timestamps` (time as `"m:ss"` string) |
| `creator_name` | `nickname` | `userName` | `channel.name` |
| `video_url` | `videoUrl` | `videoUrl` | `VideoURL` |

---

## Platform Template (copy this for new platforms)

## <Platform Name>

- **Actor ID:** ``
- **Approx cost:** 
- **Approx runtime:** 

### Input

```
run_input = {

}
```

### Output shape (per item)

### Key fields for Kladje

| Field | Purpose |
|---|---|

### Notes
