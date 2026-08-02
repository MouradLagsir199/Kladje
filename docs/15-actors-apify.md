# Apify Actor Reference — Social Media Transcript Extraction

Documentation of Apify actors used to retrieve video transcripts and metadata from
social platforms.

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
